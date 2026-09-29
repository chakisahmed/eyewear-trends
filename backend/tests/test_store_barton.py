"""Barton Perreira (Shopify, USA): colourways from JSON-LD offers, a compound colour name of which only the front is the
frame's colour, one product per model when a model is sold once per size, and single-filter passes that respect the real
robots.txt. Offline: markup trimmed from the real pages (2026-09-29), served by httpx.MockTransport."""

import json
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import ColorSplit, VariantsRule, load_store_configs, parse_store_configs
from app.collectors.stores.parser import _tree, model_key, offer_variants, parse_product_page, split_color
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product

BP = "https://bartonperreira.com"
ROBOTS = """User-agent: *
Disallow: /*/cart/
Disallow: /collections/*sort_by*
Disallow: /*/collections/*sort_by*
Disallow: /collections/*+*
Disallow: /collections/*%2B*
Disallow: /*/collections/*+*
Disallow: /collections/*filter*&*filter*
Disallow: /*/collections/*filter*&*filter*
"""
SHAPE, MATERIAL = "filter.v.m.filter.shape", "filter.v.m.filter.material"
IN, OUT = "https://schema.org/InStock", "https://schema.org/OutOfStock"

# slug -> (name as the card and page show it, [(colour name, sku, availability)])
FRAMES = {
    "euclid": ("Euclid", [("Black / Clear / Black / Pewter", "EUCLAF5301", IN),
                          ("Absinthe / Clear / Chestnut / Antique Gold", "EUCLAF5302", OUT),
                          ("Hickory Gradient / Clear / Hickory Gradient / Pewter", "EUCLAF5303", IN)]),
    "norton-46": ("Norton (46)", [("Chestnut", "NORT4601", IN), ("Black", "NORT4602", IN)]),
    "norton-48": ("Norton (48)", [("Chestnut", "NORT4801", IN)]),
    "banks-48": ("Banks (48)", [("Espresso", "BANK4801", OUT), ("Black", "BANK4802", OUT)]),   # every colourway sold out
    "cassady-47": ("Cassady (47)", [("Black", "CASS4701", IN)]),
    "lamarr": ("Lamarr", [("Heroine Chic / Smolder (AR)", "LAMA5002", IN), ("Black / Noir (AR)", "LAMA5001", IN)]),
}
PLACEMENT = {  # collection -> (page 1 slugs, page 2 slugs)
    "optical-collection": (["euclid", "norton-46", "norton-48", "banks-48"], ["cassady-47"]),
    "sunglass-collection": (["lamarr"], []),
}
SHAPES = {"optical-collection": {"Cat Eye": ["euclid"], "Cateye": ["banks-48"], "Round": ["norton-46", "norton-48"]},
          "sunglass-collection": {"Cat Eye": ["lamarr"]}}
MATERIALS = {"optical-collection": {"Titanium": ["euclid"], "Acetate": ["banks-48", "norton-46", "cassady-47"]},
             "sunglass-collection": {"Acetate": ["lamarr"]}}


def card(slug: str) -> str:
    name = FRAMES[slug][0]
    return (f'<product-item class="product-item product-item--custom "><div class="product-item__info-top">'
            f'<a href="/products/{slug}"><div class="product-item-meta__title">{name}</div></a></div>'
            f'<div class="product-item__image-wrapper"><a href="/products/{slug}"><img alt=""></a></div></product-item>')


def form(collection: str) -> str:
    def group(param, options):
        return "".join(f'<input type="checkbox" name="{param}" id="{param}-{i}-{layout}" value="{v}">'
                       f'<label for="{param}-{i}-{layout}">{v}</label>'
                       for layout in ("d", "m") for i, v in enumerate(options, start=1))
    return group(SHAPE, SHAPES[collection]) + group(MATERIAL, MATERIALS[collection])


def listing(collection: str, slugs: list[str], next_href: str | None = None, with_form: bool = True) -> str:
    head = f'<link rel="next" href="{next_href}">' if next_href else ""
    return f'<html><head>{head}</head><body>{form(collection) if with_form else ""}{"".join(card(s) for s in slugs)}</body></html>'


def product_page(slug: str) -> str:
    name, colourways = FRAMES[slug]
    offers = [{"@type": "Offer", "name": colour, "availability": availability, "price": "670.0", "priceCurrency": "USD",
               "sku": sku, "url": f"{BP}/products/{slug}?variant={i}"} for i, (colour, sku, availability) in enumerate(colourways, start=1)]
    ld = {"@context": "http://schema.org/", "@type": "Product", "name": name, "url": f"{BP}/products/{slug}",
          "brand": {"@type": "Brand", "name": "Barton Perreira"}, "offers": offers}
    return f'<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head><body><h1>{name}</h1></body></html>'


def filter_url(collection: str, param: str, value: str, page: int | None = None) -> str:
    return f"/collections/{collection}?{urlencode({param: value, **({'page': page} if page else {})}, quote_via=quote)}"


def site() -> dict[str, str]:
    pages = {"/robots.txt": ROBOTS}
    for collection, (first, second) in PLACEMENT.items():
        pages[f"/collections/{collection}"] = listing(collection, first, f"/collections/{collection}?page=2" if second else None)
        if second:
            pages[f"/collections/{collection}?page=2"] = listing(collection, second, with_form=False)
        for param, groups in ((SHAPE, SHAPES[collection]), (MATERIAL, MATERIALS[collection])):
            for value, slugs in groups.items():
                pages[filter_url(collection, param, value)] = listing(collection, slugs, with_form=False)
    for slug in FRAMES:
        pages[f"/products/{slug}"] = product_page(slug)
    return pages


async def crawl_barton():
    cfg = load_store_configs()["bartonperreira.com"]
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


# --- the crawl on the real page shapes ---------------------------------------------------------------

@pytest.mark.anyio
async def test_one_product_per_model_named_without_its_size_and_never_dropped():
    products, requested, report = await crawl_barton()
    assert sorted(products) == ["banks-48", "cassady-47", "euclid", "lamarr", "norton-46"]      # norton-48 is another size
    assert [p.name for p in (products["norton-46"], products["cassady-47"], products["banks-48"])] == ["Norton", "Cassady", "Banks"]
    assert f"{BP}/products/norton-48" in report.listed and report.complete                     # on the shelf: nothing is dropped
    assert "/products/norton-48" not in {u.path for u in requested}                            # neither fetched nor stored
    euclid = products["euclid"]
    assert (euclid.name, euclid.brand, euclid.price, euclid.currency) == ("Euclid", "Barton Perreira", 670.0, "USD")
    assert euclid.db_url() == f"{BP}/products/euclid"
    assert euclid.flags["categories"] == "Optique" and products["lamarr"].flags["categories"] == "Solaire"


@pytest.mark.anyio
async def test_only_the_front_of_a_compound_colour_is_the_frames_colour_and_codes_are_the_skus():
    products, _, _ = await crawl_barton()
    variants = products["euclid"].flags["variants"]
    assert [(v["code"], v["color"], v["in_stock"]) for v in variants] == [
        ("EUCLAF5301", "Black", True), ("EUCLAF5302", "Absinthe", False), ("EUCLAF5303", "Hickory Gradient", True)]
    assert variants[1]["parts"] == ["Absinthe", "Clear", "Chestnut", "Antique Gold"]            # kept, not tagged
    lamarr = products["lamarr"].flags["variants"]
    assert lamarr[0] == {"code": "LAMA5002", "color": "Heroine Chic", "in_stock": True, "parts": ["Heroine Chic", "Smolder (AR)"]}
    colours = {t for t in tags(products["euclid"]) if t[0] == "color"}
    # not "clear" (that is the lens), no marketing name is guessed (Absinthe: none yet); "Hickory Gradient" is a brown that is also a gradient
    assert colours == {("color", "black", "EUCLAF5301"), ("color", "brown", "EUCLAF5303"), ("color", "two_tone", "EUCLAF5303")}
    norton = tags(products["norton-46"])
    assert ("color", "brown", "NORT4601") in norton and ("color", "black", "NORT4602") in norton   # Chestnut is a plain brown


@pytest.mark.anyio
async def test_stock_is_per_colourway_and_a_frame_is_sold_out_only_when_every_colourway_is():
    products, _, _ = await crawl_barton()
    assert products["euclid"].flags.get("out_of_stock") is False                               # one colourway is still available
    assert products["banks-48"].flags["out_of_stock"] is True


@pytest.mark.anyio
async def test_both_spellings_of_cat_eye_and_the_material_come_from_the_filters():
    products, _, _ = await crawl_barton()
    assert products["euclid"].flags["raw_specs"] == {"Shape": "Cat Eye", "Materials": "Titanium"}
    assert products["banks-48"].flags["raw_specs"] == {"Shape": "Cateye", "Materials": "Acetate"}
    assert ("shape", "cat_eye", None) in tags(products["euclid"]) and ("shape", "cat_eye", None) in tags(products["banks-48"])
    assert ("shape", "round", None) in tags(products["norton-46"])
    assert ("material", "titanium", None) in tags(products["euclid"]) and ("material", "acetate", None) in tags(products["lamarr"])
    assert ("product_type", "sun", None) in tags(products["lamarr"]) and ("product_type", "optical", None) in tags(products["euclid"])


@pytest.mark.anyio
async def test_requests_respect_robots_one_filter_no_sort_no_plus():
    _, requested, _ = await crawl_barton()
    for url in (u for u in requested if u.path != "/robots.txt"):
        raw = url.raw_path.decode()
        assert "sort_by" not in raw and "+" not in raw and ".json" not in raw, raw
        assert sum(k.startswith("filter.") for k, _ in parse_qsl(urlsplit(raw).query)) <= 1, raw
    assert any(u.raw_path.decode() == filter_url("optical-collection", SHAPE, "Cat Eye") for u in requested)   # spaces are %20


def test_the_shipped_entry_is_a_us_brand_catalog_with_json_ld_variants():
    cfg = load_store_configs()["bartonperreira.com"]
    assert (cfg.country, cfg.default_brand, cfg.name_strip) == ("US", "Barton Perreira", r"\s*\(\d{2}\)$")
    assert cfg.variants.json_ld_offers and cfg.variants.color_split == ColorSplit(sep=" / ", color=0)
    assert [f.param for f in cfg.listing.facets] == [SHAPE, MATERIAL] and cfg.listing.pagination.next == "link[rel=next]"
    assert [(k, model_key(f"{BP}/products/{k}", cfg.listing.model_regex)) for k in ("norton-48", "lamarr", "princeton-49")] == [
        ("norton-48", "norton"), ("lamarr", "lamarr"), ("princeton-49", "princeton")]


# --- the generic pieces -----------------------------------------------------------------------------

def offer(name, sku, availability=IN, **extra):
    return {"@type": "Offer", "name": name, "sku": sku, "availability": availability, **extra}


def test_offer_variants_read_sku_name_and_stock_never_the_price():
    node = {"offers": [offer("Black", "A1", price="670"), offer("Tortoise", "A2", OUT, price="670"), offer("Black", "A1"),
                       {"@type": "Offer", "name": "No sku"}, {"sku": "A9"}, "junk", offer("Blue", "A3", "https://schema.org/SoldOut")]}
    assert offer_variants(node) == [{"code": "A1", "color": "Black", "in_stock": True}, {"code": "A2", "color": "Tortoise", "in_stock": False},
                                    {"code": "A3", "color": "Blue", "in_stock": False}]           # one per sku, the first wins
    assert offer_variants({"offers": offer("Solo", "S1")}) == [{"code": "S1", "color": "Solo", "in_stock": True}]   # a single offer, not a list
    assert offer_variants({"offers": offer("No stock info", "S2", availability=None)})[0].get("in_stock") is None
    assert offer_variants({}) == [] and offer_variants(None) == [] and offer_variants({"offers": "broken"}) == []


@pytest.mark.parametrize("label, expected_color, expected_parts", [
    ("Black", "Black", None),                                                         # one part: nothing to split
    ("Heroine Chic / Smolder (AR)", "Heroine Chic", ["Heroine Chic", "Smolder (AR)"]),
    ("Absinthe / Clear / Chestnut / Antique Gold", "Absinthe", ["Absinthe", "Clear", "Chestnut", "Antique Gold"]),
    ("  Black  /  Clear ", "Black", ["Black", "Clear"]),                                # spaces around the parts
    (" / Clear", None, ["", "Clear"]),                                                # no front colour: no colour rather than a wrong one
])
def test_split_color_keeps_the_frame_part_and_all_parts(label, expected_color, expected_parts):
    variants = [{"code": "X", "color": label}]
    split_color(variants, ColorSplit())
    assert variants[0].get("color") == expected_color and variants[0].get("parts") == expected_parts


def test_split_color_can_pick_another_part_and_ignores_variants_without_a_color():
    variants = [{"code": "X", "color": "Black / Grey Gradient"}, {"code": "Y"}, {"code": "Z", "color": "Solo"}]
    split_color(variants, ColorSplit(color=1))
    assert variants == [{"code": "X", "color": "Grey Gradient", "parts": ["Black", "Grey Gradient"]}, {"code": "Y"}, {"code": "Z"}]


def test_variants_rule_needs_exactly_one_source():
    assert VariantsRule(json_ld_offers=True).rows is None
    assert VariantsRule(rows="label", code={"regex": "^(\\S+)"}).json_ld_offers is False
    for bad in ({}, {"json_ld_offers": True, "rows": "label", "code": {}}, {"rows": "label"}, {"code": {}}):
        with pytest.raises(ValueError):
            VariantsRule(**bad)


YAML = """
stores:
  shop.test:
    name: Shop
    base_url: https://shop.test
    lang: en
    listing: {urls: ['/x'], product: 'li', link: 'a', model_regex: '^https://[^/]+/p/(.+?)(?:-\\d{2})?$'}
    product_pages: {enabled: true}
    variants: {json_ld_offers: true}
"""


def test_a_product_page_without_offers_gives_no_variants_and_a_page_with_them_gives_the_frames_stock():
    cfg = parse_store_configs(YAML)["shop.test"]
    empty = parse_product_page("<html><script type='application/ld+json'>{\"@type\":\"Product\",\"name\":\"X\"}</script></html>", "https://shop.test/p/x", cfg)
    assert "variants" not in empty.flags
    ld = {"@type": "Product", "name": "X", "offers": [offer("Black", "B1", OUT), offer("Blue", "B2", OUT)]}
    page = parse_product_page(f"<html><script type='application/ld+json'>{json.dumps(ld)}</script></html>", "https://shop.test/p/x", cfg)
    assert [v["code"] for v in page.flags["variants"]] == ["B1", "B2"] and page.flags["out_of_stock"] is True


def test_model_key_and_the_config_validators():
    regex = r"^https://[^/]+/p/(.+?)(?:-\d{2})?$"
    assert [model_key(f"https://shop.test/p/{s}", regex) for s in ("norton-46", "norton-48", "norton", "a-b-12")] == ["norton", "norton", "norton", "a-b"]
    assert model_key("https://elsewhere.test/x", regex) is None and model_key("https://shop.test/p/x", None) is None
    with pytest.raises(ValueError, match="capture group"):
        parse_store_configs(YAML.replace("(.+?)", ".+?"))
    with pytest.raises(ValueError):
        parse_store_configs(YAML.replace("lang: en", "lang: en\n    name_strip: '(unclosed'"))
