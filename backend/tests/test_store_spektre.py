"""Spektre (Italy / Milan; creator eyewear founded in 2009 by Niccolò Pocchini):
Handcrafted in Italy using bold Mazzucchelli acetate, stainless steel wireframes, flat sunglasses,
and vibrant mirror/pastel lens tints blending Milanese streetwear with Italian artisanal craft.
Collections: sun (/product-category/sun/), optical (/product-category/optical/),
and bestsellers (/product-category/best/).
Architecture: WooCommerce listing cards provide model name, price in EUR, thumbnail,
and best-seller / stock status. Product pages enrich with precise Materials (Acetate vs Stainless Steel),
frame measurements (Caliber, Nose, Temple), and color variant options.
Offline: fixture HTML from real site pages (2026-10-02), served by httpx.MockTransport.
"""

from pathlib import Path
import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs
from app.collectors.stores.parser import parse_listing, parse_product_page
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product
from app.taxonomy import load_taxonomy

SPEKTRE_BASE = "https://spektre.com"
ROBOTS = """User-agent: *
Disallow: /wp-admin/
Disallow: /wp-content/uploads/wc-logs/
Allow: /
"""

FIXTURES_DIR = Path(__file__).parent / "fixtures"
LISTING_HTML = (FIXTURES_DIR / "spektre_listing.html").read_text(encoding="utf-8")
PRODUCT_HTML = (FIXTURES_DIR / "spektre_product.html").read_text(encoding="utf-8")


def test_spektre_config_valid():
    configs = load_store_configs()
    assert "spektre.com" in configs
    cfg = configs["spektre.com"]
    assert cfg.name == "Spektre"
    assert cfg.country == "IT"
    assert cfg.default_currency == "EUR"
    assert cfg.default_brand == "Spektre"
    assert cfg.product_pages.enabled is True
    assert cfg.product_pages.max_products == 250
    assert len(cfg.listing.urls) == 3
    assert cfg.listing.pagination is not None
    assert cfg.listing.pagination.next == "a.next.page-numbers"
    assert cfg.listing.pagination.max_pages == 10
    assert cfg.listing.url_regex == r"(/product/[^/?#]+)"
    assert cfg.specs is not None
    assert cfg.specs.rows == "p.m-0"
    assert cfg.specs.key == "b"
    assert cfg.specs.tail is True
    assert cfg.variants is not None


def test_spektre_listing_parser():
    cfg = load_store_configs()["spektre.com"]
    listing_url = f"{SPEKTRE_BASE}/product-category/sun/"
    items = parse_listing(LISTING_HTML, listing_url, cfg)
    assert len(items) == 20

    rigaut2 = next(it for it in items if it.url == f"{SPEKTRE_BASE}/product/rigaut-2")
    assert rigaut2.css["name"] == "RIGAUT 2"
    assert rigaut2.css["price"] == 179.0
    assert rigaut2.flags["is_bestseller"] is True
    assert rigaut2.flags["out_of_stock"] is False
    assert "FRONT-2" in rigaut2.css["image_url"]

    palm = next(it for it in items if it.url == f"{SPEKTRE_BASE}/product/palm")
    assert palm.css["name"] == "PALM"
    assert palm.css["price"] == 249.0
    assert palm.flags["is_bestseller"] is True


def test_spektre_product_page_parser():
    cfg = load_store_configs()["spektre.com"]
    pdp_url = f"{SPEKTRE_BASE}/product/rea/"
    pdp = parse_product_page(PRODUCT_HTML, pdp_url, cfg)

    # JSON-LD extraction
    assert pdp.json_ld.get("name") == "REA"
    assert pdp.json_ld.get("price") == 189.0
    assert pdp.json_ld.get("currency") == "EUR"

    # Specs extraction
    specs = pdp.flags.get("raw_specs", {})
    assert specs.get("Materials") == "Acetate, Nylon Lenses"
    assert specs.get("Caliber") == "59"
    assert specs.get("Nose") == "12"
    assert specs.get("Temple") == "140"

    # Variants extraction
    variants = pdp.flags.get("variants", [])
    assert len(variants) >= 20
    black_smoke = next((v for v in variants if v["code"] == "black-smoke"), None)
    assert black_smoke is not None
    assert black_smoke["color"] == "Black & Smoke"


@pytest.mark.anyio
async def test_spektre_crawler_offline():
    cfg = load_store_configs()["spektre.com"]
    cfg_test = cfg.model_copy(update={
        "listing": cfg.listing.model_copy(update={
            "urls": [cfg.listing.urls[0]],  # 1 collection for offline test
            "pagination": None  # 1 page for offline test
        }),
        "product_pages": cfg.product_pages.model_copy(update={
            "max_products": 5  # limit PDPs for unit test speed
        })
    })

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=ROBOTS)
        if "product-category/sun" in url:
            return httpx.Response(200, text=LISTING_HTML)
        # Any product page
        return httpx.Response(200, text=PRODUCT_HTML)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=SPEKTRE_BASE) as client:
        crawler = BaseStoreCrawler(cfg_test, client=client)
        products = await crawler.crawl()

    assert len(products) == 20
    first_p = products[0]
    assert first_p.brand == "Spektre"
    assert first_p.currency == "EUR"
    assert first_p.price in (179.0, 189.0, 249.0)
    assert first_p.flags is not None
    assert "raw_specs" in first_p.flags
    assert first_p.flags["raw_specs"]["Materials"] == "Acetate, Nylon Lenses"
    assert "variants" in first_p.flags
    assert len(first_p.flags["variants"]) >= 20


def test_spektre_tagging():
    tax = load_taxonomy()

    # 1. Spektre Acetate Frame (REA)
    rea_flags = {
        "categories": "Solaire",
        "raw_specs": {
            "Materials": "Acetate, Nylon Lenses",
            "Caliber": "59",
            "Nose": "12",
            "Temple": "140",
        },
        "variants": [
            {"code": "black-smoke", "color": "Black & Smoke"},
            {"code": "gold-glossy-tobacco", "color": "Gold Glossy & Tobacco"},
            {"code": "avory-black", "color": "Avory & Black"},
            {"code": "fuchsia-smoke", "color": "Fuchsia & Smoke"},
        ]
    }
    tags = tag_product("REA", rea_flags, tax)
    tag_map = {(t.dimension, t.code) for t in tags}

    # Material: Acetate
    assert ("material", "acetate") in tag_map
    # Product type: Sun
    assert ("product_type", "sun") in tag_map
    # Variant colors with v25 aliases:
    # tobacco -> brown
    assert ("color", "brown") in tag_map
    # avory -> white
    assert ("color", "white") in tag_map
    # fuchsia -> pink
    assert ("color", "pink") in tag_map
    # black & smoke -> black and grey
    assert ("color", "black") in tag_map
    assert ("color", "grey") in tag_map

    # 2. Spektre Stainless Steel Frame (RIGAUT 2)
    rigaut_flags = {
        "categories": "Solaire",
        "raw_specs": {
            "Materials": "Nylon Lenses, Stainless Steel",
            "Caliber": "52",
            "Nose": "20",
        }
    }
    rigaut_tags = tag_product("RIGAUT 2", rigaut_flags, tax)
    rigaut_map = {(t.dimension, t.code) for t in rigaut_tags}
    assert ("material", "metal") in rigaut_map
