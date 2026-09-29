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

from app.collectors.stores.config import FieldRule, ScraperConfig, ValueRule, VariantsRule

log = logging.getLogger(__name__)
PRODUCT_FIELDS = ("name", "brand", "price", "list_price", "currency", "image_url")
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


def _resolve(value: Any, by_id: dict[str, dict]) -> Any:
    """A bare {"@id": …} reference (Yoast: "image": {"@id": "…#primaryimage"}) -> the node it points to."""
    if isinstance(value, list):
        return [_resolve(v, by_id) for v in value]
    if isinstance(value, dict) and set(value) == {"@id"}:
        return by_id.get(value["@id"], value)
    return value


def extract_json_ld_products(tree) -> list[dict]:
    """All schema.org Product nodes in the page's JSON-LD (@graph and ItemList flattened), with their
    brand / image / offers references resolved against the other nodes of the page."""
    nodes = []
    for script in tree.cssselect('script[type="application/ld+json"]'):
        try:
            nodes += list(_walk(json.loads(script.text or "")))
        except json.JSONDecodeError:
            continue
    by_id = {n["@id"]: n for n in nodes if isinstance(n.get("@id"), str) and set(n) != {"@id"}}
    return [{**n, **{k: _resolve(n[k], by_id) for k in ("brand", "image", "offers") if k in n}}
            for n in nodes if "Product" in _types(n)]


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def _json_price(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ".")) if value not in (None, "") else None
    except ValueError:
        return None


NOT_CURRENT_PRICE = ("listprice", "strikethroughprice", "msrp", "srp")  # schema.org priceType values


def _price_specs(specs: Any) -> list[tuple[str, dict]]:
    """(price type, spec) for each priceSpecification entry with a price; type "" = selling price."""
    out = []
    for spec in specs if isinstance(specs, list) else [specs]:
        if isinstance(spec, dict) and spec.get("price") not in (None, ""):
            out.append((str(spec.get("priceType") or "").rsplit("/", 1)[-1].lower(), spec))
    return out


def _current_price_spec(specs: Any) -> dict | None:
    """The priceSpecification entry that is the actual selling price (not the struck-through list price)."""
    return next((spec for kind, spec in _price_specs(specs) if kind not in NOT_CURRENT_PRICE), None)


def _list_price_spec(specs: Any) -> dict | None:
    """The pre-markdown price (schema.org ListPrice / StrikethroughPrice / MSRP), if published."""
    return next((spec for kind, spec in _price_specs(specs) if kind in NOT_CURRENT_PRICE), None)


DESCRIPTION_SPLIT = re.compile(r"[–—|•;\n]")  # – — | • ; newline
DESCRIPTION_PAIR = re.compile(r"^(?P<key>[^:]{2,40}?)\s*:\s*(?P<value>.+)$")


def description_specs(text: str | None) -> dict[str, str]:
    """ "Forme : Oeil de Chat – Style : Tendance – …" -> {"Forme": "Oeil de Chat", "Style": "Tendance"}.
    Parts without "Label : value" are skipped; the first occurrence of a label wins."""
    specs: dict[str, str] = {}
    for part in DESCRIPTION_SPLIT.split(text or ""):
        m = DESCRIPTION_PAIR.match(" ".join(part.split()))  # split() also folds non-breaking spaces
        if m:
            specs.setdefault(m["key"].strip(), m["value"].strip())
    return specs


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
        price, currency = _json_price(offer.get("price", offer.get("lowPrice"))), offer.get("priceCurrency")
        if price is None:  # e.g. Yoast/Woo sales: only priceSpecification[] (current price + ListPrice)
            spec = _current_price_spec(offer.get("priceSpecification"))
            if spec:
                price, currency = _json_price(spec.get("price")), currency or spec.get("priceCurrency")
        if price is not None:
            out["price"] = price
            listed = _list_price_spec(offer.get("priceSpecification"))
            if listed:  # kept only if above the price (ScrapedProduct drops it otherwise)
                out["list_price"] = _json_price(listed.get("price"))
        if isinstance(currency, str):
            out["currency"] = currency
    image = _first(node.get("image"))
    image = (image.get("url") or image.get("contentUrl")) if isinstance(image, dict) else image
    if isinstance(image, str) and image.strip():
        out["image_url"] = urljoin(page_url, image.strip())
    if isinstance(node.get("url"), str):
        out["url"] = urljoin(page_url, node["url"])
    return out


# --- CSS rules ---------------------------------------------------------------------------------------

def _read(el, rule: FieldRule | ValueRule) -> str | None:
    """The element's text, or its first non-empty rule.attr, then rule.regex (group 1, or the whole match)."""
    if rule.attr:
        attrs = [rule.attr] if isinstance(rule.attr, str) else rule.attr
        value = next((el.get(a).strip() for a in attrs if (el.get(a) or "").strip()), None)
    else:
        value = " ".join(el.text_content().split()) or None
    if value and rule.regex:
        m = re.search(rule.regex, value)
        value = (m.group(1) if m.groups() else m.group(0)).strip() if m else None
    return value or None


def _extract(element, rule: FieldRule) -> str | None:
    matches = element.cssselect(rule.css)
    return _read(matches[0], rule) if matches else None


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
        elif name == "list_price":
            listed, _ = parse_price(value)
            if listed is not None:
                out["list_price"] = listed
        elif name == "image_url":
            url = urljoin(base_url, value)
            if url.startswith(("http://", "https://")):  # skip lazy-load placeholders (data:image/svg+xml,...)
                out["image_url"] = url
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


def canonical_url(url: str, url_regex: str | None) -> str:
    """The product's identity URL: group 1 of url_regex made absolute ("/collections/sun/products/izzi?variant=1"
    -> "/products/izzi"), so one frame listed in two collections, or once per color, is one product."""
    m = re.search(url_regex, url) if url_regex else None
    return urljoin(url, m.group(1)) if m and m.group(1) else url


def facet_values(html: str, param: str) -> list[tuple[str, str]]:
    """(value, label) of each option of a listing filter (<input name=param>), deduplicated: Shopify themes render
    the filter twice (desktop and mobile). Label: aria-label, else its <label for=id>, else the enclosing label."""
    tree = _tree(html)
    labels = {lab.get("for"): " ".join(lab.text_content().split()) for lab in tree.cssselect("label[for]")}
    out: dict[str, str] = {}
    for inp in tree.cssselect("input[name]"):
        value = (inp.get("value") or "").strip()
        if inp.get("name") != param or not value or value in out:
            continue
        enclosing = next((a for a in inp.iterancestors("label")), None)
        label = ((inp.get("aria-label") or "").strip() or labels.get(inp.get("id"))
                 or (" ".join(enclosing.text_content().split()) if enclosing is not None else ""))
        if label:
            out[value] = label
    return list(out.items())


def parse_variants(tree, rule: VariantsRule) -> list[dict[str, Any]]:
    """[{"code": "HV/BL", "color": "Havana", "in_stock": True}, …] in page order, one entry per code."""
    def value(row, r: ValueRule | None) -> str | None:
        if r is None:
            return None
        el = row if r.css is None else next(iter(row.cssselect(r.css)), None)
        return _read(el, r) if el is not None else None

    variants: dict[str, dict[str, Any]] = {}
    for row in tree.cssselect(rule.rows):
        code = value(row, rule.code)
        if not code or code in variants:
            continue
        variant: dict[str, Any] = {"code": code}
        if label := value(row, rule.label):
            variant["color"] = label
        available = {"true": True, "1": True, "false": False, "0": False}.get((value(row, rule.available) or "").lower())
        if available is not None:
            variant["in_stock"] = available
        variants[code] = variant
    return list(variants.values())


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
        url = canonical_url(urljoin(page_url, href), cfg.listing.url_regex)
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
    raw_nodes = extract_json_ld_products(tree)
    nodes = [json_ld_fields(n, page_url) for n in raw_nodes]
    i = next((k for k, f in enumerate(nodes) if f.get("url") == page_url), 0)
    json_ld = nodes[i] if nodes else {}
    flags = css_flags(tree, cfg, "page")
    specs: dict[str, str] = {}
    if cfg.specs:
        for row in tree.cssselect(cfg.specs.rows):
            k, v = row.cssselect(cfg.specs.key), row.cssselect(cfg.specs.value)
            key = " ".join(k[0].text_content().split()) if k else ""
            if key and v:
                specs[key] = " ".join(v[0].text_content().split())
    if cfg.description_specs and raw_nodes:
        described = description_specs(raw_nodes[i].get("description"))
        specs = described | specs  # a table value wins over the description on the same label
    if specs:
        flags["raw_specs"] = specs
    if cfg.variants and (variants := parse_variants(tree, cfg.variants)):
        flags["variants"] = variants
        stock = [v["in_stock"] for v in variants if "in_stock" in v]
        if stock:  # sold out only when no variant is available; an explicit out_of_stock flag rule wins
            flags.setdefault("out_of_stock", not any(stock))
    return ProductPage(json_ld=json_ld, css=css_fields(tree, cfg.fields, "page", page_url), flags=flags)


def merge(*layers: dict[str, Any], default_currency: str | None = None, default_brand: str | None = None) -> dict[str, Any]:
    """Per field, the first layer that has a value wins (layers in precedence order); the config
    defaults only fill a field no layer provided. A price <= 0 counts as missing: stores publish
    0.00 for out-of-stock or price-on-request items (e.g. Outika's JSON-LD)."""
    def usable(f: str, v: Any) -> bool:
        return v is not None and not (f == "price" and v <= 0)
    out = {f: next((layer[f] for layer in layers if usable(f, layer.get(f))), None) for f in PRODUCT_FIELDS}
    # The list price must come from the layer that gave the price: pairing a JSON-LD sale price with a
    # struck-through price read elsewhere on the page could invent a discount.
    price_layer = next((layer for layer in layers if usable("price", layer.get("price"))), {})
    out["list_price"] = price_layer.get("list_price") if usable("price", price_layer.get("list_price")) else None
    if out["currency"] is None:
        out["currency"] = default_currency
    if out["brand"] is None:
        out["brand"] = default_brand
    return out
