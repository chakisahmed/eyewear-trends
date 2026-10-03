"""Kirk & Kirk (UK / London & Brighton, handmade in France & Italy; independent creator brand):
Known for lightweight 10mm bespoke Italian acrylic frames in saturated kaleidoscope colours.
Optical (/glasses/) and sun (/sunglasses/) collections.
Card-level extraction: listing cards supply full model name, price in GBP, high-res CDN image,
silhouette shape hints in image title attribute, and all variant colorway chips with swatches.
Offline: markup trimmed from real site pages (2026-10-02), served by httpx.MockTransport.
"""

import httpx
import pytest

from app.collectors.stores.base import BaseStoreCrawler
from app.collectors.stores.config import load_store_configs
from app.collectors.stores.parser import canonical_url
from app.collectors.stores.schemas import ScrapedProduct
from app.collectors.stores.tagger import tag_product

KAK = "https://kirkandkirk.com"
ROBOTS = """User-agent: *
Disallow: /wp-admin/
Crawl-delay: 10

User-agent: *
Disallow:

Sitemap: https://kirkandkirk.com/sitemap_index.xml
"""

CARD_EMMA = """
<div class="kak-card" data-cat-name="Emma" data-category="0">
  <div class="kak-card__image-wrapper">
    <img class="kak-card__image kak-card__image--default" data-variant="0" title="Mischievous little frame combining gentle roundness with an edge. Great for smaller faces." alt="" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/Contour_Emma_F4_s_Jungle_Product_Thumbnail_Front-600x400.jpg">
    <a href="https://kirkandkirk.com/product/emma-jungle/">
      <img class="kak-card__image kak-card__image--hover" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/Contour_Emma_F4_s_Jungle_Product_Thumbnail_Side.jpg">
    </a>
  </div>
  <div class="kak-card__content">
    <div class="kak-card__title">
      <a class="kak-product" href="https://kirkandkirk.com/product/emma-jungle/">Emma</a>
    </div>
    <div class="kak-card-price">
      <span class="woocommerce-Price-amount amount"><bdi><span class="woocommerce-Price-currencySymbol">£</span>490.00</bdi></span>
    </div>
    <div class="kak-card-variant">
      <span class="kak-card-variant__type">Colour:</span>
      <span class="kak-card-variant__name">Jungle</span>
    </div>
    <div class="kak-card-controls">
      <div class="kak-card-controls__wrapper colour-carousel-scroll">
        <div data-variant="0" class="kak-card-controls__pill active">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="0" class="kak-card-controls__dot" title="Jungle" alt="Jungle" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/CONTOUR-JUNGLE-100x100.png">
          </div>
        </div>
        <div data-variant="1" class="kak-card-controls__pill">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="1" class="kak-card-controls__dot" title="Smoke" alt="Smoke" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/CONTOUR-SMOKE-100x100.png">
          </div>
        </div>
        <div data-variant="2" class="kak-card-controls__pill">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="2" class="kak-card-controls__dot" title="Glacier" alt="Glacier" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/CONTOUR-GLACIER-100x100.png">
          </div>
        </div>
        <div data-variant="3" class="kak-card-controls__pill">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="3" class="kak-card-controls__dot" title="Indigo" alt="Indigo" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/CONTOUR-INDIGO-100x100.png">
          </div>
        </div>
        <div data-variant="4" class="kak-card-controls__pill">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="4" class="kak-card-controls__dot" title="Admiral" alt="Admiral" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/CONTOUR-ADMIRAL-100x100.png">
          </div>
        </div>
        <div data-variant="5" class="kak-card-controls__pill">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="5" class="kak-card-controls__dot" title="Jet" alt="Jet" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/CONTOUR-JET-100x100.png">
          </div>
        </div>
        <div data-variant="6" class="kak-card-controls__pill">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="6" class="kak-card-controls__dot" title="Candy" alt="Candy" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/CONTOUR-CANDY-100x100.png">
          </div>
        </div>
        <div data-variant="7" class="kak-card-controls__pill">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="7" class="kak-card-controls__dot" title="Carmine" alt="Carmine" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/CONTOUR-CARMINE-100x100.png">
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""

CARD_LAYLA = """
<div class="kak-card" data-cat-name="Layla" data-category="1">
  <div class="kak-card__image-wrapper">
    <img class="kak-card__image kak-card__image--default" data-variant="0" title="Elegant, upswept frame with under-stated bevels, chamfers and hand-polished facets." alt="" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/Contour_Layla_F14_s_Admiral_Product_Thumbnail_Front-600x400.jpg">
    <a href="https://kirkandkirk.com/product/layla-admiral/">
      <img class="kak-card__image kak-card__image--hover" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/Contour_Layla_F14_s_Admiral_Product_Thumbnail_Side.jpg">
    </a>
  </div>
  <div class="kak-card__content">
    <div class="kak-card__title">
      <a class="kak-product" href="https://kirkandkirk.com/product/layla-admiral/">Layla</a>
    </div>
    <div class="kak-card-price">
      <span class="woocommerce-Price-amount amount"><bdi><span class="woocommerce-Price-currencySymbol">£</span>490.00</bdi></span>
    </div>
  </div>
</div>
"""

CARD_EVAN = """
<div class="kak-card" data-cat-name="Evan" data-category="0">
  <div class="kak-card__image-wrapper">
    <img class="kak-card__image kak-card__image--default" data-variant="0" title="Flying the Aviator to new destinations, Evan toys with the familiar silhouette and brings it’s own unique attitude." alt="" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/12/Sunglasses_Collection_Evan_S2s_Glacier_Product_Thumbnail_Front-600x400.jpg">
    <a href="https://kirkandkirk.com/product/evan-glacier/">
      <img class="kak-card__image kak-card__image--hover" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/12/Sunglasses_Collection_Evan_S2s_Glacier_Product_Thumbnail_Side.jpg">
    </a>
  </div>
  <div class="kak-card__content">
    <div class="kak-card__title">
      <a class="kak-product" href="https://kirkandkirk.com/product/evan-glacier/">Evan</a>
    </div>
    <div class="kak-card-price">
      <span class="woocommerce-Price-amount amount"><bdi><span class="woocommerce-Price-currencySymbol">£</span>525.00</bdi></span>
    </div>
    <div class="kak-card-controls">
      <div class="kak-card-controls__wrapper colour-carousel-scroll">
        <div data-variant="0" class="kak-card-controls__pill active">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="0" class="kak-card-controls__dot" title="Glacier" alt="Glacier" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/06/CENTENA-MATTE-MATTE-ICE-100x100.png">
          </div>
        </div>
        <div data-variant="1" class="kak-card-controls__pill">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="1" class="kak-card-controls__dot" title="Sage" alt="Sage" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/06/KALEIDOSCOPE-JUNIPER-100x100.png">
          </div>
        </div>
        <div data-variant="2" class="kak-card-controls__pill">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="2" class="kak-card-controls__dot" title="Royal" alt="Royal" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/06/CENTENA-ROYAL-100x100.png">
          </div>
        </div>
        <div data-variant="3" class="kak-card-controls__pill">
          <div class="kak-card-controls__pill__img_wrapper">
            <img data-variant="3" class="kak-card-controls__dot" title="Walnut" alt="Walnut" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/06/CENTENA-WALNUT-1-100x100.png">
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""

# Celebrity photo cards should be excluded by the selector
CARD_CELEBRITY = """
<div class="kak-card celebrity-wrapper">
  <img alt="" src="https://spcdn.shortpixel.ai/spio/ret_img+q_cdnize/kirkandkirk.com/wp-content/uploads/2023/09/Contour_Layla_Model_Img.jpeg">
  <span>Melicia wearing Layla in Indigo</span>
</div>
"""


def fake_kirk_and_kirk() -> httpx.MockTransport:
    routes = {
        "/robots.txt": ROBOTS,
        "/glasses/": f"<html><body><div id='listing'>{CARD_EMMA}{CARD_CELEBRITY}{CARD_LAYLA}</div></body></html>",
        "/sunglasses/": f"<html><body><div id='listing'>{CARD_EVAN}</div></body></html>",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode()
        body = routes.get(path)
        if body is not None:
            return httpx.Response(200, text=body)
        return httpx.Response(404, text="Not Found")

    return httpx.MockTransport(handler)


def test_kirk_and_kirk_shipped_config_valid():
    cfg = load_store_configs()["kirkandkirk.com"]
    assert cfg.name == "Kirk & Kirk"
    assert str(cfg.base_url) == "https://kirkandkirk.com/"
    assert cfg.country == "GB"
    assert cfg.default_currency == "GBP"
    assert cfg.default_brand == "Kirk & Kirk"
    assert cfg.lang == "en"
    assert [u.url for u in cfg.listing.urls] == ["/glasses/", "/sunglasses/"]
    assert cfg.product_pages.enabled is False
    assert cfg.listing.product == "div.kak-card[data-cat-name]"
    assert cfg.listing.link == "a.kak-product"
    assert cfg.listing.url_regex == "(/product/[^/?#]+)"


@pytest.mark.anyio
async def test_kirk_and_kirk_crawl_end_to_end():
    cfg = load_store_configs()["kirkandkirk.com"]
    async with httpx.AsyncClient(transport=fake_kirk_and_kirk(), headers={"User-Agent": "TestBot/1"}) as client:
        crawler = BaseStoreCrawler(cfg, client=client)
        crawler.delay_s = 0
        products: list[ScrapedProduct] = await crawler.crawl()

    assert len(products) == 3
    by_url = {str(p.url): p for p in products}

    emma_url = canonical_url(f"{KAK}/product/emma-jungle/", cfg.listing.url_regex)
    layla_url = canonical_url(f"{KAK}/product/layla-admiral/", cfg.listing.url_regex)
    evan_url = canonical_url(f"{KAK}/product/evan-glacier/", cfg.listing.url_regex)

    assert emma_url in by_url
    assert layla_url in by_url
    assert evan_url in by_url

    # Check Emma
    emma = by_url[emma_url]
    assert emma.name == "Emma"
    assert emma.brand == "Kirk & Kirk"
    assert emma.currency == "GBP"
    assert emma.price == 490.0
    assert "Contour_Emma" in str(emma.image_url)
    assert "roundness" in emma.flags.get("description", "")

    variants_emma = emma.flags.get("variants") or []
    assert len(variants_emma) == 8
    colors_emma = {v["color"] for v in variants_emma}
    assert "Jungle" in colors_emma
    assert "Glacier" in colors_emma
    assert "Admiral" in colors_emma
    swatches_emma = {v["swatch"] for v in variants_emma if "swatch" in v}
    assert any("CONTOUR-JUNGLE-100x100.png" in s for s in swatches_emma)

    # Check Layla
    layla = by_url[layla_url]
    assert layla.name == "Layla"
    assert layla.price == 490.0
    assert "upswept" in layla.flags.get("description", "")

    # Check Evan (Sunglasses)
    evan = by_url[evan_url]
    assert evan.name == "Evan"
    assert evan.price == 525.0
    assert "Aviator" in evan.flags.get("description", "")
    variants_evan = evan.flags.get("variants") or []
    assert len(variants_evan) == 4
    colors_evan = {v["color"] for v in variants_evan}
    assert colors_evan == {"Glacier", "Sage", "Royal", "Walnut"}


def test_kirk_and_kirk_tagger_rules_v21():
    # Product 1: Emma (roundness in description, 8 colorful variants)
    p1 = {
        "name": "Emma",
        "flags": {
            "categories": "Optique",
            "description": "Mischievous little frame combining gentle roundness with an edge. Great for smaller faces.",
            "variants": [
                {"code": "Jungle", "color": "Jungle"},
                {"code": "Smoke", "color": "Smoke"},
                {"code": "Glacier", "color": "Glacier"},
                {"code": "Indigo", "color": "Indigo"},
                {"code": "Admiral", "color": "Admiral"},
                {"code": "Jet", "color": "Jet"},
                {"code": "Candy", "color": "Candy"},
                {"code": "Carmine", "color": "Carmine"},
            ],
        },
    }
    tags1 = tag_product(p1["name"], p1["flags"])
    by_dim1 = {t.dimension: t.code for t in tags1}
    assert by_dim1["product_type"] == "optical"
    assert by_dim1["shape"] == "round"  # from "roundness" (v21 alias)

    color_tags1 = {t.code for t in tags1 if t.dimension == "color"}
    assert "green" in color_tags1  # Jungle (v21 alias)
    assert "grey" in color_tags1   # Smoke (v21 alias)
    assert "clear" in color_tags1  # Glacier (v21 alias)
    assert "blue" in color_tags1   # Indigo & Admiral (v21 alias)
    assert "black" in color_tags1  # Jet (v21 alias)
    assert "pink" in color_tags1   # Candy (v21 alias)
    assert "red" in color_tags1    # Carmine (v21 alias)

    # Product 2: Layla (upswept in description)
    p2 = {
        "name": "Layla",
        "flags": {
            "categories": "Optique",
            "description": "Elegant, upswept frame with under-stated bevels, chamfers and hand-polished facets.",
        },
    }
    tags2 = tag_product(p2["name"], p2["flags"])
    by_dim2 = {t.dimension: t.code for t in tags2}
    assert by_dim2["product_type"] == "optical"
    assert by_dim2["shape"] == "cat_eye"  # from "upswept" (v21 alias)

    # Product 3: Evan (Aviator in description, sunglasses)
    p3 = {
        "name": "Evan",
        "flags": {
            "categories": "Solaire",
            "description": "Flying the Aviator to new destinations, Evan toys with the familiar silhouette.",
            "variants": [
                {"code": "Sage", "color": "Sage"},
                {"code": "Royal", "color": "Royal"},
                {"code": "Walnut", "color": "Walnut"},
            ],
        },
    }
    tags3 = tag_product(p3["name"], p3["flags"])
    by_dim3 = {t.dimension: t.code for t in tags3}
    assert by_dim3["product_type"] == "sun"
    assert by_dim3["shape"] == "aviator"

    color_tags3 = {t.code for t in tags3 if t.dimension == "color"}
    assert "green" in color_tags3  # Sage
    assert "blue" in color_tags3   # Royal (v21 alias)
    assert "brown" in color_tags3  # Walnut (v21 alias)
