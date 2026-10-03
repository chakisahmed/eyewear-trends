"""Face à Face (France, Umbraco .NET CMS, presence-only creator brand):
Sculptural acetate and metal designs, optical and sun collections, query pagination (?Page=N),
structured specs (Material, Style, Front Type, Size, Temple Length), and active variant swatches.
Offline: markup trimmed from real site pages (2026-10-01), served by httpx.MockTransport.
"""

import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs
from app.collectors.stores.parser import canonical_url
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product

FAF = "https://www.faceaface-paris.com"
ROBOTS = """User-agent: *
Disallow: /umbraco/
Allow: /
"""

FRAMES = {
    "/en/optical/face-a-face/friday/friday-3132051": {
        "name": "FRIDAY 2",
        "concept": "FRIDAY",
        "category": "Optique",
        "desc": "Corporate creative attitude. Deep blue, stately brown, shocking fuchsia. Friday revives the Mad Men aesthetic in a modern twist.",
        "specs": [
            ("Name", "friday 2"),
            ("Material", "acetate"),
            ("Style", "feminine"),
            ("Front Type", "full rim"),
            ("Size", "50 22 mm"),
            ("Temple Length", "142 mm"),
        ],
        "variant": ("100", "BLACK"),
        "img": "/media/ki5b14qx/syncedimage_520607.jpg?format=webp&quality=85",
        "listing_page": "/en/optical",
        "code_param": "100",
    },
    "/en/optical/out-of-office/11h-59/11h59-3132136": {
        "name": "11H 59",
        "concept": "11H 59",
        "category": "Optique",
        "desc": "Striking architectural design with refined lines.",
        "specs": [
            ("Name", "11h 59"),
            ("Material", "titanium"),
            ("Style", "masculine"),
            ("Front Type", "semi-rimless"),
            ("Size", "52 18 mm"),
            ("Temple Length", "145 mm"),
        ],
        "variant": ("1027", "HAVANA"),
        "img": "/media/ev3n1lnl/syncedimage_747703.jpg?format=webp&quality=85",
        "listing_page": "/en/optical",
        "code_param": "1027",
    },
    "/en/optical/bocca/bocca-step/bocca-step-3132001": {
        "name": "BOCCA STEP 2",
        "concept": "BOCCA STEP",
        "category": "Optique",
        "desc": "Iconic high-heeled shoe temple tips with vibrant metallic accents.",
        "specs": [
            ("Name", "bocca step 2"),
            ("Material", "aluminium"),
            ("Style", "feminine"),
            ("Front Type", "full rim"),
            ("Size", "53 17 mm"),
            ("Temple Length", "140 mm"),
        ],
        "variant": ("200", "RED"),
        "img": "/media/bocca/step2.jpg?format=webp&quality=85",
        "listing_page": "/en/optical?Page=2",
        "code_param": "200",
    },
    "/en/sun/face-a-face/looks/looks-3132099": {
        "name": "LOOKS 1",
        "concept": "LOOKS",
        "category": "Solaire",
        "desc": "Bold sunglasses with an understated rimless attitude.",
        "specs": [
            ("Name", "looks 1"),
            ("Material", "acetate"),
            ("Style", "unisex"),
            ("Front Type", "rimless"),
            ("Size", "54 19 mm"),
            ("Temple Length", "145 mm"),
        ],
        "variant": ("300", "TORTOISE"),
        "img": "/media/looks/looks1.jpg?format=webp&quality=85",
        "listing_page": "/en/sun",
        "code_param": "300",
    },
}


def card_html(path: str, data: dict) -> str:
    # Umbraco card links include port :443 and ?colorCode=...
    href = f"{FAF}:443{path}?colorCode={data['code_param']}"
    return (
        f'<div class="product-placement__wrapper product-container__placement">'
        f'<a href="{href}" class="product-showcase__placement product-placement">'
        f'<div class="product-placement__image product-placement__image--front lazy lazy-bg" data-bg="{data["img"]}"></div>'
        f'<div class="product-placement__text">'
        f'<span class="product-placement__concept">{data["concept"]}</span>'
        f'</div></a></div>'
    )


def listing_page_html(page_url: str) -> str:
    matching = [card_html(p, d) for p, d in FRAMES.items() if d["listing_page"] == page_url]
    return f'<html><body><div class="product-grid">{"".join(matching)}</div></body></html>'


def product_html(path: str, data: dict) -> str:
    specs = "".join(
        f'<div class="specs__container">'
        f'<span class="specs--label">{k}</span>'
        f'<span class="specs--value">{v}</span>'
        f'</div>'
        for k, v in data["specs"]
    )
    v_code, v_name = data["variant"]
    return (
        f'<!DOCTYPE html><html><head><title>{data["name"]} | Face à Face</title></head><body>'
        f'<div class="slider-caption">'
        f'<div class="slider-caption__shape"><span class="slider-caption__shape--name">{data["name"]}</span></div>'
        f'<div class="slider-caption__break"></div>'
        f'<div class="slider-caption__color">'
        f'<span class="slider-caption__color--name">{v_name}</span>'
        f'<span class="slider-caption__color--code">{v_code}</span>'
        f'</div></div>'
        f'<div class="concept-box__container">'
        f'<span class="concept-box__name">{data["concept"]}</span>'
        f'<div class="concept-box__description">{data["desc"]}</div>'
        f'</div>'
        f'<section class="product-specification">{specs}</section>'
        f'<img class="product-slider__image" src="{data["img"]}" />'
        f'</body></html>'
    )


def site_pages() -> dict[str, str]:
    pages = {
        "/robots.txt": ROBOTS,
        "/en/optical": listing_page_html("/en/optical"),
        "/en/optical?Page=2": listing_page_html("/en/optical?Page=2"),
        "/en/sun": listing_page_html("/en/sun"),
    }
    for path, data in FRAMES.items():
        pages[path] = product_html(path, data)
    return pages


async def crawl_faf():
    cfg = load_store_configs()["faceaface-paris.com"]
    pages = site_pages()
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        path = request.url.raw_path.decode()
        if path in pages:
            return httpx.Response(200, text=pages[path])
        # Also match path without query if exact query not found
        clean_path = path.split("?")[0]
        if clean_path in pages:
            return httpx.Response(200, text=pages[clean_path])
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products = {p.db_url().replace(FAF, ""): p for p in await crawler.crawl()}
    return products, requested, crawler.report


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_face_a_face_crawl_optical_and_sun_pagination():
    products, requested, report = await crawl_faf()

    # All 4 sample products across optical (pages 1 and 2) and sun must be crawled
    assert len(products) == 4
    assert "/en/optical/face-a-face/friday/friday-3132051" in products
    assert "/en/optical/out-of-office/11h-59/11h59-3132136" in products
    assert "/en/optical/bocca/bocca-step/bocca-step-3132001" in products
    assert "/en/sun/face-a-face/looks/looks-3132099" in products

    # Canonical URLs: port :443 and query strings are completely stripped
    friday = products["/en/optical/face-a-face/friday/friday-3132051"]
    assert friday.db_url() == f"{FAF}/en/optical/face-a-face/friday/friday-3132051"
    assert friday.name == "FRIDAY 2"
    assert friday.brand == "Face à Face"
    assert friday.currency == "EUR"
    assert friday.price is None  # Presence-only brand

    # Active variant extraction
    assert friday.flags.get("variants") == [{"code": "100", "color": "BLACK"}]
    # Description extraction
    assert "Friday revives the Mad Men aesthetic" in friday.flags.get("description", "")


@pytest.mark.anyio
async def test_face_a_face_specs_and_tagging():
    products, _, _ = await crawl_faf()

    # 1. FRIDAY 2: feminine acetate optical
    friday = products["/en/optical/face-a-face/friday/friday-3132051"]
    friday_tags = {(t.dimension, t.code) for t in tag_product(friday.name, friday.flags)}
    assert ("product_type", "optical") in friday_tags
    assert ("material", "acetate") in friday_tags
    assert ("audience", "women") in friday_tags  # From Style: feminine
    assert ("color", "black") in friday_tags  # From variant: 100 BLACK
    black_tag = next(t for t in tag_product(friday.name, friday.flags) if t.dimension == "color" and t.code == "black")
    assert black_tag.supplier_code == "100"

    # 2. 11H 59: masculine titanium semi-rimless optical
    h59 = products["/en/optical/out-of-office/11h-59/11h59-3132136"]
    h59_tags = {(t.dimension, t.code) for t in tag_product(h59.name, h59.flags)}
    assert ("product_type", "optical") in h59_tags
    assert ("material", "titanium") in h59_tags
    assert ("audience", "men") in h59_tags  # From Style: masculine
    assert ("shape", "rimless") in h59_tags  # From Front Type: semi-rimless
    assert ("color", "tortoiseshell") in h59_tags  # From variant: 1027 HAVANA

    # 3. BOCCA STEP 2: aluminium metal optical
    bocca = products["/en/optical/bocca/bocca-step/bocca-step-3132001"]
    bocca_tags = {(t.dimension, t.code) for t in tag_product(bocca.name, bocca.flags)}
    assert ("material", "metal") in bocca_tags  # aluminium -> metal
    assert ("audience", "women") in bocca_tags
    assert ("color", "red") in bocca_tags

    # 4. LOOKS 1: unisex rimless sun
    looks = products["/en/sun/face-a-face/looks/looks-3132099"]
    looks_tags = {(t.dimension, t.code) for t in tag_product(looks.name, looks.flags)}
    assert ("product_type", "sun") in looks_tags
    assert ("material", "acetate") in looks_tags
    assert ("audience", "unisex") in looks_tags
    assert ("shape", "rimless") in looks_tags  # From Front Type: rimless
    assert ("color", "tortoiseshell") in looks_tags


def test_face_a_face_canonical_url_regex():
    cfg = load_store_configs()["faceaface-paris.com"]
    rx = cfg.listing.url_regex

    # Port :443 and ?colorCode= stripped
    raw1 = f"{FAF}:443/en/optical/face-a-face/friday/friday-3132051?colorCode=100"
    assert canonical_url(raw1, rx) == f"{FAF}/en/optical/face-a-face/friday/friday-3132051"

    # Clean URL without port
    raw2 = f"{FAF}/en/sun/face-a-face/looks/looks-3132099"
    assert canonical_url(raw2, rx) == f"{FAF}/en/sun/face-a-face/looks/looks-3132099"

    # Relative path joined to base
    raw3 = f"{FAF}/en/optical/out-of-office/11h-59/11h59-3132136?colorCode=1027"
    assert canonical_url(raw3, rx) == f"{FAF}/en/optical/out-of-office/11h-59/11h59-3132136"
