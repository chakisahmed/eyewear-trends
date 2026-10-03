# Step 27: Retrosuperfuture (Italy, Shopify, Milanese Designer Acetate & Zero-Product-Page Architecture)

Scouting: `docs/scouting/retrosuperfuture/notes.md` (live checks & Shopify rate-limit inspection, 2026-10-02).
Founded in Milan, Italy in 2007 by Daniel Beckerman, Retrosuperfuture (RSF) sparked the worldwide contemporary indie eyewear movement by combining clean classic Italian silhouette craft with bold, eclectic street and avant-garde culture. Frames are handcrafted in Italy using high-grade cellulose acetate and Zeiss German precision sun lenses. RSF also produces licensed creator eyewear lines for MM6 Maison Margiela, Marni, and 8000.

---

## 1. What the Pages Show

- **Catalog Structure**:
  - The RSF site uses Shopify Online Store 2.0 with a custom headless-inspired theme.
  - The site features a **Shapes Gallery** (`/collections/rsf-shape-sun` with 68 shape cards, `/collections/rsf-shape-optical` with 56 shape cards, `/collections/rsf-belli-shapes` with 98 shape cards) where each shape links to a dedicated shape family collection (e.g. `/collections/caro-rsf-sun` with 18 variants).
  - In addition, RSF's faceted catalog on `/collections/all` provides direct pagination of all individual colorways:
    - RSF In-Stock Sunglasses: 19 pages ($\sim$455 items at 24/page).
    - RSF In-Stock Optical: 13 pages ($\sim$310 items at 24/page).
    - Total in-stock core catalog: **$\sim$765 frames across 32 pages**.
- **Crucial Rate-Limiting Discovery & Zero-Product-Page Architecture**:
  - Individual product pages (`/products/<slug>`) on Shopify storefronts can quickly return **HTTP 429 Too Many Requests** when requested in high volume.
  - Collection listing pages (`/collections/all?...`) return **HTTP 200 OK** swiftly with all key product attributes directly present in the HTML card:
    - Model & colorway name: `p.rsf-card-product__title` (e.g. "Caro Refined", "Flat Top Black", "Classic Black", "America Black").
    - Price in EUR: `span.rsf-card-product__price` (e.g. `169EUR`, `189EUR`, `199EUR`).
    - High-resolution image: `img.rsf-card-product__slide-img` (`src` and `data-src`).
    - Canonical product link: `a.rsf-card-product__link` with `url_regex: '(/products/[^/?#]+)'`.
    - Frame material: Class attribute on the card `rsf-card-product--material-acetate`, `rsf-card-product--material-metal`, `rsf-card-product--material-combined`.
    - Sold-out status: `a[data-rsf-find-stockist]` ("Sold out · Find a stockist") indicates out of stock, while in-stock products feature an Add to Cart button (`button[data-rsf-cart-add]`).
  - Therefore, like *Oliver Goldsmith*, *Theo*, *Cutler and Gross*, and *Kirk & Kirk*, Retrosuperfuture is implemented with **Zero-Product-Page scraping (`product_pages.enabled: false`)**.
  - The entire core catalog of $\sim$765 frames is collected in $\sim$32 polite HTTP requests!

---

## 2. Store Entry (`store_configs.yaml`, `retrosuperfuture.com`, `country: IT`)

```yaml
  retrosuperfuture.com:
    name: "Retrosuperfuture"
    base_url: "https://retrosuperfuture.com"
    lang: en
    country: IT                         # Milan, Italy (founded 2007 by Daniel Beckerman; handmade in Italy, Zeiss lenses)
    default_brand: "Retrosuperfuture"
    default_currency: EUR
    delay_s: 1.5
    listing:
      urls:
        - { url: "/collections/all?filter.v.availability=1&filter.p.vendor=RETROSUPERFUTURE&filter.p.product_type=Eyewear&filter.p.m.rsf.category=Sunglass", categories: "Solaire" }
        - { url: "/collections/all?filter.v.availability=1&filter.p.vendor=RETROSUPERFUTURE&filter.p.product_type=Eyewear&filter.p.m.rsf.category=Optical", categories: "Optique" }
        - { url: "/collections/best-seller-in-stock", flag: "is_bestseller" }
      pagination: { param: page, max_pages: 20 }
      product: "li.rsf-card-product"
      link: "a.rsf-card-product__link"
      url_regex: '(/products/[^/?#]+)'
    fields:
      name: { css: "p.rsf-card-product__title" }
      price: { css: "span.rsf-card-product__price" }
      image_url: { css: "img.rsf-card-product__slide-img", attr: ["src", "data-src"] }
    flags:
      description: { css: "img.rsf-card-product__slide-img", attr: "alt" }
      material: { css: ".rsf-card-product", attr: "class", regex: 'rsf-card-product--material-([a-z]+)' }
      out_of_stock: { css: "a[data-rsf-find-stockist]", exists: true }
```

---

## 3. Tagger Vocabulary (v24)

- **Shape Aliases (`SPEC_ALIASES["shape"]`)**:
  - `flat top` $\rightarrow$ `square` (RSF signature flat-top silhouette)
- **Color Aliases (`SPEC_ALIASES["color"]`)**:
  - `azure` $\rightarrow$ `blue` (e.g. Caro Azure)
  - `canarino` $\rightarrow$ `orange` (e.g. Carino Canarino $\rightarrow$ Orange / Jaune taxonomy family)
  - `panna` $\rightarrow$ `white` (e.g. Cocca Panna)
  - `petrolium` $\rightarrow$ `blue` (e.g. Ambos Petrolium)
  - `burnt havana` $\rightarrow$ `tortoiseshell` (e.g. Cinema Burnt Havana)
  - `spotted havana` $\rightarrow$ `tortoiseshell` (e.g. Amata Spotted Havana)

---

## 4. Execution Steps

1. **Scouting Documentation**:
   - `docs/scouting/retrosuperfuture/notes.md` updated with complete findings, collection filters, and card selectors.
2. **Configuration**:
   - Add `retrosuperfuture.com` entry in `backend/app/collectors/stores/store_configs.yaml`.
3. **Taxonomy & Tagger**:
   - Bump `RULES_VERSION` to 24 in `backend/app/collectors/stores/tagger.py`.
   - Add shape and color aliases for Retrosuperfuture.
4. **Unit Test Suite & Offline Fixtures**:
   - Save `backend/tests/fixtures/retrosuperfuture_listing.html`.
   - Create `backend/tests/test_store_retrosuperfuture.py` testing listing parse, prices, canonical links, material extraction, and tagging.
   - Update `backend/tests/test_store_crawlers.py` active store count assertion (17 $\rightarrow$ 18).
   - Run full pytest test suite (100% green).
5. **Live Verification & Integration**:
   - Run live crawl: `python -m app.cli crawl-stores retrosuperfuture.com`.
   - Run retagging: `python -m app.cli retag-products`.
   - Update `docs/acetate-creative-brands.md` status for Retrosuperfuture to `Tracked (crawled)`.

---

## 5. Live Execution Results (Verified)

- **Test Suite**: **448 passed in 44.07s (100% green)**.
- **Live Crawl**:
  - **760 products crawled**: 760 inserted, 0 updated, 0 conflicts, 0 reactivated, **0 dropped**.
  - **Best-Sellers Flagged**: 302 products flagged via `/collections/best-seller-in-stock`.
  - **Zero PDP Rate Limits**: Completed in 33 polite requests (19 sun, 13 optical, 1 best-seller flag pass) in ~120s.
- **Database Status**:
  - System total grew to **4,483 products across 18 active stores**.
  - Retrosuperfuture breakdown:
    - `product_type`: 760 (100% tagged)
    - `material`: 461 tagged as `acetate` (extracted cleanly from card class attributes)
    - `color`: 368 tagged across 10 distinct color families (black, tortoiseshell, blue, red, green, pink, silver, brown, purple, white)
    - `shape`: 5 tagged as `square` via Flat Top silhouette alias
- **Index**:
  - `docs/acetate-creative-brands.md` updated: `Retrosuperfuture` marked as `Tracked (crawled)`.
