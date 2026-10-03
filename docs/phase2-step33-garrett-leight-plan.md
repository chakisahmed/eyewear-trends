# Phase 2 — Step 33: Garrett Leight Onboarding Plan

## Target Store
- **Brand**: Garrett Leight California Optical (GLCO) & Mr. Leight
- **Domain**: `garrettleight.com`
- **Country**: `US` (Venice Beach, Los Angeles, California, USA)
- **Currency**: `USD`
- **Catalog Size**: 155 unique frames (77 optical, 78 sun; 125 GLCO, 30 Mr. Leight)
- **Flagship Silhouettes**: Hampton, Kinney, Brooks, Wilson, Harding, Clune, Calabar

---

## 1. Offline Fixtures
- Fetch sample optical and sunglasses JSON listings from `garrettleight.com`:
  - `backend/tests/fixtures/garrettleight_eyeglasses.json` (sample from `/collections/eyeglasses/products.json?limit=250`)
  - `backend/tests/fixtures/garrettleight_sunglasses.json` (sample from `/collections/sunglasses/products.json?limit=250`)
  - `backend/tests/fixtures/garrettleight_bestsellers.json` (sample from `/collections/bestsellers/products.json?limit=250`)

---

## 2. Parser Enhancements (`backend/app/collectors/stores/parser.py`)
- Support `shape:<value>` tags (in addition to `shape-<value>`):
  - Ingest `shape:square`, `shape:round`, `shape:aviator`, `shape:rectangle`, `shape:oval`, `shape:geometric`, `shape:cat eye`, `shape:octagonal` into `flags["description"]`.
- Vendor normalization:
  - If vendor is `GLCO` and default brand is `Garrett Leight`, set brand to `Garrett Leight`.
  - If vendor is `Mr. Leight`, retain `Mr. Leight` (or format as `Garrett Leight (Mr. Leight)`).
- Material extraction:
  - `material:acetate` or `material:combo` -> `acetate`
  - `material:metal` or `titanium` -> `metal`
  - Default for Garrett Leight frames without explicit material tag: `acetate`.

---

## 3. Store Configuration (`backend/app/collectors/stores/store_configs.yaml`)
- Add `garrettleight.com` under `stores:`:
  ```yaml
  garrettleight.com:
    name: "Garrett Leight"
    base_url: "https://www.garrettleight.com"
    lang: en
    country: US                         # Venice Beach, Los Angeles, USA (founded 2010)
    default_brand: "Garrett Leight"
    default_currency: USD
    delay_s: 2.0
    listing:
      urls:
        - { url: "/collections/eyeglasses/products.json?limit=250", categories: "Optique" }
        - { url: "/collections/mr-leight-eyeglasses/products.json?limit=250", categories: "Optique" }
        - { url: "/collections/sunglasses/products.json?limit=250", categories: "Solaire" }
        - { url: "/collections/mr-leight-sunglasses/products.json?limit=250", categories: "Solaire" }
        - { url: "/collections/ml-sunglasses/products.json?limit=250", categories: "Solaire" }
        - { url: "/collections/bestsellers/products.json?limit=250", flag: "is_bestseller" }
        - { url: "/collections/forever-classics/products.json?limit=250", flag: "is_bestseller" }
        - { url: "/collections/new-eyeglasses/products.json?limit=250", flag: "is_new" }
        - { url: "/collections/new-sunglasses/products.json?limit=250", flag: "is_new" }
      product: ".product-card"
      link: "a"
      url_regex: '(/products/[^/?#]+)'
    fields:
      name: { css: ".product-card__title" }
      price: { css: ".price" }
      image_url: { css: "img" }
  ```

---

## 4. Taxonomy & Color Aliases (`backend/app/collectors/stores/tagger.py`)
- Bump `RULES_VERSION = 30`.
- Add GLCO signature color aliases to `SPEC_ALIASES['color']`:
  - `true demi` -> `tortoiseshell`
  - `olio` -> `green`
  - `cyprus fade`, `cyprus` -> `green`
  - `cola` -> `brown`
  - `willow` -> `green`
  - `brew` -> `brown`
  - `sandstorm` -> `beige`
  - `himalayan salt` -> `pink`
  - `strawberry jam` -> `red`
  - `douglas fir` -> `green`
  - `pinewood` -> `green`
  - `pure glass` -> `clear`
  - `oakmoss` -> `green`
  - `barolo` -> `red`
  - `sea glass` -> `green`
  - `truffle` -> `brown`
  - `java drift` -> `brown`
  - `sandalwood drift` -> `beige`
  - `kelp` -> `green`
  - `prosecco` -> `beige`
  - `stillwater` -> `blue`
  - `driftwood` -> `beige`
  - `pewter` -> `grey`
  - `basalt` -> `grey`
  - `hunter` -> `green`
  - `limu` -> `green`
  - `serpentine` -> `green`
  - `lipstick` -> `red`
  - `fig` -> `purple`
- Add shape alias `octagonal` -> `geometric`.

---

## 5. Test Suite & Verification
- Create `backend/tests/test_store_garrett_leight.py`:
  - `test_garrett_leight_config_valid()`
  - `test_garrett_leight_listing_parser_optical()` (Hancock, Weddington, Verdugo)
  - `test_garrett_leight_listing_parser_sunglasses()` (Chaparral, Lugo, Kinney)
  - `test_garrett_leight_crawler_offline()` (MockTransport, 0 dropped, bestseller flags)
  - `test_garrett_leight_tagging()`
- Update `test_store_crawlers.py`:
  - 23 -> 24 stores (`test_shipped_config_has_the_twenty_four_stores()`).
  - Add `"garrettleight.com"` and `"US"`.
- Run full pytest test suite (target: 478+ tests passing, 100% green).

---

## 6. Live Crawl & Retag
- Run live crawl: `python -m app.cli crawl-stores --force garrettleight.com`
- Verify ~155 frames inserted with 0 dropped products.
- Run retag: `python -m app.cli retag-products`
- Update scouting notes and [docs/acetate-creative-brands.md](file:///c:/Users/chaki/eyewear-trends/docs/acetate-creative-brands.md) row 36 to `Tracked (crawled)`.
