"""Kuboraum (Germany, Kuboraum GmbH Berlin, presence-only creator brand):
Monumental sculptural acetate and mixed-material masks, optical and sun collections,
clean specs formatted as `<span class="bold">KEY:</span> VALUE <br>`, and active variant codes.
Offline: markup trimmed from real site pages (2026-10-01), served by httpx.MockTransport.
"""

import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs
from app.collectors.stores.parser import canonical_url
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product

KUB = "https://www.kuboraum.com"
ROBOTS = """User-agent: *
Disallow:
"""

FRAMES = {
    "/masks/d71-violet-petal/": {
        "name": "D71 VIOLET PETAL",
        "category": "Optique",
        "specs": [
            ("CODE", "D71 VP"),
            ("MATERIAL", "ACETATE & METAL"),
            ("COLOR", "Violet Petal"),
            ("TEMPLES COLOR", "Antique Light Gold + Brown"),
            ("LENS", "Clear"),
            ("BRIDGE", "20 mm"),
            ("LENS WIDTH", "52 mm"),
            ("TEMPLE LENGTH", "145 mm"),
        ],
        "img": "https://www.kuboraum.com/wp-content/uploads/2025/03/D71-VP-01.jpg",
        "listing_page": "/collections/optical-mask/",
    },
    "/masks/k36-black-shine/": {
        "name": "K36 BLACK SHINE",
        "category": "Optique",
        "specs": [
            ("CODE", "K36 BS"),
            ("MATERIAL", "ACETATE"),
            ("COLOR", "BLACK SHINE"),
            ("LENS", "CLEAR"),
            ("BRIDGE", "18 mm"),
            ("LENS WIDTH", "50 mm"),
            ("TEMPLE LENGTH", "145 mm"),
        ],
        "img": "https://www.kuboraum.com/wp-content/uploads/2025/03/K36-BS-01.jpg",
        "listing_page": "/collections/optical-mask/",
    },
    "/masks/e15-silver/": {
        "name": "E15 SILVER",
        "category": "Solaire",
        "specs": [
            ("CODE", "E15 SI"),
            ("MATERIAL", "Metal, Nylon, Acetate"),
            ("COLOR", "Silver + Black Matt"),
            ("LENS", "Grey"),
            ("LENS WIDTH", "144 mm"),
            ("TEMPLE LENGTH", "145 mm"),
        ],
        "img": "https://www.kuboraum.com/wp-content/uploads/2025/03/E15-SI-01.jpg",
        "listing_page": "/collections/sun-mask/",
    },
    "/masks/e15-ruthenium/": {
        "name": "E15 RUTHENIUM",
        "category": "Solaire",
        "specs": [
            ("CODE", "E15 BB"),
            ("MATERIAL", "Metal, Nylon, Acetate"),
            ("COLOR", "RUTHENIUM + BLACK MATT"),
            ("LENS", "Electric Green"),
            ("LENS WIDTH", "144 mm"),
            ("TEMPLE LENGTH", "145 mm"),
        ],
        "img": "https://www.kuboraum.com/wp-content/uploads/2025/03/E15-BB-01.jpg",
        "listing_page": "/collections/sun-mask/",
    },
}


def card_html(path: str, data: dict) -> str:
    return (
        f'<div class="col-10 col-lg-6 d-flex p-0 mask-item">'
        f'<figure class="col-6 col-lg-7 p-0 position-relative">'
        f'<a href="{KUB}{path}" class="mask-link">'
        f'<img data-src="{data["img"]}" class="img-fluid main-image" />'
        f'</a></figure>'
        f'<h2>{data["name"]}</h2>'
        f'</div>'
    )


def listing_page_html(page_url: str) -> str:
    matching = [card_html(p, d) for p, d in FRAMES.items() if d["listing_page"] == page_url]
    return f'<html><body><div class="mask-grid">{"".join(matching)}</div></body></html>'


def product_html(path: str, data: dict) -> str:
    specs_html = "".join(
        f'<span class="bold">{k}:</span> {v} <br>'
        for k, v in data["specs"]
    )
    return (
        f'<!DOCTYPE html><html><head><title>{data["name"]} - Kuboraum</title></head><body>'
        f'<h1>{data["name"]}</h1>'
        f'<p class="new-description pt-2">{specs_html}</p>'
        f'<img class="img-fluid gallery-image" src="{data["img"]}" />'
        f'</body></html>'
    )


def site_pages() -> dict[str, str]:
    pages = {
        "/robots.txt": ROBOTS,
        "/collections/optical-mask/": listing_page_html("/collections/optical-mask/"),
        "/collections/sun-mask/": listing_page_html("/collections/sun-mask/"),
    }
    for path, data in FRAMES.items():
        pages[path] = product_html(path, data)
    return pages


async def crawl_kub():
    cfg = load_store_configs()["kuboraum.com"]
    pages = site_pages()
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        path = request.url.raw_path.decode()
        if path in pages:
            return httpx.Response(200, text=pages[path])
        clean_path = path.split("?")[0]
        if clean_path in pages:
            return httpx.Response(200, text=pages[clean_path])
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products = {p.db_url().replace(KUB, ""): p for p in await crawler.crawl()}
    return products, requested, crawler.report


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_kuboraum_crawl_optical_and_sun():
    products, requested, report = await crawl_kub()

    # All 4 sample products crawled
    assert len(products) == 4
    assert "/masks/d71-violet-petal/" in products
    assert "/masks/k36-black-shine/" in products
    assert "/masks/e15-silver/" in products
    assert "/masks/e15-ruthenium/" in products

    # 1. Optical mask
    d71 = products["/masks/d71-violet-petal/"]
    assert d71.db_url() == f"{KUB}/masks/d71-violet-petal/"
    assert d71.name == "D71 VIOLET PETAL"
    assert d71.brand == "Kuboraum"
    assert d71.currency == "EUR"
    assert d71.price is None  # Presence-only brand

    # Specs extracted with tail text
    raw_specs = d71.flags.get("raw_specs", {})
    assert raw_specs["CODE:"] == "D71 VP"
    assert raw_specs["MATERIAL:"] == "ACETATE & METAL"
    assert raw_specs["COLOR:"] == "Violet Petal"
    assert raw_specs["BRIDGE:"] == "20 mm"
    assert raw_specs["LENS WIDTH:"] == "52 mm"
    assert raw_specs["TEMPLE LENGTH:"] == "145 mm"

    # Variant extracted
    assert d71.flags.get("variants") == [{"code": "D71 VP", "color": "Violet Petal"}]

    # 2. Sun mask
    e15 = products["/masks/e15-silver/"]
    assert e15.db_url() == f"{KUB}/masks/e15-silver/"
    assert e15.name == "E15 SILVER"
    assert e15.flags.get("raw_specs", {})["MATERIAL:"] == "Metal, Nylon, Acetate"
    assert e15.flags.get("variants") == [{"code": "E15 SI", "color": "Silver + Black Matt"}]


@pytest.mark.anyio
async def test_kuboraum_specs_and_tagging():
    products, _, _ = await crawl_kub()

    # 1. D71: Violet Petal acetate & metal optical
    d71 = products["/masks/d71-violet-petal/"]
    d71_tags = {(t.dimension, t.code) for t in tag_product(d71.name, d71.flags)}
    assert ("product_type", "optical") in d71_tags
    assert ("material", "acetate") in d71_tags
    assert ("material", "metal") in d71_tags
    assert ("color", "purple") in d71_tags  # Violet -> purple
    purple_tag = next(t for t in tag_product(d71.name, d71.flags) if t.dimension == "color" and t.code == "purple")
    assert purple_tag.supplier_code == "D71 VP"

    # 2. K36: Black Shine acetate optical
    k36 = products["/masks/k36-black-shine/"]
    k36_tags = {(t.dimension, t.code) for t in tag_product(k36.name, k36.flags)}
    assert ("product_type", "optical") in k36_tags
    assert ("material", "acetate") in k36_tags
    assert ("color", "black") in k36_tags
    black_tag = next(t for t in tag_product(k36.name, k36.flags) if t.dimension == "color" and t.code == "black")
    assert black_tag.supplier_code == "K36 BS"

    # 3. E15 Silver: Silver + Black Matt metal / nylon / acetate sun
    e15 = products["/masks/e15-silver/"]
    e15_tags = {(t.dimension, t.code) for t in tag_product(e15.name, e15.flags)}
    assert ("product_type", "sun") in e15_tags
    assert ("material", "metal") in e15_tags
    assert ("material", "tr90") in e15_tags  # Nylon -> tr90
    assert ("material", "acetate") in e15_tags
    assert ("color", "silver") in e15_tags
    assert ("color", "black") in e15_tags

    # 4. E15 Ruthenium: Ruthenium + Black Matt sun
    e15_ruth = products["/masks/e15-ruthenium/"]
    ruth_tags = {(t.dimension, t.code) for t in tag_product(e15_ruth.name, e15_ruth.flags)}
    assert ("material", "metal") in ruth_tags
    assert ("color", "grey") in ruth_tags  # Ruthenium -> grey
    assert ("color", "black") in ruth_tags


def test_kuboraum_canonical_url_regex():
    cfg = load_store_configs()["kuboraum.com"]
    rx = cfg.listing.url_regex

    assert canonical_url(f"{KUB}/masks/d71-violet-petal/?ref=share", rx) == f"{KUB}/masks/d71-violet-petal/"
    assert canonical_url(f"{KUB}/masks/e15-silver/", rx) == f"{KUB}/masks/e15-silver/"
