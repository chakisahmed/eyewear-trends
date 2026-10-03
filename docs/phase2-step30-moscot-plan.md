# Phase 2 Step 30: Moscot (`moscot.com`) Implementation Plan

## 1. Context & Objectives
- **Target**: **Moscot** (`moscot.com`, New York City, USA).
- **Heritage**: Founded in 1915 on Manhattan's Lower East Side by Hyman Moscot; five generations of family optical heritage. World-renowned for classic American vintage acetate icons (**LEMTOSH**, **MILTZEN**, **DAHVEN**, **ARTHUR**, **NEBB**, **ZOLMAN**).
- **Catalog Size**: **290 unique frames** (116 optical, 174 sun, 0 overlap).
- **Best-Sellers**: 55 optical best-sellers, 72 sun best-sellers.
- **Architecture**: Zero-Product-Page scraping via Shopify collection products JSON endpoints (`/collections/<cat>/products.json?limit=250`).
- **Politeness & Rate-Limiting**: High-yield stateless reads with `delay_s: 2.0` and automatic cookie clearing in `BaseStoreCrawler`.

---

## 2. Store Configuration (`store_configs.yaml`)

```yaml
  # Moscot (New York, USA), Shopify. Checked 2026-10-02: Iconic American creator eyewear house
  # founded in 1915 on Manhattan's Lower East Side by Hyman Moscot. Five generations of family
  # optical expertise. Known for timeless classic acetate silhouettes (Lemtosh, Miltzen, Dahven)
  # with real riveted hinges and rich colorways. Captures all 290 frames across 4 polite requests.
  moscot.com:
    name: "Moscot"
    base_url: "https://moscot.com"
    lang: en
    country: US                         # New York City, Lower East Side (heritage since 1915)
    default_brand: "Moscot"
    default_currency: USD
    delay_s: 2.0
    listing:
      urls:
        - { url: "/collections/eyeglasses/products.json?limit=250", categories: "Optique" }
        - { url: "/collections/sunglasses/products.json?limit=250", categories: "Solaire" }
        - { url: "/collections/best-selling-eyeglasses/products.json?limit=250", flag: "is_bestseller" }
        - { url: "/collections/best-selling-sunglasses/products.json?limit=250", flag: "is_bestseller" }
        - { url: "/collections/new-eyeglasses/products.json?limit=250", flag: "is_new" }
        - { url: "/collections/new-sunglasses/products.json?limit=250", flag: "is_new" }
      product: ".card-product"
      link: "a[href*='/products/']"
      url_regex: '(/products/[^/?#]+)'
    product_pages:
      enabled: false                    # Zero-Product-Page scraping: JSON endpoint supplies full metadata
    fields:
      name: { css: ".card__heading" }
      price: { css: ".price" }
      image_url: { css: "img" }
```

---

## 3. Parser Enhancement (`parser.py`)

- In `parse_shopify_json_listing`:
  - When variant `option1` is present and the product's options indicate `name == "Color"` or `name == "Colour"`, use `v["option1"]` as the variant color (cleanly omitting the `/ 44` frame size).
  - Support `shape-<silhouette>` tags (e.g. `shape-square`, `shape-round`, `shape-aviator`, `shape-cateye`) by mapping stripped values into `desc_parts` to enable shape taxonomy classification.

---

## 4. Taxonomy & Tagger Rules (v27 in `tagger.py`)

- **Bump `RULES_VERSION = 27`**.
- Add Moscot color aliases:
  - `flesh` $\rightarrow$ `beige` (Moscot's signature vintage crystal champagne nude acetate)
  - `bark` $\rightarrow$ `brown`
  - `butterscotch` $\rightarrow$ `orange`
  - `spot tortoise`, `tokyo tortoise`, `antique tortoise`, `heritage tortoise`, `burnt tortoise`, `matte tortoise` $\rightarrow$ `tortoiseshell`
  - `g 15`, `g 15 fade` $\rightarrow$ `green`
  - `umber crystal` $\rightarrow$ `brown`
  - `brown smoke` $\rightarrow$ `brown`, `blue smoke` $\rightarrow$ `blue`

---

## 5. Offline Fixtures & Test Suite

1. **Fixtures**:
   - `backend/tests/fixtures/moscot_eyeglasses_products.json` (116 frames).
   - `backend/tests/fixtures/moscot_sunglasses_products.json` (174 frames).
2. **Unit Tests (`tests/test_store_moscot.py`)**:
   - Config validation (store name, currency `USD`, country `US`, 6 listing URLs, `product_pages.enabled: false`).
   - Parser tests for eyeglasses (116 items, prices, variants, material acetate, shape).
   - Parser tests for sunglasses (174 items, prices, variants, material).
   - Offline crawler simulation with `httpx.MockTransport` and real robots.txt rules.
   - Tagging tests verifying `material: acetate`, `color: beige` (Flesh), `color: tortoiseshell` (Spot Tortoise), `shape: round/square` (Lemtosh/Miltzen).
3. **Integration**:
   - Update `test_store_crawlers.py` active store count assertion from 20 to 21 stores.
   - Verify full pytest test suite (463 passed, 100% green).

---

## 6. Execution Steps (Completed 2026-10-02)

1. Saved offline fixtures `moscot_eyeglasses_products.json` and `moscot_sunglasses_products.json`.
2. Applied `parser.py` enhancement (`option1` colorway, `shape-` tag detection, and canonical brand prefix normalization).
3. Added `moscot.com` entry in `store_configs.yaml` with Zero-Product-Page scraping and `delay_s: 2.0`.
4. Bumped `RULES_VERSION = 27` and added Moscot aliases in `tagger.py`.
5. Implemented `tests/test_store_moscot.py` and updated `tests/test_store_crawlers.py`.
6. Full pytest test suite: **463 tests passing (100% green)**.
7. Live crawl executed: **290 products crawled, 290 updated, 0 dropped, 127 best-sellers flagged, 26 new arrivals flagged**.
8. Retagged: 5,116 products across all 21 stores in DB. Moscot yield: 160 acetate, 26 metal, 174 sun, 116 optical, rich shapes and colorways.
9. Documentation updated: `docs/scouting/moscot/notes.md` and `docs/acetate-creative-brands.md` row 35 set to `Tracked (crawled)`.
