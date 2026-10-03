# Step 26: Oliver Goldsmith (UK, Shopify, British Heritage Acetate & Zero-Product-Page Architecture)

Scouting: `docs/scouting/oliver-goldsmith/notes.md` (live checks & Shopify rate-limit inspection, 2026-10-02).
Iconic British heritage creator eyewear house founded in London in 1926 by P. Oliver Goldsmith. Celebrated worldwide for pioneering sunglasses as fashion in the mid-20th century and framing style legends including Audrey Hepburn (*Breakfast at Tiffany's* Manhattan frame), Michael Caine (*The Italian Job* Lord frame), Grace Kelly, Peter Sellers, and John Lennon. Frames handmade in Italy from premium cotton acetate.

---

## 1. What the Pages Show

- **Catalog Structure**:
  - Optical `/collections/glasses`: ~40–47 frames on a single page.
  - Sun `/collections/sunglasses`: ~57 frames across 2 pages (`?page=2`).
  - Total catalog: **~91–104 frames**.
- **Crucial Rate-Limiting Discovery & Architecture**:
  - Individual product pages (`/products/<slug>`) return **HTTP 429 Too Many Requests** when scraped in sequence.
  - In contrast, collection listing pages (`/collections/glasses`, `/collections/sunglasses`) return **HTTP 200 OK** swiftly.
  - All essential data fields (model name, price in GBP, high-res image, silhouette shape & material descriptions in `img[alt]`, and all variant colorway chips) are directly present on the listing cards!
  - Therefore, like *Cutler and Gross* and *Kirk & Kirk*, Oliver Goldsmith is implemented with **Zero-Product-Page scraping (`product_pages.enabled: false`)**.
  - The entire ~100-frame catalog is crawled in **just 3 polite HTTP requests** in under 5 seconds!
- **Cards on Listing Pages (`product-block.product-block:not(.col-promo-box)`)**:
  - Filter: `:not(.col-promo-box)` cleanly excludes editorial promotional tiles (e.g. Ego banner).
  - Link: `a.product-link` (`url_regex: '(/products/[^/?#]+)'`).
  - Model Name: `div.product-block__title` (e.g. `Manhattan`, `Hep`, `Vivian`, `Sophia`, `Hillman`, `Lord`).
  - Price: `div.price__default` (`£365` / `£395` $\rightarrow$ `365.0` / `395.0 GBP`).
  - Image: `img` (`https://www.olivergoldsmith.com/cdn/shop/files/...`).
  - New Arrival Badge: `span.product-label, .badge` with regex `(?i)new` $\rightarrow$ `is_new: True`.
  - Shape & Material in Image Alt (`flags.description`):
    - *"round frame"* $\rightarrow$ `shape: round`
    - *"rounded square frame"* $\rightarrow$ `shape: square, round`
    - *"oval frame"* $\rightarrow$ `shape: oval`
    - *"squared aviator"* $\rightarrow$ `shape: aviator`
    - *"angular olive frame"* $\rightarrow$ `shape: geometric`
    - *"acetate frame"* $\rightarrow$ `material: acetate`
  - Variant Colorways: `span.product-block-options__item[data-option-item]` with swatch color names.

---

## 2. Store Entry (`store_configs.yaml`, `olivergoldsmith.com`, `country: GB`)

```yaml
  olivergoldsmith.com:
    name: "Oliver Goldsmith"
    base_url: "https://www.olivergoldsmith.com"
    lang: en
    country: GB                         # London, UK (founded 1926; Audrey Hepburn, Michael Caine)
    default_brand: "Oliver Goldsmith"
    default_currency: GBP
    delay_s: 1.5
    listing:
      urls:
        - { url: "/collections/glasses", categories: "Optique" }
        - { url: "/collections/sunglasses", categories: "Solaire" }
      pagination: { next: "a.pagination__next", max_pages: 5 }
      product: "product-block.product-block:not(.col-promo-box)"
      link: "a.product-link"
      url_regex: '(/products/[^/?#]+)'
    fields:
      name: { css: ".product-block__title" }
      price: { css: "div.price__default" }
      image_url: { css: "img", attr: ["src", "data-src"] }
    flags:
      description: { css: "img", attr: "alt" }
      is_new: { css: ".product-label, .badge", regex: '(?i)new', exists: true }
    variants:
      rows: "span.product-block-options__item[data-option-item]"
      code: { attr: "data-option-item" }
      label: { attr: "data-option-item" }
```

---

## 3. Tagger Vocabulary (v23)

- **Shape Aliases (`SPEC_ALIASES["shape"]`)**:
  - `squared aviator` $\rightarrow$ `aviator`
- **Color Aliases (`SPEC_ALIASES["color"]`)**:
  - `tangerine` $\rightarrow$ `orange`
  - `tokyo 50` $\rightarrow$ `tortoiseshell`
  - `tortoise 50` $\rightarrow$ `tortoiseshell`
  - `dark tortoiseshell` $\rightarrow$ `tortoiseshell`
  - `earth tortoise` $\rightarrow$ `tortoiseshell`
  - `amberfleck` $\rightarrow$ `tortoiseshell`
  - `night sea` $\rightarrow$ `blue`
  - `bahama` $\rightarrow$ `blue`
  - `anchor` $\rightarrow$ `blue`
  - `rainwater` $\rightarrow$ `clear`
  - `wakame` $\rightarrow$ `green`
  - `plankton` $\rightarrow$ `green`
  - `military` $\rightarrow$ `green`
  - `blacksilver` $\rightarrow$ `black`
  - `blackgold` $\rightarrow$ `black`
  - `black cat` $\rightarrow$ `black`
  - `slate storm` $\rightarrow$ `grey`
  - `etaupe` $\rightarrow$ `beige`
  - `rouge` $\rightarrow$ `red`

---

## 4. Execution Steps

1. **Step 26.1**: Add `olivergoldsmith.com` entry to `backend/app/collectors/stores/store_configs.yaml`.
2. **Step 26.2**: Save mock fixture `backend/tests/fixtures/oliver_goldsmith_listing.html`.
3. **Step 26.3**: Update tagger vocabulary in `tagger.py` (bump `RULES_VERSION = 23`).
4. **Step 26.4**: Create unit test suite `backend/tests/test_store_oliver_goldsmith.py`:
   - Offline card parsing test (Manhattan, Hep, Vivian, Sophia).
   - Price, badge, variants, and shape extraction tests.
   - Mock transport crawl test.
   - Update `test_store_crawlers.py` assertion to 17 stores.
5. **Step 26.5**: Run pytest to verify 100% green tests.
6. **Step 26.6**: Run live crawl for `olivergoldsmith.com`:
   - Verify ~91–104 products scraped, 0 dropped.
   - Retag catalog with rules version 23.
   - Update `docs/acetate-creative-brands.md` status to "Tracked (crawled)".
