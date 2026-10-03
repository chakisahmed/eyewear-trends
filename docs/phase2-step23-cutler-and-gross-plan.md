# Step 23: Cutler and Gross, the tenth creator brand (UK / Italy, Shopify, e-commerce)

Scouting: `docs/scouting/cutler-and-gross/` (notes and live checks, 2026-10-02).
Iconic luxury British eyewear brand founded in Knightsbridge, London in 1969 by Graham Cutler and Tony Gross, handmade in their own atelier in Cadore, Italy. Celebrated for thick, architectural handmade acetate frames, bold tortoiseshells, and graduated colorways.

---

## 1. What the Pages Show

- **Catalogs**:
  - Optical `/collections/optical-designer-glasses`: **127** frames across 3 server-rendered pages (45 + 45 + 37).
  - Sun `/collections/sunglasses`: **113** frames across 5 server-rendered pages (26 + 26 + 26 + 26 + 9).
  - Total catalog: exactly **240** models.
- **Pagination**: Server query parameter `?page=2..6` (Shopify standard collection pagination, 8 total requests across both collections).
- **Cards on listing pages (`product-card.product-card`)**:
  - Frame link & clean name: `a[title^='Go to ']` with regex `Go to (.+)` (e.g. `1434 Square Sunglass`, `9261 Cat Eye Sunglasses`, `0001 Round Sunglasses`).
    - Every title explicitly encodes: Model number (`1434`, `9261`), Silhouette shape (`Square`, `Cat Eye`, `Round`, `Aviator`), and Category (`Sunglass` / `Sunglasses` / `Glasses`).
  - Price: `span.product-card__price` (`Regular price £410.00` $\rightarrow$ `410.0 GBP`).
  - Image: `img[data-card-media-image]` (high-resolution CDN images).
  - Badges: `span.product-card__badges` (`New`).
  - Colorway variants: `<fieldset> input.variant-option-radio-input` exposes all colorway names (`Olive on Black`, `Humble Potato`, `Old Brown Havana`, `Olive`, `Black`, `Havana`, `Horn Crystal`, `Sand Crystal`).
- **Architectural Breakthrough**:
  - Individual product pages (`/products/{handle}`) are protected by Cloudflare / Shopify rate limiting (`429 local_rate_limited` with 60s cooldown).
  - Because collection listing cards already provide **100% of all required fields** (descriptive model title, silhouette shape, price in GBP, high-res image, `New` badge, and colorway variants), **Cutler and Gross requires zero product page crawls** (`product_pages.enabled: false`).
  - The entire 240-frame catalog is crawled in just **8 fast, polite, edge-cached HTTP requests**!

---

## 2. Architectural Decisions

1. **Catalog Entry Points & Pagination**:
   - `urls`:
     - `{ url: "/collections/optical-designer-glasses", categories: "Optique" }`
     - `{ url: "/collections/sunglasses", categories: "Solaire" }`
   - `pagination`: `{ param: page, max_pages: 6 }`
2. **Card & Canonical Links**:
   - `product`: `product-card.product-card`
   - `link`: `a[title^='Go to ']`
   - `url_regex`: `'(/products/[^/?#]+)'`
3. **Field Extraction Rules**:
   - `name`: `{ css: "a[title^='Go to ']", attr: "title", regex: 'Go to (.+)' }`
   - `price`: `{ css: "span.product-card__price" }`
   - `image_url`: `{ css: "img[data-card-media-image]", attr: ["src", "data-src"] }`
   - `flags`:
     - `is_new`: `{ css: "span.product-card__badges", exists: true }`
4. **Card Variants Rule**:
   - `variants`:
     - `rows`: `fieldset input.variant-option-radio-input`
     - `code`: `{ attr: "value" }`
     - `label`: `{ attr: "value" }`
5. **Parser Card-Level Variants Support**:
   - Enable `parse_variants(card, cfg.variants)` in `parse_listing` when `product_pages.enabled` is false so card-level variant buttons cleanly reach `flags["variants"]`.
6. **Tagger Vocabulary (v20)**:
   - Add Cutler and Gross distinct colorway terms:
     - `olive on black` $\rightarrow$ `two_tone`
     - `humble potato` $\rightarrow$ `tortoiseshell`
     - `old brown havana` $\rightarrow$ `tortoiseshell`
     - `smoke quartz` $\rightarrow$ `grey`
     - `horn crystal` $\rightarrow$ `crystal`
     - `sand crystal` $\rightarrow$ `crystal`

---

## 3. Store Entry (`store_configs.yaml`, `cutlerandgross.com`, `country: GB`)

```yaml
  cutlerandgross.com:
    name: "Cutler and Gross"
    base_url: "https://www.cutlerandgross.com"
    lang: en
    country: GB                         # Knightsbridge, London (UK), handmade in Cadore, Italy
    default_brand: "Cutler and Gross"
    default_currency: GBP
    delay_s: 1.5
    listing:
      urls:
        - { url: "/collections/optical-designer-glasses", categories: "Optique" }
        - { url: "/collections/sunglasses", categories: "Solaire" }
      pagination: { param: page, max_pages: 6 }
      product: "product-card.product-card"
      link: "a[title^='Go to ']"
      url_regex: '(/products/[^/?#]+)'
    fields:
      name: { css: "a[title^='Go to ']", attr: "title", regex: 'Go to (.+)' }
      price: { css: "span.product-card__price" }
      image_url: { css: "img[data-card-media-image]", attr: ["src", "data-src"] }
    flags:
      is_new: { css: "span.product-card__badges", exists: true }
    variants:
      rows: "fieldset input.variant-option-radio-input"
      code: { attr: "value" }
      label: { attr: "value" }
```

---

---

## 5. Execution Results & Metrics

- **Unit Tests**:
  - `backend/tests/test_store_cutler_and_gross.py`: 3/3 passed.
  - Full test suite: **432 passed in 39.86s (100% green)**.
- **Live Crawl**:
  - `cutlerandgross.com`: **240 products crawled** (127 optical, 113 sun across 8 pagination requests).
  - Breakdown: `inserted 240, updated 0, conflicts 0, reactivated 0, dropped 0`.
- **Tagger v20 Yield**:
  - `product_type`: 240 / 240 (100.0%)
  - `shape`: 238 / 240 (99.2%)
  - `color`: 192 / 240 (80.0%)
- **Database Total**:
  - **3,573 products across 14 stores**.
- **Status**: **COMPLETE**.

