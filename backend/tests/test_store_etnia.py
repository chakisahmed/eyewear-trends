"""Etnia Barcelona (Shopify, creator brand): facet passes, canonical product URLs, color variants (Palier 3), and
the generic crawler additions they brought. Offline: markup trimmed from the real site (2026-09-29), served by
httpx.MockTransport with the real robots.txt rules."""

import json
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

import httpx
import pytest
from sqlalchemy import select

from app.collectors.stores.base import BaseStoreCrawler, add_label
from app.collectors.stores.config import load_store_configs, parse_store_configs
from app.collectors.stores.parser import canonical_url, facet_values
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.service import StoreSyncService
from app.collectors.stores.tagger import tag_product
from app.db import SessionLocal, init_db
from app.models import Product

from tests.test_store_crawlers import BASE, CONFIG_YAML

ETNIA = "https://etniabarcelona.com"
# The "User-agent: *" group of the real robots.txt, trimmed to the rules a catalog crawl can meet.
ROBOTS = """User-agent: *
Disallow: /cart
Disallow: /account
Disallow: /collections/*sort_by*
Disallow: /*/collections/*sort_by*
Disallow: /collections/*+*
Disallow: /collections/*%2B*
Disallow: /collections/*%2b*
Disallow: */collections/*filter*&*filter*
Disallow: /search
Disallow: /recommendations/products
"""
SHAPE, GENDER, MATERIAL = "filter.p.m.custom.shape", "filter.v.m.custom.gender", "filter.p.m.custom.material"
GID = {"OVAL": "519865794937", "PANTOS SQUARE": "519865860473", "CAT-EYE/BUTTERFLY": "519865696633", "ROUND": "519865991545",
       "Man": "542791565689", "Woman": "542791598457", "Unisex": "542791631225", "Acetate": "542791827833", "Metal": "542791893369"}


def gid(label: str) -> str:
    return f"gid://shopify/Metaobject/{GID[label]}"


def filter_url(collection: str, param: str, label: str, page: int | None = None) -> str:
    """The path + query the crawler builds for one filter value (':' and '/' escaped, as the store's own links do)."""
    q = urlencode({param: gid(label), **({"page": page} if page else {})}, quote_via=quote)
    return f"/collections/{collection}?{q}"


# --- markup ---------------------------------------------------------------------------------------

def card(collection: str, slug: str, name: str, price: str, variant: int = 64506181484921) -> str:
    return (
        f'<li class="product-grid__item product-grid__item--0" data-page="1" data-product-id="15768901321081" ref="cards[]">'
        f'<product-card class="product-card size-style" data-product-id="15768901321081">'
        f'<a href="/collections/{collection}/products/{slug}?variant={variant}" class="product-card__link" '
        f'ref="productCardLink"><span class="visually-hidden"> {name} </span></a>'
        f'<div class="product-card__content"><a class="contents" ref="cardGalleryLink" '
        f'href="/collections/{collection}/products/{slug}?variant={variant}" aria-label="{name}"></a>'
        f'<div class="price__regular"><span class="price">{price} €</span></div></div></product-card></li>'
    )


def facet_form(options: dict[str, list[str]]) -> str:
    """The filter form, rendered twice like the theme does (horizontal bar + vertical drawer). The shape filter has
    an aria-label; gender and material only a <label for>. A filter the config does not use is present too."""
    html = []
    for layout in ("horizontal-", "vertical-true"):
        for param, labels in options.items():
            for label in labels:
                iid = f"Filter-{param.replace('.', '-')}-gid-shopify-metaobject-{GID[label]}-{layout}"
                aria = f' aria-label="{label}"' if param == SHAPE else ""
                html.append(f'<input type="checkbox" name="{param}" value="{gid(label)}" id="{iid}"{aria}>'
                            f'<label for="{iid}">{label.title() if param == SHAPE else label}</label>')
        html.append(f'<input type="checkbox" name="filter.p.m.custom.product_title" value="KORE" '
                    f'id="Filter-product_title-kore-{layout}"><label for="Filter-product_title-kore-{layout}">KORE</label>')
    return f'<form id="FacetFiltersForm">{"".join(html)}</form>'


def listing(cards: list[str], next_href: str | None = None, form: str = "") -> str:
    head = f'<link rel="next" href="{next_href}">' if next_href else ""
    more = f'<load-more-products data-next-url="{next_href}"></load-more-products>' if next_href else ""
    return f'<html><head>{head}</head><body>{form}<ul class="product-grid">{"".join(cards)}</ul>{more}</body></html>'


def product(slug: str, name: str, price: str, swatches: list[tuple[str, str, bool]], *, lenses: bool = False) -> str:
    offers = [{"@type": "Offer", "price": price, "priceCurrency": "EUR", "sku": f"5 {name} 54O {code.replace('/', '')}",
               "url": f"{ETNIA}/products/{slug}?variant={640 + i}",
               "availability": f"https://schema.org/{'InStock' if ok else 'OutOfStock'}"}
              for i, (code, _, ok) in enumerate(swatches)]
    ld = {"@context": "https://schema.org", "@type": "Product", "name": name,
          "brand": {"@type": "Brand", "name": "ETNIA BARCELONA"}, "url": f"{ETNIA}/products/{slug}",
          "image": f"https://scdn.speedsize.com/f325/https://etniabarcelona.com/cdn/shop/files/5-{name}-54O_2_1200x.jpg",
          "offers": offers}
    radios = "".join(
        f'<label class="variant-option__button-label variant-option__button-label--has-swatch">'
        f'<input type="radio" name="Color-AVlJwVEgrZEpsWmVXR__variant_picker_R3rGDr-15768901321081" value="{code}" '
        f'aria-label="{label}{"" if ok else " - Notify me"}" data-option-available="{str(ok).lower()}" '
        f'data-variant-id="{640 + i}" data-option-display-label="{label}">'
        f'<span class="swatch swatch--variant-image"></span><span class="visually-hidden">{label}</span></label>'
        for i, (code, label, ok) in enumerate(swatches))
    lens = ('<input type="radio" name="LensName-AVlJwVEgrZEpsWmVXR__variant_picker_R3rGDr-15768901321081" value="GY" '
            'aria-label="Grey" data-option-available="true" data-option-display-label="Grey">') if lenses else ""
    return (f'<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head><body>'
            f'<variant-picker><fieldset class="variant-option">{radios}</fieldset>'
            f'<fieldset class="variant-option">{lens}</fieldset></variant-picker></body></html>')


def site() -> dict[str, str]:
    optical_form = facet_form({SHAPE: ["OVAL", "PANTOS SQUARE", "CAT-EYE/BUTTERFLY"], GENDER: ["Man", "Woman", "Unisex"],
                               MATERIAL: ["Acetate", "Metal"]})
    return {
        "/robots.txt": ROBOTS,
        "/collections/optical": listing(
            [card("optical", "kore", "KORE", "255,46"), card("optical", "mao", "MAO", "229,00"),
             card("optical", "kore", "KORE", "255,46", variant=64506181550457)],   # another color of KORE: same product
            "/collections/optical?page=2", optical_form),
        "/collections/optical?page=2": listing([card("optical", "xylo", "XYLO", "199,00"),
                                                card("optical", "vreeland", "VREELAND", "239,00")]),
        filter_url("optical", SHAPE, "OVAL"): listing([card("optical", "kore", "KORE", "255,46")]),
        filter_url("optical", SHAPE, "PANTOS SQUARE"): listing(
            [card("optical", "mao", "MAO", "229,00")], filter_url("optical", SHAPE, "PANTOS SQUARE", page=2)),
        filter_url("optical", SHAPE, "PANTOS SQUARE", page=2): listing([card("optical", "xylo", "XYLO", "199,00")]),
        filter_url("optical", SHAPE, "CAT-EYE/BUTTERFLY"): listing([card("optical", "vreeland", "VREELAND", "239,00")]),
        filter_url("optical", GENDER, "Man"): listing([card("optical", "kore", "KORE", "255,46"), card("optical", "mao", "MAO", "229,00")]),
        filter_url("optical", GENDER, "Woman"): listing([card("optical", "kore", "KORE", "255,46"),
                                                         card("optical", "vreeland", "VREELAND", "239,00")]),
        filter_url("optical", GENDER, "Unisex"): listing([]),
        filter_url("optical", MATERIAL, "Acetate"): listing([card("optical", "kore", "KORE", "255,46"),
                                                             card("optical", "unlisted", "UNLISTED", "99,00")]),
        filter_url("optical", MATERIAL, "Metal"): listing([card("optical", "xylo", "XYLO", "199,00")]),
        "/collections/sun": listing([card("sun", "izzi", "IZZI", "262,46")], form=facet_form({SHAPE: ["ROUND"]})),
        filter_url("sun", SHAPE, "ROUND"): listing([card("sun", "izzi", "IZZI", "262,46")]),
        "/products/kore": product("kore", "KORE", "255.46", [
            ("HV/BL", "Havana", True), ("BE", "Beige", False), ("BK", "Black", True), ("BL/HO", "Blue", True),
            ("OG", "Orange", True)]),
        "/products/mao": product("mao", "MAO", "229.00", [("BK", "Black", True)]),
        "/products/vreeland": product("vreeland", "VREELAND", "239.00", [("GD", "Golden", True), ("GD/BK", "Golden", True)]),
        "/products/izzi": product("izzi", "IZZI", "262.46", [("BK/ZE", "Black", False), ("HV/CL", "Havana", False)],
                                  lenses=True),
        # /products/xylo 404s: its listing card alone must still give a valid product
    }


async def crawl_etnia() -> tuple[dict[str, ScrapedProduct], list[httpx.URL]]:
    cfg = load_store_configs()["etniabarcelona.com"]
    pages, requested = site(), []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url)
        path = request.url.raw_path.decode()
        return httpx.Response(200, text=pages[path]) if path in pages else httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products = {p.db_url().rsplit("/", 1)[-1]: p for p in await crawler.crawl()}
    return products, requested


@pytest.fixture
def anyio_backend():
    return "asyncio"


def tags(p: ScrapedProduct) -> set[tuple]:
    return {(t.dimension, t.code, t.supplier_code) for t in tag_product(p.name, p.flags)}


# --- the shipped rules on recorded markup ---------------------------------------------------------

@pytest.mark.anyio
async def test_etnia_products_prices_categories_and_canonical_urls():
    products, requested = await crawl_etnia()
    assert list(products) == ["kore", "mao", "xylo", "vreeland", "izzi"]           # listing order; KORE's 2nd color merged
    assert all(p.db_url() == f"{ETNIA}/products/{slug}" for slug, p in products.items())  # no collection, no ?variant=
    kore = products["kore"]
    assert (kore.name, kore.brand, kore.price, kore.currency, kore.rank) == ("KORE", "ETNIA BARCELONA", 255.46, "EUR", 1)
    assert str(kore.image_url).endswith("5-KORE-54O_2_1200x.jpg") and kore.flags["categories"] == "Optique"
    xylo = products["xylo"]                                                          # product page 404: card only
    assert (xylo.name, xylo.brand, xylo.price, xylo.currency) == ("XYLO", "Etnia Barcelona", 199.0, "EUR")
    assert products["izzi"].flags["categories"] == "Solaire"
    assert f"{ETNIA}/products/unlisted" not in {p.db_url() for p in products.values()}  # facet pages never add products


@pytest.mark.anyio
async def test_etnia_facets_give_shape_gender_and_material_one_filter_at_a_time():
    products, _ = await crawl_etnia()
    assert products["kore"].flags["raw_specs"] == {"Forme": "OVAL", "Gender": "Man, Woman", "Materials": "Acetate"}
    assert products["xylo"].flags["raw_specs"] == {"Forme": "PANTOS SQUARE", "Materials": "Metal"}  # facet page 2
    assert products["izzi"].flags["raw_specs"] == {"Forme": "ROUND"}
    assert tags(products["kore"]) >= {("shape", "oval", None), ("audience", "men", None), ("audience", "women", None),
                                      ("material", "acetate", None), ("product_type", "optical", None)}
    assert {c for d, c, _ in tags(products["mao"]) if d == "shape"} == {"square"}          # not also round ("pantos")
    assert {c for d, c, _ in tags(products["vreeland"]) if d == "shape"} == {"cat_eye"}    # not also butterfly
    assert ("product_type", "sun", None) in tags(products["izzi"])


@pytest.mark.anyio
async def test_etnia_variants_carry_codes_labels_and_stock():
    products, _ = await crawl_etnia()
    kore = products["kore"]
    assert kore.flags["variants"] == [
        {"code": "HV/BL", "color": "Havana", "in_stock": True}, {"code": "BE", "color": "Beige", "in_stock": False},
        {"code": "BK", "color": "Black", "in_stock": True}, {"code": "BL/HO", "color": "Blue", "in_stock": True},
        {"code": "OG", "color": "Orange", "in_stock": True}]                         # " - Notify me" never in a label
    assert kore.flags["out_of_stock"] is False
    # Palier 1-3: the store's own color name decides the family; blue / orange have no family yet: untagged
    assert {t for t in tags(kore) if t[0] == "color"} == {
        ("color", "tortoiseshell", "HV/BL"), ("color", "beige", "BE"), ("color", "black", "BK")}
    assert {t for t in tags(products["vreeland"]) if t[0] == "color"} == {("color", "gold", "GD"), ("color", "gold", "GD/BK")}
    izzi = products["izzi"]
    assert [v["code"] for v in izzi.flags["variants"]] == ["BK/ZE", "HV/CL"]           # LensName radios are not colors
    assert izzi.flags["out_of_stock"] is True                                           # every color sold out
    assert "variants" not in products["xylo"].flags


@pytest.mark.anyio
async def test_etnia_requests_respect_robots_and_never_combine_filters():
    _, requested = await crawl_etnia()
    listed = [u for u in requested if u.path != "/robots.txt"]
    for url in listed:
        raw = url.raw_path.decode()
        assert "sort_by" not in raw and "+" not in raw and "%2B" not in raw.upper(), raw
        assert sum(k.startswith("filter.") for k, _ in parse_qsl(urlsplit(raw).query)) <= 1, raw
        assert not raw.endswith(".json") and "/search" not in raw, raw
    product_paths = {u.path for u in listed if "/products/" in u.path}
    assert product_paths == {f"/products/{s}" for s in ("kore", "mao", "xylo", "vreeland", "izzi")}  # one fetch each
    assert all(not u.query for u in listed if "/products/" in u.path)
    assert sum(1 for u in listed if u.path == "/products/kore") == 1
    assert not any("product_title" in u.raw_path.decode() for u in listed)            # only the configured filters
    assert any(u.raw_path.decode() == filter_url("optical", SHAPE, "PANTOS SQUARE", page=2) for u in listed)


@pytest.mark.anyio
async def test_etnia_codes_of_one_family_persist_side_by_side():
    products, _ = await crawl_etnia()
    init_db()
    cfg = load_store_configs()["etniabarcelona.com"]
    with SessionLocal() as s:
        service = StoreSyncService(s)
        source = service.source_for(cfg)
        assert source.country == "ES"
        service.sync(source.id, list(products.values()))
        vreeland = s.scalar(select(Product).where(Product.url == f"{ETNIA}/products/vreeland"))
        gold = sorted((t.supplier_code, t.color_family, t.color_hex) for t in vreeland.tags if t.dimension == "color")
        assert [g[:2] for g in gold] == [("GD", "gold"), ("GD/BK", "gold")] and gold[0][2] == gold[1][2]
        service.sync(source.id, list(products.values()))                                # a re-crawl adds nothing
        assert len([t for t in vreeland.tags if t.dimension == "color"]) == 2


# --- generic pieces -------------------------------------------------------------------------------

def test_canonical_url():
    rx = r"(/products/[^/?#]+)"
    assert canonical_url(f"{ETNIA}/collections/sun/products/izzi?variant=1", rx) == f"{ETNIA}/products/izzi"
    assert canonical_url(f"{ETNIA}/pages/about", rx) == f"{ETNIA}/pages/about"          # no match: unchanged
    assert canonical_url(f"{ETNIA}/products/izzi?variant=1", None) == f"{ETNIA}/products/izzi?variant=1"


def test_facet_values_dedupe_and_read_every_kind_of_label():
    html = facet_form({SHAPE: ["OVAL"], GENDER: ["Man"]}) + (
        '<label><input type="checkbox" name="filter.v.m.custom.size" value="L"> Large </label>'
        '<input type="checkbox" name="filter.v.m.custom.size" value="XS">')                # no label at all: skipped
    assert facet_values(html, SHAPE) == [(gid("OVAL"), "OVAL")]                         # aria-label first
    assert facet_values(html, GENDER) == [(gid("Man"), "Man")]                          # <label for>
    assert facet_values(html, "filter.v.m.custom.size") == [("L", "Large")]             # enclosing label
    assert facet_values("<p>no form</p>", SHAPE) == []


def test_add_label_joins_without_repeats():
    d: dict = {}
    for label in ("Man", "Woman", "Man"):
        add_label(d, "Gender", label)
    assert d == {"Gender": "Man, Woman"}


@pytest.mark.parametrize("patch", [
    ('      link: "a.card-link"', '      link: "a.card-link"\n      url_regex: "/products/"'),             # no group
    ('      link: "a.card-link"', '      link: "a.card-link"\n      url_regex: "(/products/"'),            # bad regex
    ('      link: "a.card-link"', '      link: "a.card-link"\n      facets: [{name: Forme, param: "a b"}]'),  # not a param
    ("{enabled: true, max_products: 2}", "{enabled: true, max_products: 1001}"),
    ("    specs: {", '    variants: {rows: "input", code: {css: "//x"}}\n    specs: {'),          # XPath refused
    ("    specs: {", '    variants: {rows: "input", code: {attr: value, regex: "(x"}}\n    specs: {'),
])
def test_new_rules_are_validated_at_load_time(patch):
    old, new = patch
    with pytest.raises(ValueError, match="shop.test"):
        parse_store_configs(CONFIG_YAML.replace(old, new, 1))


@pytest.mark.anyio
async def test_raw_specs_from_facets_and_the_product_page_are_merged_page_first():
    """Before this, the page's raw_specs replaced the listing's: facet values would have been lost."""
    yaml_text = CONFIG_YAML.replace('      link: "a.card-link"\n',
                                    '      link: "a.card-link"\n      facets: [{name: Gender, param: g}, {name: Forme, param: f}]\n', 1)
    cfg = parse_store_configs(yaml_text)["shop.test"]
    form = ('<input name="g" value="w" aria-label="Femme"><input name="f" value="r" aria-label="Ronde">'
            '<li class="card"><a class="card-link" href="/p/a"><h3 class="card-title">A</h3></a></li>')
    one = '<li class="card"><a class="card-link" href="/p/a"><h3 class="card-title">A</h3></a></li>'
    pages = {"/robots.txt": "User-agent: *\nDisallow: /admin\n", "/lunettes": form, "/lunettes?g=w": one, "/lunettes?f=r": one,
             "/p/a": '<table class="specs"><tr><th>Forme</th><td>Pilote</td></tr><tr><th>Calibre</th><td>52</td></tr></table>'}

    def handler(request: httpx.Request) -> httpx.Response:
        body = pages.get(request.url.raw_path.decode())
        return httpx.Response(200, text=body) if body is not None else httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        (a,) = await crawler.crawl()
    assert a.db_url() == f"{BASE}/p/a"
    assert a.flags["raw_specs"] == {"Gender": "Femme", "Forme": "Pilote", "Calibre": "52"}  # the page wins on Forme
