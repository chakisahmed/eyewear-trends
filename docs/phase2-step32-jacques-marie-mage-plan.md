# Phase 2 Step 32: Jacques Marie Mage (`jacquesmariemage.com`) Implementation Plan

## 1. Context & Objectives
- **Target**: **Jacques Marie Mage** (`jacquesmariemage.com`, Los Angeles, USA).
- **Heritage**: Founded in 2014 by French designer Jerome Jacques Marie Mage; hand-assembled in Sabae, Japan. World-renowned pinnacle of limited-edition luxury acetate eyewear (thick 10mm block cured cellulose acetate, sterling silver 925 and 18k gold hardware, custom 7-barrel hinges, serialized numbered batches of 250–500 pieces).
- **Catalog Size**: **259 unique frames** (36 optical, 223 sun, 0 overlap).
- **Iconic Models**: DEALAN, ZEPHIRIN, MOLINO, TORINO, FELLINI, TAOS, ENZO, WALKER.
- **Architecture**: Zero-Product-Page scraping via Shopify collection products JSON endpoints (`/collections/optical-1/products.json?limit=250` and `/collections/sunglasses/products.json?limit=250`, plus `/collections/the-icons/products.json?limit=250`).
- **Politeness & Rate-Limiting**: Avoids heavy HTML storefront pages that trigger HTTP 429 rate limits; captures 100% of the catalog in just **3 polite requests** (`delay_s: 2.0`).

---

## 2. Store Configuration (`store_configs.yaml`)

```yaml
  # Jacques Marie Mage (Los Angeles, USA), Shopify. Checked 2026-10-02:
  # Ultra-luxury creator eyewear founded in 2014 by Jerome Jacques Marie Mage;
  # handcrafted in Sabae, Japan from 10mm cured cellulose acetate with sterling silver
  # hardware. Uses Shopify products.json API to bypass HTML HTTP 429 rate limits,
  # capturing all 259 frames across 3 polite requests.
  jacquesmariemage.com:
    name: "Jacques Marie Mage"
    base_url: "https://jacquesmariemage.com"
    lang: en
    country: US                         # Los Angeles, USA (handcrafted in Sabae, Japan)
    default_brand: "Jacques Marie Mage"
    default_currency: USD
    delay_s: 2.0
    listing:
      urls:
        - { url: "/collections/optical-1/products.json?limit=250", categories: "Optique" }
        - { url: "/collections/sunglasses/products.json?limit=250", categories: "Solaire" }
        - { url: "/collections/the-icons/products.json?limit=250", flag: "is_bestseller" }
      product: ".product-card"
      link: "a"
      url_regex: '(/products/[^/?#]+)'
    product_pages:
      enabled: false                    # Zero-Product-Page scraping: JSON endpoint supplies full metadata & avoids 429s
    fields:
      name: { css: ".product-card__title" }
      price: { css: ".price" }
      image_url: { css: "img" }
```

---

## 3. Parser Enhancements (`parser.py`)

- In `parse_shopify_json_listing`:
  - When `cfg.default_brand == "Jacques Marie Mage"`:
    - If `any("metal" in t or "titanium" in t for t in lower_tags) or "ti" in p.get("title", "").lower().split()`:
      `flags["material"] = "metal"`
    - Else:
      `flags["material"] = "acetate"` (JMM's signature 10mm cured cellulose acetate).
  - Support `Best Sellers` and `The Icons` tags:
    `if any(t in ("best seller", "best sellers", "bestseller", "bestsellers", "the icons") for t in lower_tags): flags["is_bestseller"] = True`.

---

## 4. Taxonomy & Tagger Rules (v29 in `tagger.py`)

- **Bump `RULES_VERSION = 29`**.
- Add Jacques Marie Mage color aliases to `SPEC_ALIASES["color"]`:
  ```python
  # Jacques Marie Mage (USA)
  ("argyle", "tortoiseshell"),
  ("bourbon", "brown"),
  ("bloodstone", "red"),
  ("agar", "tortoiseshell"),
  ("beluga", "black"),
  ("darjeeling", "brown"),
  ("amarena", "red"),
  ("frost", "clear"),
  ("vanta", "black"),
  ("auburn", "brown"),
  ("taupe", "beige"),
  ("rover", "green"),
  ("solar", "orange"),
  ("tempest", "grey"),
  ("charbon", "black"),
  ("suntan", "beige"),
  ("himalaya", "clear"),
  ("viridian", "green"),
  ("stallion", "black"),
  ```

---

## 5. Offline Fixtures & Test Suite (`test_store_jacques_marie_mage.py`)

- Save fixtures:
  - `backend/tests/fixtures/jacquesmariemage_optical.json`
  - `backend/tests/fixtures/jacquesmariemage_sunglasses.json`
- Tests:
  1. `test_jacques_marie_mage_config_valid`: Validates store config schema, 3 URLs, zero product pages, US/USD.
  2. `test_jacques_marie_mage_listing_parser_optical`: Validates optical parsing (Dealan MX RX, Zephirin MX RX, Molino MX RX, prices, variants, acetate).
  3. `test_jacques_marie_mage_listing_parser_sunglasses`: Validates sun parsing (Photochromic Dealan, Molino, Torino, prices, variants, acetate, shapes).
  4. `test_jacques_marie_mage_crawl_mock`: Tests `BaseStoreCrawler` with `httpx.MockTransport` across all listing URLs, validating 0 dropped and bestseller flagging.
  5. `test_jacques_marie_mage_tagging`: Validates color and material taxonomy tagging for JMM variants.
- Update `backend/tests/test_store_crawlers.py`:
  - Active store count updated from 22 to 23.

---

## 6. Execution & Verification

1. Run unit test suite: `python -m pytest backend/tests/test_store_jacques_marie_mage.py` and `python -m pytest backend/tests/`.
2. Live crawl: `python -m app.cli crawl-stores --force jacquesmariemage.com`.
3. Retag: `python -m app.cli retag-products`.
4. Update `docs/scouting/jacques-marie-mage/notes.md` with live stats and update `docs/acetate-creative-brands.md` row 37 to `Tracked (crawled)`.
