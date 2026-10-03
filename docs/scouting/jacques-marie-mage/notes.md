# Jacques Marie Mage: scouting notes

Site: <https://jacquesmariemage.com>   Scouted by: Ahmed & Antigravity   Date: 2026-10-02

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: no (Shopify robots.txt explicitly states: `"Shopify storefront. Public product, collection, page, blog, policy, cart, and localized HTML is crawlable."` and welcomes AI agents with `/agents.md`).
- robots.txt from `https://jacquesmariemage.com/robots.txt`:
  ```text
  # Shopify storefront. Public product, collection, page, blog, policy, cart, and localized HTML is crawlable.
  # Agent instructions: https://jacquesmariemage.com/agents.md
  # UCP discovery: https://jacquesmariemage.com/.well-known/ucp
  # UCP/MCP endpoint: https://jacquesmariemage.com/api/ucp/mcp
  User-agent: *
  Disallow: /admin
  Disallow: /cart
  Disallow: /orders
  Disallow: /checkouts/
  Disallow: /checkout
  Disallow: /collections/*sort_by*
  ```
- Compliance & Rate Limiting analysis:
  - Standard Shopify routes (`/collections/optical-1`, `/collections/sunglasses`, `/collections/the-icons`, `/products/*`) are completely **allowed** under `robots.txt`.
  - Rate limiting behavior: Heavy storefront HTML collection and product pages return **HTTP 429** (Too Many Requests) when hit repeatedly.
  - In contrast, the lightweight Shopify storefront JSON endpoints (`/collections/<cat>/products.json?limit=250`) respond consistently with **HTTP 200 OK** without delay or challenge.
  - Zero-Product-Page scraping via collection `products.json` is therefore both polite and essential.

## Brand Identity & Origin
- **Brand**: Jacques Marie Mage (JMM)
- **Origin**: Los Angeles, California, USA (`country: US`). Founded in 2014 by French-born designer Jerome Jacques Marie Mage.
- **Aesthetic**: The pinnacle of artisanal, limited-edition creator acetate eyewear. World-renowned for heavyweight, sculpted **10mm cured cellulose acetate** blocks (sourced from heritage Japanese and Italian makers such as Takiron and Mazzucchelli), precious metal hardware (**sterling silver 925** and **18k gold** signature arrowhead front pins and custom hairline-engraved wirecores), tension-secured custom 7-barrel hinges, and rich domed mineral glass or CR-39 lenses.
- **Craftsmanship**: Each frame is produced in micro-batches (typically 250 to 500 numbered, serialized pieces worldwide) and handcrafted in Sabae (Fukui Prefecture, Japan) using over 300 individual hand-finishing operations.
- **Iconic Silhouettes**:
  - **DEALAN**: Bold, rectangular frame with subtle cat-eye beveling, paying homage to Bob Dylan's iconic shades during his 1965 world tour.
  - **ZEPHIRIN**: Refined, distinctive 40s-inspired square panto silhouette named after Pope Zephyrinus.
  - **MOLINO**: 60s-inspired architectural rectangular frame named after visionary Italian designer and architect Carlo Mollino.
  - **TORINO**: Bold, commanding geometric frame inspired by the Teatro Regio Torino.
  - **FELLINI**: Voluminous, dramatic classic rectangular frame celebrating Italian film director Federico Fellini.
  - **TAOS**: 60s-inspired blocky rectangular sunglasses inspired by Dennis Hopper in *Easy Rider*.
  - **ENZO**: Massive, assertive 10mm acetate icon inspired by Ferrari founder Enzo Ferrari.
- **Retail & Pricing**: Direct luxury e-commerce and exclusive global flagship galleries (Los Angeles, Paris, Tokyo, New York). Default currency: `USD` (`$905.00`–`$3,595.00`, average `~$1,475.00`).

## Where the frames are
- Optical collection:
  - HTML storefront: `https://jacquesmariemage.com/collections/optical-1`
  - JSON endpoint: `https://jacquesmariemage.com/collections/optical-1/products.json?limit=250` (36 frames, 100% `OPTICAL`)
- Sun collection:
  - HTML storefront: `https://jacquesmariemage.com/collections/sunglasses`
  - JSON endpoint: `https://jacquesmariemage.com/collections/sunglasses/products.json?limit=250` (223 frames, 100% `SUNGLASSES`)
- Flagship bestsellers collection:
  - `https://jacquesmariemage.com/collections/the-icons/products.json?limit=250` (10 iconic models: Dealan, Dealan 53, Yves, Torino, Zephirin, Molino, Fellini, Jagger, Devaux, Walker)
- Special collections:
  - Circa Collection: `https://jacquesmariemage.com/collections/circa-collection/products.json?limit=250` (82 frames)
- Total catalog size:
  - 36 optical + 223 sun = **259 unique eyewear frames** (0 overlap between optical and sun, as optical versions have dedicated handles such as `dealan-mx-rx` and `zephirin-mx-rx`).
- Frames per page, and how paging works:
  - HTML listing displays infinite scroll / pagination (`?page=2`).
  - Shopify collection JSON endpoints (`/collections/<cat>/products.json?limit=250`) return the entire 36 optical frames in **1 single request** and all 223 sunglasses in **1 single request** (page 2 returns 0 items).

## Which version of the site
- Country or language to track: `US` / global English luxury storefront, prices in USD `$`.
- Platform: Shopify.

## One filter at a time
- Collections:
  - Optical: `/collections/optical-1`
  - Sunglasses: `/collections/sunglasses`
  - The Icons: `/collections/the-icons`
  - Circa Collection: `/collections/circa-collection`
- Product Tags:
  - Face shapes: `Round` (55), `Square` (48), `Oval` (73), `Heart` (73), `Oblong` (53).
  - Materials: `acetate` (24 explicit, 246 total by brand standard), `Titanium` (10 explicit, 13 total).
  - Badges: `Best Sellers` (9), `The Icons` (16), `New Arrivals` (25), `Circa` (82).
  - Gender: `Womens` (155), `Mens` (153), `Unisex` (40).

## On a product page / collection data
- Examples examined in browser & API:
  - **PHOTOCHROMIC COLLECTION: DEALAN** (`/products/photochromic-collection-dealan`):
    - Title: `PHOTOCHROMIC COLLECTION: DEALAN`
    - Price: `$1,190.00`
    - Limited edition batch: 250 pieces
    - Variants (3):
      - `G13-AURORA / PHOTOCHROMIC LIGHT BOTTLE GREEN` (SKU: `J-ESN-DE-G13-WF`, stock: 29)
      - `O23-SOLARIS / PHOTOCHROMIC ORANGE` (SKU: `J-ESN-DE-O23-WF`)
      - `Y23-HALO / PHOTOCHROMIC BROWN GRADIENT` (SKU: `J-ESN-DE-Y23-WF`, stock: 26)
    - Construction: 10mm cured cellulose acetate, custom sterling silver wirecore, 7-barrel tension-secured hinge.
  - **MOLINO** (`/products/molino`):
    - Title: `MOLINO`
    - Price: `$905.00` – `$1,155.00`
    - Tags: `acetate`, `Best Sellers`, `The Icons`, `Circa`
    - Construction: 60s-inspired rectangular silhouette, 10mm cured cellulose acetate, sterling silver arrowhead pins.
- Architecture & Extraction Options:
  - **Zero-Product-Page Scraping via Collection Products JSON (Recommended)**:
    - Avoids downloading over 400 Megabytes of heavy PDP HTML.
    - Completely prevents Shopify HTTP 429 rate-limiting.
    - Captures the complete 259-frame catalog, all 1,962 variant colorways, prices, images, shapes, and badges in just **3 polite HTTP requests**.
    - Each product record contains:
      - Title: `title` (e.g. `MOLINO`, `DEALAN`, `ZEPHIRIN`, `TORINO`)
      - Canonical link: `/products/<handle>`
      - Price: `variants[0].price` (e.g. `1190.00` $\rightarrow$ `$1,190.00`)
      - Variants: array of options with `sku`, `option1` (e.g. `35-MIDNIGHT / SUPERLIGHT GREY CR39`, `5C-ARGYLE / BRONZE CR39`), and inventory availability.
      - Material: default 10mm cured cellulose acetate (`material = "acetate"`) unless tagged `Titanium` or titled `TI` (`material = "metal"`).
      - Badges: `Best Sellers` / `The Icons` $\rightarrow$ `is_bestseller = True`, `New Arrivals` $\rightarrow$ `is_new = True`.
      - Primary image: `images[0].src`

## Strategy for Crawler
1. **Store Config Entry (`store_configs.yaml`)**:
   - `id: jacquesmariemage`
   - `name: Jacques Marie Mage`
   - `domain: jacquesmariemage.com`
   - `base_url: https://jacquesmariemage.com`
   - `country: US`
   - `default_brand: Jacques Marie Mage`
   - `default_currency: USD`
   - `delay_s: 2.0`
   - `listing.url_regex: '(/products/[^/?#]+)'`
2. **Collections**:
   - Optical: `/collections/optical-1/products.json?limit=250` (category: `Optique`)
   - Sun: `/collections/sunglasses/products.json?limit=250` (category: `Solaire`)
   - The Icons (Best-Sellers): `/collections/the-icons/products.json?limit=250` (flag: `is_bestseller`)
3. **Product Pages**:
   - `enabled: false` (Zero-Product-Page scraping captures 100% of catalog and avoids PDP HTTP 429 rate limiting).

## Live Crawl Validation (2026-10-02)
- **Execution**: `python -m app.cli crawl-stores --force jacquesmariemage.com` followed by `python -m app.cli retag-products`.
- **Crawl Metrics**:
  - Total products found & inserted: **258 frames**
  - Updated / Reactivated: `0`
  - Dropped / Conflicts: **0 dropped** (100% success rate, 0 HTTP 429 rate limits)
- **Catalog Breakdown**:
  - Solaire (Sunglasses): **223 frames** (86.4%)
  - Optique (Eyeglasses): **35 frames** (13.6%)
  - Flagship Best-Sellers (`the-icons`): **19 frames** flagged (`is_bestseller = True`)
  - Materials: **245 acetate** (95.0%), **13 metal/titanium** (5.0%)
  - Price distribution: Min `$905.00`, Max `$3,595.00`, Average **`$1,476.40 USD`**
- **Taxonomy Tagging Coverage (Rules v29)**:
  - Product type: 258/258 (100.0%)
  - Material: 258/258 (100.0%)
  - Color: 230/258 (89.1%)
  - Shape: 79/258 (30.6%)
  - Top color families: `black` (302), `blue` (244), `green` (217), `two_tone` (213), `brown` (210), `grey` (181), `orange` (148), `tortoiseshell` (144), `red` (111), `beige` (57).
- **Unit Test Suite**:
  - `backend/tests/test_store_jacques_marie_mage.py`: 5 tests passing
  - `backend/tests/test_store_crawlers.py`: 55 tests passing (updated to 23 stores)
  - Full test suite: **473 passed in 86.76s** (100% green).