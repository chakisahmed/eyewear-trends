"""Ahlem (France / Paris & Los Angeles; luxury creator eyewear founded in 2014 by Ahlem Manai-Platt):
Handcrafted in historic artisanal workshops in Oyonnax and Morez (Jura, France), with Japanese titanium.
Known for thick 8mm Mazzucchelli vintage cellulose acetate, raw hand-beveled contours, geometric facet cuts,
and 22k electroplated gold and palladium hardware.
Collections: sun (/collections/sun/products.json?limit=250), optical (/collections/optical/products.json?limit=250),
and new arrivals (/collections/new-arrivals/products.json?limit=250).
Architecture: Zero-Product-Page scraping via Shopify collection products JSON to bypass headless SPA DOM
rendering and PDP HTTP 429 rate limits, capturing 100% of the catalog (178 frames) in 2 polite requests.
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

AHLEM_BASE = "https://www.ahlemeyewear.com"
ROBOTS = """User-agent: *
Disallow: /admin
Disallow: /checkout
Allow: /collections/
"""

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SUN_JSON = (FIXTURES_DIR / "ahlem_sun_products.json").read_text(encoding="utf-8")
OPTICAL_JSON = (FIXTURES_DIR / "ahlem_optical_products.json").read_text(encoding="utf-8")


def test_ahlem_config_valid():
    configs = load_store_configs()
    assert "ahlemeyewear.com" in configs
    cfg = configs["ahlemeyewear.com"]
    assert cfg.name == "Ahlem"
    assert cfg.country == "FR"
    assert cfg.default_currency == "USD"
    assert cfg.default_brand == "Ahlem"
    assert cfg.product_pages.enabled is False
    assert len(cfg.listing.urls) == 3
    assert cfg.listing.url_regex == r"(/products/[^/?#]+)"


def test_ahlem_listing_parser_sun():
    cfg = load_store_configs()["ahlemeyewear.com"]
    listing_url = f"{AHLEM_BASE}/collections/sun/products.json?limit=250"
    items = parse_listing(SUN_JSON, listing_url, cfg)
    assert len(items) == 82

    guerin = next(it for it in items if it.url == f"{AHLEM_BASE}/products/guerin")
    assert guerin.css["name"] == "Limited Edition: Guérin"
    assert guerin.css["price"] == 660.0
    assert guerin.flags["material"] == "metal"
    assert guerin.flags["is_new"] is True
    assert guerin.flags["is_limited"] is True
    assert "aviator" in guerin.flags["description"].lower()
    assert len(guerin.flags["variants"]) == 3
    assert guerin.flags["variants"][0]["code"] == "SM117-CHAM-NA/GNGR4-M3"
    assert guerin.flags["variants"][0]["color"] == "Champagne / Green Gradient"


def test_ahlem_listing_parser_optical():
    cfg = load_store_configs()["ahlemeyewear.com"]
    listing_url = f"{AHLEM_BASE}/collections/optical/products.json?limit=250"
    items = parse_listing(OPTICAL_JSON, listing_url, cfg)
    assert len(items) == 96

    st_marcel = next(it for it in items if it.url == f"{AHLEM_BASE}/products/st-marcel")
    assert st_marcel.css["name"] == "St Marcel"
    assert st_marcel.css["price"] == 580.0
    assert st_marcel.flags["material"] == "acetate"
    assert st_marcel.flags["is_new"] is True
    assert len(st_marcel.flags["variants"]) >= 3


@pytest.mark.anyio
async def test_ahlem_crawler_offline():
    cfg = load_store_configs()["ahlemeyewear.com"]
    cfg_test = cfg.model_copy(update={
        "listing": cfg.listing.model_copy(update={
            "urls": [cfg.listing.urls[0]],  # 1 collection for offline test
        })
    })

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=ROBOTS)
        if "collections/sun" in url:
            return httpx.Response(200, text=SUN_JSON)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=AHLEM_BASE) as client:
        crawler = BaseStoreCrawler(cfg_test, client=client)
        products = await crawler.crawl()

    assert len(products) == 82
    guerin = next(p for p in products if p.name == "Limited Edition: Guérin")
    assert guerin.brand == "Ahlem"
    assert guerin.currency == "USD"
    assert guerin.price == 660.0
    assert guerin.flags.get("material") == "metal"
    assert guerin.flags.get("categories") == "Solaire"


def test_ahlem_tagging():
    tax = load_taxonomy()

    # 1. St Marcel Acetate Frame
    marcel_flags = {
        "categories": "Optique",
        "material": "acetate",
        "variants": [
            {"code": "STM-BLK", "color": "Black"},
            {"code": "STM-LT", "color": "Light Turtle"},
            {"code": "STM-DP", "color": "Dry Pampa"},
            {"code": "STM-SQ", "color": "Smoky Quartz"},
        ]
    }
    marcel_tags = tag_product("St Marcel", marcel_flags, tax)
    marcel_map = {(t.dimension, t.code) for t in marcel_tags}

    assert ("material", "acetate") in marcel_map
    assert ("product_type", "optical") in marcel_map
    assert ("color", "black") in marcel_map
    # v26 color aliases:
    assert ("color", "tortoiseshell") in marcel_map  # light turtle -> tortoiseshell
    assert ("color", "beige") in marcel_map          # dry pampa -> beige
    assert ("color", "grey") in marcel_map           # smoky quartz -> grey

    # 2. Guérin Metal Aviator Sunglasses
    guerin_flags = {
        "categories": "Solaire",
        "material": "metal",
        "description": "A narrow unisex sunglass balancing soft curves with definitive angles. Aviator",
        "variants": [
            {"code": "SM117-CHAM", "color": "Champagne / Green Gradient"},
            {"code": "SM117-ROSE", "color": "Old Fashioned Rose"},
            {"code": "SM117-PEOG", "color": "Peony Gold"},
        ]
    }
    guerin_tags = tag_product("Limited Edition: Guérin", guerin_flags, tax)
    guerin_map = {(t.dimension, t.code) for t in guerin_tags}

    assert ("material", "metal") in guerin_map
    assert ("product_type", "sun") in guerin_map
    assert ("shape", "aviator") in guerin_map
    assert ("color", "pink") in guerin_map  # old fashioned rose, peony gold -> pink
    assert ("color", "green") in guerin_map # green gradient -> green
