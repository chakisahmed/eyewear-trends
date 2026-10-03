"""Retrosuperfuture (Italy / Milan; Italian creator eyewear founded in 2007 by Daniel Beckerman):
Pioneered contemporary independent eyewear by merging classic Italian silhouette craft with
bold, eclectic street culture. Handcrafted in Italy from premium cellulose acetate with Zeiss lenses.
Collections: sun (/collections/all?filter.v.availability=1&filter.p.vendor=RETROSUPERFUTURE&filter.p.product_type=Eyewear&filter.p.m.rsf.category=Sunglass)
and optical (/collections/all?filter.v.availability=1&filter.p.vendor=RETROSUPERFUTURE&filter.p.product_type=Eyewear&filter.p.m.rsf.category=Optical).
Zero-Product-Page architecture: listing cards supply model name, price in EUR, high-res image,
material class (rsf-card-product--material-acetate), out_of_stock status, and canonical product links.
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

RSF_BASE = "https://retrosuperfuture.com"
ROBOTS = """User-agent: *
Allow: /
Disallow: /admin
Disallow: /cart/
Disallow: /checkout
"""

FIXTURES_DIR = Path(__file__).parent / "fixtures"
LISTING_HTML = (FIXTURES_DIR / "retrosuperfuture_listing.html").read_text(encoding="utf-8")


def test_rsf_config_valid():
    configs = load_store_configs()
    assert "retrosuperfuture.com" in configs
    cfg = configs["retrosuperfuture.com"]
    assert cfg.name == "Retrosuperfuture"
    assert cfg.country == "IT"
    assert cfg.default_currency == "EUR"
    assert cfg.default_brand == "Retrosuperfuture"
    assert cfg.product_pages.enabled is False
    assert len(cfg.listing.urls) == 3
    assert cfg.listing.pagination is not None
    assert cfg.listing.pagination.param == "page"
    assert cfg.listing.pagination.max_pages == 20
    assert cfg.listing.url_regex == r"(/products/[^/?#]+)"


def test_rsf_listing_parser():
    cfg = load_store_configs()["retrosuperfuture.com"]
    listing_url = (
        f"{RSF_BASE}/collections/all?filter.v.availability=1"
        f"&filter.p.vendor=RETROSUPERFUTURE&filter.p.product_type=Eyewear&filter.p.m.rsf.category=Sunglass"
    )
    items = parse_listing(LISTING_HTML, listing_url, cfg)
    assert len(items) == 24

    caro = next(it for it in items if it.url == f"{RSF_BASE}/products/ifgj")
    assert caro.css["name"] == "Caro Refined"
    assert caro.css["price"] == 199.0
    assert caro.css["currency"] == "EUR"
    assert "cdn/shop/products/E007_4KJ" in caro.css["image_url"]
    assert caro.flags["material"] == "acetate"
    assert caro.flags["out_of_stock"] is False
    assert "Caro Refined" in caro.flags["description"]

    classic = next(it for it in items if it.url == f"{RSF_BASE}/products/ib3w")
    assert classic.css["name"] == "Classic Black"
    assert classic.css["price"] == 169.0
    assert classic.flags["material"] == "acetate"
    assert classic.flags["out_of_stock"] is False

    flat_top = next(it for it in items if it.url == f"{RSF_BASE}/products/iyn4")
    assert flat_top.css["name"] == "Flat Top Black"
    assert flat_top.css["price"] == 169.0
    assert flat_top.flags["material"] == "acetate"


@pytest.mark.anyio
async def test_rsf_crawler_mock():
    cfg = load_store_configs()["retrosuperfuture.com"]
    cfg_test = cfg.model_copy(update={
        "listing": cfg.listing.model_copy(update={
            "urls": [cfg.listing.urls[0]],  # 1 collection for offline test
            "pagination": None  # 1 page for offline test
        })
    })

    def handle(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=ROBOTS)
        if "category=Sunglass" in url or "rsf.category" in url:
            return httpx.Response(200, text=LISTING_HTML)
        return httpx.Response(404)

    transport = httpx.MockTransport(handle)
    async with httpx.AsyncClient(transport=transport, base_url=RSF_BASE) as client:
        crawler = BaseStoreCrawler(cfg_test, client=client)
        products = await crawler.crawl()

    assert len(products) == 24
    caro = next(p for p in products if p.name == "Caro Refined")
    assert caro.brand == "Retrosuperfuture"
    assert caro.currency == "EUR"
    assert caro.price == 199.0
    assert caro.flags.get("out_of_stock") is False
    assert caro.flags.get("material") == "acetate"
    assert caro.flags.get("categories") == "Solaire"


def test_rsf_taxonomy_tagging():
    tax = load_taxonomy()

    # 1. Flat Top Black with description -> shape: square (RSF flat top alias), color: black, material: acetate
    t_flattop = tag_product(
        "Flat Top Black",
        {
            "description": "Flat Top Black - Retrosuperfuture -",
            "material": "acetate",
            "categories": "Solaire",
        },
        tax,
    )
    flattop_dims = {(t.dimension, t.code) for t in t_flattop}
    assert ("shape", "square") in flattop_dims
    assert ("color", "black") in flattop_dims
    assert ("material", "acetate") in flattop_dims
    assert ("product_type", "sun") in flattop_dims

    # 2. Caro Azure with variant color -> color: blue, material: acetate, product_type: sun
    t_azure = tag_product(
        "Caro",
        {
            "variants": [{"code": "AZU", "color": "Azure"}],
            "material": "acetate",
            "categories": "Solaire",
        },
        tax,
    )
    azure_dims = {(t.dimension, t.code) for t in t_azure}
    assert ("color", "blue") in azure_dims
    assert ("material", "acetate") in azure_dims
    assert ("product_type", "sun") in azure_dims

    # 3. Cocca Panna with spec -> color: white, product_type: optical
    t_panna = tag_product(
        "Cocca",
        {
            "raw_specs": {"Couleur": "Panna"},
            "categories": "Optique",
        },
        tax,
    )
    panna_dims = {(t.dimension, t.code) for t in t_panna}
    assert ("color", "white") in panna_dims
    assert ("product_type", "optical") in panna_dims

    # 4. Carino Canarino with variant -> color: orange, material: acetate
    t_canarino = tag_product(
        "Carino",
        {
            "variants": [{"code": "NVA", "color": "Canarino"}],
            "material": "acetate",
            "categories": "Solaire",
        },
        tax,
    )
    canarino_dims = {(t.dimension, t.code) for t in t_canarino}
    assert ("color", "orange") in canarino_dims
    assert ("material", "acetate") in canarino_dims
