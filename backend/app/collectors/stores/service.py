"""Persist crawler output (list[ScrapedProduct]) into the products table.

The only store module that touches the database. `products.url` is unique on its own, so rows are
matched by url: same source -> updated, another source -> reported as a conflict and left alone.
Every inserted or updated product is re-tagged (tagger.py, rule-based) in the same transaction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from collections import Counter

from sqlalchemy import func, null, select
from sqlalchemy.orm import Session

from app.collectors.base import get_or_create_source
from app.collectors.stores.config import ScraperConfig
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import RULES_VERSION, tag_product
from app.models import Product, ProductTag, Source

log = logging.getLogger(__name__)
CHUNK = 500  # urls per IN (...) lookup


@dataclass
class SyncResult:
    inserted: int = 0
    updated: int = 0
    conflicts: int = 0


class StoreSyncService:
    def __init__(self, session: Session):
        self.session = session

    def source_for(self, cfg: ScraperConfig) -> Source:
        return get_or_create_source(
            self.session, name=cfg.name, kind="store", url=str(cfg.base_url), lang=cfg.lang, country=cfg.country
        )

    def sync(self, source_id: int, products: list[ScrapedProduct]) -> SyncResult:
        """Upsert by url in one transaction. In-batch duplicates: the last one wins."""
        latest = {p.db_url(): p for p in products}
        urls = list(latest)
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
                row = Product(source_id=source_id, url=url, **values)
                self.session.add(row)
                result.inserted += 1
            elif row.source_id == source_id:
                for key, value in values.items():
                    setattr(row, key, value)
                result.updated += 1
            else:
                log.warning("Product %s belongs to source %s, not %s: skipped", url, row.source_id, source_id)
                result.conflicts += 1
                continue
            self._apply_tags(row, p.name, p.flags)
        self.session.commit()
        return result

    def _apply_tags(self, row: Product, name: str, flags: dict | None) -> None:
        """Make row.tags equal the tagger's output. Diffed, not replaced: a delete + re-insert of the same
        (dimension, code) in one flush would hit the unique constraint (SQLAlchemy inserts first)."""
        wanted = {(t.dimension, t.code): t for t in tag_product(name, flags)}
        current = {(t.dimension, t.code): t for t in row.tags}
        for key, tag in current.items():
            if key not in wanted:
                row.tags.remove(tag)  # delete-orphan
        for key, t in wanted.items():
            if key in current:
                current[key].field, current[key].term, current[key].rules_version = t.field, t.term, RULES_VERSION
            else:
                row.tags.append(ProductTag(dimension=t.dimension, code=t.code, field=t.field, term=t.term,
                                           rules_version=RULES_VERSION))

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
