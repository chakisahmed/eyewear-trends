"""Morel (Shopify, creator brand, France): presence-only catalog (no price shown), spec-table shapes and materials,
and colour codes that get their colour from the variant-level colour filter. Offline: markup trimmed from the real
site (2026-09-29), served by httpx.MockTransport with the real robots.txt rules."""

import json
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs
from app.collectors.stores.parser import _tree, canonical_url, link_variant_id, shopify_variant_titles
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product

MOREL = "https://morel.com"
ROBOTS = """User-agent: *
Allow: /
Disallow: /services
Disallow: /collections/*sort_by*
Disallow: /*/collections/*sort_by*
Disallow: /collections/*+*
Disallow: /*/collections/*+*
Disallow: */collections/*filter*&*filter*
Disallow: /search
"""
GENDER, MATERIAL, COLOR = "filter.p.m.mymorel.gender", "filter.p.m.mymorel.material", "filter.v.m.mymorel.color_name"
# (code, variant id, colour-filter label) per frame; the colour exists only in the filter
FRAMES = {
    "agathe1": [("BM02", 64359734313337, "Blue"), ("NV03", 64359734346105, "Black"), ("RP01", 64359734378873, "Red")],
    "mila4": [("EC01", 64359700000001, "Tortoiseshell"), ("EC02", 64359700000002, "Tortoiseshell")],  # two of one colour
    "sol1": [("GR01", 64359800000001, "Vert")],
}


def filter_url(collection: str, param: str, value: str, page: int | None = None) -> str:
    return f"/en/collections/{collection}?{urlencode({param: value, **({'page': page} if page else {})}, quote_via=quote)}"


def card(collection: str, slug: str, name: str, variant: int | None = None) -> str:
    href = f"/en/collections/{collection}/products/{slug}" + (f"?_pos=1&_fid=1cd8d4b2f&_ss=c&variant={variant}" if variant else "")
    return (f'<product-card class="product-card"><div class="product-card__figure">'
            f'<a class="product-card__media" href="{href}"><img alt=""></a></div>'
            f'<div class="product-card__info"><a class="product-title h6 " href="{href}">{name}</a></div></product-card>')


def form(options: dict[str, list[str]]) -> str:
    return "".join(f'<input type="checkbox" name="{param}" value="{v}" id="f-{param}-{v}-{layout}">'
                   f'<label for="f-{param}-{v}-{layout}">{v}</label>'
                   for layout in ("h", "v") for param, values in options.items() for v in values)


def listing(cards: list[str], next_href: str | None = None, facets: str = "") -> str:
    head = f'<link rel="next" href="{next_href}">' if next_href else ""
    return f'<html><head>{head}</head><body>{facets}<product-list>{"".join(cards)}</product-list></body></html>'


def product(slug: str, name: str, specs: dict[str, str]) -> str:
    variants = FRAMES[slug]
    radios = "".join(
        f'<input type="radio" id="option-value-{i}-main-product-form-main-1-option1-{1240500 + i}" value="{1240500 + i}" '
        f'data-option-position="1"><label for="option-value-{i}-main-product-form-main-1-option1-{1240500 + i}">'
        f'<span>{code} {name}</span></label>' for i, (code, _, _) in enumerate(variants, start=1))
    meta = {"product": {"id": 15735655137657, "vendor": "2608-MOREL", "type": "MOREL", "variants": [
        {"id": vid, "price": 11900 + 1000 * i, "name": f"{name} - {code} {name}", "public_title": f"{code} {name}",
         "sku": f"M20345K{code}50"} for i, (code, vid, _) in enumerate(variants)]}}
    table = "".join(f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>" for k, v in specs.items())
    return (f"<html><head><title>{name}</title><script>var meta = {json.dumps(meta)};\n"
            "for (var attr in meta) { window.ShopifyAnalytics.meta[attr] = meta[attr]; }</script></head><body>"
            f'<form class="product-form">{radios}</form>'
            f'<div class="accordion__content prose"><table>{table}</table></div></body></html>')


def site() -> dict[str, str]:
    optical_facets = form({GENDER: ["Man", "Woman"], MATERIAL: ["Acetate", "Wood"],
                           COLOR: ["Blue", "Black", "Red", "Tortoiseshell"]})
    pages = {
        "/robots.txt": ROBOTS,
        "/en/collections/optical": listing([card("optical", "agathe1", "AGATHE 1")], "/en/collections/optical?page=2", optical_facets),
        "/en/collections/optical?page=2": listing([card("optical", "mila4", "MILA 4")]),
        "/en/collections/sunglasses": listing([card("sunglasses", "sol1", "SOL 1"), card("sunglasses", "agathe1", "AGATHE 1")],
                                              facets=form({COLOR: ["Vert"]})),
        filter_url("optical", GENDER, "Woman"): listing([card("optical", "agathe1", "AGATHE 1")]),
        filter_url("optical", GENDER, "Man"): listing([card("optical", "mila4", "MILA 4")]),
        filter_url("optical", MATERIAL, "Acetate"): listing([card("optical", "agathe1", "AGATHE 1")]),
        filter_url("optical", MATERIAL, "Wood"): listing([card("optical", "mila4", "MILA 4")]),
        "/en/products/agathe1": product("agathe1", "AGATHE 1", {"Size": "M", "Shape": "Hexagonal", "Front material": "Acetate",
                                                                "Temple material": "Stainless steel", "Type": "Rimmed", "Gender": "Woman"}),
        "/en/products/mila4": product("mila4", "MILA 4", {"Shape": "Panto", "Front material": "Wood", "Type": "Semi-rimless"}),
        # /en/products/sol1 404s: its listing card alone must still give a valid product
    }
    for collection, frames in (("optical", ("agathe1", "mila4")), ("sunglasses", ("sol1",))):
        for label in {c for slug in frames for _, _, c in FRAMES[slug]}:
            # a variant-level filter lists a frame once, linking the FIRST variant that matches (not the default one);
            # the sunglasses cards carry no ?variant= at all, to check that nothing per-variant is recorded then
            cards = [card(collection, slug, slug.upper(),
                          next(vid for _, vid, c in FRAMES[slug] if c == label) if collection == "optical" else None)
                     for slug in frames if any(c == label for _, _, c in FRAMES[slug])]
            pages[filter_url(collection, COLOR, label)] = listing(cards)
    return pages


async def crawl_morel() -> tuple[dict[str, ScrapedProduct], list[httpx.URL]]:
    products, requested, _ = await crawl_morel_report()
    return products, requested


async def crawl_morel_report(without: tuple[str, ...] = ()):
    """(products, requested urls, CrawlReport); `without`: paths that 404."""
    cfg = load_store_configs()["morel.com"]
    pages, requested = {k: v for k, v in site().items() if k not in without}, []

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


def colors(p: ScrapedProduct) -> set[tuple]:
    return {(t.code, t.supplier_code) for t in tag_product(p.name, p.flags) if t.dimension == "color"}


@pytest.mark.anyio
async def test_morel_frames_are_presence_only_with_canonical_urls():
    products, _ = await crawl_morel()
    assert list(products) == ["agathe1", "mila4", "sol1"]                       # AGATHE 1 in both collections: one product
    assert all(p.db_url() == f"{MOREL}/en/products/{slug}" for slug, p in products.items())
    agathe = products["agathe1"]
    assert (agathe.name, agathe.brand, agathe.price, agathe.currency) == ("AGATHE 1", "Morel", None, None)  # analytics prices ignored
    assert agathe.flags["categories"] == "Optique, Solaire"
    assert (products["sol1"].name, products["sol1"].price) == ("SOL 1", None)   # product page 404: card only


@pytest.mark.anyio
async def test_morel_codes_get_their_colour_from_the_colour_filter():
    products, _ = await crawl_morel()
    agathe = products["agathe1"]
    assert agathe.flags["variants"] == [
        {"code": "BM02", "id": "64359734313337", "color": "Blue"},
        {"code": "NV03", "id": "64359734346105", "color": "Black"},
        {"code": "RP01", "id": "64359734378873", "color": "Red"}]                # not decoded from the code
    assert "variant_colors" not in agathe.flags                                 # the join map is not stored
    assert colors(agathe) == {("blue", "BM02"), ("black", "NV03"), ("red", "RP01")}
    mila = products["mila4"]                                                    # two tortoiseshell codes: the filter links one
    assert [v.get("color") for v in mila.flags["variants"]] == ["Tortoiseshell", None]
    assert mila.flags["raw_specs"]["Couleur"] == "Tortoiseshell"               # the frame still counts as tortoiseshell
    assert ("tortoiseshell", "EC01") in colors(mila)
    sol = products["sol1"]                                                      # filter card without ?variant=
    assert sol.flags["raw_specs"]["Couleur"] == "Vert" and "variant_colors" not in sol.flags
    assert colors(sol) == {("green", None)}                                     # frame-level colour, no code


@pytest.mark.anyio
async def test_morel_specs_give_shape_material_and_gender():
    products, _ = await crawl_morel()
    tags = lambda p: {(t.dimension, t.code) for t in tag_product(p.name, p.flags)}
    agathe = tags(products["agathe1"])
    assert {("shape", "geometric"), ("material", "acetate"), ("material", "metal"), ("audience", "women")} <= agathe
    mila = tags(products["mila4"])
    assert {("shape", "round"), ("material", "wood"), ("audience", "men")} <= mila
    assert ("shape", "rimless") not in mila                                     # "Semi-rimless" (Type) is not a shape label


@pytest.mark.anyio
async def test_morel_requests_respect_robots_and_never_combine_filters():
    _, requested = await crawl_morel()
    for url in (u for u in requested if u.path != "/robots.txt"):
        raw = url.raw_path.decode()
        assert "sort_by" not in raw and "+" not in raw and ".json" not in raw, raw
        assert sum(k.startswith("filter.") for k, _ in parse_qsl(urlsplit(raw).query)) <= 1, raw
    assert {u.path for u in requested if "/products/" in u.path} == {"/en/products/agathe1", "/en/products/mila4", "/en/products/sol1"}


@pytest.mark.anyio
async def test_morel_report_lists_every_frame_and_ignores_a_failing_colour_filter():
    products, _, report = await crawl_morel_report()
    assert report.complete and report.listed == {p.db_url() for p in products.values()}
    # the colour filter is an enrichment pass: losing one page loses a colour, not the frames
    products, _, report = await crawl_morel_report(without=(filter_url("optical", COLOR, "Red"),))
    assert report.complete and set(products) == {"agathe1", "mila4", "sol1"}
    # the second optical listing page is not: frames on it may exist without our knowing
    _, _, report = await crawl_morel_report(without=("/en/collections/optical?page=2",))
    assert not report.complete and report.problems == ["/en/collections/optical page 2: not fetched"]


# --- generic pieces -------------------------------------------------------------------------------

def test_canonical_url_joins_every_group_and_variant_ids_are_read_before():
    link = f"{MOREL}/en/collections/optical/products/agathe1?_pos=3&variant=64359734378873"
    assert canonical_url(link, r"(/en)/collections/[^/]+(/products/[^/?#]+)") == f"{MOREL}/en/products/agathe1"
    assert canonical_url(link, r"(/products/[^/?#]+)") == f"{MOREL}/products/agathe1"   # one group: as before (Etnia)
    assert link_variant_id(link) == "64359734378873" and link_variant_id(f"{MOREL}/en/products/x") is None


def test_shopify_variant_titles_reads_ids_and_titles_only_and_tolerates_bad_blocks():
    page = product("agathe1", "AGATHE 1", {})
    assert shopify_variant_titles(_tree(page)) == {"64359734313337": "BM02 AGATHE 1", "64359734346105": "NV03 AGATHE 1",
                                                   "64359734378873": "RP01 AGATHE 1"}
    assert shopify_variant_titles(_tree("<script>var meta = {broken;</script>")) == {}
    assert shopify_variant_titles(_tree("<p>no meta</p>")) == {}


@pytest.mark.anyio
async def test_morel_a_failing_colour_filter_page_is_a_per_variant_gap():
    _, _, report = await crawl_morel_report(without=(filter_url("optical", COLOR, "Red"),))
    (gap,) = report.gaps
    assert (gap.facet, gap.label, gap.flag, gap.per_variant) == ("Couleur", "Red", None, True) and report.complete
    _, _, report = await crawl_morel_report()
    assert report.gaps == []
