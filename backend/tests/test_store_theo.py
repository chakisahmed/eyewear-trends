"""Theo (Antwerp, Belgium; independent creator brand):
Known for fluorescent/neon colors, asymmetric and geometric silhouettes, and dual-color laminations.
Organized into design families (/families/<family_slug>) with mother model pages (/mothers/<model_slug>).
Offline: fixture HTML trimmed from real site pages (2026-10-02), served by httpx.MockTransport.
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

THEO_BASE = "https://www.theo.be"
ROBOTS = """User-agent: *
Disallow:
"""

FIXTURES_DIR = Path(__file__).parent / "fixtures"
LISTING_HTML = (FIXTURES_DIR / "theo_listing.html").read_text(encoding="utf-8")
PRODUCT_HTML = (FIXTURES_DIR / "theo_product.html").read_text(encoding="utf-8")


def test_theo_config_valid():
    configs = load_store_configs()
    assert "theo.be" in configs
    cfg = configs["theo.be"]
    assert cfg.name == "Theo"
    assert cfg.country == "BE"
    assert cfg.default_currency == "EUR"
    assert cfg.default_brand == "Theo"
    assert cfg.product_pages.enabled is True
    assert len(cfg.listing.urls) == 9
    assert all("/families/" in u.url for u in cfg.listing.urls)
    assert cfg.variants is not None
    assert cfg.variants.color_split is not None
    assert cfg.variants.color_split.sep == " + "


def test_theo_listing_parser():
    cfg = load_store_configs()["theo.be"]
    items = parse_listing(LISTING_HTML, f"{THEO_BASE}/families/clin-d-oeil", cfg)
    assert len(items) == 4

    urls = [it.url for it in items]
    assert urls == [
        f"{THEO_BASE}/mothers/apple",
        f"{THEO_BASE}/mothers/eye",
        f"{THEO_BASE}/mothers/pipe",
        f"{THEO_BASE}/mothers/sky",
    ]

    apple = items[0]
    assert apple.css["name"] == "APPLE"
    assert "cdn.prod.website-files.com" in apple.css["image_url"]
    assert apple.flags["description"] == "12colours"


def test_theo_product_page_parser():
    cfg = load_store_configs()["theo.be"]
    page = parse_product_page(PRODUCT_HTML, f"{THEO_BASE}/mothers/apple", cfg)
    variants = page.flags.get("variants", [])
    assert len(variants) == 12

    v0 = variants[0]
    assert v0["code"] == "003"
    assert v0["color"] == "MM ELECTRIC BLUE"
    assert v0["parts"] == ["MM ELECTRIC BLUE", "TRANSPARENT DELFT WARE BLUE"]
    assert "APPE-3.jpeg" in v0["swatch"]

    v_orange = next(v for v in variants if v["code"] == "014")
    assert v_orange["color"] == "FLUO ORANGE"
    assert v_orange["parts"] == ["FLUO ORANGE", "ORANGE GIVREE"]

    v_ecail = next(v for v in variants if v["code"] == "007")
    assert v_ecail["color"] == "DARK NIGHT"
    assert v_ecail["parts"] == ["DARK NIGHT", "BLUE RED ECAIL"]


@pytest.mark.anyio
async def test_theo_crawler_mock():
    cfg = load_store_configs()["theo.be"]
    cfg_test = cfg.model_copy(update={
        "listing": cfg.listing.model_copy(update={
            "urls": [cfg.listing.urls[7]]  # clin-d-oeil
        })
    })

    def handle(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=ROBOTS)
        if "/families/clin-d-oeil" in url:
            return httpx.Response(200, text=LISTING_HTML)
        if "/mothers/apple" in url:
            return httpx.Response(200, text=PRODUCT_HTML)
        # return dummy page for other models
        return httpx.Response(200, text="<html><body></body></html>")

    transport = httpx.MockTransport(handle)
    async with httpx.AsyncClient(transport=transport, base_url=THEO_BASE) as client:
        crawler = BaseStoreCrawler(cfg_test, client=client)
        products = await crawler.crawl()

    assert len(products) == 4
    apple = next(p for p in products if p.name == "APPLE")
    assert apple.brand == "Theo"
    assert apple.currency == "EUR"
    assert apple.price is None  # showroom pricing
    assert str(apple.url) == f"{THEO_BASE}/mothers/apple"
    assert len(apple.flags["variants"]) == 12


def test_theo_tagger_vocabulary():
    tax = load_taxonomy()
    cfg = load_store_configs()["theo.be"]

    # 1. Fluo orange variant
    p_orange = ScrapedProduct(
        url=f"{THEO_BASE}/mothers/apple",
        name="APPLE",
        brand="Theo",
        currency="EUR",
        flags={
            "variants": [
                {"code": "014", "color": "FLUO ORANGE", "parts": ["FLUO ORANGE", "ORANGE GIVREE"]}
            ]
        }
    )
    tags = tag_product(p_orange.name, p_orange.flags, taxonomy=tax)
    color_tags = [t for t in tags if t.dimension == "color"]
    assert any(t.code == "orange" and t.supplier_code == "014" for t in color_tags)

    # 2. Electric blue variant
    p_blue = ScrapedProduct(
        url=f"{THEO_BASE}/mothers/apple",
        name="APPLE",
        brand="Theo",
        currency="EUR",
        flags={
            "variants": [
                {"code": "003", "color": "MM ELECTRIC BLUE", "parts": ["MM ELECTRIC BLUE", "TRANSPARENT DELFT WARE BLUE"]}
            ]
        }
    )
    tags_blue = tag_product(p_blue.name, p_blue.flags, taxonomy=tax)
    color_tags_blue = [t for t in tags_blue if t.dimension == "color"]
    assert any(t.code == "blue" and t.supplier_code == "003" for t in color_tags_blue)

    # 3. Fluo red variant
    p_red = ScrapedProduct(
        url=f"{THEO_BASE}/mothers/apple",
        name="APPLE",
        brand="Theo",
        currency="EUR",
        flags={
            "variants": [
                {"code": "016", "color": "FLUO RED", "parts": ["FLUO RED", "PANTY"]}
            ]
        }
    )
    tags_red = tag_product(p_red.name, p_red.flags, taxonomy=tax)
    color_tags_red = [t for t in tags_red if t.dimension == "color"]
    assert any(t.code == "red" and t.supplier_code == "016" for t in color_tags_red)


