"""Cubitts (Shopify, UK): plain `rel=next` pages, product-level shape and material filters one at a time, colour
swatches as variants, and a best-sellers collection that only flags frames the other listings already found. Offline:
markup trimmed from the real pages (2026-09-30), served by httpx.MockTransport with the real robots.txt rules."""

import json
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import ListingUrl, load_store_configs, parse_store_configs
from app.collectors.stores.schemas import FacetGap, ScrapedProduct
from app.collectors.stores.service import carry_over
from app.collectors.stores.tagger import tag_product

CUB = "https://cubitts.com"
ROBOTS = """User-agent: *
Disallow: /*/cart/
Disallow: /collections/*sort_by*
Disallow: /*/collections/*sort_by*
Disallow: /collections/*+*
Disallow: /collections/*%2B*
Disallow: /collections/*filter*&*filter*
Disallow: /*/collections/*filter*&*filter*
"""
SHAPE, MATERIAL = "filter.p.m.custom.shape", "filter.p.m.custom.material"
SORT, COLOUR, SIZE = "filter.p.m.custom.sort_by", "filter.v.option.colour", "filter.v.option.size"

# slug -> (name, [colour names])
FRAMES = {
    "albion": ("Albion", ["Khaki", "Black", "Celadon"]),
    "eyre-spectacles": ("Eyre", ["Crimson Wash", "Ink Wash"]),
    "dalmeny": ("Dalmeny", ["Khaki", "Black", "Slate", "Dark Turtle", "Haze"]),
    "cyrus": ("Cyrus", ["Black"]),
    "clayton-sunglass": ("Clayton", ["Beechwood Fade", "Dark Turtle", "Black"]),
    "brydon-sunglass": ("Brydon", ["Black"]),
    "laystall-sunglass": ("Laystall", ["Crystal"]),
}
PLACEMENT = {  # collection -> pages of slugs
    "spectacles": [["albion", "eyre-spectacles", "dalmeny"], ["cyrus"]],
    "sunglasses": [["clayton-sunglass", "brydon-sunglass"], ["laystall-sunglass"]],
}
BEST = [["albion", "ghost"], ["cyrus"]]      # "ghost" is only in the best-sellers list: it is not a frame of the shelves
SHAPES = {"spectacles": {"Square": ["albion", "dalmeny"], "Cat-eye": ["eyre-spectacles"], "Round": ["cyrus"]},
          "sunglasses": {"Square": ["clayton-sunglass"], "Round": ["brydon-sunglass", "laystall-sunglass"]}}
MATERIALS = {"spectacles": {"Acetate": ["albion", "dalmeny", "cyrus"], "Steel": ["eyre-spectacles"]},
             "sunglasses": {"Acetate": ["clayton-sunglass", "brydon-sunglass", "laystall-sunglass"]}}


def card(slug: str) -> str:
    name = FRAMES.get(slug, (slug.title(), []))[0]
    return (f'<product-card class=" product-card product-list__item" data-show-index="true"><div class="product-card__media">'
            f'<a class="product-card__link" href="/products/{slug}">{name}</a></div></product-card>')


def form(collection: str) -> str:
    def group(param, options):
        return "".join(f'<input type="checkbox" name="{param}" id="{param}-{i}" value="{v}"><label for="{param}-{i}">{v}</label>'
                       for i, v in enumerate(options, start=1))
    return (group(SHAPE, SHAPES[collection]) + group(MATERIAL, MATERIALS[collection]) + group(SORT, ["Bestsellers", "New in"])
            + f'<input type="checkbox" name="{COLOUR}" id="c1" value="gid://shopify/FilterSettingGroup/1"><label for="c1">Crimson Wash</label>'
            + f'<input type="checkbox" name="{SIZE}" id="s1" value="gid://shopify/FilterSettingGroup/2"><label for="s1">Medium</label>')


def listing(slugs, *, next_href=None, collection=None) -> str:
    head = f'<link rel="next" href="{next_href}">' if next_href else ""
    return f'<html><head>{head}</head><body>{form(collection) if collection else ""}{"".join(card(s) for s in slugs)}</body></html>'


def product_page(slug: str) -> str:
    name, colours = FRAMES[slug]
    offers = [{"@type": "Offer", "name": f"M|Medium / {c} / Prescription", "price": 175.0, "priceCurrency": "GBP",
               "availability": "https://schema.org/InStock", "url": f"{CUB}/products/{slug}?variant={i}"} for i, c in enumerate(colours, start=1)]
    ld = {"@context": "http://schema.org/", "@type": "Product", "name": name, "url": f"{CUB}/products/{slug}",
          "brand": {"@type": "Brand", "name": "Cubitts"}, "offers": offers}
    swatches = "".join(f'<input class="product-color-swatch__radio" type="radio" name="Colour" value="{c}" data-value="{c}" '
                       f'data-variant-url="/products/{slug}?variant={i}">' for i, c in enumerate(colours, start=1))
    return (f'<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head>'
            f'<body><h1>{name}</h1><div class="product-color-swatch">{swatches}</div></body></html>')


def filter_url(collection: str, param: str, value: str, page: int | None = None) -> str:
    return f"/collections/{collection}?{urlencode({param: value, **({'page': page} if page else {})}, quote_via=quote)}"


def site() -> dict[str, str]:
    pages = {"/robots.txt": ROBOTS}
    for collection, chunks in PLACEMENT.items():
        for i, slugs in enumerate(chunks, start=1):
            more = f"/collections/{collection}?page={i + 1}" if i < len(chunks) else None
            pages[f"/collections/{collection}" + (f"?page={i}" if i > 1 else "")] = listing(slugs, next_href=more, collection=collection if i == 1 else None)
        for param, groups in ((SHAPE, SHAPES[collection]), (MATERIAL, MATERIALS[collection])):
            for value, slugs in groups.items():
                pages[filter_url(collection, param, value)] = listing(slugs)
    for i, slugs in enumerate(BEST, start=1):
        pages["/collections/bestselling-glasses" + (f"?page={i}" if i > 1 else "")] = listing(slugs, next_href="/collections/bestselling-glasses?page=2" if i == 1 else None)
    for slug in FRAMES:
        pages[f"/products/{slug}"] = product_page(slug)
    return pages


async def crawl_cubitts(without: tuple[str, ...] = (), cfg=None):
    cfg = cfg or load_store_configs()["cubitts.com"]
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


def tags(p: ScrapedProduct) -> set[tuple]:
    return {(t.dimension, t.code, t.supplier_code) for t in tag_product(p.name, p.flags)}


# --- the crawl ---------------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_every_page_of_both_collections_is_followed_and_each_frame_read_once():
    products, requested, report = await crawl_cubitts()
    assert sorted(products) == sorted(FRAMES) and report.complete
    paths = {u.raw_path.decode() for u in requested}
    assert {"/collections/spectacles?page=2", "/collections/sunglasses?page=2"} <= paths
    albion = products["albion"]
    assert (albion.name, albion.brand, albion.price, albion.currency) == ("Albion", "Cubitts", 175.0, "GBP")
    assert albion.db_url() == f"{CUB}/products/albion"
    assert albion.flags["categories"] == "Optique" and products["clayton-sunglass"].flags["categories"] == "Solaire"
    assert ("product_type", "optical", None) in tags(albion) and ("product_type", "sun", None) in tags(products["laystall-sunglass"])


@pytest.mark.anyio
async def test_colour_swatches_are_the_variants_and_the_store_name_is_the_code():
    products, _, _ = await crawl_cubitts()
    variants = products["dalmeny"].flags["variants"]
    assert [(v["code"], v["color"]) for v in variants] == [(c, c) for c in FRAMES["dalmeny"][1]]
    colours = {(c, s) for d, c, s in tags(products["dalmeny"]) if d == "color"}
    # plain names give their family with the name as Palier 3; names the taxonomy does not know (Dark Turtle, Haze) stay untagged, never guessed
    assert colours == {("green", "Khaki"), ("black", "Black"), ("grey", "Slate")}
    eyre = {(c, s) for d, c, s in tags(products["eyre-spectacles"]) if d == "color"}
    assert eyre == {("red", "Crimson Wash")}                              # "Ink Wash" is not known: waiting for the crawl's report


@pytest.mark.anyio
async def test_shape_and_material_come_from_the_product_level_filters():
    products, _, _ = await crawl_cubitts()
    assert products["eyre-spectacles"].flags["raw_specs"] == {"Shape": "Cat-eye", "Materials": "Steel"}
    assert ("shape", "cat_eye", None) in tags(products["eyre-spectacles"]) and ("material", "metal", None) in tags(products["eyre-spectacles"])
    assert ("shape", "square", None) in tags(products["albion"]) and ("material", "acetate", None) in tags(products["albion"])
    assert ("shape", "round", None) in tags(products["brydon-sunglass"])


@pytest.mark.anyio
async def test_only_frames_the_shelves_list_are_flagged_best_sellers_and_true_only():
    products, requested, report = await crawl_cubitts()
    assert {s for s, p in products.items() if p.flags.get("is_bestseller") is True} == {"albion", "cyrus"}
    assert all("is_bestseller" not in p.flags for s, p in products.items() if s not in ("albion", "cyrus"))   # unset, never False
    assert "ghost" not in products and f"{CUB}/products/ghost" not in report.listed                        # a list-only frame is no frame
    assert "/products/ghost" not in {u.path for u in requested}
    assert any(u.path == "/collections/bestselling-glasses" and u.query == b"page=2" for u in requested)  # the flag list's page 2 too


@pytest.mark.anyio
async def test_requests_respect_robots_one_filter_no_sort_no_plus_and_no_colour_or_size_pass():
    _, requested, _ = await crawl_cubitts()
    for url in (u for u in requested if u.path != "/robots.txt"):
        raw = url.raw_path.decode()
        assert "sort_by" not in raw and "+" not in raw and ".json" not in raw, raw
        assert "filter.v.option" not in raw, raw                          # the colour and size filters are not used
        assert sum(k.startswith("filter.") for k, _ in parse_qsl(urlsplit(raw).query)) <= 1, raw
    assert any(u.raw_path.decode() == filter_url("spectacles", SHAPE, "Cat-eye") for u in requested)


@pytest.mark.anyio
async def test_the_order_of_the_listings_in_the_config_does_not_matter():
    cfg = load_store_configs()["cubitts.com"]
    first, *rest = cfg.listing.urls[2], *cfg.listing.urls[:2]              # the flag listing first
    reordered = cfg.model_copy(update={"listing": cfg.listing.model_copy(update={"urls": [first, *rest]})})
    products, _, _ = await crawl_cubitts(cfg=reordered)
    assert {s for s, p in products.items() if p.flags.get("is_bestseller")} == {"albion", "cyrus"} and sorted(products) == sorted(FRAMES)


@pytest.mark.anyio
async def test_a_failing_best_sellers_page_is_a_gap_that_keeps_the_previous_flags():
    products, _, report = await crawl_cubitts(without=("/collections/bestselling-glasses?page=2",))
    (gap,) = report.gaps
    assert (gap.facet, gap.flag) == ("is_bestseller", "is_bestseller") and gap.url.endswith("bestselling-glasses?page=2")
    assert report.complete                                                 # the shelves were read in full: drops stay possible
    assert products["albion"].flags["is_bestseller"] is True and "is_bestseller" not in products["cyrus"].flags
    assert carry_over({"is_bestseller": True}, products["cyrus"].flags, report.gaps)["is_bestseller"] is True   # cyrus keeps its flag


# --- generic pieces ------------------------------------------------------------------------------------

YAML = """
stores:
  shop.test:
    name: Shop
    base_url: https://shop.test
    lang: en
    listing: {urls: ['/x', {url: '/best', flag: is_bestseller}], product: 'li', link: 'a'}
"""


def test_a_flag_listing_needs_an_identifier_no_categories_and_a_main_listing_beside_it():
    cfg = parse_store_configs(YAML)["shop.test"]
    assert cfg.listing.urls == ["/x", ListingUrl(url="/best", flag="is_bestseller")]
    for bad in ("{url: '/best', flag: 'is best'}", "{url: '/best', flag: is_bestseller, categories: Optique}"):
        with pytest.raises(ValueError):
            parse_store_configs(YAML.replace("{url: '/best', flag: is_bestseller}", bad))
    with pytest.raises(ValueError, match="not a flag-only"):
        parse_store_configs(YAML.replace("'/x', ", ""))


def test_the_shipped_entry_is_a_uk_brand_catalog():
    cfg = load_store_configs()["cubitts.com"]
    assert (cfg.country, cfg.default_brand) == ("GB", None)
    assert [f.param for f in cfg.listing.facets] == [SHAPE, MATERIAL]        # never the sort_by, colour or size filters
    assert cfg.listing.urls[2] == ListingUrl(url="/collections/bestselling-glasses", flag="is_bestseller")
    assert cfg.variants.rows == "input.product-color-swatch__radio[name='Colour']" and cfg.variants.code.attr == "value"


def test_facet_gap_notes_name_the_flag_listing():
    assert FacetGap("is_bestseller", "list", "is_bestseller", False, f"{CUB}/collections/bestselling-glasses?page=2").note == (
        "facet is_bestseller = list (/collections/bestselling-glasses): not fetched")
