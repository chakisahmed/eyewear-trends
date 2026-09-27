"""The contract between store crawlers and persistence: one product as seen on a store listing.

Aligned with the `products` table (lengths, nullability). Invalid data fails here, in the crawler,
not at commit time.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
MAX_URL, MAX_NAME, MAX_BRAND = 1000, 300, 100  # products.url / name / brand column lengths


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScrapedProduct(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    url: HttpUrl  # identity (products.url is unique); db_url() is the only conversion to the stored string
    name: str = Field(min_length=1)
    brand: str | None = None
    price: float | None = Field(default=None, ge=0)
    list_price: float | None = Field(default=None, ge=0)  # pre-markdown price; kept only when above price
    currency: str | None = None  # ISO 4217, e.g. "TND", "EUR"
    rank: int | None = Field(default=None, ge=1)  # 1-based position on the store's listing
    image_url: HttpUrl | None = None
    flags: dict[str, Any] | None = None  # e.g. {"is_bestseller": True, "raw_specs": {"Forme": "Pilote"}}
    seen_at: datetime = Field(default_factory=utcnow)

    @field_validator("name")
    @classmethod
    def _truncate_name(cls, v: str) -> str:
        return " ".join(v.split())[:MAX_NAME]  # "BALENCIAGA  BB0273-O" -> one space: same frame, same name

    @field_validator("brand", mode="before")
    @classmethod
    def _clean_brand(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()[:MAX_BRAND]
            return v or None
        return v

    @field_validator("currency", mode="before")
    @classmethod
    def _upper_currency(cls, v: Any) -> Any:
        return v.strip().upper() or None if isinstance(v, str) else v

    @field_validator("currency")
    @classmethod
    def _iso_currency(cls, v: str | None) -> str | None:
        if v is not None and not CURRENCY_RE.match(v):
            raise ValueError("currency must be a 3-letter ISO 4217 code")
        return v

    @field_validator("url", "image_url")
    @classmethod
    def _url_fits_column(cls, v: HttpUrl | None) -> HttpUrl | None:
        if v is not None and len(str(v)) > MAX_URL:
            raise ValueError(f"URL longer than {MAX_URL} characters")
        return v

    @field_validator("flags")
    @classmethod
    def _json_flags(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None:
            try:
                json.dumps(v)
            except (TypeError, ValueError) as e:
                raise ValueError(f"flags must be JSON-serialisable: {e}") from e
        return v

    @field_validator("seen_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _list_price_is_a_markdown(self) -> ScrapedProduct:
        """A list price only matters as a discount signal: drop it unless it is above the selling price."""
        if self.list_price is not None and (self.price is None or self.list_price <= self.price):
            object.__setattr__(self, "list_price", None)  # the model is frozen: bypass the setter guard
        return self

    def db_url(self) -> str:
        return str(self.url)

    def db_image_url(self) -> str | None:
        return str(self.image_url) if self.image_url else None
