"""Per-retailer extraction rules, read from store_configs.yaml.

Each store is a YAML entry keyed by its domain. Rules are CSS only (never XPath) and are validated
when the file is loaded, so a bad selector fails at startup, not halfway through a crawl.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import yaml
from cssselect import HTMLTranslator, SelectorError
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, field_validator, model_validator

CONFIG_PATH = Path(__file__).with_name("store_configs.yaml")
FIELD_NAMES = Literal["name", "brand", "price", "currency", "image_url"]
_translator = HTMLTranslator()


def check_css(css: str) -> str:
    css = css.strip()
    if not css or css.startswith(("/", "(")) or "//" in css or "@" in css:
        raise ValueError(f"not a CSS selector (XPath is not allowed): {css!r}")
    try:
        _translator.css_to_xpath(css)
    except SelectorError as e:
        raise ValueError(f"invalid CSS selector {css!r}: {e}") from e
    return css


def normalize_domain(value: str) -> str:
    host = (urlsplit(value).hostname if "://" in value else value) or ""
    host = host.strip().lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FieldRule(_Strict):
    css: str
    attr: str | list[str] | None = None  # read attribute(s) instead of text; first non-empty wins
    regex: str | None = None  # applied to the extracted value: group 1, or the whole match
    scope: Literal["card", "page"] = "card"  # listing card, or product page

    @field_validator("css")
    @classmethod
    def _css(cls, v: str) -> str:
        return check_css(v)

    @field_validator("regex")
    @classmethod
    def _compiles(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"invalid regex {v!r}: {e}") from e
        return v


class FlagRule(FieldRule):
    exists: bool = False  # True: the flag is whether the selector matches


class SpecsRule(_Strict):
    rows: str
    key: str
    value: str

    @field_validator("rows", "key", "value")
    @classmethod
    def _css(cls, v: str) -> str:
        return check_css(v)


class Pagination(_Strict):
    param: str | None = None  # ?param=2..max_pages
    next: str | None = None  # CSS of the "next page" link
    max_pages: int = Field(3, ge=1, le=20)

    @field_validator("next")
    @classmethod
    def _css(cls, v: str | None) -> str | None:
        return check_css(v) if v is not None else v

    @model_validator(mode="after")
    def _one_mode(self) -> Pagination:
        if (self.param is None) == (self.next is None):
            raise ValueError("pagination needs exactly one of 'param' or 'next'")
        return self


class ListingRule(_Strict):
    urls: list[str] = Field(min_length=1)  # relative to base_url, or absolute
    pagination: Pagination | None = None
    product: str  # one element per product card
    link: str  # the product page link inside a card (href)

    @field_validator("product", "link")
    @classmethod
    def _css(cls, v: str) -> str:
        return check_css(v)


class ProductPages(_Strict):
    enabled: bool = False
    max_products: int = Field(60, ge=1, le=500)


class ScraperConfig(_Strict):
    domain: str  # the YAML key, lower-case, without "www."
    name: str
    base_url: HttpUrl
    lang: Literal["fr", "en"]
    country: str | None = None
    default_currency: str | None = None  # when neither JSON-LD nor CSS gives one
    default_brand: str | None = None  # e.g. a single-brand store whose pages never name the brand
    listing: ListingRule
    product_pages: ProductPages = ProductPages()
    fields: dict[FIELD_NAMES, FieldRule] = {}
    flags: dict[str, FlagRule] = {}
    specs: SpecsRule | None = None  # product page table -> flags["raw_specs"]
    delay_s: float = Field(1.5, ge=0.5)  # politeness floor between requests

    @field_validator("default_currency")
    @classmethod
    def _iso(cls, v: str | None) -> str | None:
        if v is not None and not re.fullmatch(r"[A-Z]{3}", v):
            raise ValueError("default_currency must be a 3-letter ISO 4217 code")
        return v


def parse_store_configs(text: str, source: str = "<string>") -> dict[str, ScraperConfig]:
    data = yaml.safe_load(text) or {}
    stores = data.get("stores") or {}
    if not isinstance(stores, dict):
        raise ValueError(f"{source}: 'stores' must be a mapping of domain -> rules")
    configs: dict[str, ScraperConfig] = {}
    for key, raw in stores.items():
        domain = normalize_domain(str(key))
        try:
            configs[domain] = ScraperConfig.model_validate({**(raw or {}), "domain": domain})
        except ValidationError as e:
            raise ValueError(f"{source}: store '{key}': {e}") from None
    return configs


def load_store_configs(path: Path = CONFIG_PATH) -> dict[str, ScraperConfig]:
    return parse_store_configs(path.read_text(encoding="utf-8"), source=str(path))


def config_for(url_or_domain: str, configs: dict[str, ScraperConfig] | None = None) -> ScraperConfig:
    configs = load_store_configs() if configs is None else configs
    domain = normalize_domain(url_or_domain)
    if domain not in configs:
        raise KeyError(f"No store config for {domain!r}")
    return configs[domain]
