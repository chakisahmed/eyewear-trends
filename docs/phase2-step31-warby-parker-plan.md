# Phase 2 Step 31: Warby Parker (`warbyparker.com`) Implementation Plan

## 1. Context & Objectives
- **Target**: **Warby Parker** (`warbyparker.com`, New York City, USA).
- **Heritage**: Founded in 2010 by Neil Blumenthal, Andrew Hunt, David Gilboa, and Jeffrey Raider (Wharton classmates). Pioneer of the direct-to-consumer (DTC) acetate eyewear revolution, famous for classic vintage-inspired silhouettes, custom cellulose acetate from family-run Italian factories, and making designer eyewear accessible starting at $95.
- **Catalog Size**: **365 unique frame models**, totaling **740 colorway variants** (240 optical models / 498 colorways, 125 sun models / 242 colorways). Matches 100% of the 741 product URLs in `sitemap-products.xml`.
- **Best-Sellers**: 61 optical best-sellers, 43 sun best-sellers (via `merch=best-seller`).
- **New Arrivals**: 26 optical new arrivals, 25 sun new arrivals (via `merch=new-arrival`).
- **Architecture**: Zero-Product-Page scraping via reverse-engineered internal catalog API (`/v1/catalog/frames/search`).
  - Completely allowed under `robots.txt`.
  - Avoids downloading over 500MB of heavy Next.js CSR HTML.
  - Completely avoids DataDome bot challenges and IP rate-limiting.
  - Captures 100% of the catalog in just **6 polite HTTP requests**.
- **Politeness & Rate-Limiting**: Delay of 2.0s per request (`delay_s: 2.0`), total runtime ~15s.

---

## 2. Store Configuration (`store_configs.yaml`)

```yaml
  # Warby Parker (New York, USA), Next.js / Internal Catalog API. Checked 2026-10-02:
  # Pioneer of DTC acetate eyewear founded in 2010. Hand-polished cellulose acetate,
  # classic vintage silhouettes, starting at $95. Uses internal catalog search API
  # (/v1/catalog/frames/search) allowed by robots.txt, capturing all 365 models, 740 colorways,
  # shapes, materials, and bestseller flags across 6 polite requests.
  warbyparker.com:
    name: "Warby Parker"
    base_url: "https://www.warbyparker.com"
    lang: en
    country: US                         # New York City, USA (founded 2010; DTC acetate pioneer)
    default_brand: "Warby Parker"
    default_currency: USD
    delay_s: 2.0
    listing:
      urls:
        - { url: "/v1/catalog/frames/search?kind=eyeGlasses&size=300", categories: "Optique" }
        - { url: "/v1/catalog/frames/search?kind=sunGlasses&size=300", categories: "Solaire" }
        - { url: "/v1/catalog/frames/search?kind=eyeGlasses&merch=best-seller&size=300", flag: "is_bestseller" }
        - { url: "/v1/catalog/frames/search?kind=sunGlasses&merch=best-seller&size=300", flag: "is_bestseller" }
        - { url: "/v1/catalog/frames/search?kind=eyeGlasses&merch=new-arrival&size=300", flag: "is_new" }
        - { url: "/v1/catalog/frames/search?kind=sunGlasses&merch=new-arrival&size=300", flag: "is_new" }
      product: ".frame-card"
      link: "a"
      url_regex: '(/sunglasses/[^/?#]+|/eyeglasses/[^/?#]+)'
    product_pages:
      enabled: false                    # Zero-Product-Page scraping: API supplies complete catalog & variants
    fields:
      name: { css: ".frame-name" }
      price: { css: ".frame-price" }
      image_url: { css: "img" }
```

---

## 3. Parser Support (`parser.py`)

- Add `parse_warby_parker_json_listing` in `backend/app/collectors/stores/parser.py`:
  - Recognizes JSON payloads containing `"total"` and `"items"` when `cfg.default_brand == "Warby Parker"` or `"warbyparker" in page_url`.
  - For each model family `fam` in `items`:
    - Derive canonical model URL: `/{kind}/{model_slug}` (e.g. `/sunglasses/bix`, `/sunglasses/bodie`, `/eyeglasses/esme`, `/eyeglasses/durand`).
    - Model name: `name` (e.g. `Bix`, `Bodie`, `Esme`).
    - Price: float from `v0.get("price")` (e.g. `95.0`).
    - Brand: `Warby Parker`.
    - Image: `images.front` or `images.angle` or `images.baseTransparent`.
    - Material: `"HB"` $\rightarrow$ `"acetate"`; `"GD"`/`"SB"`/`"DM"` $\rightarrow$ `"metal"`.
    - Description: `description` + `primaryShape.lower()`.
    - Variants: `flags["variants"] = [{"code": v["id"], "color": v["color"], "in_stock": v.get("isInStock", True)}]`.
    - Out of stock: `flags["out_of_stock"] = not any(v.get("isInStock", True) for v in fam)`.

---

## 4. Taxonomy & Tagger Rules (v28 in `tagger.py`)

- **Bump `RULES_VERSION = 28`**.
- Add Warby Parker color aliases to `SPEC_ALIASES["color"]`:
  ```python
  # Warby Parker (USA)
  ("striped sassafras", "brown"),
  ("striped cypress", "brown"),
  ("saltwater matte", "blue"),
  ("oak barrel", "brown"),
  ("brushed ink", "blue"),
  ("cactus crystal", "green"),
  ("laguna crystal", "blue"),
  ("seaweed crystal", "green"),
  ("rose water", "pink"),
  ("eastern bluebird fade", "blue"),
  ("black walnut", "brown"),
  ("honeydew", "green"),
  ("canopy", "green"),
  ("ristretto", "brown"),
  ("tamarind", "brown"),
  ("marzipan", "beige"),
  ```

---

## 5. Offline Fixtures & Test Suite (`test_store_warby_parker.py`)

- Capture real fixture responses:
  - `backend/tests/fixtures/warbyparker_eyeglasses.json`
  - `backend/tests/fixtures/warbyparker_sunglasses.json`
- Tests:
  1. `test_warby_parker_config_valid`: Validates store config schema, 6 URLs, zero product pages, US/USD.
  2. `test_warby_parker_listing_parser_eyeglasses`: Validates optical parsing, model URLs, prices, variants, material, and shape description.
  3. `test_warby_parker_listing_parser_sunglasses`: Validates sun parsing, Bix/Bodie models, Umber Crystal / Saltwater Matte colorways.
  4. `test_warby_parker_crawl_mock`: Tests `BaseStoreCrawler` with `httpx.MockTransport` over all 6 listing URLs, validating 0 dropped, bestseller flagging, and new arrivals.
- Update `backend/tests/test_store_crawlers.py`:
  - Active store count updated from 21 to 22.

---

## 6. Execution & Verification

1. Run unit test suite: `pytest backend/tests/test_store_warby_parker.py` and `pytest backend/tests/`.
2. Live crawl: `python -m app.cli crawl-stores --force warbyparker.com`.
3. Retag: `python -m app.cli retag-products`.
4. Update `docs/scouting/warby-parker/notes.md` with live stats and update `docs/acetate-creative-brands.md` row 39 to `Tracked (crawled)`.
