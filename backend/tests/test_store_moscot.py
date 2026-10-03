"""Moscot (USA / New York; iconic creator eyewear house founded in 1915 on Manhattan's Lower East Side):
Five generations of family optical heritage (Hyman Moscot). World-renowned for classic American vintage
acetate icons (LEMTOSH, MILTZEN, DAHVEN, ARTHUR, NEBB, ZOLMAN) featuring real riveted hinges and rich acetate tones.
Collections: eyeglasses (/collections/eyeglasses/products.json?limit=250),
sunglasses (/collections/sunglasses/products.json?limit=250), best-sellers, and new arrivals.
Architecture: Zero-Product-Page scraping via Shopify collection products JSON to capture 100% of the catalog
(290 frames) in 4 polite requests without downloading >600MB of heavy PDP HTML.
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

MOSCOT_BASE = "https://moscot.com"
ROBOTS = """User-agent: *
Disallow: /admin
Disallow: /checkout
Allow: /collections/
"""

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EYEGLASSES_JSON = (FIXTURES_DIR / "moscot_eyeglasses_products.json").read_text(encoding="utf-8")
SUNGLASSES_JSON = (FIXTURES_DIR / "moscot_sunglasses_products.json").read_text(encoding="utf-8")


def test_moscot_config_valid():
    configs = load_store_configs()
    assert "moscot.com" in configs
    cfg = configs["moscot.com"]
    assert cfg.name == "Moscot"
    assert cfg.country == "US"
    assert cfg.default_currency == "USD"
    assert cfg.default_brand == "Moscot"
    assert cfg.product_pages.enabled is False
    assert len(cfg.listing.urls) == 6
    assert cfg.listing.url_regex == r"(/products/[^/?#]+)"


def test_moscot_listing_parser_eyeglasses():
    cfg = load_store_configs()["moscot.com"]
    listing_url = f"{MOSCOT_BASE}/collections/eyeglasses/products.json?limit=250"
    items = parse_listing(EYEGLASSES_JSON, listing_url, cfg)
    assert len(items) == 116

    lemtosh = next(it for it in items if it.url == f"{MOSCOT_BASE}/products/lemtosh")
    assert lemtosh.css["name"] == "LEMTOSH"
    assert lemtosh.css["price"] == 340.0
    assert lemtosh.flags["material"] == "acetate"
    assert "square" in lemtosh.flags["description"].lower()
    assert len(lemtosh.flags["variants"]) >= 10
    # Clean option1 colorway extraction:
    assert any(v["color"] == "Flesh" for v in lemtosh.flags["variants"])
    assert any(v["color"] == "Matte Tortoise" for v in lemtosh.flags["variants"])
    assert not any(v["color"].endswith(("/ 44", "/ 46", "/ 49", "/ 52")) for v in lemtosh.flags["variants"])

    miltzen = next(it for it in items if it.url == f"{MOSCOT_BASE}/products/miltzen")
    assert miltzen.css["name"] == "MILTZEN"
    assert miltzen.css["price"] == 340.0
    assert miltzen.flags["material"] == "acetate"
    assert "round" in miltzen.flags["description"].lower()


def test_moscot_listing_parser_sunglasses():
    cfg = load_store_configs()["moscot.com"]
    listing_url = f"{MOSCOT_BASE}/collections/sunglasses/products.json?limit=250"
    items = parse_listing(SUNGLASSES_JSON, listing_url, cfg)
    assert len(items) == 174

    lemtosh_sun = next(it for it in items if it.url == f"{MOSCOT_BASE}/products/lemtosh-sun")
    assert lemtosh_sun.css["name"] == "LEMTOSH SUN"
    assert lemtosh_sun.css["price"] == 370.0
    assert lemtosh_sun.flags["material"] == "acetate"
    assert len(lemtosh_sun.flags["variants"]) >= 10


@pytest.mark.anyio
async def test_moscot_crawler_offline():
    cfg = load_store_configs()["moscot.com"]
    cfg_test = cfg.model_copy(update={
        "listing": cfg.listing.model_copy(update={
            "urls": [cfg.listing.urls[0]],  # 1 collection for offline test
        })
    })

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=ROBOTS)
        if "collections/eyeglasses" in url:
            return httpx.Response(200, text=EYEGLASSES_JSON)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=MOSCOT_BASE) as client:
        crawler = BaseStoreCrawler(cfg_test, client=client)
        products = await crawler.crawl()

    assert len(products) == 116
    lemtosh = next(p for p in products if p.name == "LEMTOSH")
    assert lemtosh.brand == "Moscot"
    assert lemtosh.currency == "USD"
    assert lemtosh.price == 340.0
    assert lemtosh.flags.get("material") == "acetate"
    assert lemtosh.flags.get("categories") == "Optique"


def test_moscot_tagging():
    tax = load_taxonomy()

    # 1. Lemtosh Optical (Acetate, Square, Flesh -> Beige, Spot Tortoise -> Tortoiseshell)
    lemtosh_flags = {
        "categories": "Optique",
        "material": "acetate",
        "description": "The LEMTOSH stands the test of time. Square shape.",
        "variants": [
            {"code": "LEM-BLK", "color": "Black"},
            {"code": "LEM-FLSH", "color": "Flesh"},
            {"code": "LEM-SPTRT", "color": "Spot Tortoise"},
            {"code": "LEM-BS", "color": "Butterscotch"},
        ]
    }
    lemtosh_tags = tag_product("LEMTOSH", lemtosh_flags, tax)
    lemtosh_map = {(t.dimension, t.code) for t in lemtosh_tags}

    assert ("material", "acetate") in lemtosh_map
    assert ("product_type", "optical") in lemtosh_map
    assert ("shape", "square") in lemtosh_map
    assert ("color", "black") in lemtosh_map
    assert ("color", "beige") in lemtosh_map         # flesh -> beige
    assert ("color", "tortoiseshell") in lemtosh_map # spot tortoise -> tortoiseshell
    assert ("color", "orange") in lemtosh_map        # butterscotch -> orange

    # 2. Miltzen Sun (Acetate, Round, Bark -> Brown, G-15 -> Green)
    miltzen_flags = {
        "categories": "Solaire",
        "material": "acetate",
        "description": "The round, full-vue MILTZEN first introduced in the 1930s.",
        "variants": [
            {"code": "MIL-BRK", "color": "Bark"},
            {"code": "MIL-G15", "color": "G-15"},
            {"code": "MIL-BLU", "color": "Blue Smoke"},
        ]
    }
    miltzen_tags = tag_product("MILTZEN SUN", miltzen_flags, tax)
    miltzen_map = {(t.dimension, t.code) for t in miltzen_tags}

    assert ("material", "acetate") in miltzen_map
    assert ("product_type", "sun") in miltzen_map
    assert ("shape", "round") in miltzen_map
    assert ("color", "brown") in miltzen_map # bark -> brown
    assert ("color", "green") in miltzen_map # g-15 -> green
    assert ("color", "blue") in miltzen_map  # blue smoke -> blue
