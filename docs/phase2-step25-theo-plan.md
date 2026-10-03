# Step 25: Theo Eyewear (Belgium, Webflow, Design Families & Mother Models)

Scouting: `docs/scouting/theo/notes.md` (live checks & architectural inspection, 2026-10-02).
Belgian avant-garde creator brand founded in Antwerp in 1989 by Patrick Hoet and Wim Somers (*"theo loves you"*). Celebrated worldwide for fearless fluorescent color pairings, architectural shapes, asymmetric cuts, dual-color acetate laminations, and surgical stainless steel/titanium frames.

---

## 1. What the Pages Show

- **Catalog Hierarchy**:
  - **Families**: 9 active design collections (`tubes`, `friskos`, `isolines`, `flow`, `waves`, `glues`, `locks`, `clin-d-oeil`, `bourbon-way`).
  - **Models ("Mothers")**: 48 unique frame silhouettes across all 9 families (5 to 6 models per family).
  - **Colorways ("Children")**: 8 to 14 distinct colorways per frame model (~450–550 total SKUs).
- **Navigation & Access**:
  - `robots.txt`: Completely open (length 0, zero disallow rules).
  - CDN: Webflow CMS on Cloudflare edge cache (`cf-cache-status: HIT`).
  - Front-end sliding drawer (Barba.js + GSAP) renders 100% static HTML on direct HTTP requests.
- **Family Collection Pages (`/families/<slug>`)**:
  - Cards: `a.product-item[data-family-item]` with link `href="/mothers/<model>"`
  - Model name: `h2.product-item__name` (e.g. `YG`, `APPLE`, `BELLO`, `LOCTITE`)
  - Image: `img.product-item__img`
  - Color count: `p.p-med` (e.g. `10 colours`)
- **Model Product Pages (`/mothers/<slug>`)**:
  - Rich variant list: `div.product-item.is--wide`
  - Exact color formula in `a.save-icon[data-model]` (e.g. `APPLE 003 MM ELECTRIC BLUE + TRANSPARENT DELFT WARE BLUE`, `APPLE 014 FLUO ORANGE + ORANGE GIVREE`, `APPLE 007 DARK NIGHT + BLUE RED ECAIL`)
  - Variant code: `^[A-Z0-9-]+\s+(\d+)`
  - High-res frame photo: `img.product-item__img.is--wide[src]`
  - Story & Design text: Conceptual collection text in `.p-reg` / `.h-reg`
- **Pricing**:
  - Independent creator brand showroom / optician locator (`store locator`, B2B portal at `jules2.theo.be`); no consumer DTC checkout (retail prices are `None`, standard for creator showrooms like Lafont, Face à Face, and Anne & Valentin).

---

## 2. Store Configuration (`store_configs.yaml`, `theo.be`, `country: BE`)

```yaml
  theo.be:
    name: "Theo"
    base_url: "https://www.theo.be"
    lang: en
    country: BE                         # Antwerp, Belgium ("theo loves you", Patrick Hoet & Wim Somers)
    default_brand: "Theo"
    default_currency: EUR
    delay_s: 1.5
    listing:
      urls:
        - { url: "/families/tubes", categories: "Optique" }
        - { url: "/families/friskos", categories: "Optique" }
        - { url: "/families/isolines", categories: "Optique" }
        - { url: "/families/flow", categories: "Optique" }
        - { url: "/families/waves", categories: "Optique" }
        - { url: "/families/glues", categories: "Optique" }
        - { url: "/families/locks", categories: "Optique" }
        - { url: "/families/clin-d-oeil", categories: "Optique" }
        - { url: "/families/bourbon-way", categories: "Optique" }
      product: "a.product-item[data-family-item]"
      link: "a.product-item[data-family-item]"
      url_regex: '(/mothers/[^/?#]+)'
    product_pages:
      enabled: true
      max_products: 60                  # covers all 48 models
    fields:
      name: { css: "h2.product-item__name" }
      image_url: { css: "img.product-item__img", attr: ["src", "data-src"] }
    flags:
      description: { css: ".product-item__info", regex: '(\d+\s+colours?)' }
    variants:
      rows: "div.product-item.is--wide"
      code: { css: "a.save-icon", attr: "data-model", regex: '^[A-Z0-9-]+\s+(\d+)' }
      label: { css: "a.save-icon", attr: "data-model", regex: '^[A-Z0-9-]+\s+\d+\s+(.+)' }
      swatch: { css: "img.product-item__img.is--wide", attr: "src" }
      color_split: { sep: " + ", color: 0 }
```

---

## 3. Tagger Vocabulary (v22)

Theo introduces avant-garde color aliases and dual-tone phrasing:
- **Color Aliases (`SPEC_ALIASES["color"]`)**:
  - `fluo orange` $\rightarrow$ `orange`
  - `fluo yellow` $\rightarrow$ `yellow`
  - `fluo red` $\rightarrow$ `red`
  - `fluo purple` $\rightarrow$ `purple`
  - `delft ware blue` $\rightarrow$ `blue`
  - `electric blue` $\rightarrow$ `blue`
  - `targa blue` $\rightarrow$ `blue`
  - `sanremo green` $\rightarrow$ `green`
  - `rosso cavallino` $\rightarrow$ `red`
  - `ecail` $\rightarrow$ `tortoiseshell`
  - `ecaille` $\rightarrow$ `tortoiseshell`
  - `citrus black` $\rightarrow$ `black`
  - `dark night` $\rightarrow$ `black`
- **Shape Aliases**:
  - Map conceptual model silhouettes where applicable.

---

## 4. Execution Steps

1. **Step 25.1**: Add `theo.be` to `backend/app/collectors/stores/store_configs.yaml`.
2. **Step 25.2**: Capture HTML mock fixtures:
   - Family listing: `backend/tests/fixtures/theo_listing.html` (e.g. from `/families/clin-d-oeil`).
   - Mother product page: `backend/tests/fixtures/theo_product.html` (e.g. from `/mothers/apple`).
3. **Step 25.3**: Create unit test suite `backend/tests/test_store_theo.py`:
   - Listing parsing test (4 models on Clin d'Oeil: `APPLE`, `EYE`, `PIPE`, `SKY`).
   - Product page variant parsing test (12 variants with codes, dual-tone labels, and high-res images).
   - Mock transport integration crawl test.
   - Update `test_store_crawlers.py` store count assertion from 15 to 16.
4. **Step 25.4**: Run pytest to guarantee 100% green tests.
5. **Step 25.5**: Run live crawl for `theo.be`:
   - Verify 48 products scraped, 0 dropped.
   - Retag catalog with rules version bumped to 22.
   - Update `docs/acetate-creative-brands.md` status to "Tracked (crawled)".
