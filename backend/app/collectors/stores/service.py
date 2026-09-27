"""Persist crawler output (list[ScrapedProduct]) into the products table.

The only store module that touches the database. `products.url` is unique on its own, so rows are
matched by url: same source -> updated, another source -> reported as a conflict and left alone.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import get_or_create_source
from app.collectors.stores.config import ScraperConfig
from app.collectors.stores.schemas import ScrapedProduct
from app.models import Product, Source

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
            values = dict(name=p.name, brand=p.brand, price=p.price, currency=p.currency, rank=p.rank,
                          flags=p.flags, image_url=p.db_image_url(), seen_at=p.seen_at)
            row = existing.get(url)
            if row is None:
                self.session.add(Product(source_id=source_id, url=url, **values))
                result.inserted += 1
            elif row.source_id == source_id:
                for key, value in values.items():
                    setattr(row, key, value)
                result.updated += 1
            else:
                log.warning("Product %s belongs to source %s, not %s: skipped", url, row.source_id, source_id)
                result.conflicts += 1
        self.session.commit()
        return result
