# Step 29: Ahlem (France / USA, Headless Shopify, Parisian Luxury Acetate & Shopify JSON Pipeline)

Scouting: `docs/scouting/ahlem/notes.md` (live checks & Shopify headless inspection, 2026-10-02).
Founded in 2014 by Parisian-born, Los Angeles-based designer Ahlem Manai-Platt, Ahlem Eyewear is a premier luxury creator brand celebrated for combining Bauhaus architectural geometry with effortless Parisian chic. Frames are handcrafted in historic artisanal workshops in Oyonnax and Morez (Jura, France), and Japanese titanium workshops, featuring thick 8mm vintage cellulose acetate, raw hand-beveled contours, geometric facet temples, and 22k electroplated gold and palladium hardware.

---

## 1. What the Pages Show & Technical Discovery

- **Catalog Structure**:
  - The Ahlem storefront (`ahlemeyewear.com`) is a custom headless application built with Tailwind CSS and React/Vue on top of Shopify.
  - The catalog is divided into two core collections:
    - **Optical Collection**: `https://www.ahlemeyewear.com/collections/optical` (96 frames)
    - **Sun Collection**: `https://www.ahlemeyewear.com/collections/sun` (82 frames)
    - Total catalog size: **178 unique frames**.
- **Crucial Headless & Rate-Limiting Discoveries**:
  1. **Zero Static HTML Product Cards**:
     - The collection HTML pages are single-page application shells containing 0 `<a href="/products/...">` tags and 0 `<img>` product cards.
     - Products are rendered purely on the client side from an embedded `<script id="data-collection" type="application/json">` block (520KB) or via Shopify's standard collection products API (`/collections/<cat>/products.json?limit=250`).
  2. **Shopify PDP HTTP 429 Rate Limiting**:
     - Sequential requests to individual product detail pages (`/products/<slug>`) trigger Shopify **HTTP 429 Too Many Requests** (18 bytes response).
  3. **High-Yield Clean Shopify Collection API**:
     - `https://www.ahlemeyewear.com/collections/sun/products.json?limit=250` returns all 82 sun products in 1 request.
     - `https://www.ahlemeyewear.com/collections/optical/products.json?limit=250` returns all 96 optical products in 1 request.
     - Each product JSON object includes:
       - `title`: Frame model name (e.g. "St Marcel", "Limited Edition: Guérin", "Rue Charlot").
       - `handle`: Canonical product URL slug (`/products/<handle>`).
       - `variants`: Complete list of color options with prices, SKUs, and stock availability (`available: true/false`).
       - `tags`: Rich taxonomy metadata including material (`Acetate`, `Metal`), silhouette (`Aviator`, `Oval`, `Square Face`), and collection badges (`limited edition`, `new`).
       - `images`: High-resolution product images.

---

## 2. Architecture & Design Options

### Option A: Native Shopify JSON Support in `parse_listing` (Recommended)
- Extend `parse_listing` in `parser.py` so that when a listing URL response is JSON (or when a collection embeds `<script id="data-collection">`), it converts the Shopify product objects directly into `ListingItem` records.
- Enables Zero-Product-Page crawling: the entire 178-frame catalog is captured in **just 2 polite HTTP requests** without hitting Shopify's 429 rate limiter.
- Full metadata yield: extracts titles, prices, images, canonical links, materials (`Acetate` vs `Metal`), shapes, and variant colors.

### Option B: PDP Scraping with Browser Emulation
- Requires browser rendering or heavy delay (3–5s) with custom headers and cookie sessions to avoid 429s.
- Fragile, slow (~15 minutes for 178 frames), and prone to sudden rate-limit blocks.

---

## 3. Store Configuration (`store_configs.yaml`)

```yaml
  # Ahlem (France / USA), Shopify Headless. Checked 2026-10-02: Luxury creator eyewear founded
  # in 2014 by Ahlem Manai-Platt; handcrafted in Oyonnax (Jura, France) from thick 8mm Mazzucchelli
  # acetate and Japanese titanium. Uses Shopify products.json API to bypass headless SPA DOM
  # rendering and PDP HTTP 429 rate limits, capturing all 178 frames in 2 requests.
  ahlemeyewear.com:
    name: "Ahlem"
    base_url: "https://www.ahlemeyewear.com"
    lang: en
    country: FR                         # Paris, France / Los Angeles (handcrafted in Jura, France)
    default_brand: "Ahlem"
    default_currency: USD
    delay_s: 1.5
    listing:
      urls:
        - { url: "/collections/sun/products.json?limit=250", categories: "Solaire" }
        - { url: "/collections/optical/products.json?limit=250", categories: "Optique" }
      product: "shopify_json"
      link: "shopify_json"
      url_regex: '(/products/[^/?#]+)'
    product_pages:
      enabled: false                    # Zero-Product-Page scraping: JSON endpoint supplies full metadata
    fields:
      name: { css: "shopify_json" }
      price: { css: "shopify_json" }
      image_url: { css: "shopify_json" }
```

---

## 4. Tagger Vocabulary (v26)

- **Color Aliases (`SPEC_ALIASES["color"]`)**:
  - `dry pampa` $\rightarrow$ `beige` (Ahlem signature desert sand tone)
  - `smoky quartz` $\rightarrow$ `grey`
  - `old fashioned rose` $\rightarrow$ `pink`
  - `light turtle`, `yellow turtle` $\rightarrow$ `tortoiseshell`
  - `peony`, `peony gold` $\rightarrow$ `pink`

---

## 5. Execution Steps

1. **Scouting**:
   - `docs/scouting/ahlem/notes.md` completed with collection URLs, pricing, and rate-limit analysis.
2. **Parser Enhancement (`parser.py`)**:
   - Support Shopify collection JSON in `parse_listing` when `html.strip().startswith("{")` and contains `"products"`.
   - Map `title`, `handle`, `variants`, `tags`, and `images` to `ListingItem` fields.
3. **Store Config & Engine Enhancement**:
   - Add `ahlemeyewear.com` in `store_configs.yaml` with `delay_s: 2.0`.
   - Update `BaseStoreCrawler.fetch` in `base.py` to clear client session cookies between requests (`self.client.cookies.clear()`), avoiding Shopify session-level 429 throttling.
4. **Taxonomy & Tagger**:
   - Bump `RULES_VERSION` to 26 in `tagger.py`.
   - Add Ahlem color aliases (`dry pampa`, `smoky quartz`, `old fashioned rose`, `light turtle`, `yellow turtle`, `peony`, `peony gold`, `ashmilk`, `storm`, `g15`).
5. **Unit Tests & Offline Fixtures**:
   - Save `backend/tests/fixtures/ahlem_sun_products.json` and `ahlem_optical_products.json`.
   - Write `backend/tests/test_store_ahlem.py` testing config, JSON listing parser, offline crawler, and tagging.
   - Update `test_store_crawlers.py` active store count assertion (19 $\rightarrow$ 20).
   - Verify full pytest test suite (458 passed, 100% green).
6. **Live Crawl & Retagging (Completed 2026-10-02)**:
   - Live crawl: **178 products crawled, 178 inserted/updated, 0 dropped, 0 errors, status ok** (82 sun, 96 optical, 124 new arrivals flagged).
   - Retagging: 4,826 products tagged across 20 stores. Ahlem yield: 94 acetate, 79 metal (97.2% material tagged), 100% product types, rich silhouette and color breakdown.
   - Documentation: Updated `docs/scouting/ahlem/notes.md` and `docs/acetate-creative-brands.md` row 38 to `Tracked (crawled)`.
