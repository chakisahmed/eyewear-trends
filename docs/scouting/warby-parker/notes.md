# Warby Parker: scouting notes

Site: <https://www.warbyparker.com>   Scouted by: Ahmed & Antigravity   Date: 2026-10-02

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: no (public catalog and sitemaps explicitly permitted; standard e-commerce restrictions on cart, checkout, and account operations).
- robots.txt from `https://www.warbyparker.com/robots.txt`:
  ```text
  User-agent: *
  Disallow: /account
  Disallow: /my-account
  Disallow: /ajax
  Disallow: /ajaxcontent
  Disallow: /api
  Disallow: /wapi
  Disallow: /cart
  Disallow: /checkout
  Disallow: /logout
  Disallow: /virtual-tryon
  Disallow: /preview
  Disallow: /cms
  Disallow: /rx-upload
  Disallow: /pd-upload
  Disallow: /atc/*
  Disallow: /prescription/*
  Disallow: /appointments/eye-exams/
  Disallow: /appointments/cancel
  Allow: /appointments/eye-exams/booking/
  Crawl-delay: 30

  Sitemap: https://www.warbyparker.com/sitemap.xml
  ```
- Compliance analysis:
  - All public collection routes (`/eyeglasses`, `/sunglasses`), canonical frame model pages (`/eyeglasses/<model>`, `/sunglasses/<model>`), and internal catalog API endpoints (`/v1/catalog/frames/search`) are **allowed** under `robots.txt`.
  - Disallowed routes are strictly transactional (`/cart`, `/checkout`, `/account`, `/prescription/*`, `/api`, `/wapi`).
  - Sitemaps: `sitemap.xml` provides index linking to `sitemap-products.xml` (1,330 URLs, including 741 product pages and 420 landing/category pages) and `sitemap-llms.xml`.
  - Bot protection: Next.js App Router fronted by DataDome / Cloudflare. Bot requests to static HTML pages return CSR-only empty shells, but the internal catalog JSON API (`/v1/catalog/frames/search`) responds cleanly with 200 OK to standard requests without challenge.

## Brand Identity & Origin
- **Brand**: Warby Parker
- **Origin**: New York City, USA (`country: US`). Founded in 2010 by Neil Blumenthal, Andrew Hunt, David Gilboa, and Jeffrey Raider (classmates at the Wharton School of the University of Pennsylvania).
- **Aesthetic**: Pioneer of the direct-to-consumer (DTC) acetate eyewear movement. Built upon vintage-inspired classic silhouettes, custom cellulose acetate sourced from family-run Italian factories, akulon-coated screws, signature five-barrel hinges, and crystal/tortoise layered hues. Known for making high-craft eyewear accessible and transparent, starting at $95.
- **Retail & Pricing**: Omnichannel optical powerhouse with over 200 physical optical stores across the US and Canada, home try-on service, and virtual vision tools. Default currency: `USD` (`$95.00`–`$195.00`).

## Where the frames are
- Optical collection:
  - HTML storefront: `https://www.warbyparker.com/eyeglasses`
  - Catalog API: `https://www.warbyparker.com/v1/catalog/frames/search?kind=eyeGlasses&size=300` (240 models, 498 colorways)
- Sun collection:
  - HTML storefront: `https://www.warbyparker.com/sunglasses`
  - Catalog API: `https://www.warbyparker.com/v1/catalog/frames/search?kind=sunGlasses&size=300` (125 models, 242 colorways)
- Best-selling collections:
  - Eyeglasses best-sellers: `https://www.warbyparker.com/v1/catalog/frames/search?kind=eyeGlasses&merch=best-seller&size=300` (61 models)
  - Sunglasses best-sellers: `https://www.warbyparker.com/v1/catalog/frames/search?kind=sunGlasses&merch=best-seller&size=300` (43 models)
  - Best-seller landing page: `https://www.warbyparker.com/collections/best-selling-glasses-and-sunglasses`
- New arrivals collections:
  - Eyeglasses new arrivals: `https://www.warbyparker.com/v1/catalog/frames/search?kind=eyeGlasses&merch=new-arrival&size=300` (26 models)
  - Sunglasses new arrivals: `https://www.warbyparker.com/v1/catalog/frames/search?kind=sunGlasses&merch=new-arrival&size=300` (25 models)
  - New collections: `https://www.warbyparker.com/collections/new-classics`, `https://www.warbyparker.com/collections/bestsellers-new-colors`
- Total catalog size:
  - 240 optical + 125 sun = **365 unique frame models**, totaling **740 colorway variants** (matching 100% of the 741 product URLs in `sitemap-products.xml`).
- Frames per page, and how paging works:
  - Web UI uses client-side infinite scroll with dynamic pagination.
  - The internal catalog API supports pagination or batch querying with `size=300`, returning all models in single requests.

## Which version of the site
- Country or language to track: `US` / global English storefront, prices in USD `$`.
- Platform: Custom Next.js App Router (React, Node.js, Vercel/Cloudflare, DataDome protection).

## One filter at a time
- Filters offered:
  - **Shop by**: Bestsellers (`merch=best-seller`), Trending: 90s minimalism (`merch=90s`), New arrivals (`merch=new-arrival`).
  - **Gender**: Men's (`gender=M`), Women's (`gender=F`).
  - **Shape**: Square, Rectangle, Round, Oval, Cat-eye, Geometric, Aviator (`shapes=Round`, `shapes=Square`, etc.).
  - **Frame width**: Extra narrow, Narrow, Medium, Wide, Extra wide (`availableWidths=narrow`, `availableWidths=wide`, etc.).
  - **Color**: Black, Brown, Tortoise, Crystal, Multicolor, Two-tone, Gold, Silver, Red, Yellow, Green, Blue, Pink, Purple, Grey, Clear (`colors=crystal`, `colors=tortoise`, etc.).
  - **Material**: Metal, Acetate (`materials=Cellulose+Acetate`), Mixed, Nylon.
- Filter URLs from browser:
  - `https://www.warbyparker.com/sunglasses/round`
  - `https://www.warbyparker.com/sunglasses?shapes=Round&colors=crystal`

## On a product page / collection data
- Examples examined in browser & API:
  - **Bix** (`/sunglasses/bix`):
    - Starting at $95. Color: `Umber Crystal` (`umber-crystal`). Aviator shape.
    - Material: `Made from hand-polished cellulose acetate`.
    - Lenses: Polycarbonate / CR-39.
  - **Bodie** (`/sunglasses/bodie`):
    - Starting at $95. Colors: `Saltwater Matte`, `Rye Tortoise`. Round shape.
    - URL: `https://www.warbyparker.com/sunglasses/bodie/saltwater-matte?w=wide`.
    - Material: Hand-polished cellulose acetate (`eyewireMaterial: "HB"`).
  - **Esme** (`/eyeglasses/esme` & `/sunglasses/esme`):
    - Starting at $95. Colors: `Sesame Tortoise`, `Crystal`, `Aventurine Tortoise with Polished Gold`, `Canopy`, `Rose Water`.
    - Square / subtle cat-eye shape.
- Architecture & Extraction Options:
  - **Zero-Product-Page Scraping via Catalog Search API (Recommended)**:
    - Avoids downloading over 500 Megabytes of heavy Next.js CSR HTML (static HTML contains no product markup).
    - Prevents DataDome IP rate-limiting that would occur if attempting to scrape 740 individual PDPs.
    - Captures the complete 365-model / 740-colorway catalog, prices, high-res images, shapes, materials, descriptions, bestsellers, and new arrivals in just **6 polite HTTP requests**.
    - Each record in `/v1/catalog/frames/search` contains:
      - Model Name: `name` (e.g. `Bix`, `Bodie`, `Esme`, `Durand`, `Percey`, `Haskell`, `Wright`, `Gillian`)
      - Canonical route: `action.cta.route` (e.g. `/sunglasses/bix/umber-crystal/atc` $\rightarrow$ canonical model URL `/sunglasses/bix`)
      - Price: `price` (e.g. `95.00` $\rightarrow$ `$95.00`)
      - Material: `eyewireMaterial` (`"HB"` $\rightarrow$ Cellulose Acetate) and description `"Made from hand-polished cellulose acetate"`
      - Shape: `primaryShape` (`Square`, `Round`, `Rectangle`, `Cat-eye`, `Aviator`, `Geometric`, `Oval`)
      - Image: `images.front`, `images.angle`, `images.baseTransparent`, `images.swatch`
      - Narrative description: `description`
      - Variants array: All colorway variants with code, name, in_stock status, and swatch thumbnails.
- Typical price: $95.00 base, up to $145.00–$195.00 for titanium/mixed collections.

## Strategy for Crawler
1. **Store Config Entry (`store_configs.yaml`)**:
   - `name: Warby Parker`
   - `base_url: https://www.warbyparker.com`
   - `country: US`
   - `default_brand: Warby Parker`
   - `default_currency: USD`
   - `delay_s: 2.0`
   - `listing.url_regex: '(/sunglasses/[^/?#]+|/eyeglasses/[^/?#]+)'`
2. **Collections**:
   - Optical: `/v1/catalog/frames/search?kind=eyeGlasses&size=300` (category: `Optique`)
   - Sun: `/v1/catalog/frames/search?kind=sunGlasses&size=300` (category: `Solaire`)
   - Optical Best-Sellers: `/v1/catalog/frames/search?kind=eyeGlasses&merch=best-seller&size=300` (flag: `is_bestseller`)
   - Sun Best-Sellers: `/v1/catalog/frames/search?kind=sunGlasses&merch=best-seller&size=300` (flag: `is_bestseller`)
   - Optical New Arrivals: `/v1/catalog/frames/search?kind=eyeGlasses&merch=new-arrival&size=300` (flag: `is_new`)
   - Sun New Arrivals: `/v1/catalog/frames/search?kind=sunGlasses&merch=new-arrival&size=300` (flag: `is_new`)
3. **Product Pages**:
   - `enabled: false` (Zero-Product-Page scraping covers 100% of catalog, variants, and specs).

## Live Crawl Verification (2026-10-02)
- **Engine**: Zero-Product-Page scraping via reverse-engineered internal catalog search API endpoints (`/v1/catalog/frames/search`).
- **Results**:
  - Total frames crawled: **365** (240 optical, 125 sun, 0 overlap).
  - Total colorway variants: **740** variants.
  - Dropped frames: **0** (100% catalog retention).
  - Best-sellers flagged: **104** models (61 optical, 43 sun).
  - New arrivals flagged: **51** models (26 optical, 25 sun).
  - Duration: ~15 seconds across 6 polite requests (`delay_s: 2.0`).
- **Taxonomy Tagging Yield (`RULES_VERSION = 28`)**:
  - **Material**: 359 frames (348 acetate, 11 metal — 98.4% coverage).
  - **Product Type**: 365 frames (125 sun, 240 optical — 100% coverage).
  - **Shape**: 573 tags across round (136), square (133), rectangle (82), browline (52), cat_eye (49), oversized (33), geometric (30), aviator (24), oval (15), shield (12).
  - **Colors**: 847 color tags with Palier 3 variant codes: tortoiseshell (218), clear (122), black (98), brown (96), gold (89), blue (77), green (39), silver (38), pink (23), grey (15).

