 # Step 24: Kirk & Kirk, the eleventh creator brand (UK / France / Italy, WooCommerce, e-commerce)

Scouting: `docs/scouting/kirk-and-kirk/` (notes and live checks, 2026-10-02).
British independent creator brand founded in London/Brighton, UK by Jason and Karen Kirk (heritage dating back to London optics in 1919). Celebrated worldwide for ultra-lightweight bespoke 10mm Italian acrylic frames in saturated, translucent kaleidoscope colors with sterling silver animal jewelry pins on temples, handmade in France and Italy.

---

## 1. What the Pages Show

- **Catalogs**:
  - Optical `/glasses/`: **28** frames on a single server-rendered page.
  - Sun `/sunglasses/`: **8** frames on a single server-rendered page.
  - Total catalog: exactly **36** unique models.
- **Pagination**: None required (all products render directly on each collection page).
- **Cards on listing pages (`div.kak-card[data-cat-name]`)**:
  - Filtering: `div.kak-card[data-cat-name]` cleanly selects real product cards while excluding editorial celebrity photo cards (`.celebrity-wrapper`).
  - Model name & link: `a.kak-product` (e.g. `Emma`, `Evan`, `Layla`, `Stanley`, `Yvonne`).
  - Price: `.kak-card-price .woocommerce-Price-amount` (`£490.00`, `£525.00`, `£595.00` $\rightarrow$ `GBP`).
  - Image: `img.kak-card__image--default` (high-resolution CDN front product image).
  - Editorial description / shape: `img.kak-card__image--default[title]` embeds silhouette descriptions (e.g. "gentle roundness", "Aviator", "geometric", "upswept", "hexagonal").
  - Colorway variants: `.kak-card-controls .kak-card-controls__pill` with `img.kak-card-controls__dot[title]` and swatch in `img.kak-card-controls__dot[src]`.
- **Zero-Product-Page Architecture**:
  - Because collection listing cards supply 100% of required fields (model name, price in GBP, high-res image, editorial description/shape, and all variant colorways with swatches), **Kirk & Kirk requires zero product page crawls** (`product_pages.enabled: false`).
  - The entire 36-frame catalog is crawled in just **2 fast, polite HTTP requests**!

---

## 2. Store Entry (`store_configs.yaml`, `kirkandkirk.com`, `country: GB`)

```yaml
  kirkandkirk.com:
    name: "Kirk & Kirk"
    base_url: "https://kirkandkirk.com"
    lang: en
    country: GB                         # London/Brighton (UK), handmade in France & Italy
    default_brand: "Kirk & Kirk"
    default_currency: GBP
    delay_s: 1.5
    listing:
      urls:
        - { url: "/glasses/", categories: "Optique" }
        - { url: "/sunglasses/", categories: "Solaire" }
      product: "div.kak-card[data-cat-name]"
      link: "a.kak-product"
      url_regex: '(/product/[^/?#]+)'
    fields:
      name: { css: "a.kak-product" }
      price: { css: ".kak-card-price .woocommerce-Price-amount" }
      image_url: { css: "img.kak-card__image--default", attr: ["src", "data-src"] }
    flags:
      description: { css: "img.kak-card__image--default", attr: "title" }
    variants:
      rows: ".kak-card-controls .kak-card-controls__pill"
      code: { css: "img.kak-card-controls__dot", attr: "title" }
      label: { css: "img.kak-card-controls__dot", attr: "title" }
      swatch: { css: "img.kak-card-controls__dot", attr: "src" }
```

---

## 3. Tagger Vocabulary (v21)

- **Shape Aliases (`SPEC_ALIASES["shape"]`)**:
  - `roundness` $\rightarrow$ `round`
  - `upswept` $\rightarrow$ `cat_eye`
  - `aviators` $\rightarrow$ `aviator`
  - `angular` $\rightarrow$ `geometric`
  - `circular` $\rightarrow$ `round`
- **Color Aliases (`SPEC_ALIASES["color"]`)**:
  - `admiral` $\rightarrow$ `blue`
  - `apple` $\rightarrow$ `green`
  - `candy` $\rightarrow$ `pink`
  - `capri` $\rightarrow$ `blue`
  - `carmine` $\rightarrow$ `red`
  - `chilli` $\rightarrow$ `red`
  - `citrus` $\rightarrow$ `orange`
  - `coffee` $\rightarrow$ `brown`
  - `corn` $\rightarrow$ `orange`
  - `earth` $\rightarrow$ `brown`
  - `glacier` $\rightarrow$ `clear`
  - `indigo` $\rightarrow$ `blue`
  - `iris` $\rightarrow$ `purple`
  - `jet` $\rightarrow$ `black`
  - `jungle` $\rightarrow$ `green`
  - `juniper` $\rightarrow$ `green`
  - `lagoon` $\rightarrow$ `blue`
  - `matte vamp` $\rightarrow$ `red`
  - `meadow` $\rightarrow$ `green`
  - `melon` $\rightarrow$ `orange`
  - `ocean` $\rightarrow$ `blue`
  - `passion` $\rightarrow$ `red`
  - `prince` $\rightarrow$ `purple`
  - `royal` $\rightarrow$ `blue`
  - `secret` $\rightarrow$ `grey`
  - `smoke` $\rightarrow$ `grey`
  - `stone` $\rightarrow$ `grey`
  - `tiger` $\rightarrow$ `tortoiseshell`
  - `walnut` $\rightarrow$ `brown`

---

## 4. Verification Workflow

1. **Config & Store Setup**:
   - Add `kirkandkirk.com` to `backend/app/collectors/stores/store_configs.yaml`.
   - Update `tagger.py` to `RULES_VERSION = 21` with shape and color aliases.
2. **Offline Unit Tests (`test_store_kirk_and_kirk.py`)**:
   - Mock transport serving optical `/glasses/` and sun `/sunglasses/` cards.
   - Assert extraction of name, price in GBP, image, description, and variant colorways with swatches.
   - Test tagger v21 rules for shapes (round, cat_eye, aviator, geometric) and colors.
   - Update shipped config test for 15 stores in `test_store_crawlers.py`.
   - Run full pytest test suite (must remain 100% green).
3. **Live Crawl & Retag**:
   - Run `python -m app.cli crawl-store kirkandkirk.com`.
   - Verify product counts (36 frames, 0 dropped).
   - Retag and verify tag yields: `python -m app.cli retag-products kirkandkirk.com`.
4. **Documentation Updates**:
   - Mark Kirk & Kirk as `Tracked (crawled)` in `docs/acetate-creative-brands.md` and update `docs/scouting/kirk-and-kirk/notes.md`.

---

## 5. Execution Results & Metrics

- **Unit Tests**:
  - `backend/tests/test_store_kirk_and_kirk.py`: 3/3 passed.
  - `backend/tests/test_store_crawlers.py`: 15-store check passed.
  - Full test suite: **435 passed in 34.73s (100% green)**.
- **Live Crawl**:
  - `kirkandkirk.com`: **35 products crawled** (28 optical, 7 sun across 2 polite requests).
  - Breakdown: `inserted 35, updated 0, conflicts 0, reactivated 0, dropped 0`.
- **Tagger v21 Yield**:
  - `product_type`: 35 / 35 (100.0%)
  - `color`: 35 / 35 (100.0%)
  - `shape`: 15 / 35 (42.9%)
- **Database Total**:
  - **3,608 products across 15 stores**.
- **Status**: **COMPLETE**.

