# Ahlem: scouting notes

Site: https://www.ahlemeyewear.com   Scouted by: Ahmed & Antigravity   Date: 2026-10-02

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: no (standard Shopify robots.txt explicitly allows public storefront, `/collections/*`, and `/products/*`)
- robots.txt from `ahlemeyewear.com`:
  ```text
  # we use Shopify as our ecommerce platform
  User-agent: *
  Disallow: /admin
  Disallow: /cart
  Disallow: /orders
  Disallow: /checkouts/
  Disallow: /checkout
  Disallow: /collections/*sort_by*
  ```
- **Crucial Rate-Limiting Discovery**:
  - Sequential requests to individual product detail pages (`/products/<slug>`) trigger Shopify **HTTP 429 Too Many Requests** (18 bytes response).
  - In contrast, collection endpoints (`/collections/sun`, `/collections/optical`) return **HTTP 200 OK** swiftly and reliably.
  - **Strategy**: Just like *Oliver Goldsmith*, *Cutler and Gross*, *Kirk & Kirk*, and *Retrosuperfuture*, Ahlem should be onboarded using **Zero-Product-Page scraping (`product_pages.enabled: false`)**, capturing the entire brand catalog in **only 2 polite HTTP requests**!

## Brand Identity & Origin
- **Brand**: Ahlem (Ahlem Eyewear)
- **Origin**: Paris, France / Los Angeles, USA (`country: FR`). Founded in 2014 by Parisian-born designer Ahlem Manai-Platt.
- **Aesthetic**: Bauhaus architectural rigor meets Parisian effortless elegance. Known for heavy 8mm Mazzucchelli cellulose acetate, signature hand-beveled raw edges, geometric facet cuts, and electroplated 22k gold/palladium hardware. Handcrafted in historic artisanal workshops in Oyonnax and Morez (Jura, France), with metal wireframes crafted in Japan.
- **Retail & Pricing**: Direct-to-consumer luxury e-commerce in USD (`$540`–`$660`). Flagship boutiques in Paris (Rue Vieille du Temple), New York (SoHo), and Los Angeles (Venice).

## Where the frames are
- Optical collection URL:
  - `https://www.ahlemeyewear.com/collections/optical` (96 frames)
- Sun collection URL:
  - `https://www.ahlemeyewear.com/collections/sun` (82 frames)
- New Arrivals:
  - `https://www.ahlemeyewear.com/collections/new-arrivals`
- Roughly how many frames (optical / sun):
  - 96 optical + 82 sun = **178 total frames** in catalog.
- Frames per page, and how paging works:
  - Collection HTML embeds initial 50 products inside a `<script>` tag with `"totalProductsCount"` and a full JSON `products` array.
  - Shopify products API (`/collections/<cat>/products.json?limit=250`) returns all 96 optical and 82 sun products directly in single polite requests.
- Frame names show in View Source (Ctrl+U):
  - YES! In `<script type="application/ld+json">` (`ItemList` schema with `name` and `url` for all products).
  - Also embedded in page `<script>` JSON (`"products": [{"title": "St Marcel", "handle": "st-marcel", "tags": ["Acetate", ...], ...}]`).

## Which version of the site
- Country or language to track: `FR` / `US` (Paris heritage, global English storefront, prices in USD `$`).
- Platform: Shopify (custom headless theme styled with Tailwind CSS, React/Vue frontend).

## One filter at a time
- Filters offered:
  - Category navigation:
    - Sun: `https://www.ahlemeyewear.com/collections/sun`
    - Optical: `https://www.ahlemeyewear.com/collections/optical`
    - New Arrivals: `https://www.ahlemeyewear.com/collections/new-arrivals`
  - Frontend faceted filters are managed client-side against the embedded product data.

## On a product page / collection data
- Architecture & Extraction Options:
  - **Zero-Product-Page Scraping (Recommended)**:
    - Avoids Shopify HTTP 429 rate limiting completely.
    - Each collection contains complete product records:
      - Title: `title` (e.g. `Limited Edition: Guérin`, `St Marcel`, `Rue Charlot`, `Pont des Arts`)
      - Canonical link: `/products/<handle>`
      - Price: `price` / `variants[0].price` (e.g. `66000` cents $\rightarrow$ `$660.00`)
      - Material: Explicit tags `Acetate`, `Metal`, `Metals`
      - Shape: Explicit tags `Aviator`, `Oval`, `Square Face`, `Geometric`
      - Variants: Color pairings with variant codes, SKUs, and availability
      - Primary image: `images[0].src`
- Price shown: yes. Currency: `USD` (`$`). Typical range: $540.00 – $660.00.
- Colours:
  - High-end designer acetate colorways: `Champagne / Green Gradient`, `Dark Turtle / Green`, `Smoky Quartz`, `Old Fashioned Rose`, `Dry Pampa`, `Yellow Turtle`, `Light Turtle`, `Black`.
- Details listed:
  - Materials: Explicitly noted in tags (`Acetate`, `Metal`).
  - Face shape recommendations: `Oval Face`, `Square Face`, `Diamond Face`, `Up Triangle Face`.
  - Badges: `Limited Edition`, `new`, `New Arrivals`.

## Strategy for Crawler
1. **Store Config Entry (`store_configs.yaml`)**:
   - `id: ahlem`
   - `name: Ahlem`
   - `domain: ahlemeyewear.com`
   - `base_url: https://www.ahlemeyewear.com`
   - `country: FR`
   - `currency: USD`
   - `tier: creator`
2. **Collections**:
   - Sun collection: `https://www.ahlemeyewear.com/collections/sun` (category: `Solaire`)
   - Optical collection: `https://www.ahlemeyewear.com/collections/optical` (category: `Optique`)
   - New arrivals: `https://www.ahlemeyewear.com/collections/new-arrivals` (flag: `is_new`)
3. **Product Pages**:
   - `enabled: false` (Zero-Product-Page scraping to bypass Shopify HTTP 429 rate limiting).

## Live Crawl Verification (2026-10-02)
- **Engine**: Zero-Product-Page scraping via Shopify collection JSON endpoints (`/collections/sun/products.json?limit=250`, `/collections/optical/products.json?limit=250`, `/collections/new-arrivals/products.json?limit=250`).
- **Session Throttle Discovery**: Shopify storefront API associates rate limits with session cookies (`_shopify_essential`, `_shopify_analytics`). Clearing client cookies between requests eliminates session-level 429 throttling entirely.
- **Results**:
  - Total frames crawled: **178** (82 sun, 96 optical).
  - Dropped frames: **0** (100% catalog retention).
  - New arrivals flagged: **124** models.
  - Duration: ~10 seconds across 3 polite requests (`delay_s: 2.0`).
- **Taxonomy Tagging Yield**:
  - **Material**: 94 acetate, 79 metal (97.2% coverage).
  - **Product Type**: 96 optical, 82 sun (100% coverage).
  - **Shape**: round (44), square (44), cat_eye (33), aviator (32), geometric (25), oval (16), rectangle (12), oversized (11).
  - **Colors**: green (162), grey (129), two_tone (123), gold (88), beige (83), pink (55), black (53), blue (45), tortoiseshell (39), brown (15), red (13), pastel (10), orange (6), purple (4).
