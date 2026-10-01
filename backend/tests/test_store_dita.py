"""Dita (Shopify, USA), storefront /en-fr: `a[rel=next]` paging, two filters one value at a time, card links that gain
tracking parameters on filtered pages, and colourways from JSON-LD offers whose frame colour is the first token of the
first part of "Frame - Finish / Lens". Offline: markup trimmed from the real pages (2026-09-30), MockTransport, real robots rules."""

import json
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import ColorSplit, load_store_configs
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product

DITA = "https://dita.com"
ROBOTS = """User-agent: *
Disallow: /*/cart/
Disallow: /collections/*sort_by*
Disallow: /*/collections/*sort_by*
Disallow: /collections/*+*
Disallow: /*/collections/*+*
Disallow: /collections/*filter*&*filter*
Disallow: /*/collections/*filter*&*filter*
"""
SHAPE, MATERIAL = "filter.v.m.vdp.frame_shape", "filter.v.m.vdp.frame_composition"
UNUSED = ("filter.v.m.vdp.frame_color", "filter.v.m.vdp.lens_color", "filter.v.m.vdp.frame_size", "filter.v.price.gte", "filter.v.price.lte",
          "filter.p.product_type", "filter.v.m.custom.gender_filter")
IN = "https://schema.org/InStock"

# slug -> (name, sku prefix, price, [offer names as the store writes them])
FRAMES = {
    "laurhyn": ("LAURHYN", "DTX204", 595, ["White Gold / Clear", "Silver / Clear", "Smoked Pearl / Clear"]),
    "evercharm": ("EVERCHARM", "DTS754", 795, ["Black Glass - Silver / Grey to Clear Gradient", "Tortoise Haze - White Gold / Brown",
                                               "Swanshell - Rose Gold / Dark Grey to Peach Gradient"]),
    "sahvana": ("SAHVANA", "DTX213", 565, ["Future Dusk Blue / Clear"]),
    "monolix-optical": ("MONOLIX Optical", "DTX750", 565, ["Crystal Clear / Clear"]),
    "lineage-68x": ("LINEAGE.68x", "DTS482", 995, ["Yellow Gold - Black - Shiny Silver / Dark Grey to Clear Gradient",
                                                  "Brush White Gold - Burnt Timber - Yellow Gold / Brown"]),
    "mach-five": ("MACH-FIVE", "DRX-2087", 1195, ["Matte Black - Yellow Gold / Grey Gradient", "Black Palladium - Black Iron / Green Gradient"]),
    "flight-006": ("FLIGHT 006", "DTS106", 995, ["Black Iron / Grey"]),
}
PLACEMENT = {"optical": [["laurhyn", "evercharm"], ["sahvana"], ["monolix-optical"]],
             "sunglasses": [["lineage-68x", "mach-five"], ["flight-006"]]}
SHAPES = {"optical": {"Cat-Eye": ["evercharm"], "Round": ["laurhyn", "sahvana"], "Polyangular": ["monolix-optical"]},
          "sunglasses": {"Shield": ["lineage-68x"], "Navigator": ["mach-five"], "Diamond": ["flight-006"]}}
MATERIALS = {"optical": {"Titanium": ["laurhyn"], "Titanuim": ["sahvana"], "Titanium/Acetate": ["evercharm"], "Acetate": ["monolix-optical"]},
             "sunglasses": {"Titanium": ["lineage-68x", "mach-five"], "Acetate": ["flight-006"]}}


def card(slug: str, tracking: bool = False) -> str:
    href = f"/en-fr/products/{slug}" + ("?_pos=1&_fid=18b6c785d&_ss=c" if tracking else "")
    return (f'<product-item class="product-item"><a href="{href}"><img alt=""></a>'
            f'<div class="product-item__info"><a href="{href}">{FRAMES[slug][0]}</a></div></product-item>')


def form(collection: str) -> str:
    def group(param, options):
        return "".join(f'<input type="checkbox" name="{param}" id="{param}-{i}" value="{v}"><label for="{param}-{i}">{v}</label>'
                       for i, v in enumerate(options, start=1))
    return (group(SHAPE, SHAPES[collection]) + group(MATERIAL, MATERIALS[collection])
            + '<input type="checkbox" name="filter.v.m.vdp.frame_color" id="fc" value="Black Iron"><label for="fc">Black Iron</label>'
            + '<input type="checkbox" name="filter.v.m.vdp.lens_color" id="lc" value="gid://shopify/FilterSettingGroup/1"><label for="lc">Grey Wash</label>'
            + '<input type="checkbox" name="filter.v.m.vdp.frame_size" id="fs" value="Medium"><label for="fs">Medium</label>'
            + '<input type="number" name="filter.v.price.gte" value=""><input type="number" name="filter.v.price.lte" value="">')


def listing(slugs, *, next_href=None, collection=None, tracking=False) -> str:
    pager = (f'<nav><a class="pagination__nav-item heading" href="{next_href}">2</a>'
             f'<a class="pagination__nav-item" rel="next" href="{next_href}"></a></nav>') if next_href else ""
    return f'<html><body>{form(collection) if collection else ""}{"".join(card(s, tracking) for s in slugs)}{pager}</body></html>'


def product_page(slug: str) -> str:
    name, prefix, price, colourways = FRAMES[slug]
    offers = [{"@type": "Offer", "name": c, "sku": f"{prefix}-A-{i:02d}", "price": price, "priceCurrency": "EUR", "availability": IN,
               "url": f"{DITA}/en-fr/products/{slug}?variant={i}"} for i, c in enumerate(colourways, start=1)]
    ld = {"@context": "http://schema.org/", "@type": "Product", "name": name, "url": f"{DITA}/en-fr/products/{slug}",
          "brand": {"@type": "Brand", "name": "DITA Eyewear"}, "offers": offers}
    return f'<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head><body><h1>{name}</h1></body></html>'


def filter_url(collection: str, param: str, value: str) -> str:
    return f"/en-fr/collections/{collection}?{urlencode({param: value}, quote_via=quote)}"


def site() -> dict[str, str]:
    pages = {"/robots.txt": ROBOTS}
    for collection, chunks in PLACEMENT.items():
        for i, slugs in enumerate(chunks, start=1):
            more = f"/en-fr/collections/{collection}?page={i + 1}" if i < len(chunks) else None
            pages[f"/en-fr/collections/{collection}" + (f"?page={i}" if i > 1 else "")] = listing(slugs, next_href=more, collection=collection if i == 1 else None)
        for param, groups in ((SHAPE, SHAPES[collection]), (MATERIAL, MATERIALS[collection])):
            for value, slugs in groups.items():
                pages[filter_url(collection, param, value)] = listing(slugs, tracking=True)     # filtered pages tag their links
    for slug in FRAMES:
        pages[f"/en-fr/products/{slug}"] = product_page(slug)
    return pages


async def crawl_dita():
    cfg = load_store_configs()["dita.com"]
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


def colours(p: ScrapedProduct) -> set[tuple]:
    return {(c, s) for d, c, s in tags(p) if d == "color"}


@pytest.mark.anyio
async def test_every_page_is_followed_by_its_rel_next_anchor_and_identities_ignore_tracking():
    products, requested, report = await crawl_dita()
    assert sorted(products) == sorted(FRAMES) and report.complete and report.gaps == []
    paths = {u.raw_path.decode() for u in requested}
    assert {"/en-fr/collections/optical?page=2", "/en-fr/collections/optical?page=3", "/en-fr/collections/sunglasses?page=2"} <= paths
    assert all("?" not in p.db_url() for p in products.values())              # the ?_pos=&_fid=&_ss= of filtered pages is cut
    laurhyn = products["laurhyn"]
    assert (laurhyn.name, laurhyn.brand, laurhyn.price, laurhyn.currency) == ("LAURHYN", "DITA Eyewear", 595.0, "EUR")
    assert laurhyn.db_url() == f"{DITA}/en-fr/products/laurhyn"
    assert laurhyn.flags["categories"] == "Optique" and products["mach-five"].flags["categories"] == "Solaire"


@pytest.mark.anyio
async def test_filtered_frames_are_the_same_products_as_the_plain_listings():
    products, _, _ = await crawl_dita()
    assert products["evercharm"].flags["raw_specs"] == {"Shape": "Cat-Eye", "Materials": "Titanium/Acetate"}
    assert products["sahvana"].flags["raw_specs"] == {"Shape": "Round", "Materials": "Titanuim"}
    assert products["mach-five"].flags["raw_specs"] == {"Shape": "Navigator", "Materials": "Titanium"}


@pytest.mark.anyio
async def test_the_frame_colour_is_the_first_token_of_the_first_part_and_codes_are_the_skus():
    products, _, _ = await crawl_dita()
    variants = products["evercharm"].flags["variants"]
    assert [(v["code"], v["color"]) for v in variants] == [("DTS754-A-01", "Black Glass"), ("DTS754-A-02", "Tortoise Haze"), ("DTS754-A-03", "Swanshell")]
    assert variants[0]["parts"] == ["Black Glass - Silver", "Grey to Clear Gradient"] and variants[0]["subparts"] == ["Black Glass", "Silver"]
    assert all(v["in_stock"] for v in variants)
    # Black Glass -> black, Tortoise Haze -> tortoiseshell; the finish (Silver, White Gold) and the lens are not tags; Swanshell is not known, so not guessed
    assert colours(products["evercharm"]) == {("black", "DTS754-A-01"), ("tortoiseshell", "DTS754-A-02")}
    assert colours(products["mach-five"]) == {("black", "DRX-2087-A-01"), ("black", "DRX-2087-A-02")}      # Matte Black; Black Palladium


@pytest.mark.anyio
async def test_white_gold_is_gold_and_not_also_white():
    products, _, _ = await crawl_dita()
    assert colours(products["laurhyn"]) == {("gold", "DTX204-A-01"), ("silver", "DTX204-A-02")}     # Smoked Pearl: not known yet
    assert colours(products["lineage-68x"]) == {("gold", "DTS482-A-01"), ("gold", "DTS482-A-02")}    # Yellow Gold; Brush White Gold
    assert not any(c == "white" for c, _ in colours(products["lineage-68x"]))


@pytest.mark.anyio
async def test_shape_and_material_labels_become_tags_including_the_sites_own_typo():
    products, _, _ = await crawl_dita()
    got = lambda slug: {(d, c) for d, c, _ in tags(products[slug]) if d in ("shape", "material")}
    assert got("evercharm") == {("shape", "cat_eye"), ("material", "titanium"), ("material", "acetate")}    # Titanium/Acetate is both
    assert got("sahvana") == {("shape", "round"), ("material", "titanium")}                                # "Titanuim"
    assert got("monolix-optical") == {("shape", "geometric"), ("material", "acetate")}                    # Polyangular
    assert got("lineage-68x") == {("shape", "shield"), ("material", "titanium")}
    assert got("flight-006") == {("shape", "geometric"), ("material", "acetate")}                         # Diamond
    assert got("mach-five") == {("material", "titanium"), ("shape", "aviator")}                            # Navigator -> aviator (v15)


@pytest.mark.anyio
async def test_requests_respect_robots_one_filter_no_sort_no_plus_and_only_the_two_wanted_filters():
    _, requested, _ = await crawl_dita()
    for url in (u for u in requested if u.path != "/robots.txt"):
        raw = url.raw_path.decode()
        assert "sort_by" not in raw and "+" not in raw and ".json" not in raw, raw
        assert not any(name in raw for name in UNUSED), raw
        assert sum(k.startswith("filter.") for k, _ in parse_qsl(urlsplit(raw).query)) <= 1, raw
    assert any(u.raw_path.decode() == filter_url("optical", MATERIAL, "Titanium/Acetate") for u in requested)   # "/" is %2F


def test_the_shipped_entry_is_a_us_brand_catalog_on_the_fr_storefront():
    cfg = load_store_configs()["dita.com"]
    assert (cfg.country, cfg.default_brand, cfg.listing.pagination.next) == ("US", None, "a[rel=next]")
    assert [u.url for u in cfg.listing.urls] == ["/en-fr/collections/optical", "/en-fr/collections/sunglasses"]
    assert [f.param for f in cfg.listing.facets] == [SHAPE, MATERIAL]
    assert cfg.variants.color_split == ColorSplit(sep=" / ", color=0, then=ColorSplit(sep=" - ", color=0))
