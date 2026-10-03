"""Jacques Marie Mage (Los Angeles, USA; founded in 2014 by Jerome Jacques Marie Mage):
Pinnacle of artisanal limited-edition creator acetate eyewear, handcrafted in Sabae, Japan.
World-renowned for thick 10mm cured cellulose acetate blocks, sterling silver 925 and 18k gold
signature arrowhead front pins and hairline-engraved wirecores, and custom 7-barrel hinges.
Collections: optical (/collections/optical-1/products.json?limit=250),
sunglasses (/collections/sunglasses/products.json?limit=250),
and bestsellers (/collections/the-icons/products.json?limit=250).
Architecture: Zero-Product-Page scraping via Shopify collection products JSON to bypass headless SPA DOM
rendering and PDP HTTP 429 rate limits, capturing 100% of the catalog (259 frames) in 3 polite requests.
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

JMM_BASE = "https://jacquesmariemage.com"
ROBOTS = """# Shopify storefront. Public product, collection, page, blog, policy, cart, and localized HTML is crawlable.
# Agent instructions: https://jacquesmariemage.com/agents.md
User-agent: *
Disallow: /admin
Disallow: /cart
Disallow: /orders
Disallow: /checkouts/
Disallow: /checkout
Disallow: /collections/*sort_by*
"""

FIXTURES_DIR = Path(__file__).parent / "fixtures"
OPTICAL_JSON = (FIXTURES_DIR / "jacquesmariemage_optical.json").read_text(encoding="utf-8")
SUNGLASSES_JSON = (FIXTURES_DIR / "jacquesmariemage_sunglasses.json").read_text(encoding="utf-8")
ICONS_JSON = (FIXTURES_DIR / "jacquesmariemage_icons.json").read_text(encoding="utf-8")


def test_jacques_marie_mage_config_valid():
    configs = load_store_configs()
    assert "jacquesmariemage.com" in configs
    cfg = configs["jacquesmariemage.com"]
    assert cfg.name == "Jacques Marie Mage"
    assert cfg.country == "US"
    assert cfg.default_currency == "USD"
    assert cfg.default_brand == "Jacques Marie Mage"
    assert cfg.product_pages.enabled is False
    assert len(cfg.listing.urls) == 3
    assert cfg.listing.url_regex == r"(/products/[^/?#]+)"


def test_jacques_marie_mage_listing_parser_optical():
    cfg = load_store_configs()["jacquesmariemage.com"]
    listing_url = f"{JMM_BASE}/collections/optical-1/products.json?limit=250"
    items = parse_listing(OPTICAL_JSON, listing_url, cfg)
    assert len(items) == 15

    dealan_rx = next(it for it in items if it.url == f"{JMM_BASE}/products/dealan-mx-rx")
    assert dealan_rx.css["name"] == "DEALAN MX RX"
    assert dealan_rx.css["brand"] == "Jacques Marie Mage"
    assert dealan_rx.css["price"] == 1155.0
    assert "image_url" in dealan_rx.css
    assert dealan_rx.flags["material"] == "acetate"
    assert dealan_rx.flags["out_of_stock"] is False
    assert len(dealan_rx.flags["variants"]) == 3
    assert dealan_rx.flags["variants"][0]["code"] == "J-ERX-CHO-35-WF"
    assert dealan_rx.flags["variants"][0]["color"] == "35-MIDNIGHT / SUPERLIGHT GREY CR39"
    assert dealan_rx.flags["variants"][1]["code"] == "J-ERX-CHO-5C-WF"
    assert dealan_rx.flags["variants"][1]["color"] == "5C-ARGYLE / SUPERLIGHT BRONZE CR39"

    zephirin_rx = next(it for it in items if it.url == f"{JMM_BASE}/products/zephirin-mx-rx")
    assert zephirin_rx.css["name"] == "ZEPHIRIN MX RX"
    assert zephirin_rx.flags["material"] == "acetate"


def test_jacques_marie_mage_listing_parser_sunglasses():
    cfg = load_store_configs()["jacquesmariemage.com"]
    listing_url = f"{JMM_BASE}/collections/sunglasses/products.json?limit=250"
    items = parse_listing(SUNGLASSES_JSON, listing_url, cfg)
    assert len(items) == 35

    p_dealan = next(it for it in items if it.url == f"{JMM_BASE}/products/photochromic-collection-dealan")
    assert p_dealan.css["name"] == "PHOTOCHROMIC COLLECTION: DEALAN"
    assert p_dealan.css["price"] == 1190.0
    assert p_dealan.flags["material"] == "acetate"
    assert len(p_dealan.flags["variants"]) == 3
    assert "oval" in p_dealan.flags["description"]
    assert "round" in p_dealan.flags["description"]
    assert "square" in p_dealan.flags["description"]

    torino_ti = next(it for it in items if it.url == f"{JMM_BASE}/products/torino-ti")
    assert torino_ti.css["name"] == "TORINO TI"
    assert torino_ti.css["price"] == 1385.0
    assert torino_ti.flags["material"] == "metal"  # 'TI' in title defaults material to metal


@pytest.mark.anyio
async def test_jacques_marie_mage_crawler_offline():
    cfg = load_store_configs()["jacquesmariemage.com"].model_copy(update={"delay_s": 0.0})

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=ROBOTS)
        if "collections/optical-1" in url:
            return httpx.Response(200, text=OPTICAL_JSON)
        if "collections/sunglasses" in url:
            return httpx.Response(200, text=SUNGLASSES_JSON)
        if "collections/the-icons" in url:
            return httpx.Response(200, text=ICONS_JSON)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=JMM_BASE) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        products = await crawler.crawl()

    # 15 optical + 35 sunglasses = 50 unique frames
    assert len(products) == 50
    dealan = next(p for p in products if p.name == "PHOTOCHROMIC COLLECTION: DEALAN")
    assert dealan.brand == "Jacques Marie Mage"
    assert dealan.currency == "USD"
    assert dealan.price == 1190.0
    assert dealan.flags.get("categories") == "Solaire"
    assert dealan.flags.get("material") == "acetate"

    # Verify best-seller flag propagated from the-icons collection
    molino = next(p for p in products if p.name == "MOLINO")
    assert molino.flags.get("is_bestseller") is True


def test_jacques_marie_mage_tagging():
    tax = load_taxonomy()

    # 1. Optical Acetate Frame: Dealan MX RX (Optique, Acetate, Argyle -> Tortoiseshell, Midnight -> Blue)
    dealan_flags = {
        "categories": "Optique",
        "material": "acetate",
        "variants": [
            {"code": "J-ERX-CHO-35-WF", "color": "35-MIDNIGHT / SUPERLIGHT GREY CR39"},
            {"code": "J-ERX-CHO-5C-WF", "color": "5C-ARGYLE / SUPERLIGHT BRONZE CR39"},
            {"code": "J-ERX-CHO-18U-WF", "color": "18U-HUDSON / SUPERLIGHT BLUE CR39"},
        ],
    }
    dealan_tags = tag_product("DEALAN MX RX", dealan_flags, tax)
    dealan_map = {(t.dimension, t.code) for t in dealan_tags}

    assert ("material", "acetate") in dealan_map
    assert ("product_type", "optical") in dealan_map
    assert ("color", "tortoiseshell") in dealan_map  # argyle -> tortoiseshell
    assert ("color", "blue") in dealan_map           # midnight / blue -> blue

    # 2. Sun Titanium Metal Frame: Torino TI (Solaire, Metal, Square shape, Bourbon -> Brown, Bloodstone -> Red)
    torino_flags = {
        "categories": "Solaire",
        "material": "metal",
        "description": "Bold angular rectangular frame. Square silhouette.",
        "variants": [
            {"code": "J-ESN-TO-BOUR", "color": "BOURBON / GREEN CR39"},
            {"code": "J-ESN-TO-BLOD", "color": "BLOODSTONE / DARK GREY"},
            {"code": "J-ESN-TO-FROS", "color": "FROST / SILVER MIRROR"},
            {"code": "J-ESN-TO-ROVR", "color": "ROVER / BOTTLE GREEN"},
            {"code": "J-ESN-TO-VANT", "color": "VANTA / POLARIZED"},
        ],
    }
    torino_tags = tag_product("TORINO TI", torino_flags, tax)
    torino_map = {(t.dimension, t.code) for t in torino_tags}

    assert ("material", "metal") in torino_map
    assert ("product_type", "sun") in torino_map
    assert ("shape", "square") in torino_map
    assert ("color", "brown") in torino_map   # bourbon -> brown
    assert ("color", "red") in torino_map     # bloodstone -> red
    assert ("color", "clear") in torino_map   # frost -> clear
    assert ("color", "green") in torino_map   # rover -> green
    assert ("color", "black") in torino_map   # vanta -> black
