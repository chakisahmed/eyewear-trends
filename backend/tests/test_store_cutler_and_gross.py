"""Cutler and Gross (UK / London 1969, handmade in Cadore, Italy; luxury creator brand):
Known for thick, architectural handmade acetate frames, bold tortoiseshells, and graduated colorways.
Optical (/collections/optical-designer-glasses) and sun (/collections/sunglasses) collections.
Card-level extraction: listing cards embed full model name, silhouette shape, price in GBP,
high-res CDN image, New badges, and variant colorway radio swatches, enabling zero product page crawls.
Offline: markup trimmed from real site pages (2026-10-02), served by httpx.MockTransport.
"""

import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs
from app.collectors.stores.parser import canonical_url
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product

CNG = "https://www.cutlerandgross.com"
ROBOTS = """User-agent: *
Disallow: /admin
Disallow: /checkout
Disallow: /collections/*+*

Sitemap: https://www.cutlerandgross.com/sitemap.xml
"""

CARD_OPTICAL_9389 = """
<product-card class="product-card">
  <div class="product-card__content">
    <a href="/products/the-9389-square-optical-small?variant=44125549494375" title="Go to The 9389 Square Optical (Small)">
      <img data-card-media-image="" src="//www.cutlerandgross.com/cdn/shop/files/CGOP_9389_04_48-1.jpg?v=1788793770&width=128" alt="The 9389 Square Optical (Small)">
    </a>
    <span class="product-card__badges">
      <span class="product-card__badge product-card__badge--square">New</span>
    </span>
    <span class="product-card__price">Regular price\n          £395.00</span>
    <fieldset class="product__variant-options js-product-card-options" role="radiogroup">
      <div class="button--variant" tabindex="0">
        <input type="radio" value="Striped Dark Green" class="variant-option-radio-input">
        <label><span class="swatch" style="--swatch--background: url(//www.cutlerandgross.com/cdn/shop/files/StripedDark_Green.jpg?v=1743515727&width=50);"></span></label>
      </div>
      <div class="button--variant" tabindex="0">
        <input type="radio" value="Grey on Granny Chic" class="variant-option-radio-input">
        <label><span class="swatch" style="--swatch--background: url(//www.cutlerandgross.com/cdn/shop/files/Grey_on_Granny_Chic.jpg?v=1743514158&width=50);"></span></label>
      </div>
      <div class="button--variant" tabindex="0">
        <input type="radio" value="Horn Crystal" class="variant-option-radio-input">
        <label><span class="swatch" style="--swatch--background: url(//www.cutlerandgross.com/cdn/shop/files/Horn_Crystal.jpg?v=1785771040&width=50);"></span></label>
      </div>
      <div class="button--variant" tabindex="0">
        <input type="radio" value="Black" class="variant-option-radio-input">
        <label><span class="swatch" style="--swatch--background: rgb(0 0 0);"></span></label>
      </div>
    </fieldset>
  </div>
</product-card>
"""

CARD_OPTICAL_9261 = """
<product-card class="product-card">
  <div class="product-card__content">
    <a href="/products/9261-cat-eye-opticals?variant=44124505604199" title="Go to 9261 Cat Eye Opticals">
      <img data-card-media-image="" src="//www.cutlerandgross.com/cdn/shop/files/CGOP_9261_01_48-2-3.jpg?v=1770128021" alt="9261 Cat Eye Opticals">
    </a>
    <span class="product-card__badges">
      <span class="product-card__badge product-card__badge--square">Limited Edition</span>
    </span>
    <span class="product-card__price">Regular price\n          £410.00</span>
    <fieldset class="product__variant-options js-product-card-options" role="radiogroup">
      <div class="button--variant" tabindex="0">
        <input type="radio" value="Obsidian" class="variant-option-radio-input">
        <label><span class="swatch" style="--swatch--background: rgb(15 15 15);"></span></label>
      </div>
    </fieldset>
  </div>
</product-card>
"""

CARD_SUN_GR15 = """
<product-card class="product-card">
  <div class="product-card__content">
    <a href="/products/gr15-aviator-polarised-sunglasses?variant=44124622291047" title="Go to GR15 Aviator Polarised Sunglasses">
      <img data-card-media-image="" src="//www.cutlerandgross.com/cdn/shop/files/CGSN_GR15_01_54-1.jpg?v=1788793770" alt="GR15 Aviator Polarised Sunglasses">
    </a>
    <span class="product-card__badges">
      <span class="product-card__badge product-card__badge--square">New</span>
    </span>
    <span class="product-card__price">Regular price\n          £450.00</span>
    <fieldset class="product__variant-options js-product-card-options" role="radiogroup">
      <div class="button--variant" tabindex="0">
        <input type="radio" value="Havana" class="variant-option-radio-input">
        <label><span class="swatch" style="--swatch--background: url(//www.cutlerandgross.com/cdn/shop/files/Havana.jpg?v=1743515727&width=50);"></span></label>
      </div>
      <div class="button--variant" tabindex="0">
        <input type="radio" value="Olive on Black" class="variant-option-radio-input">
        <label><span class="swatch" style="--swatch--background: url(//www.cutlerandgross.com/cdn/shop/files/Olive_on_Black.jpg?v=1743515727&width=50);"></span></label>
      </div>
      <div class="button--variant" tabindex="0">
        <input type="radio" value="Humble Potato" class="variant-option-radio-input">
        <label><span class="swatch" style="--swatch--background: url(//www.cutlerandgross.com/cdn/shop/files/Humble_Potato.jpg?v=1743515727&width=50);"></span></label>
      </div>
    </fieldset>
  </div>
</product-card>
"""


def fake_cutler_and_gross() -> httpx.MockTransport:
    routes = {
        "/robots.txt": ROBOTS,
        "/collections/optical-designer-glasses": f"<html><body><div id='collection'>{CARD_OPTICAL_9389}{CARD_OPTICAL_9261}</div></body></html>",
        "/collections/sunglasses": f"<html><body><div id='collection'>{CARD_SUN_GR15}</div></body></html>",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode()
        body = routes.get(path)
        if body is not None:
            return httpx.Response(200, text=body)
        return httpx.Response(404, text="Not Found")

    return httpx.MockTransport(handler)


def test_cutler_and_gross_shipped_config_valid():
    cfg = load_store_configs()["cutlerandgross.com"]
    assert cfg.name == "Cutler and Gross"
    assert str(cfg.base_url) == "https://www.cutlerandgross.com/"
    assert cfg.country == "GB"
    assert cfg.default_currency == "GBP"
    assert cfg.default_brand == "Cutler and Gross"
    assert cfg.lang == "en"
    assert [u.url for u in cfg.listing.urls] == [
        "/collections/optical-designer-glasses",
        "/collections/sunglasses",
    ]
    assert cfg.product_pages.enabled is False
    assert cfg.listing.url_regex == "(/products/[^/?#]+)"
    assert cfg.listing.product == "product-card.product-card"
    assert cfg.listing.link == "a[title^='Go to ']"


@pytest.mark.anyio
async def test_cutler_and_gross_crawl_end_to_end():
    cfg = load_store_configs()["cutlerandgross.com"]
    async with httpx.AsyncClient(transport=fake_cutler_and_gross(), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products: list[ScrapedProduct] = await crawler.crawl()

    assert len(products) == 3
    by_url = {str(p.url): p for p in products}

    opt1_url = canonical_url(f"{CNG}/products/the-9389-square-optical-small", cfg.listing.url_regex)
    opt2_url = canonical_url(f"{CNG}/products/9261-cat-eye-opticals", cfg.listing.url_regex)
    sun1_url = canonical_url(f"{CNG}/products/gr15-aviator-polarised-sunglasses", cfg.listing.url_regex)

    assert opt1_url in by_url
    assert opt2_url in by_url
    assert sun1_url in by_url

    # Check 9389 Square Optical
    opt1 = by_url[opt1_url]
    assert opt1.name == "The 9389 Square Optical (Small)"
    assert opt1.brand == "Cutler and Gross"
    assert opt1.currency == "GBP"
    assert opt1.price == 395.0
    assert "CGOP_9389_04_48-1.jpg" in str(opt1.image_url)
    assert opt1.flags.get("is_new") is True

    variants1 = opt1.flags.get("variants") or []
    assert len(variants1) == 4
    colors1 = {v["color"] for v in variants1}
    assert colors1 == {"Striped Dark Green", "Grey on Granny Chic", "Horn Crystal", "Black"}
    swatches1 = {v["swatch"] for v in variants1 if "swatch" in v}
    assert any("StripedDark_Green.jpg" in s for s in swatches1)

    # Check 9261 Cat Eye Opticals (Limited Edition badge, not New)
    opt2 = by_url[opt2_url]
    assert opt2.name == "9261 Cat Eye Opticals"
    assert opt2.price == 410.0
    assert opt2.currency == "GBP"
    assert opt2.flags.get("is_new") is False

    variants2 = opt2.flags.get("variants") or []
    assert len(variants2) == 1
    assert variants2[0]["code"] == "Obsidian"

    # Check GR15 Aviator Polarised Sunglasses
    sun1 = by_url[sun1_url]
    assert sun1.name == "GR15 Aviator Polarised Sunglasses"
    assert sun1.price == 450.0
    assert sun1.flags.get("is_new") is True

    variants3 = sun1.flags.get("variants") or []
    assert len(variants3) == 3
    colors3 = {v["color"] for v in variants3}
    assert colors3 == {"Havana", "Olive on Black", "Humble Potato"}


def test_cutler_and_gross_tagger_rules_v20():
    cfg = load_store_configs()["cutlerandgross.com"]

    # Product 1: The 9389 Square Optical (Small)
    p1 = {
        "name": "The 9389 Square Optical (Small)",
        "flags": {
            "categories": "Optique",
            "is_new": True,
            "variants": [
                {"code": "Striped Dark Green", "color": "Striped Dark Green"},
                {"code": "Grey on Granny Chic", "color": "Grey on Granny Chic"},
                {"code": "Horn Crystal", "color": "Horn Crystal"},
                {"code": "Black", "color": "Black"},
            ],
        },
    }
    tags1 = tag_product(p1["name"], p1["flags"])
    by_dim1 = {t.dimension: t.code for t in tags1}
    assert by_dim1["product_type"] == "optical"
    assert by_dim1["shape"] == "square"

    color_tags1 = {t.code for t in tags1 if t.dimension == "color"}
    assert "green" in color_tags1       # Striped Dark Green
    assert "grey" in color_tags1        # Grey on Granny Chic
    assert "clear" in color_tags1       # Horn Crystal (v20 alias)
    assert "black" in color_tags1       # Black

    # Product 2: 9261 Cat Eye Opticals
    p2 = {
        "name": "9261 Cat Eye Opticals",
        "flags": {
            "categories": "Optique",
            "variants": [
                {"code": "Obsidian", "color": "Obsidian"},
            ],
        },
    }
    tags2 = tag_product(p2["name"], p2["flags"])
    by_dim2 = {t.dimension: t.code for t in tags2}
    assert by_dim2["product_type"] == "optical"
    assert by_dim2["shape"] == "cat_eye"
    color_tags2 = {t.code for t in tags2 if t.dimension == "color"}
    assert "black" in color_tags2       # Obsidian (v20 alias)

    # Product 3: GR15 Aviator Polarised Sunglasses
    p3 = {
        "name": "GR15 Aviator Polarised Sunglasses",
        "flags": {
            "categories": "Solaire",
            "is_new": True,
            "variants": [
                {"code": "Havana", "color": "Havana"},
                {"code": "Olive on Black", "color": "Olive on Black"},
                {"code": "Humble Potato", "color": "Humble Potato"},
            ],
        },
    }
    tags3 = tag_product(p3["name"], p3["flags"])
    by_dim3 = {t.dimension: t.code for t in tags3}
    assert by_dim3["product_type"] == "sun"
    assert by_dim3["shape"] == "aviator"

    color_tags3 = {t.code for t in tags3 if t.dimension == "color"}
    assert "tortoiseshell" in color_tags3  # Havana & Humble Potato (v20 alias)
    assert "two_tone" in color_tags3       # Olive on Black (v20 alias)
