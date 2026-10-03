# Spektre: scouting notes

Site: https://spektre.com   Scouted by: Ahmed & Antigravity   Date: 2026-10-02

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no (direct access to public catalog; `/product-category/private/` is password-protected and excluded)
- Terms of use forbid automated access: no (standard WooCommerce robots.txt explicitly allows public storefront, products, and categories; standard terms of service)
- robots.txt from `spektre.com`:
  ```text
  User-agent: *
  Disallow: /wp-content/uploads/wc-logs/
  Disallow: /wp-content/uploads/woocommerce_transient_files/
  Disallow: /wp-content/uploads/woocommerce_uploads/
  Disallow: /*?add-to-cart=
  Disallow: /*?*add-to-cart=
  Disallow: /wp-admin/
  Allow: /wp-admin/admin-ajax.php
  Sitemap: https://spektre.com/wp-sitemap.xml
  ```

## Brand Identity & Origin
- **Brand**: Spektre (Spektre Sunglasses / Eyewear)
- **Origin**: Milan, Italy (`country: IT`). Founded in Milan in 2009 by Niccolò Pocchini.
- **Aesthetic**: Bold, chunky Italian acetate, clean stainless steel wireframes, flat lenses, and vivid mirror/pastel tints blending Milanese streetwear luxury with classic Italian eyewear craft. Handcrafted in Italy.
- **Retail & Pricing**: Direct-to-consumer e-commerce in EUR (`€179`–`€249`).

## Where the frames are
- Optical collection URL:
  - `https://spektre.com/product-category/optical/` (70 frames across 4 pages)
- Sun collection URL:
  - `https://spektre.com/product-category/sun/` (95 frames across 5 pages)
- Best Sellers collection URL:
  - `https://spektre.com/product-category/best/` (21 best-selling frames across 2 pages)
- Roughly how many frames (optical / sun):
  - 70 optical + 95 sun = **165 total frames** in catalog (9 listing pages total).
  - 21 best-sellers overlap across sun and optical.
- Frames per page, and how paging works:
  - 20 frames per page (last page has remainder: 15 for sun, 10 for optical).
  - Standard WooCommerce path pagination: `/page/2/`, `/page/3/`...
  - Next page link selector: `nav.woocommerce-pagination a.next.page-numbers`
- Frame names show in View Source (Ctrl+U):
  - YES! In `h2.woocommerce-loop-product__title` (e.g. `RIGAUT 2`, `PALM`, `ATLAS`, `VICE`, `REA`, `DEFCON 1`, `OASIS`, `LARA`).
  - Also embedded in each listing card's `div.variations_form.in_loop[data-product_variations]` JSON attribute (e.g. `"display_name": "RIGAUT 2 - Silver & Aqua"`).

## Which version of the site
- Country or language to track: `IT` / `EUR` (Milan, Italy; English storefront, prices in EUR `€`).
- Platform: WordPress / WooCommerce (theme: `spektre_15`, `wp-content/plugins/woocommerce`).

## One filter at a time
- Filters offered:
  - Spektre organizes its catalog via top-level category taxonomies rather than faceted frontend checkboxes (no shape/color dropdown widgets on PLP).
  - Main categories:
    - Sun: `https://spektre.com/product-category/sun/`
    - Optical: `https://spektre.com/product-category/optical/`
    - Best Sellers: `https://spektre.com/product-category/best/`
    - Private: `https://spektre.com/product-category/private/` (password protected, exclude)
- URL after ticking a single value:
  - Category URLs above; pagination follows `/product-category/<cat>/page/<n>/`.

## On a product page / listing card
- Architecture & Extraction Options:
  - **Option A (Zero-Product-Page scraping)**:
    - Incredibly rich data embedded directly on each listing card (`li.product.type-product`):
      - Canonical link: `a.woocommerce-LoopProduct-link` (`href="https://spektre.com/product/<slug>/"`)
      - Model Name: `h2.woocommerce-loop-product__title` (e.g. `RIGAUT 2`)
      - Price: `span.price span.woocommerce-Price-amount` (e.g. `179.00 €`)
      - Currency: `span.woocommerce-Price-currencySymbol` (`€` -> `EUR`)
      - Image: `img.attachment-woocommerce_thumbnail` or `img` (`src`)
      - In stock: Card class `instock` (vs `outofstock`)
      - Best seller: Card class `product_cat-best`
      - Color variations: `div.variations_form.in_loop[data-product_variations]` JSON containing `sku`, `attribute_pa_color`, `display_name`, `is_in_stock`, `display_price`.
    - Crawls the entire catalog in just **9 polite HTTP requests**!
  - **Option B (PDP Enrichment)**:
    - With only 165 total products, a PDP crawl takes ~4 minutes at 1.5s delay.
    - Product detail pages cleanly expose specifications in sequential `<p class="m-0">` tags:
      - Colors: `Black & Smoke, Havana & Green`
      - Materials: `Materials: Acetate, Nylon Lenses` or `Materials: Nylon Lenses, Stainless Steel`
      - Caliber: `Caliber: 59`
      - Nose: `Nose: 12`
      - Temple: `Temple: 140`
    - Also includes Schema.org `Product` JSON-LD (`name`, `sku`, `offers`).
- Price shown: yes. Currency: `EUR` (`€`). Typical range: €179.00 - €249.00.
- Colours:
  - Swatch attribute slugs: `silver-aqua`, `black-smoke`, `havana-green`, `gold-deep-green`, `gold-orange-flash`, `ancient-silver-smoke`.
  - PDP color text: `Black & Silver Mirror, Black & Smoke, Black & Sunset, Gold & Deep Green...`
- Details listed:
  - Materials: Explicitly stated as `Acetate, Nylon Lenses` or `Stainless Steel, Nylon Lenses`.
  - Frame measurements: Caliber, Nose (bridge), and Temple length.
- Badges:
  - Best-seller: Card class `product_cat-best` and dedicated `/product-category/best/` collection.
  - Stock status: Card classes `instock` vs `outofstock`, plus variation-level `is_in_stock` boolean.

## Strategy for Crawler
1. **Store Config Entry (`store_configs.yaml`)**:
   - `id: spektre`
   - `name: Spektre`
   - `domain: spektre.com`
   - `base_url: https://spektre.com`
   - `country: IT`
   - `currency: EUR`
   - `tier: creator`
2. **Collections**:
   - Sun collection: `https://spektre.com/product-category/sun/` (category: `Solaire`, max_pages: 5)
   - Optical collection: `https://spektre.com/product-category/optical/` (category: `Optique`, max_pages: 4)
   - Best sellers: `https://spektre.com/product-category/best/` (flag: `is_bestseller`, max_pages: 2)
3. **Card Selectors**:
   - `product`: `li.product.type-product`
   - `link`: `a.woocommerce-LoopProduct-link` (`url_regex: '(/product/[^/?#]+)'`)
   - `name`: `h2.woocommerce-loop-product__title`
   - `price`: `span.price span.woocommerce-Price-amount`
   - `image_url`: `img.attachment-woocommerce_thumbnail` (or fallback `img`)
   - `flags.is_bestseller`: `{ css: "li.product", attr: "class", regex: 'product_cat-best' }`
   - `flags.out_of_stock`: `{ css: "li.product", attr: "class", regex: 'outofstock' }`
4. **Pagination**:
   - Path-based: `type: "path"`, `pattern: "/page/{page}/"`, `max_pages: 6` (or next link `a.next.page-numbers`).
5. **Product Detail Enrichment (`product_pages`)**:
   - `enabled: true` to capture `p.m-0` specs (Acetate vs Stainless Steel, Caliber, Nose, Temple) for high taxonomy yield.

## Tagger Vocabulary Plan
- **Color Aliases**:
  - `ancient-silver`, `ancient-gold`, `ancient` -> `vintage` / `silver` / `gold`
  - `avory` -> `white` (ivory)
  - `tobacco` -> `brown`
  - `petrol` -> `blue`
  - `smoke` -> `grey`
  - `deep green` -> `green`
  - `aqua` -> `blue`
  - `fuchsia` -> `pink`
- **Material Aliases**:
  - `stainless steel` -> `metal`
  - `nylon lenses` -> `nylon`
  - `acetate` -> `acetate`

## Crawl Results
- Live crawl executed: 2026-10-02
- Status: 165 products crawled, 165 inserted, 0 updated, 0 conflicts, 0 reactivated, 0 dropped
- Best-sellers flagged: 21 products flagged via `/product-category/best/`
- Full PDP enrichment: 165 product pages opened and parsed for materials, measurements, and variants
- Test suite: 453 passed (100% green)
- Database totals: 4,648 products across 19 active stores
- Spektre breakdown:
  - `product_type`: 165
  - `material`: 302 tags (126 acetate, 122 nylon/tr90, 53 metal, 1 titanium)
  - `color`: 8,443 tags across variant options (top: gold, black, tortoiseshell, blue, two_tone, silver, green, grey)

