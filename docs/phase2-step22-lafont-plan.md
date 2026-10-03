# Step 22: Lafont, the ninth creator brand (France, Paris / Jura, presence-only)

Scouting: `docs/scouting/lafont/` (notes and live checks, 2026-10-02).
Artisan creator brand founded in Paris in 1923, renowned for colorful, bespoke acetate laminations, tortoiseshells, and retro cat-eye/round silhouettes. Certified "Origine France Garantie" (manufactured in Oyonnax, Jura, France).

---

## 1. What the Pages Show

- **Catalogs**:
  - Optical `/eyeglasses`: **111** unique model cards (~550–700 colorway variants).
  - Sun `/sunglasses`: **11** unique model cards (~50–70 colorway variants).
  - Note: `/sunglasses/` (with trailing slash) issues a 301 redirect to `/sunglasses` (without trailing slash).
  - Total catalog: **122** unique models (~600–750 colorway SKUs).
- **Pagination**: All models load on a single page per collection (no pagination or infinite scroll needed).
- **Cards on listing pages**:
  - Card selector: `div.article_mosaic_catalog`.
  - Main frame link: `a[href*='/catalog/article/']`.
  - Card image alt text: `alt="Glasses Lafont: DELICATE - 100- Acetate"` explicitly provides Model Name (`DELICATE`), Color Code (`100`), and Material (`Acetate`).
  - Swatches on card: `.article_color_mosaic a` with swatch thumbnail images (`/image.php?img=/colors/{code}.jpg`) and codes.
- **Product page**:
  - Model name: `h1.title_article` ("Delicate", "Clic").
  - Size: `h2.taille_article` ("Size 54").
  - Description: `<div class="info_article"> p` — rich editorial paragraph highlighting silhouette, material, and styling:
    - *DELICATE*: "An easy addition to any eyeglass wardrobe DELICATE offers a sleek rectangle silhouette in an array of Lafont acetate colors." (`shape: rectangle`, `material: acetate`).
    - *CLIC*: "P3 perfection. The new CLIC offers a playful two-tone metal option in a classic silhouette." (`shape: p3`, `material: metal`, `lamination: two_tone`).
  - Technical data table (`.technique .info_tech ul.edi li`):
    - Eye height: `40`
    - Eye width: `54`
    - Bridge: `15`
    - Temple length: `137`
    - Effective diameter: `60`
    - Lens base: `4`
  - Colorway variants & swatches (`.article_color_article a`):
    - Colors are identified strictly by **numeric reference codes** (`100`, `3100`, `3223`, `5201`) and **swatch thumbnail images** (`/image.php?img=/colors/{code}.jpg`), representing bespoke creative acetate laminations (two-tone diagonal splits, ombré gradients, terrazzo mosaics, marbled floral tortoiseshells).
- **Pricing**: **Presence-only** (no consumer price displayed, B2B optician distribution, `default_currency: EUR`).

---

## 2. Architectural Decisions

1. **Catalog Entry Points**:
   - `urls`:
     - `{ url: "/eyeglasses", categories: "Optique" }`
     - `{ url: "/sunglasses", categories: "Solaire" }`
   - Clean URLs without trailing slashes to avoid 301 redirects.
2. **Card & Canonical Links**:
   - `product`: `div.article_mosaic_catalog`
   - `link`: `a[href*='/catalog/article/']`
   - `url_regex`: `'(/catalog/article/[A-Z0-9]+)'`
   - `model_regex`: `'(/catalog/article/[A-Z]{3,4})'` (groups colorways under their 3-4 letter model code).
3. **Product Page Extraction**:
   - `name`: `{ css: "h1.title_article", scope: page }`
   - `image_url`: `{ css: "#image-face, .fiche_article_img img", attr: ["src", "data-src"], scope: page }`
   - `flags`:
     - `description`: `{ css: ".info_article > p", scope: page }`
     - `is_new`: `{ css: "p", regex: '(?i)^new$', scope: listing }`
   - `specs`:
     - `rows`: `".technique .info_tech ul.edi li"`
     - `regex` / `key`: `b` value extraction with preceding key label.
   - `variants`:
     - `rows`: `".article_color_article a"`
     - `code`: `{ css: "p" }`
     - `label`: `{ css: "img", attr: "src" }` (preserves the swatch image URL).
4. **Tagger Updates (`tagger.py`, v19)**:
   - Add Lafont's standard color code aliases:
     - `100` -> `black`
   - Ensure `description` matching parses `rectangle`, `p3`, `two-tone`, `acetate`, `metal`.

---

## 3. Store Entry (`store_configs.yaml`, `lafont.com`, `country: FR`)

```yaml
  lafont.com:
    name: "Lafont"
    base_url: "https://www.lafont.com"
    lang: en
    country: FR                         # Parisian eyewear house, manufactured in Oyonnax, Jura (France)
    default_brand: "Lafont"
    default_currency: EUR
    delay_s: 1.5
    listing:
      urls:
        - { url: "/eyeglasses", categories: "Optique" }
        - { url: "/sunglasses", categories: "Solaire" }
      product: "div.article_mosaic_catalog"
      link: "a[href*='/catalog/article/']"
      url_regex: '(/catalog/article/[A-Z0-9]+)'
      model_regex: '(/catalog/article/[A-Z]{3,4})'
    product_pages:
      enabled: true
      max_products: 300                 # Catalog has 122 unique models (111 optical, 11 sun)
    fields:
      name: { css: "h1.title_article", scope: page }
      image_url: { css: "#image-face, .fiche_article_img img", attr: ["src", "data-src"], scope: page }
    flags:
      description: { css: ".info_article > p", scope: page }
      is_new: { css: "p", regex: '(?i)^new$', scope: listing }
    specs:
      rows: ".technique .info_tech ul.edi li"
      key: "self"
      value: "b"
    variants:
      rows: ".article_color_article a"
      code: { css: "p" }
      label: { css: "img", attr: "src" }
```

---

## 4. Verification & Testing Workflow

1. **Offline Unit Tests (`test_store_lafont.py`)**:
   - Test listing extraction on sample mock HTML (model cards, optical/sun categories, badges).
   - Test product page extraction (name, image, description, specs, variants with swatch image URLs).
   - Test tagger v19 with Lafont vocabulary (shapes, materials, color code `100` -> black).
   - Update shipped config test in `test_store_crawlers.py` for 13 stores.
   - Run full pytest test suite (must remain 100% green).
2. **Live Crawl & Retag**:
   - Run `python -m app.cli crawl-store lafont.com`.
   - Verify product counts (~122 models) and tag yields.
   - Run `python -m app.cli retag-products lafont.com`.
3. **Documentation Updates**:
   - Mark Lafont as `Tracked (crawled)` in `docs/acetate-creative-brands.md` and `docs/build-plan.md`.

---

## 5. Execution Results

- **Live Crawl**:
  - `Lafont: 120 products crawled — inserted 120, updated 0, conflicts 0, reactivated 0, dropped 0`
- **Tag Yields (v19)**:
  - `product_type`: 120 / 120 (100%)
  - `material`: 83 / 120 (69.2%)
  - `shape`: 75 / 120 (62.5%)
  - `color`: 19 / 120 (15.8% — including code `100` $\rightarrow$ `black`)
  - `style`: 1
- **Database Status**:
  - Total catalog products stored across 13 stores: **3,333 products** (Lafont: 120).
- **Test Suite**:
  - **429 tests passed in 40.18s** (100% green).
