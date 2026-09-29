"""Persist crawler output (list[ScrapedProduct]) into the products table.

The only store module that touches the database. `products.url` is unique on its own, so rows are
matched by url: same source -> updated, another source -> reported as a conflict and left alone.
Every inserted or updated product is re-tagged (tagger.py, rule-based) in the same transaction.

Catalog history: a product is inserted with first_seen_at (never rewritten); one seen again is (re)activated. Given a
CrawlReport, active products of the source that the listings no longer return are marked inactive with dropped_at, but
only if the crawl was complete and the listing did not shrink suspiciously (see `sync`). Their seen_at is left alone.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from collections import Counter

from sqlalchemy import func, null, select
from sqlalchemy.orm import Session

from app.collectors.base import get_or_create_source
from app.collectors.stores.config import ScraperConfig
from app.collectors.stores.schemas import CrawlReport, ScrapedProduct, utcnow
from app.collectors.stores.tagger import RULES_VERSION, tag_product
from app.models import Product, ProductTag, Source

log = logging.getLogger(__name__)
CHUNK = 500  # urls per IN (...) lookup
MIN_LISTED_SHARE = 0.7  # a crawl listing fewer than this share of the store's active products drops nothing


@dataclass
class SyncResult:
    inserted: int = 0
    updated: int = 0
    conflicts: int = 0
    reactivated: int = 0  # dropped products that are back on the shelf
    dropped: int = 0  # active products the listings no longer return
    drop_skipped: str | None = None  # why nothing was dropped although a report was given (incomplete, shrunk)


class StoreSyncService:
    def __init__(self, session: Session):
        self.session = session

    def source_for(self, cfg: ScraperConfig) -> Source:
        return get_or_create_source(
            self.session, name=cfg.name, kind="store", url=str(cfg.base_url), lang=cfg.lang, country=cfg.country
        )

    def sync(self, source_id: int, products: list[ScrapedProduct], report: CrawlReport | None = None,
             accept_drops: bool = False) -> SyncResult:
        """Upsert by url in one transaction. In-batch duplicates: the last one wins.

        With a CrawlReport, active products of this source that neither the batch nor `report.listed` contain are
        dropped (is_active False, dropped_at = the crawl's time). Never when the report is incomplete, and never when
        the listing holds under MIN_LISTED_SHARE of the previously active products (a layout change or a bot page,
        not a catalog cull); `accept_drops` waives that second guard only. Without a report nothing is dropped."""
        latest = {p.db_url(): p for p in products}
        urls = list(latest)
        active_before = {row.url: row for row in self.session.scalars(
            select(Product).where(Product.source_id == source_id, Product.is_active.is_(True)))}
        existing: dict[str, Product] = {}
        for i in range(0, len(urls), CHUNK):
            existing |= {row.url: row for row in self.session.scalars(select(Product).where(Product.url.in_(urls[i : i + CHUNK])))}

        result = SyncResult()
        for url, p in latest.items():
            # null(): SQL NULL for no flags; a plain None would be stored as the JSON text 'null'
            values = dict(name=p.name, brand=p.brand, price=p.price, list_price=p.list_price, currency=p.currency, rank=p.rank,
                          flags=p.flags or null(), image_url=p.db_image_url(), seen_at=p.seen_at)
            row = existing.get(url)
            if row is None:
                row = Product(source_id=source_id, url=url, first_seen_at=p.seen_at, **values)
                self.session.add(row)
                result.inserted += 1
            elif row.source_id == source_id:
                for key, value in values.items():
                    setattr(row, key, value)
                if not row.is_active:
                    row.is_active, row.dropped_at = True, None
                    result.reactivated += 1
                result.updated += 1
            else:
                log.warning("Product %s belongs to source %s, not %s: skipped", url, row.source_id, source_id)
                result.conflicts += 1
                continue
            self._apply_tags(row, p.name, p.flags)
        if report is not None:
            self._drop_missing(result, active_before, set(latest) | report.listed, report, accept_drops,
                               when=max((p.seen_at for p in products), default=None) or utcnow())
        self.session.commit()
        return result

    @staticmethod
    def _drop_missing(result: SyncResult, active_before: dict[str, Product], present: set[str], report: CrawlReport,
                      accept_drops: bool, when) -> None:
        if not report.complete:
            more = f" (+{len(report.problems) - 1} more)" if len(report.problems) > 1 else ""
            result.drop_skipped = f"incomplete crawl: {report.problems[0]}{more}"
        elif not accept_drops and active_before and len(present) / len(active_before) < MIN_LISTED_SHARE:
            result.drop_skipped = f"listing shrank {len(active_before)} -> {len(present)}"
        else:
            for url, row in active_before.items():
                if url not in present:
                    row.is_active, row.dropped_at = False, when
                    result.dropped += 1

    def _apply_tags(self, row: Product, name: str, flags: dict | None) -> None:
        """Make row.tags equal the tagger's output. Diffed, not replaced: a delete + re-insert of the same
        (dimension, code) in one flush would hit the unique constraint (SQLAlchemy inserts first)."""
        wanted = {(t.dimension, t.code, t.supplier_code): t for t in tag_product(name, flags)}
        current = {(t.dimension, t.code, t.supplier_code): t for t in row.tags}
        for key, tag in current.items():
            if key not in wanted:
                row.tags.remove(tag)  # delete-orphan
        for key, t in wanted.items():
            if key in current:
                cur = current[key]
                cur.field, cur.term, cur.rules_version = t.field, t.term, RULES_VERSION
                cur.color_family, cur.color_hex = t.color_family, t.color_hex
            else:
                row.tags.append(ProductTag(dimension=t.dimension, code=t.code, field=t.field, term=t.term,
                                           rules_version=RULES_VERSION, color_family=t.color_family,
                                           color_hex=t.color_hex, supplier_code=t.supplier_code))

    def retag_all(self, source_id: int | None = None) -> int:
        """Re-run the tagger over stored products (after a rules or taxonomy change). Idempotent, no network."""
        q = select(Product).order_by(Product.id)
        if source_id is not None:
            q = q.where(Product.source_id == source_id)
        n = 0
        for row in self.session.scalars(q):
            self._apply_tags(row, row.name, row.flags)
            n += 1
        self.session.commit()
        return n

    def tag_counts(self, source_id: int | None = None) -> dict[str, int]:
        """Tagged products per dimension, e.g. {"material": 55, "product_type": 222}."""
        q = select(ProductTag.dimension, func.count(func.distinct(ProductTag.product_id))).group_by(ProductTag.dimension)
        if source_id is not None:
            q = q.join(Product, Product.id == ProductTag.product_id).where(Product.source_id == source_id)
        return dict(Counter(dict(self.session.execute(q).all())).most_common())
