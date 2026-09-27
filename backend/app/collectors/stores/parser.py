"""Deterministic product extraction: schema.org JSON-LD first, CSS rules from the store config second.

Pure functions (HTML in, dicts out): no I/O, no database, no LLM. Each source is returned as its own
layer (json_ld, css, flags) so the crawler can apply the precedence: product-page JSON-LD, listing
JSON-LD, product-page CSS, listing CSS.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

from lxml import html as lxml_html

from app.collectors.stores.config import FieldRule, ScraperConfig

log = logging.getLogger(__name__)
PRODUCT_FIELDS = ("name", "brand", "price", "currency", "image_url")
CURRENCY_TOKENS = {  # checked in this order, case-insensitive
    "TND": "TND", "DT": "TND", "د.ت": "TND", "EUR": "EUR", "€": "EUR", "USD": "USD", "$": "USD",
    "GBP": "GBP", "£": "GBP", "MAD": "MAD", "CHF": "CHF",
}
NUMBER_RE = re.compile(r"\d[\d\s.,  ']*")


@dataclass
class ListingItem:
    url: str
    rank: int
    json_ld: dict[str, Any] = field(default_factory=dict)
    css: dict[str, Any] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProductPage:
    json_ld: dict[str, Any] = field(default_factory=dict)
    css: dict[str, Any] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)  # page-scope flags + raw_specs


# --- prices ------------------------------------------------------------------------------------------

def _to_number(raw: str) -> float | None:
    s = re.sub(r"[\s  ']", "", raw).strip(".,")
    if not s:
        return None
    if "," in s and "." in s:  # the last separator is the decimal one
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:  # FR / TN convention: comma is decimal ("89,000 DT" = 89 dinars)
        s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 else s.replace(",", "")
    elif s.count(".") > 1:  # "1.234.567" thousands separators
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_price(text: str | None) -> tuple[float | None, str | None]:
    """Price and ISO currency from display text: "1 234,50 DT", "€89.90", "89,000 TND"."""
    if not text:
        return None, None
    match = NUMBER_RE.search(text)
    price = _to_number(match.group(0)) if match else None
    upper = text.upper()
    currency = next((iso for token, iso in CURRENCY_TOKENS.items() if token.upper() in upper), None)
    return (price, currency) if price is not None else (None, None)


# --- JSON-LD -----------------------------------------------------------------------------------------

def _types(node: dict) -> set[str]:
    t = node.get("@type")
    return {t} if isinstance(t, str) else set(t) if isinstance(t, list) else set()


def _walk(node: Any):
    if isinstance(node, list):
        for x in node:
            yield from _walk(x)
    elif isinstance(node, dict):
        yield node
        for key in ("@graph", "itemListElement", "item"):
            if key in node:
                yield from _walk(node[key])


def extract_json_ld_products(tree) -> list[dict]:
    """All schema.org Product nodes in the page's JSON-LD (@graph and ItemList flattened)."""
    products = []
    for script in tree.cssselect('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.text or "")
        except json.JSONDecodeError:
            continue
        products += [n for n in _walk(data) if "Product" in _types(n)]
    return products


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def _json_price(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ".")) if value not in (None, "") else None
    except ValueError:
        return None


def json_ld_fields(node: dict, page_url: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(node.get("name"), str) and node["name"].strip():
        out["name"] = node["name"].strip()
    brand = _first(node.get("brand"))
    brand = brand.get("name") if isinstance(brand, dict) else brand
    if isinstance(brand, str) and brand.strip():
        out["brand"] = brand.strip()
    offer = _first(node.get("offers"))
    if isinstance(offer, dict):
        price = _json_price(offer.get("price", offer.get("lowPrice")))
        if price is not None:
            out["price"] = price
        if isinstance(offer.get("priceCurrency"), str):
            out["currency"] = offer["priceCurrency"]
    image = _first(node.get("image"))
    image = image.get("url") if isinstance(image, dict) else image
    if isinstance(image, str) and image.strip():
        out["image_url"] = urljoin(page_url, image.strip())
    if isinstance(node.get("url"), str):
        out["url"] = urljoin(page_url, node["url"])
    return out


# --- CSS rules ---------------------------------------------------------------------------------------

def _extract(element, rule: FieldRule) -> str | None:
    matches = element.cssselect(rule.css)
    if not matches:
        return None
    el = matches[0]
    if rule.attr:
        attrs = [rule.attr] if isinstance(rule.attr, str) else rule.attr
        value = next((el.get(a).strip() for a in attrs if (el.get(a) or "").strip()), None)
    else:
        value = " ".join(el.text_content().split()) or None
    if value and rule.regex:
        m = re.search(rule.regex, value)
        value = (m.group(1) if m.groups() else m.group(0)).strip() if m else None
    return value


def css_fields(element, rules: dict[str, FieldRule], scope: str, base_url: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    price_currency = None  # currency read from the price text ("189 DT"), used if no currency rule matched
    for name, rule in rules.items():
        if rule.scope != scope or (value := _extract(element, rule)) is None:
            continue
        if name == "price":
            price, price_currency = parse_price(value)
            if price is not None:
                out["price"] = price
        elif name == "image_url":
            out["image_url"] = urljoin(base_url, value)
        else:
            out[name] = value
    if "currency" not in out and price_currency:
        out["currency"] = price_currency
    return out


def css_flags(element, cfg: ScraperConfig, scope: str) -> dict[str, Any]:
    flags: dict[str, Any] = {}
    for name, rule in cfg.flags.items():
        if rule.scope != scope:
            continue
        if rule.exists:
            flags[name] = bool(element.cssselect(rule.css))
        elif (value := _extract(element, rule)) is not None:
            flags[name] = value
    return flags


# --- pages -------------------------------------------------------------------------------------------

def _tree(html: str):
    return lxml_html.fromstring(html) if html and html.strip() else lxml_html.fromstring("<html></html>")


def parse_listing(html: str, page_url: str, cfg: ScraperConfig, start_rank: int = 1) -> list[ListingItem]:
    """One item per product card, ranked in page order; JSON-LD matched to cards by absolute URL."""
    tree = _tree(html)
    by_url = {}
    for node in extract_json_ld_products(tree):
        fields = json_ld_fields(node, page_url)
        if "url" in fields:
            by_url.setdefault(fields["url"], fields)
    items: list[ListingItem] = []
    for card in tree.cssselect(cfg.listing.product):
        links = card.cssselect(cfg.listing.link)
        if not links and card.tag == "a" and card.get("href"):
            links = [card]
        href = (links[0].get("href") or "").strip() if links else ""
        if not href:
            continue
        url = urljoin(page_url, href)
        items.append(ListingItem(
            url=url, rank=start_rank + len(items), json_ld=by_url.get(url, {}),
            css=css_fields(card, cfg.fields, "card", page_url), flags=css_flags(card, cfg, "card"),
        ))
    return items


def next_page_url(html: str, page_url: str, css: str) -> str | None:
    links = _tree(html).cssselect(css)
    href = (links[0].get("href") or "").strip() if links else ""
    return urljoin(page_url, href) if href else None


def parse_product_page(html: str, page_url: str, cfg: ScraperConfig) -> ProductPage:
    tree = _tree(html)
    nodes = [json_ld_fields(n, page_url) for n in extract_json_ld_products(tree)]
    json_ld = next((f for f in nodes if f.get("url") == page_url), nodes[0] if nodes else {})
    flags = css_flags(tree, cfg, "page")
    if cfg.specs:
        specs = {}
        for row in tree.cssselect(cfg.specs.rows):
            k, v = row.cssselect(cfg.specs.key), row.cssselect(cfg.specs.value)
            key = " ".join(k[0].text_content().split()) if k else ""
            if key and v:
                specs[key] = " ".join(v[0].text_content().split())
        if specs:
            flags["raw_specs"] = specs
    return ProductPage(json_ld=json_ld, css=css_fields(tree, cfg.fields, "page", page_url), flags=flags)


def merge(*layers: dict[str, Any], default_currency: str | None = None) -> dict[str, Any]:
    """Per field, the first layer that has a value wins (layers in precedence order)."""
    out = {f: next((layer[f] for layer in layers if layer.get(f) is not None), None) for f in PRODUCT_FIELDS}
    if out["currency"] is None:
        out["currency"] = default_currency
    return out
