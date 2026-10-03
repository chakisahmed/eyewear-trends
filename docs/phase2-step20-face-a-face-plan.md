# Step 20: Face à Face, the eighth creator brand (France, Umbraco, presence-only)

Scouting: `docs/scouting/face-a-face/` (notes and live checks, 2026-10-01). Creator brand founded in Paris (Design Eyewear Group), known for sculptural acetate, geometric architecture, and vibrant colour blocking.

## What the pages show
- Optical `/en/optical` (3 server-rendered pages of 50 each, **107** active models) and sun `/en/sun` (1 page, **12** active models; note: `/en/sunglass` was a 404). Total catalog: **119** unique models (~500+ colorway SKUs).
- Pagination: server query parameter `?Page=2` (capitalized `Page`, 50 cards per page).
- Cards on listing pages: `a.product-showcase__placement` inside `div.product-placement__wrapper`.
  - Href attributes contain port `:443` and default tracking: `https://www.faceaface-paris.com:443/en/optical/face-a-face/friday/friday-3132051?colorCode=100`.
  - Canonical identity regex: `(/en/(?:optical|sun)/[^/]+/[^/]+/[^/?#]+)` cleanly strips `:443` and `?colorCode=...`.
- Product page:
  - Structured specs inside `.specs__container`:
    - `Name: friday 2`
    - `Material: acetate` (also titanium, aluminium, stainless steel, nylon)
    - `Style: feminine` (also masculine, unisex) -> the site uses "Style" for audience/gender
    - `Front Type: full rim` (also semi-rimless, rimless)
    - `Size: 50 22 mm` (calibre 50 mm, bridge 22 mm)
    - `Temple Length: 142 mm`
  - Color swatches & variants:
    - Active colorway displayed in `.slider-caption__color`:
      - Code: `.slider-caption__color--code` ("100")
      - Name: `.slider-caption__color--name` ("BLACK")
    - Sibling colorways linked via `.product-list-item[href*="colorCode="]`.
  - Shape: No shape filter and no dedicated shape spec on the site. Model names and concept text (`.concept-box__text`) are matched where present.
- Pricing: **Presence-only** (no consumer price displayed, B2B optician distribution, `default_currency: EUR`).

## Architectural Decisions
1. **Catalog entry points & pagination**:
   - `urls`: `/en/optical` (`categories: "Optique"`), `/en/sun` (`categories: "Solaire"`).
   - `pagination`: `{ param: Page, max_pages: 5 }`.
2. **Card & Canonical links**:
   - `product`: `div.product-placement__wrapper`
   - `link`: `a.product-showcase__placement`
   - `url_regex`: `(/en/(?:optical|sun)/[^/]+/[^/]+/[^/?#]+)`
3. **Product page specs & variants**:
   - `specs`: `rows: ".specs__container"`, `key: ".specs--label"`, `value: ".specs--value"`.
   - `variants`: `rows: ".slider-caption__color"`, `code: { css: ".slider-caption__color--code" }`, `label: { css: ".slider-caption__color--name" }`.
   - `flags`: `description: { css: ".concept-box__text", scope: page }`.
4. **Tagger rules v17 (`tagger.py`)**:
   - Add audience words to `CATEGORY_TAGS`: `feminine`, `feminin` -> `women`; `masculine`, `masculin` -> `men`.
   - Update `SPEC_DIMENSIONS`: allow `style: ("style", "audience")` so stores using "Style: feminine" map cleanly to `audience: women` while retaining taxonomy style matching.
   - Map `front type: "shape"` in `SPEC_DIMENSIONS` so `semi-rimless` / `rimless` tags taxonomy shape `rimless`.
   - Add `SPEC_ALIASES["material"]`: `("aluminium", "metal")`, `("aluminum", "metal")`.

## Store Entry (`store_configs.yaml`, `faceaface-paris.com`, `country: FR`)
```yaml
  faceaface-paris.com:
    name: "Face à Face"
    base_url: "https://www.faceaface-paris.com"
    lang: en
    country: FR
    default_brand: "Face à Face"
    default_currency: EUR
    delay_s: 1.5
    listing:
      urls:
        - { url: "/en/optical", categories: "Optique" }
        - { url: "/en/sun", categories: "Solaire" }
      pagination: { param: Page, max_pages: 5 }
      product: "div.product-placement__wrapper"
      link: "a.product-showcase__placement"
      url_regex: '(/en/(?:optical|sun)/[^/]+/[^/]+/[^/?#]+)'
    product_pages:
      enabled: true
      max_products: 300
    fields:
      name: { css: ".slider-caption__shape--name, .concept-box__name", scope: page }
      image_url: { css: ".product-slider__image, .product-placement__image--front", attr: ["src", "data-bg"], scope: page }
    flags:
      description: { css: ".concept-box__description", scope: page }
    specs:
      rows: ".specs__container"
      key: ".specs--label"
      value: ".specs--value"
    variants:
      rows: ".slider-caption__color"
      code: { css: ".slider-caption__color--code" }
      label: { css: ".slider-caption__color--name" }
```

## Tests (`test_store_face_a_face.py`)
- Mock responses for optical and sun listing pages with `?Page=` pagination using `MockTransport`.
- Canonical URLs normalized (port `:443` and query string removed).
- Specs extracted: `Material: acetate` -> `material: acetate`; `Style: feminine` -> `audience: women`; `Front Type: semi-rimless` -> `shape: rimless`.
- Variant extracted: code `100`, color `BLACK` -> `color: black` with `supplier_code: 100`.
- Shipped config tests updated for 11 stores (`test_shipped_config_has_the_eleven_stores`).
- Full test suite: **423 passed in 41.58s**.

## Live Crawl Results (2026-10-01)
- `python -m app.cli crawl-store faceaface-paris.com`:
  - 107 products listed (95 optical across 3 pages, 12 sun on 1 page).
  - 107 product pages crawled.
  - Inserted: 107, updated: 0, conflicts: 0, dropped: 0.
- `python -m app.cli retag-products`:
  - 2,514 products retagged across the database.
  - 107/107 Face à Face products tagged for `audience` (100% yield: `women`, `men`, `unisex` from `Style: feminine/masculine/unisex`).
  - 105/107 tagged for `material` (`acetate`, `titanium`, `metal` via aluminium).
  - 103/107 tagged for `color` with exact supplier variant codes (Palier 3).
