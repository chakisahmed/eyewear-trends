"""Lafont (France, Parisian eyewear house, presence-only creator brand):
Known for Parisian colourful creative acetate laminations, tortoiseshells, and retro silhouettes.
Optical (/eyeglasses) and sun (/sunglasses) collections, structured technical data specs,
and colorway variants with numeric codes and visual swatch thumbnails.
Offline: markup trimmed from real site pages (2026-10-02), served by httpx.MockTransport.
"""

import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs
from app.collectors.stores.parser import canonical_url
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product

LAFONT = "https://www.lafont.com"
ROBOTS = """User-agent: *
Disallow:

Sitemap: https://www.lafont.com/sitemap.xml
"""

DELICATE_CARD = """
<div class="article_mosaic bg_beige article_mosaic_catalog">
    <p style="text-transform: uppercase; align-items: center;">New</p>
    <div style="margin: 45px 0 0 0;">
        <a href="/catalog/article/DELE3223">
            <img id="DELE3223" loading="lazy" src="/image.php?img=/articles/MINIATURE/DELE3223_M.png" alt="Glasses Lafont: DELICATE - 100- Acetate">
        </a>
    </div>
    <h3>Delicate</h3>
    <hr>
    <div class="article_color_mosaic">
        <a href="/catalog/article/DELE100"><img src="/image.php?img=/colors/100.jpg" alt="Color: 100"></a>
        <a href="/catalog/article/DELE3100"><img src="/image.php?img=/colors/3100.jpg" alt="Color: 3100"></a>
        <a href="/catalog/article/DELE5201"><img src="/image.php?img=/colors/5201.jpg" alt="Color: 5201"></a>
    </div>
</div>
"""

CLIC_CARD = """
<div class="article_mosaic bg_beige article_mosaic_catalog">
    <div style="margin: 45px 0 0 0;">
        <a href="/catalog/article/CLIC5729I">
            <img id="CLIC5729I" loading="lazy" src="/image.php?img=/articles/MINIATURE/CLIC5729I_M.png" alt="Glasses Lafont: CLIC - 5729I- Metal">
        </a>
    </div>
    <h3>Clic</h3>
    <hr>
    <div class="article_color_mosaic">
        <a href="/catalog/article/CLIC006"><img src="/image.php?img=/colors/006.jpg" alt="Color: 006"></a>
        <a href="/catalog/article/CLIC5729I"><img src="/image.php?img=/colors/5729I.jpg" alt="Color: 5729I"></a>
    </div>
</div>
"""

MONA_CARD = """
<div class="article_mosaic bg_beige article_mosaic_catalog">
    <div style="margin: 45px 0 0 0;">
        <a href="/catalog/article/MONA100BSOL">
            <img id="MONA100BSOL" loading="lazy" src="/image.php?img=/articles/MINIATURE/MONA100BSOL_M.png" alt="Glasses Lafont: MONA - 100B- Acetate">
        </a>
    </div>
    <h3>Mona</h3>
    <hr>
    <div class="article_color_mosaic">
        <a href="/catalog/article/MONA100BSOL"><img src="/image.php?img=/colors/100B.jpg" alt="Color: 100B"></a>
    </div>
</div>
"""

DELICATE_PAGE = """
<!DOCTYPE html>
<html>
<head><title>DELICATE 5201</title></head>
<body>
<div class="article">
    <div class="fiche_article_img">
        <img id="image-face" src="/image.php?img=/articles/FACE/DELE5201_F.png" alt="Glasses Lafont-DELICATE-5201">
    </div>
    <div class="info_article">
        <h1 class="title_article">Delicate</h1>
        <p style="padding: 2% 0;">
            An easy addition to any eyeglass wardrobe DELICATE offers a sleek rectangle silhouette in an array of Lafont acetate colors.
        </p>
        <h2 class="taille_article">Size 54</h2>
        <div class="article_color_article">
            <a href="/catalog/article/DELE100">
                <img src="/image.php?img=/colors/100.jpg" alt="Color: 100">
                <p>100</p>
            </a>
            <a href="/catalog/article/DELE3100">
                <img src="/image.php?img=/colors/3100.jpg" alt="Color: 3100">
                <p>3100</p>
            </a>
            <a href="/catalog/article/DELE5201">
                <img src="/image.php?img=/colors/5201.jpg" alt="Color: 5201">
                <p>5201</p>
            </a>
        </div>
    </div>
    <div class="technique">
        <h3>Technical data</h3>
        <div class="info_tech">
            <ul class="edi">
                <li>. (1) Eye height: <b>40</b></li>
                <li>. (2) Eye width: <b>54</b></li>
                <li>. (3) Bridge: <b>15</b></li>
                <li>. (6) Temple length: <b>137</b></li>
                <li>. Lens base: <b>4</b></li>
            </ul>
        </div>
    </div>
</div>
</body>
</html>
"""

CLIC_PAGE = """
<!DOCTYPE html>
<html>
<head><title>CLIC 5729I</title></head>
<body>
<div class="article">
    <div class="fiche_article_img">
        <img id="image-face" src="/image.php?img=/articles/FACE/CLIC5729I_F.png" alt="Glasses Lafont-CLIC-5729I">
    </div>
    <div class="info_article">
        <h1 class="title_article">Clic</h1>
        <p style="padding: 2% 0;">
            P3 perfection. The new CLIC offers a playful two-tone metal option in a classic silhouette.
        </p>
        <h2 class="taille_article">Size 47</h2>
        <div class="article_color_article">
            <a href="/catalog/article/CLIC006">
                <img src="/image.php?img=/colors/006.jpg" alt="Color: 006">
                <p>006</p>
            </a>
            <a href="/catalog/article/CLIC5729I">
                <img src="/image.php?img=/colors/5729I.jpg" alt="Color: 5729I">
                <p>5729I</p>
            </a>
        </div>
    </div>
    <div class="technique">
        <h3>Technical data</h3>
        <div class="info_tech">
            <ul class="edi">
                <li>. (1) Eye height: <b>38</b></li>
                <li>. (2) Eye width: <b>47</b></li>
                <li>. (3) Bridge: <b>20</b></li>
                <li>. (6) Temple length: <b>140</b></li>
            </ul>
        </div>
    </div>
</div>
</body>
</html>
"""

MONA_PAGE = """
<!DOCTYPE html>
<html>
<head><title>MONA 100B SOL</title></head>
<body>
<div class="article">
    <div class="fiche_article_img">
        <img id="image-face" src="/image.php?img=/articles/FACE/MONA100BSOL_F.png" alt="Glasses Lafont-MONA-100B">
    </div>
    <div class="info_article">
        <h1 class="title_article">Mona</h1>
        <p style="padding: 2% 0;">
            Oversized geometric cat-eye sunglasses crafted from thick sculptural acetate.
        </p>
        <h2 class="taille_article">Size 53</h2>
        <div class="article_color_article">
            <a href="/catalog/article/MONA100BSOL">
                <img src="/image.php?img=/colors/100B.jpg" alt="Color: 100B">
                <p>100B</p>
            </a>
        </div>
    </div>
    <div class="technique">
        <h3>Technical data</h3>
        <div class="info_tech">
            <ul class="edi">
                <li>. (1) Eye height: <b>45</b></li>
                <li>. (2) Eye width: <b>53</b></li>
                <li>. (3) Bridge: <b>18</b></li>
            </ul>
        </div>
    </div>
</div>
</body>
</html>
"""


def fake_lafont() -> httpx.MockTransport:
    routes = {
        "/robots.txt": ROBOTS,
        "/eyeglasses": f"<html><body><div id='catalog'>{DELICATE_CARD}{CLIC_CARD}</div></body></html>",
        "/sunglasses": f"<html><body><div id='catalog'>{MONA_CARD}</div></body></html>",
        "/catalog/article/DELE3223": DELICATE_PAGE,
        "/catalog/article/CLIC5729I": CLIC_PAGE,
        "/catalog/article/MONA100BSOL": MONA_PAGE,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode()
        body = routes.get(path)
        if body is not None:
            return httpx.Response(200, text=body)
        return httpx.Response(404, text="Not Found")

    return httpx.MockTransport(handler)


def test_lafont_shipped_config_valid():
    cfg = load_store_configs()["lafont.com"]
    assert cfg.name == "Lafont"
    assert str(cfg.base_url) == "https://www.lafont.com/"
    assert cfg.country == "FR"
    assert cfg.default_currency == "EUR"
    assert cfg.default_brand == "Lafont"
    assert cfg.lang == "en"
    assert [u.url for u in cfg.listing.urls] == ["/eyeglasses", "/sunglasses"]
    assert cfg.product_pages.enabled is True
    assert cfg.product_pages.max_products == 300
    assert cfg.listing.url_regex == "(/catalog/article/[A-Z0-9]+)"
    assert cfg.listing.model_regex == "(/catalog/article/[A-Z]{3,4})"


@pytest.mark.anyio
async def test_lafont_crawl_end_to_end():
    cfg = load_store_configs()["lafont.com"]
    async with httpx.AsyncClient(transport=fake_lafont(), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products: list[ScrapedProduct] = await crawler.crawl()

    assert len(products) == 3
    by_url = {str(p.url): p for p in products}

    dele_url = canonical_url(f"{LAFONT}/catalog/article/DELE3223", cfg.listing.url_regex)
    clic_url = canonical_url(f"{LAFONT}/catalog/article/CLIC5729I", cfg.listing.url_regex)
    mona_url = canonical_url(f"{LAFONT}/catalog/article/MONA100BSOL", cfg.listing.url_regex)

    assert dele_url in by_url
    assert clic_url in by_url
    assert mona_url in by_url

    # Check Delicate
    dele = by_url[dele_url]
    assert dele.name == "Delicate"
    assert dele.brand == "Lafont"
    assert dele.currency == "EUR"
    assert dele.price is None  # presence-only
    assert "DELE5201_F.png" in str(dele.image_url)
    assert dele.flags.get("categories") == "Optique"
    assert dele.flags.get("is_new") is True
    assert dele.flags.get("material") == "Acetate"
    assert "DELICATE offers a sleek rectangle silhouette" in dele.flags.get("description", "")

    # Specs
    raw_specs = dele.flags.get("raw_specs", {})
    assert raw_specs.get("Eye height") == "40"
    assert raw_specs.get("Eye width") == "54"
    assert raw_specs.get("Bridge") == "15"
    assert raw_specs.get("Temple length") == "137"
    assert raw_specs.get("Lens base") == "4"

    # Variants with code, color, and swatch URL
    variants = dele.flags.get("variants", [])
    assert len(variants) == 3
    codes = {v["code"] for v in variants}
    assert codes == {"100", "3100", "5201"}
    swatches = {v["swatch"] for v in variants}
    assert "/image.php?img=/colors/100.jpg" in swatches

    # Check Clic
    clic = by_url[clic_url]
    assert clic.name == "Clic"
    assert clic.flags.get("categories") == "Optique"
    assert clic.flags.get("material") == "Metal"
    assert "P3 perfection" in clic.flags.get("description", "")
    assert clic.flags.get("raw_specs", {}).get("Bridge") == "20"

    # Check Mona (Sunglasses)
    mona = by_url[mona_url]
    assert mona.name == "Mona"
    assert mona.flags.get("categories") == "Solaire"
    assert mona.flags.get("material") == "Acetate"
    assert "geometric cat-eye" in mona.flags.get("description", "")


def test_lafont_tagger_rules_v19():
    # 1. Optical delicate: optical, rectangle, acetate, black variant 100
    tags_dele = tag_product(
        "Delicate",
        {
            "categories": "Optique",
            "material": "Acetate",
            "description": "An easy addition to any eyeglass wardrobe DELICATE offers a sleek rectangle silhouette in an array of Lafont acetate colors.",
            "variants": [
                {"code": "100", "color": "100", "swatch": "/image.php?img=/colors/100.jpg"},
                {"code": "5201", "color": "5201", "swatch": "/image.php?img=/colors/5201.jpg"},
            ],
        },
    )
    dim_codes = {(t.dimension, t.code) for t in tags_dele}
    assert ("product_type", "optical") in dim_codes
    assert ("shape", "rectangle") in dim_codes
    assert ("material", "acetate") in dim_codes
    assert ("color", "black") in dim_codes

    # Check Palier 3 variant code on black tag
    black_tag = next(t for t in tags_dele if t.dimension == "color" and t.code == "black")
    assert black_tag.supplier_code == "100"
    assert black_tag.color_family == "black"

    # 2. Clic: optical, round (from P3 alias), metal
    tags_clic = tag_product(
        "Clic",
        {
            "categories": "Optique",
            "material": "Metal",
            "description": "P3 perfection. The new CLIC offers a playful two-tone metal option in a classic silhouette.",
        },
    )
    clic_dims = {(t.dimension, t.code) for t in tags_clic}
    assert ("product_type", "optical") in clic_dims
    assert ("shape", "round") in clic_dims
    assert ("material", "metal") in clic_dims

    # 3. Mona: sun, cat_eye, geometric, acetate
    tags_mona = tag_product(
        "Mona",
        {
            "categories": "Solaire",
            "material": "Acetate",
            "description": "Oversized geometric cat-eye sunglasses crafted from thick sculptural acetate.",
        },
    )
    mona_dims = {(t.dimension, t.code) for t in tags_mona}
    assert ("product_type", "sun") in mona_dims
    assert ("shape", "cat_eye") in mona_dims
    assert ("shape", "geometric") in mona_dims
    assert ("material", "acetate") in mona_dims
