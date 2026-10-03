"""Warby Parker (USA / New York; pioneer of DTC acetate eyewear, founded in 2010):
Built on vintage-inspired classic silhouettes, custom cellulose acetate from family-run Italian factories,
transparent $95 pricing, and signature detailing.
Architecture: Zero-Product-Page scraping via reverse-engineered internal catalog API (/v1/catalog/frames/search).
Captures 100% of the catalog (365 models, 740 colorways), prices, high-res images, shapes, materials, and badges
across 6 polite requests without downloading >500MB of heavy Next.js CSR HTML or triggering DataDome bot blocks.
Offline: fixture JSON from real site pages (2026-10-02), served by httpx.MockTransport.
"""

from pathlib import Path
import json
import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs
from app.collectors.stores.parser import parse_listing
from app.collectors.stores.tagger import tag_product
from app.taxonomy import load_taxonomy

WARBY_BASE = "https://www.warbyparker.com"
ROBOTS = """User-agent: *
Disallow: /account
Disallow: /cart
Disallow: /checkout
Allow: /v1/catalog/frames/search
"""

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EYEGLASSES_JSON = (FIXTURES_DIR / "warbyparker_eyeglasses.json").read_text(encoding="utf-8")
SUNGLASSES_JSON = (FIXTURES_DIR / "warbyparker_sunglasses.json").read_text(encoding="utf-8")


def test_warby_parker_config_valid():
    configs = load_store_configs()
    assert "warbyparker.com" in configs
    cfg = configs["warbyparker.com"]
    assert cfg.name == "Warby Parker"
    assert cfg.country == "US"
    assert cfg.default_currency == "USD"
    assert cfg.default_brand == "Warby Parker"
    assert cfg.product_pages.enabled is False
    assert len(cfg.listing.urls) == 6
    assert cfg.listing.url_regex == r"(/sunglasses/[^/?#]+|/eyeglasses/[^/?#]+)"


def test_warby_parker_listing_parser_eyeglasses():
    cfg = load_store_configs()["warbyparker.com"]
    listing_url = f"{WARBY_BASE}/v1/catalog/frames/search?kind=eyeGlasses&size=300"
    items = parse_listing(EYEGLASSES_JSON, listing_url, cfg)
    assert len(items) == 10

    esme = next(it for it in items if it.url == f"{WARBY_BASE}/eyeglasses/esme")
    assert esme.css["name"] == "Esme"
    assert esme.css["price"] == 95.0
    assert esme.flags["material"] == "acetate"
    assert "square" in esme.flags["description"].lower()
    assert len(esme.flags["variants"]) == 9
    assert any(v["color"] == "Sesame Tortoise" for v in esme.flags["variants"])

    durand = next(it for it in items if it.url == f"{WARBY_BASE}/eyeglasses/durand")
    assert durand.css["name"] == "Durand"
    assert durand.css["price"] == 95.0
    assert durand.flags["material"] == "acetate"
    assert "round" in durand.flags["description"].lower()
    assert len(durand.flags["variants"]) >= 3


def test_warby_parker_listing_parser_sunglasses():
    cfg = load_store_configs()["warbyparker.com"]
    listing_url = f"{WARBY_BASE}/v1/catalog/frames/search?kind=sunGlasses&size=300"
    items = parse_listing(SUNGLASSES_JSON, listing_url, cfg)
    assert len(items) == 11

    bix = next(it for it in items if it.url == f"{WARBY_BASE}/sunglasses/bix")
    assert bix.css["name"] == "Bix"
    assert bix.css["price"] == 95.0
    assert bix.flags["material"] == "acetate"
    assert "aviator" in bix.flags["description"].lower()
    assert len(bix.flags["variants"]) == 1
    assert bix.flags["variants"][0]["color"] == "Umber Crystal"

    bodie = next(it for it in items if it.url == f"{WARBY_BASE}/sunglasses/bodie")
    assert bodie.css["name"] == "Bodie"
    assert bodie.css["price"] == 95.0
    assert bodie.flags["material"] == "acetate"
    assert "round" in bodie.flags["description"].lower()
    assert len(bodie.flags["variants"]) == 2
    assert any(v["color"] == "Saltwater Matte" for v in bodie.flags["variants"])
    assert any(v["color"] == "Rye Tortoise" for v in bodie.flags["variants"])


@pytest.mark.anyio
async def test_warby_parker_crawl_mock():
    cfg = load_store_configs()["warbyparker.com"]

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=ROBOTS)
        if "kind=eyeGlasses" in url:
            return httpx.Response(200, text=EYEGLASSES_JSON)
        if "kind=sunGlasses" in url:
            return httpx.Response(200, text=SUNGLASSES_JSON)
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with BaseStoreCrawler(cfg, client=client) as crawler:
        products = await crawler.crawl()

    # 10 eyeglasses + 11 sunglasses = 21 unique models
    assert len(products) == 21
    assert crawler.report.complete is True
    assert len(crawler.report.problems) == 0

    esme_opt = next(p for p in products if str(p.url) == f"{WARBY_BASE}/eyeglasses/esme")
    assert esme_opt.name == "Esme"
    assert esme_opt.price == 95.0
    assert esme_opt.flags["categories"] == "Optique"
    assert esme_opt.flags.get("is_bestseller") is True
    assert esme_opt.flags.get("is_new") is True

    bix_sun = next(p for p in products if str(p.url) == f"{WARBY_BASE}/sunglasses/bix")
    assert bix_sun.name == "Bix"
    assert bix_sun.price == 95.0
    assert bix_sun.flags["categories"] == "Solaire"
    assert bix_sun.flags.get("is_bestseller") is True
    assert bix_sun.flags.get("is_new") is True


def test_warby_parker_tagging():
    taxonomy = load_taxonomy()

    # Test Bix
    bix_flags = {
        "material": "acetate",
        "categories": "Solaire",
        "description": "A head turn here. Made from hand-polished cellulose acetate. aviator",
        "variants": [{"code": "bix-sun-umber", "color": "Umber Crystal"}],
    }
    bix_tags = tag_product("Bix", bix_flags, taxonomy)
    dim_codes = {(t.dimension, t.code) for t in bix_tags}
    assert ("material", "acetate") in dim_codes
    assert ("product_type", "sun") in dim_codes
    assert ("shape", "aviator") in dim_codes
    assert ("color", "brown") in dim_codes

    # Test Bodie
    bodie_flags = {
        "material": "acetate",
        "categories": "Solaire",
        "description": "Handcrafted round frame in cellulose acetate",
        "variants": [
            {"code": "bodie-sun-saltwater", "color": "Saltwater Matte"},
            {"code": "bodie-sun-rye", "color": "Rye Tortoise"},
        ],
    }
    bodie_tags = tag_product("Bodie", bodie_flags, taxonomy)
    dim_codes = {(t.dimension, t.code) for t in bodie_tags}
    assert ("material", "acetate") in dim_codes
    assert ("product_type", "sun") in dim_codes
    assert ("shape", "round") in dim_codes
    assert ("color", "blue") in dim_codes
    assert ("color", "tortoiseshell") in dim_codes
