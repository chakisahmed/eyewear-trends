"""Oliver Goldsmith (UK / London; British heritage eyewear founded in 1926 by P. Oliver Goldsmith):
Pioneered sunglasses as fashion; framed Audrey Hepburn (Manhattan), Michael Caine (Lord), Grace Kelly.
Handmade in Italy from premium cotton acetate.
Collections: optical (/collections/glasses) and sun (/collections/sunglasses).
Zero-Product-Page architecture: individual product pages return HTTP 429 when scraped in sequence,
while listing cards supply model name, price in GBP, high-res image, silhouette shape & material
hints in image alt attributes, and all variant colorway chips.
Offline: fixture HTML from real site pages (2026-10-02), served by httpx.MockTransport.
"""

from pathlib import Path
import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs
from app.collectors.stores.parser import parse_listing
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product
from app.taxonomy import load_taxonomy

OG_BASE = "https://www.olivergoldsmith.com"
ROBOTS = """User-agent: *
Disallow: /admin
Disallow: /cart
Disallow: /checkout
"""

FIXTURES_DIR = Path(__file__).parent / "fixtures"
LISTING_HTML = (FIXTURES_DIR / "oliver_goldsmith_listing.html").read_text(encoding="utf-8")


def test_og_config_valid():
    configs = load_store_configs()
    assert "olivergoldsmith.com" in configs
    cfg = configs["olivergoldsmith.com"]
    assert cfg.name == "Oliver Goldsmith"
    assert cfg.country == "GB"
    assert cfg.default_currency == "GBP"
    assert cfg.default_brand == "Oliver Goldsmith"
    assert cfg.product_pages.enabled is False
    assert len(cfg.listing.urls) == 2
    assert cfg.listing.pagination is not None
    assert cfg.listing.pagination.next == "a.pagination__next"


def test_og_listing_parser():
    cfg = load_store_configs()["olivergoldsmith.com"]
    items = parse_listing(LISTING_HTML, f"{OG_BASE}/collections/sunglasses", cfg)
    assert len(items) == 50

    manhattan = next(it for it in items if it.url == f"{OG_BASE}/products/manhattan")
    assert manhattan.css["name"] == "Manhattan"
    assert manhattan.css["price"] == 395.0
    assert manhattan.css["currency"] == "GBP"
    assert "cdn/shop/files/MANHATTAN2-DARKTORTOISESHELL" in manhattan.css["image_url"]
    assert "round frame" in manhattan.flags["description"]
    assert manhattan.flags["is_new"] is False

    variants = manhattan.flags.get("variants", [])
    assert len(variants) >= 8
    var_colors = [v["color"] for v in variants]
    assert "Dark Tortoiseshell" in var_colors
    assert "Black" in var_colors
    assert "Jungle" in var_colors
    assert "Bahama" in var_colors

    vivian = next(it for it in items if it.url == f"{OG_BASE}/products/vivian")
    assert vivian.css["name"] == "Vivian"
    assert vivian.flags["is_new"] is True
    assert "rounded square frame" in vivian.flags["description"]


@pytest.mark.anyio
async def test_og_crawler_mock():
    cfg = load_store_configs()["olivergoldsmith.com"]
    cfg_test = cfg.model_copy(update={
        "listing": cfg.listing.model_copy(update={
            "urls": [cfg.listing.urls[1]],  # sunglasses
            "pagination": None  # 1 page for offline test
        })
    })

    def handle(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=ROBOTS)
        if "/collections/sunglasses" in url:
            return httpx.Response(200, text=LISTING_HTML)
        return httpx.Response(404)

    transport = httpx.MockTransport(handle)
    async with httpx.AsyncClient(transport=transport, base_url=OG_BASE) as client:
        crawler = BaseStoreCrawler(cfg_test, client=client)
        products = await crawler.crawl()

    assert len(products) == 50
    manhattan = next(p for p in products if p.name == "Manhattan")
    assert manhattan.brand == "Oliver Goldsmith"
    assert manhattan.currency == "GBP"
    assert manhattan.price == 395.0
    assert str(manhattan.url) == f"{OG_BASE}/products/manhattan"


def test_og_tagger_vocabulary():
    tax = load_taxonomy()

    # 1. Manhattan: round frame, Dark Tortoiseshell
    p1 = {
        "name": "Manhattan",
        "flags": {
            "categories": "Solaire",
            "description": "Oliver Goldsmith Manhattan sunglasses in Dark Tortoiseshell, front view of the round frame with green lenses",
            "variants": [
                {"code": "Dark Tortoiseshell", "color": "Dark Tortoiseshell"},
                {"code": "Black", "color": "Black"},
                {"code": "Jungle", "color": "Jungle"},
            ]
        }
    }
    tags1 = tag_product(p1["name"], p1["flags"], taxonomy=tax)
    by_dim1 = {t.dimension: t.code for t in tags1}
    assert by_dim1["product_type"] == "sun"
    assert by_dim1["shape"] == "round"
    colors1 = {t.code for t in tags1 if t.dimension == "color"}
    assert "tortoiseshell" in colors1
    assert "black" in colors1
    assert "green" in colors1  # Jungle

    # 2. Vivian: rounded square frame, Tangerine, Rouge, Amberfleck
    p2 = {
        "name": "Vivian",
        "flags": {
            "categories": "Solaire",
            "description": "Oliver Goldsmith Vivian sunglasses in Tangerine, front view of the rounded square frame with green lenses",
            "variants": [
                {"code": "Tangerine", "color": "Tangerine"},
                {"code": "Rouge", "color": "Rouge"},
                {"code": "Amberfleck", "color": "Amberfleck"},
            ]
        }
    }
    tags2 = tag_product(p2["name"], p2["flags"], taxonomy=tax)
    by_dim2 = {t.dimension: t.code for t in tags2}
    assert by_dim2["shape"] == "square"
    colors2 = {t.code for t in tags2 if t.dimension == "color"}
    assert "orange" in colors2       # Tangerine (v23 alias)
    assert "red" in colors2          # Rouge (v23 alias)
    assert "tortoiseshell" in colors2  # Amberfleck (v23 alias)

    # 3. Hillman: squared aviator
    p3 = {
        "name": "Hillman",
        "flags": {
            "categories": "Solaire",
            "description": "Oliver Goldsmith Hillman sunglasses in Military, front view of the squared aviator with grey gradient lenses",
            "variants": [
                {"code": "Military", "color": "Military"},
            ]
        }
    }
    tags3 = tag_product(p3["name"], p3["flags"], taxonomy=tax)
    by_dim3 = {t.dimension: t.code for t in tags3}
    assert by_dim3["shape"] == "aviator"  # squared aviator (v23 alias)
    colors3 = {t.code for t in tags3 if t.dimension == "color"}
    assert "green" in colors3             # Military (v23 alias)
