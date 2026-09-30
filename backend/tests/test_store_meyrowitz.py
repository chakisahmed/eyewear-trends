"""E.B. Meyrowitz (Shopify, UK): every colourway is its own product, the colour is written in the name after "in", card links are
collection-scoped, the price is on the product page, and there is no JSON-LD, SKU, shape or material. Offline: markup trimmed from
the real pages (2026-09-30), served by httpx.MockTransport with the real robots.txt rules."""

import re
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs, parse_store_configs
from app.collectors.stores.parser import parse_product_page
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product

EBM = "https://ebmeyrowitz.com"
ROBOTS = """User-agent: *
Disallow: /*/cart/
Disallow: /collections/*sort_by*
Disallow: /collections/*+*
Disallow: /collections/*%2B*
Disallow: /collections/*filter*&*filter*
"""

# handle -> (name as the store shows it, badge). The handle is NOT always the name: the Garrick below lives at "...-in-black".
FRAMES = {
    "the-grosvenor-in-olive": ("The Grosvenor in Olive", "Limited Release"),
    "the-grosvenor-in-jello": ("The Grosvenor in Jello", None),
    "the-garrick-in-black": ("The Garrick in Dark Mottle", "New"),                  # handle and name disagree
    "the-vigo": ("The Vigo In Amber Mottle", None),                                  # a capital "In", and no colour in the handle
    "the-new-yorker-in-colour-9": ("The New Yorker In Colour 8", "Special Edition"),   # a placeholder colour name
    "the-aldwych-in-black": ("The Aldwych in Black", None),
    "the-argyll-in-crystal": ("The Argyll in Crystal", None),
}
PLACEMENT = {  # collection -> pages of handles
    "spectacles": [["the-grosvenor-in-olive", "the-grosvenor-in-jello", "the-garrick-in-black"], ["the-vigo", "the-new-yorker-in-colour-9"]],
    "sunglasses": [["the-aldwych-in-black", "the-argyll-in-crystal"]],
}
PRICE = {"spectacles": "£1,250.00", "sunglasses": "£1,350.00"}
DETAILS = {  # model -> the "Finer details" lines (the same on every colourway of a model)
    "the-grosvenor": [("Top Line", "Arched"), ("Build", "Rounded"), ("Bridgework", "Keyhole"), ("Rim Structure", "Thick")],
    "the-garrick": [("Top Line", "Flat"), ("Build", "Soft Rectangular"), ("Bridgework", "Classical"), ("Rim Structure", "Medium-Thick")],
    "the-vigo": [("Top Line", "Rolling"), ("Build", "Ovular"), ("Bridgework", "Classical"), ("Rim Structure", "Medium")],
    "the-new-yorker": [("Top Line", "Arched"), ("Build", "Teardrop"), ("Bridgework", "Keyhole"), ("Rim Structure", "Thick")],
    "the-aldwych": [("Top Line", "Straight"), ("Build", "Rectangular"), ("Bridgework", "Keyhole"), ("Rim Structure", "Thick")],
    "the-argyll": [("Top Line", "Arched"), ("Build", "Rounded"), ("Bridgework", "Classical"), ("Rim Structure", "Medium Fine")],
}


def model_of(handle: str) -> str:
    return re.sub(r"-in-.*$", "", handle)


def collection_of(handle: str) -> str:
    return next(c for c, pages in PLACEMENT.items() if any(handle in page for page in pages))


def card(handle: str) -> str:
    name, badge = FRAMES[handle]
    collection = collection_of(handle)
    href = f"/collections/{collection}/products/{handle}"
    tag = f'<div class="product-grid-item__tag"> {badge} </div>' if badge else ""
    return (f'<div class="product-grid-item collection_{collection} "><div class="product-grid-item__images">{tag}<a href="{href}"><img alt=""></a></div>'
            f'<div class="product-grid-item__meta"><div class="product-grid-item__button"><div class="product-grid-item__title">'
            f'<h3 class="product-grid-item__heading"><a href="{href}">{name}</a></h3>'
            f'<span class="product-grid-item__price">From \n\t\t\t\t\t\t{PRICE[collection]} </span></div>'
            f'<div class="product-grid-item__shop"><a href="{href}" class="button product_type_simple">Shop now</a></div></div></div></div>')


def listing(handles: list[str], next_href: str | None = None) -> str:
    head = f'<link rel="next" href="{next_href}">' if next_href else ""
    return f'<html><head>{head}</head><body>{"".join(card(h) for h in handles)}</body></html>'


def product_page(handle: str) -> str:
    name, _ = FRAMES[handle]
    siblings = "".join(f'<li><a href="/collections/spectacles/products/{h}" title="{FRAMES[h][0].split(" in ")[-1]}">x</a></li>'
                       for h in FRAMES if h != handle and h.startswith(handle.split("-in-")[0]))
    details = "".join(f'<p class="products-details__description"> <span>{k}</span> {v} </p>' for k, v in DETAILS[model_of(handle)])
    return (f'<html><head><link rel="canonical" href="{EBM}/products/{handle}"></head><body>'
            f'<h1 class="d-none">{name}</h1><h1 class="d-none">{name}</h1>'
            f'<p class="product-showcase__price product-standard-price">{PRICE[collection_of(handle)]}</p>'
            f'<ul class="product-showcase__frame--list">{siblings}</ul>'
            f'<div class="products-details__box"><h3 class="products-page__heading">Finer details</h3>'
            f'<div class="products-details__content">{details}</div></div></body></html>')


def site() -> dict[str, str]:
    pages = {"/robots.txt": ROBOTS}
    for collection, chunks in PLACEMENT.items():
        for i, handles in enumerate(chunks, start=1):
            more = f"/collections/{collection}?page={i + 1}" if i < len(chunks) else None
            pages[f"/collections/{collection}" + (f"?page={i}" if i > 1 else "")] = listing(handles, more)
    for handle in FRAMES:
        pages[f"/products/{handle}"] = product_page(handle)
        pages[f"/collections/{collection_of(handle)}/products/{handle}"] = product_page(handle)
    return pages


async def crawl_meyrowitz():
    cfg = load_store_configs()["ebmeyrowitz.com"]
    pages, requested = site(), []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url)
        path = request.url.raw_path.decode()
        return httpx.Response(200, text=pages[path]) if path in pages else httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products = {p.db_url().rsplit("/", 1)[-1]: p for p in await crawler.crawl()}
    return products, requested, crawler.report


@pytest.fixture
def anyio_backend():
    return "asyncio"


def tags(p: ScrapedProduct) -> set[tuple]:
    return {(t.dimension, t.code, t.supplier_code) for t in tag_product(p.name, p.flags)}


@pytest.mark.anyio
async def test_every_colourway_is_a_frame_named_as_shown_with_the_collection_prefix_cut():
    products, requested, report = await crawl_meyrowitz()
    assert sorted(products) == sorted(FRAMES) and report.complete and report.gaps == []
    paths = {u.raw_path.decode() for u in requested}
    assert {"/collections/spectacles?page=2"} <= paths
    assert all("/collections/" not in p.db_url() for p in products.values())        # /products/<handle> is the identity
    olive = products["the-grosvenor-in-olive"]
    assert (olive.name, olive.brand, olive.db_url()) == ("The Grosvenor in Olive", "E.B. Meyrowitz", f"{EBM}/products/the-grosvenor-in-olive")
    assert products["the-garrick-in-black"].name == "The Garrick in Dark Mottle"     # the displayed name, not the handle's colour
    assert olive.flags["categories"] == "Optique" and products["the-aldwych-in-black"].flags["categories"] == "Solaire"


@pytest.mark.anyio
async def test_the_price_is_the_pages_not_the_cards_from_price_in_pounds():
    products, _, _ = await crawl_meyrowitz()
    assert (products["the-grosvenor-in-olive"].price, products["the-grosvenor-in-olive"].currency) == (1250.0, "GBP")
    assert (products["the-aldwych-in-black"].price, products["the-aldwych-in-black"].currency) == (1350.0, "GBP")


@pytest.mark.anyio
async def test_one_variant_per_product_from_the_name_and_the_switcher_is_ignored():
    products, _, _ = await crawl_meyrowitz()
    variants = {k: [(v["code"], v["color"]) for v in p.flags["variants"]] for k, p in products.items()}
    assert variants["the-grosvenor-in-olive"] == [("Olive", "Olive")]                 # its siblings (Jello...) are other products
    assert variants["the-grosvenor-in-jello"] == [("Jello", "Jello")]
    assert variants["the-garrick-in-black"] == [("Dark Mottle", "Dark Mottle")]
    assert variants["the-vigo"] == [("Amber Mottle", "Amber Mottle")]                  # "In" with a capital
    assert variants["the-new-yorker-in-colour-9"] == [("Colour 8", "Colour 8")]        # kept as the store writes it
    assert all("in_stock" not in v for p in products.values() for v in p.flags["variants"])   # stock is not readable here


@pytest.mark.anyio
async def test_colour_tags_agree_and_the_build_line_is_the_shape():
    products, _, _ = await crawl_meyrowitz()
    assert ("color", "black", "Black") in tags(products["the-aldwych-in-black"])
    assert ("color", "clear", "Crystal") in tags(products["the-argyll-in-crystal"])
    vigo = {(d, c) for d, c, _ in tags(products["the-vigo"]) if d == "color"}
    assert vigo == {("color", "brown")}                                               # the name and the variant say the same family
    assert not any(t[0] == "color" and t[2] == "Colour 8" for t in tags(products["the-new-yorker-in-colour-9"]))   # no family for a placeholder
    shapes = {k: {c for d, c, _ in tags(p) if d == "shape"} for k, p in products.items()}
    assert shapes == {"the-grosvenor-in-olive": {"round"}, "the-grosvenor-in-jello": {"round"},            # Rounded
                      "the-garrick-in-black": {"rectangle"}, "the-aldwych-in-black": {"rectangle"},          # Soft Rectangular, Rectangular
                      "the-vigo": {"oval"}, "the-new-yorker-in-colour-9": {"aviator"},                       # Ovular, Teardrop
                      "the-argyll-in-crystal": {"round"}}
    for p in products.values():
        assert {d for d, _, _ in tags(p)} <= {"color", "product_type", "shape"}, p.name   # no material, audience or style is invented
    assert ("product_type", "sun", None) in tags(products["the-aldwych-in-black"])


@pytest.mark.anyio
async def test_all_four_detail_lines_are_kept_but_only_build_is_tagged():
    products, _, _ = await crawl_meyrowitz()
    assert products["the-garrick-in-black"].flags["raw_specs"] == {
        "Top Line": "Flat", "Build": "Soft Rectangular", "Bridgework": "Classical", "Rim Structure": "Medium-Thick"}
    assert not any(t.field.startswith("spec:") and t.field != "spec:Build" for t in tag_product("x", products["the-vigo"].flags))


def test_a_spec_row_without_a_value_selector_reads_the_text_after_the_key():
    cfg = parse_store_configs("""
stores:
  shop.test:
    name: Shop Test
    base_url: https://shop.test
    lang: en
    listing: {urls: ["/c"], product: "div.card", link: "a"}
    specs: {rows: "p.d", key: "span"}
""")["shop.test"]
    html = ('<p class="d"><span>Top Line</span> Arched </p><p class="d"><span>Build</span>Soft   Rectangular</p>'
            '<p class="d"><span>Empty</span></p><p class="d">no key here</p>')
    assert parse_product_page(html, "https://shop.test/p/x", cfg).flags["raw_specs"] == {"Top Line": "Arched", "Build": "Soft Rectangular"}


@pytest.mark.anyio
async def test_requests_respect_robots_and_never_filter_or_sort():
    _, requested, _ = await crawl_meyrowitz()
    for url in (u for u in requested if u.path != "/robots.txt"):
        raw = url.raw_path.decode()
        assert "sort_by" not in raw and "+" not in raw and ".json" not in raw, raw
        assert not any(k.startswith("filter.") for k, _ in parse_qsl(urlsplit(raw).query)), raw


def test_the_shipped_entry_is_a_gb_catalog_with_one_variant_from_the_name():
    cfg = load_store_configs()["ebmeyrowitz.com"]
    assert (cfg.country, cfg.default_brand, cfg.default_currency, cfg.listing.facets) == ("GB", "E.B. Meyrowitz", "GBP", [])
    assert cfg.listing.url_regex == "(/products/[^/?#]+)" and cfg.listing.model_regex is None and cfg.name_strip is None
    assert cfg.variants.rows == "h1" and cfg.variants.code.regex == cfg.variants.label.regex == r"(?i)\s+in\s+(.+)$"
    assert cfg.fields["price"].scope == "page" and cfg.listing.pagination.next == "link[rel=next]"
    assert (cfg.specs.rows, cfg.specs.key, cfg.specs.value) == ("p.products-details__description", "span", None)
