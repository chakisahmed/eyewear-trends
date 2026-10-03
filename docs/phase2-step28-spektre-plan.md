# Step 28: Spektre (Italy, WooCommerce, Milanese Chunky Acetate & Detailed PDP Enrichment)

Scouting: `docs/scouting/spektre/notes.md` (live checks & WooCommerce inspection, 2026-10-02).
Founded in Milan, Italy in 2009 by Niccolò Pocchini, Spektre has grown into an internationally acclaimed creator eyewear brand, featured in Vogue, Elle, and GQ. Spektre frames are handcrafted in Italy, famous for bold and chunky Mazzucchelli acetate silhouettes, stainless steel wireframes, flat sunglasses, and vivid mirror/pastel tints blending Milanese streetwear luxury with classic Italian eyewear craft.

---

## 1. What the Pages Show

- **Catalog Structure**:
  - The Spektre storefront runs on WordPress / WooCommerce with custom theme `spektre_15`.
  - The catalog is cleanly organized into two primary collections and a curated best-seller showcase:
    - **Sun Collection**: `https://spektre.com/product-category/sun/` (95 frames across 5 pages at 20/page).
    - **Optical Collection**: `https://spektre.com/product-category/optical/` (70 frames across 4 pages at 20/page).
    - **Best Sellers**: `https://spektre.com/product-category/best/` (21 frames across 2 pages; cards carry class `product_cat-best`).
    - Total catalog size: **165 unique frames across 9 listing pages**.
- **Pagination & Robots.txt**:
  - Standard WooCommerce path pagination: `/page/2/`, `/page/3/`...
  - Next link in HTML: `nav.woocommerce-pagination a.next.page-numbers`.
  - `robots.txt` explicitly allows the public storefront, product categories, and products.
- **Listing Cards (`li.product.type-product`)**:
  - Model name: `h2.woocommerce-loop-product__title` (e.g. `RIGAUT 2`, `PALM`, `ATLAS`, `VICE`, `REA`).
  - Price in EUR: `span.price span.woocommerce-Price-amount` (e.g. `179.00 €`, `249.00 €`).
  - Image: `img.attachment-woocommerce_thumbnail` or `img` (`src`, `data-src`).
  - Canonical link: `a.woocommerce-LoopProduct-link` with `url_regex: '(/product/[^/?#]+)'`.
  - Best-seller flag: Card class `product_cat-best`.
  - Out of stock flag: Card class `outofstock` (vs `instock`).
- **Product Detail Pages (PDP Specs & Variants)**:
  - Total catalog is compact (165 frames), making full PDP enrichment fast (~4 minutes at 1.5s delay) with zero rate limiting.
  - Specifications are cleanly formatted in `<p class="m-0">` tags:
    - `<b>Materials:</b> Acetate, Nylon Lenses` or `Stainless Steel, Nylon Lenses`
    - `<b>Caliber:</b> 59`, `<b>Nose:</b> 12`, `<b>Temple:</b> 140`
  - Color variants are selectable via `<select name="attribute_pa_color">`:
    - Options provide clean color codes and human-readable names (e.g., `value="black-smoke"` -> `Black & Smoke`, `value="havana-green"` -> `Havana & Green`, `value="gold-glossy-tobacco"` -> `Gold Glossy & Tobacco`).
  - Schema.org `Product` JSON-LD provides structured backup for name, SKU, price, and currency.

---

## 2. Store Entry (`store_configs.yaml`, `spektre.com`, `country: IT`)

```yaml
  # Spektre (Italy), WooCommerce. Checked 2026-10-02: Milanese creator eyewear brand founded
  # in 2009 by Niccolò Pocchini; handcrafted in Italy with bold Mazzucchelli acetate and steel.
  # Listing cards carry title, price, images, and best-seller classes; product pages supply
  # precise material specs (Acetate vs Stainless Steel), caliber/nose/temple, and color variants.
  spektre.com:
    name: "Spektre"
    base_url: "https://spektre.com"
    lang: en
    country: IT                         # Milan, Italy (founded 2009 by Niccolò Pocchini; handcrafted in Italy)
    default_brand: "Spektre"
    default_currency: EUR
    delay_s: 1.5
    listing:
      urls:
        - { url: "/product-category/sun/", categories: "Solaire" }
        - { url: "/product-category/optical/", categories: "Optique" }
        - { url: "/product-category/best/", flag: "is_bestseller" }
      pagination: { next: "a.next.page-numbers", max_pages: 10 }
      product: "li.product.type-product"
      link: "a.woocommerce-LoopProduct-link"
      url_regex: '(/product/[^/?#]+)'
    product_pages:
      enabled: true
      max_products: 250
    fields:
      name: { css: "h2.woocommerce-loop-product__title" }
      price: { css: "span.price span.woocommerce-Price-amount" }
      image_url: { css: "img.attachment-woocommerce_thumbnail, img", attr: ["src", "data-src"] }
    flags:
      is_bestseller: { css: ".product_cat-best", exists: true }
      out_of_stock: { css: ".outofstock", exists: true }
    specs:
      rows: "p.m-0"
      key: "b"
      key_regex: '(?i)(materials|caliber|nose|temple)'
      tail: true
    variants:
      rows: "select[name=attribute_pa_color] option:not([value=''])"
      code: { attr: "value" }
      label: { }
```

---

## 3. Tagger Vocabulary (v25)

- **Color Aliases (`SPEC_ALIASES["color"]`)**:
  - `tobacco` $\rightarrow$ `brown` (e.g. Gold Glossy & Tobacco, Black & Tobacco)
  - `avory` $\rightarrow$ `white` (Spektre catalogue typo for Ivory)
  - `fuchsia` $\rightarrow$ `pink` (Spektre vibrant pink lenses and acetate tints)

---

## 4. Execution Steps

1. **Scouting Documentation**:
   - `docs/scouting/spektre/notes.md` completed with collection URLs, selectors, and catalog numbers.
   - `docs/acetate-creative-brands.md` status updated.
2. **Configuration**:
   - Add `spektre.com` entry in `backend/app/collectors/stores/store_configs.yaml`.
3. **Taxonomy & Tagger**:
   - Bump `RULES_VERSION` to 25 in `backend/app/collectors/stores/tagger.py`.
   - Add color aliases (`tobacco` -> `brown`, `avory` -> `white`, `fuchsia` -> `pink`).
4. **Unit Test Suite & Offline Fixtures**:
   - Save `backend/tests/fixtures/spektre_listing.html` and `backend/tests/fixtures/spektre_product.html`.
   - Create `backend/tests/test_store_spektre.py` covering:
     - Config schema validation.
     - Listing card extraction (items, titles, prices in EUR, links, best-seller flags).
     - Product page specs extraction (`raw_specs`: Materials, Caliber, Nose, Temple) and variants (code + color label).
     - Offline simulated crawl with `httpx.MockTransport`.
     - Taxonomy tagging assertions (material -> acetate/metal, color -> brown/white/pink/etc.).
   - Update `backend/tests/test_store_crawlers.py` active store count assertion (18 $\rightarrow$ 19).
   - Run full pytest test suite (100% green).
5. **Live Verification & Integration**:
   - Run live crawl: `python -m app.cli crawl-stores spektre.com`.
   - Run retagging: `python -m app.cli retag-products`.
   - Verify product counts, best-seller counts, and taxonomy distribution in database.
   - Update `docs/acetate-creative-brands.md` status for Spektre to `Tracked (crawled)`.
