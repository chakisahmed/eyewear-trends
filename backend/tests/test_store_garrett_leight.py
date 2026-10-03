"""Garrett Leight California Optical (Venice Beach, Los Angeles, USA; founded in 2010 by Garrett Leight):
Contemporary California aesthetic, vintage-inspired frames, cured cellulose acetate from Mazzucchelli 1849,
custom filigree wire cores, and dual lines (GLCO core line + Mr. Leight luxury collaboration line).
Collections: eyeglasses, mr-leight-eyeglasses, sunglasses, mr-leight-sunglasses, ml-sunglasses,
bestsellers, forever-classics, new-eyeglasses, new-sunglasses.
Architecture: Zero-Product-Page scraping via Shopify collection products JSON to bypass headless SPA DOM
rendering and PDP HTTP 429 rate limits, capturing 100% of the catalog (155 frames) in polite collection requests.
Offline: fixture JSON from real site pages (2026-10-02), served by httpx.MockTransport.
"""

from pathlib import Path
import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs
from app.collectors.stores.parser import parse_listing
from app.collectors.stores.tagger import tag_product
from app.taxonomy import load_taxonomy

GLCO_BASE = "https://www.garrettleight.com"
ROBOTS = """# Shopify storefront. Public product, collection, page, blog, policy, cart, and localized HTML is crawlable.
# Agent instructions: https://www.garrettleight.com/agents.md
User-agent: *
Disallow: /admin
Disallow: /cart
Disallow: /orders
Disallow: /checkouts/
Disallow: /checkout
Disallow: /collections/*sort_by*
"""

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EYEGLASSES_JSON = (FIXTURES_DIR / "garrettleight_eyeglasses.json").read_text(encoding="utf-8")
SUNGLASSES_JSON = (FIXTURES_DIR / "garrettleight_sunglasses.json").read_text(encoding="utf-8")
BESTSELLERS_JSON = (FIXTURES_DIR / "garrettleight_bestsellers.json").read_text(encoding="utf-8")


def test_garrett_leight_config_valid():
    configs = load_store_configs()
    assert "garrettleight.com" in configs
    cfg = configs["garrettleight.com"]
    assert cfg.name == "Garrett Leight"
    assert cfg.country == "US"
    assert cfg.default_currency == "USD"
    assert cfg.default_brand == "Garrett Leight"
    assert cfg.product_pages.enabled is False
    assert len(cfg.listing.urls) == 9
    assert cfg.listing.url_regex == r"(/products/[^/?#]+)"


def test_garrett_leight_listing_parser_optical():
    cfg = load_store_configs()["garrettleight.com"]
    listing_url = f"{GLCO_BASE}/collections/eyeglasses/products.json?limit=250"
    items = parse_listing(EYEGLASSES_JSON, listing_url, cfg)
    assert len(items) == 25

    hancock = next(it for it in items if it.url == f"{GLCO_BASE}/products/hancock")
    assert hancock.css["name"] == "HANCOCK"
    assert hancock.css["brand"] == "Garrett Leight"  # normalized from vendor GLCO
    assert hancock.css["price"] == 395.0
    assert "image_url" in hancock.css
    assert hancock.flags["material"] == "acetate"
    assert hancock.flags["out_of_stock"] is False
    assert "aviator" in hancock.flags["description"]
    assert "oval" in hancock.flags["description"]
    assert len(hancock.flags["variants"]) == 4
    assert hancock.flags["variants"][0]["code"] == "1197-51-COLA"
    assert hancock.flags["variants"][0]["color"] == "Cola"

    wilson = next(it for it in items if it.url == f"{GLCO_BASE}/products/wilson-m")
    assert wilson.css["name"] == "WILSON M"
    assert wilson.flags["material"] == "metal"  # Wilson M (Metal) tagged material:metal
    assert "round" in wilson.flags["description"]

    hampton = next(it for it in items if it.url == f"{GLCO_BASE}/products/hampton")
    assert hampton.css["name"] == "HAMPTON"
    assert hampton.flags["material"] == "acetate"
    assert "round" in hampton.flags["description"]


def test_garrett_leight_listing_parser_sunglasses():
    cfg = load_store_configs()["garrettleight.com"]
    listing_url = f"{GLCO_BASE}/collections/sunglasses/products.json?limit=250"
    items = parse_listing(SUNGLASSES_JSON, listing_url, cfg)
    assert len(items) == 25

    chaparral = next(it for it in items if it.url == f"{GLCO_BASE}/products/chaparral-sun")
    assert chaparral.css["name"] == "CHAPARRAL SUN"
    assert chaparral.css["brand"] == "Garrett Leight"
    assert chaparral.css["price"] == 425.0
    assert chaparral.flags["material"] == "acetate"
    assert len(chaparral.flags["variants"]) == 4
    assert chaparral.flags["variants"][0]["color"] == "Ochre/Semi-Flat Cocoa"

    lugo = next(it for it in items if it.url == f"{GLCO_BASE}/products/lugo-sun")
    assert lugo.css["name"] == "LUGO SUN"
    assert lugo.css["price"] == 455.0
    assert "rectangle" in lugo.flags["description"]
    assert "square" in lugo.flags["description"]


@pytest.mark.anyio
async def test_garrett_leight_crawler_offline():
    cfg = load_store_configs()["garrettleight.com"].model_copy(update={"delay_s": 0.0})

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=ROBOTS)
        if "eyeglasses" in url:
            return httpx.Response(200, text=EYEGLASSES_JSON)
        if "sunglasses" in url:
            return httpx.Response(200, text=SUNGLASSES_JSON)
        if "bestsellers" in url:
            return httpx.Response(200, text=BESTSELLERS_JSON)
        return httpx.Response(200, json={"products": []})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=GLCO_BASE) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        products = await crawler.crawl()

    assert len(products) == 50
    hancock = next(p for p in products if p.name == "HANCOCK")
    assert hancock.brand == "Garrett Leight"
    assert hancock.currency == "USD"
    assert hancock.price == 395.0
    assert hancock.flags.get("categories") == "Optique"
    assert hancock.flags.get("material") == "acetate"

    # Verify best-seller flag enrichment on overlapping models
    kinney = next(p for p in products if p.name == "KINNEY")
    assert kinney.flags.get("is_bestseller") is True

    hampton = next(p for p in products if p.name == "HAMPTON")
    assert hampton.flags.get("is_bestseller") is True


def test_garrett_leight_tagging():
    tax = load_taxonomy()

    # 1. Optical Acetate Frame: Hampton (Optique, Acetate, Round shape, True Demi -> tortoiseshell)
    hampton_flags = {
        "categories": "Optique",
        "material": "acetate",
        "description": "Iconic P3 round acetate silhouette with keyhole bridge. round",
        "variants": [
            {"code": "1001-46-BIO-BK", "color": "Bio Black"},
            {"code": "1001-46-BIO-MST", "color": "True Demi"},
            {"code": "1001-46-BIO-COLA", "color": "Cola"},
            {"code": "1001-46-BIO-OLIO", "color": "Olio"},
        ],
    }
    hampton_tags = tag_product("HAMPTON", hampton_flags, tax)
    hampton_map = {(t.dimension, t.code) for t in hampton_tags}

    assert ("material", "acetate") in hampton_map
    assert ("product_type", "optical") in hampton_map
    assert ("shape", "round") in hampton_map
    assert ("color", "black") in hampton_map
    assert ("color", "tortoiseshell") in hampton_map  # true demi -> tortoiseshell
    assert ("color", "brown") in hampton_map          # cola -> brown
    assert ("color", "green") in hampton_map          # olio -> green

    # 2. Sun Frame: Chaparral Sun (Solaire, Acetate, Square shape, Strawberry Jam -> Red, Willow -> Green)
    chaparral_flags = {
        "categories": "Solaire",
        "material": "acetate",
        "description": "Period-accurate narrow upswept silhouette. square",
        "variants": [
            {"code": "2201-49-JAM", "color": "Strawberry Jam"},
            {"code": "2201-49-WIL", "color": "Willow / G15"},
            {"code": "2201-49-SALT", "color": "Himalayan Salt"},
            {"code": "2201-49-BAROLO", "color": "Barolo"},
        ],
    }
    chaparral_tags = tag_product("CHAPARRAL SUN", chaparral_flags, tax)
    chaparral_map = {(t.dimension, t.code) for t in chaparral_tags}

    assert ("material", "acetate") in chaparral_map
    assert ("product_type", "sun") in chaparral_map
    assert ("shape", "square") in chaparral_map
    assert ("color", "red") in chaparral_map    # strawberry jam, barolo -> red
    assert ("color", "green") in chaparral_map  # willow -> green
    assert ("color", "pink") in chaparral_map   # himalayan salt -> pink
