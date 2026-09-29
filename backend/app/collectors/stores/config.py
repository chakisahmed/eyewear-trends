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
FIELD_NAMES = Literal["name", "brand", "price", "list_price", "currency", "image_url"]
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


def check_regex(v: str | None) -> str | None:
    if v is not None:
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"invalid regex {v!r}: {e}") from e
    return v


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
        return check_regex(v)


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


class ValueRule(_Strict):
    """One value read from a variant row: the row's own text or attribute, or a descendant's (css)."""
    css: str | None = None  # None: the row element itself
    attr: str | list[str] | None = None  # first non-empty attribute wins; None: the text
    regex: str | None = None  # group 1, or the whole match

    @field_validator("css")
    @classmethod
    def _css(cls, v: str | None) -> str | None:
        return check_css(v) if v is not None else v

    @field_validator("regex")
    @classmethod
    def _compiles(cls, v: str | None) -> str | None:
        return check_regex(v)


class VariantsRule(_Strict):
    """Product page color variants -> flags["variants"] = [{"code", "color", "in_stock"}]. The code is the store's
    own commercial code (Palier 3, kept verbatim); the color is the store's own name for it, which the tagger maps
    to a family. Nothing is decoded from the code itself."""
    rows: str  # one element per variant, e.g. a color swatch input
    code: ValueRule
    label: ValueRule | None = None
    available: ValueRule | None = None  # "true" / "false"
    # Acetate layers of a multi-colour variant ("Havana/Blue") -> variant["layers"], from a named reader since the
    # source is JSON in a script, not markup: "vto_carousel" = a virtual try-on widget's <script data-vto-carousel>.
    layers: Literal["vto_carousel"] | None = None
    # Variant ids -> variant["id"], so a listing filter's per-variant labels can reach the right code (Facet.per_variant):
    # "shopify_analytics" = Shopify's analytics metadata (id + variant title; the code rule's regex is applied to the
    # title). Prices in that metadata are never read.
    ids: Literal["shopify_analytics"] | None = None

    @field_validator("rows")
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


class ListingUrl(_Strict):
    url: str  # relative to base_url, or absolute
    categories: str | None = None  # flags["categories"] of every product listed here, e.g. "Solaire"


class Facet(_Strict):
    """A store's own listing filter, read one value at a time: every product listed under a value gets
    raw_specs[name] = that value's label. Values and labels are read from the listing's first page, so no
    store id is hard-coded. One filter per request: filters are never combined (robots.txt often forbids it)."""
    name: str  # the raw_specs key the tagger reads, e.g. "Forme"
    param: str  # the query parameter, e.g. "filter.p.m.custom.shape"
    only: list[str] | None = Field(None, min_length=1)  # value labels to list, e.g. ["Yes"]; the others are never requested
    # Set flags[flag] = True on the products listed (instead of raw_specs[name]), False on the rest of the listing
    # when every page of the pass loaded; left unset when one failed (unknown, never a false False).
    flag: str | None = None
    # A variant-level filter (Shopify "filter.v.…"): the card links the variant that matched, so also record
    # flags["variant_colors"][variant id] = label; the crawler hands it to that variant (VariantsRule.ids).
    per_variant: bool = False

    @field_validator("flag")
    @classmethod
    def _identifier(cls, v: str | None) -> str | None:
        if v is not None and not v.isidentifier():
            raise ValueError(f"flag must be an identifier, e.g. is_bestseller: {v!r}")
        return v

    @field_validator("param")
    @classmethod
    def _plain(cls, v: str) -> str:
        if not re.fullmatch(r"[\w.\-]+", v):
            raise ValueError(f"not a query parameter name: {v!r}")
        return v


class ListingRule(_Strict):
    urls: list[str | ListingUrl] = Field(min_length=1)  # relative to base_url, or absolute
    pagination: Pagination | None = None
    product: str  # one element per product card
    link: str  # the product page link inside a card (href)
    url_regex: str | None = None  # keep group 1 of each (absolute) product link, e.g. drop a collection prefix and ?variant=
    facets: list[Facet] = []

    @field_validator("product", "link")
    @classmethod
    def _css(cls, v: str) -> str:
        return check_css(v)

    @field_validator("url_regex")
    @classmethod
    def _compiles(cls, v: str | None) -> str | None:
        if v is not None and re.compile(check_regex(v)).groups < 1:
            raise ValueError(f"url_regex needs a capture group: {v!r}")
        return v


class ProductPages(_Strict):
    enabled: bool = False
    max_products: int = Field(60, ge=1, le=1000)


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
    variants: VariantsRule | None = None  # product page color variants -> flags["variants"]
    description_specs: bool = False  # also read "Label : value" pairs from the JSON-LD description
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
