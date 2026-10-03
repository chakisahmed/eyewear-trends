# Moscot: scouting notes

Site: https://moscot.com   Scouted by: Ahmed & Antigravity   Date: 2026-10-02

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: no (standard Shopify robots.txt explicitly states: `"Shopify storefront. Public product, collection, page, blog, policy, cart, and localized HTML is crawlable."`)
- Agent policy: `https://moscot.com/agents.md` welcomes AI agents and describes UCP/MCP capabilities.
- robots.txt from `moscot.com`:
  ```text
  # Shopify storefront. Public product, collection, page, blog, policy, cart, and localized HTML is crawlable.
  # Agent instructions: https://moscot.com/agents.md
  # UCP discovery: https://moscot.com/.well-known/ucp
  # UCP/MCP endpoint: https://moscot.com/api/ucp/mcp
  User-agent: *
  Disallow: /admin
  Disallow: /cart
  Disallow: /orders
  Disallow: /checkouts/
  Disallow: /checkout
  Disallow: /collections/*sort_by*
  ```

## Brand Identity & Origin
- **Brand**: Moscot (MOSCOT NYC SINCE 1915)
- **Origin**: New York City, Lower East Side, USA (`country: US`). Founded in 1915 by Hyman Moscot, who began selling ready-made eyeglasses from a pushcart on Orchard Street. Five generations of family optical heritage.
- **Aesthetic**: Iconic American classic acetate eyewear. Renowned worldwide for timeless mid-century silhouettes, real riveted hinges, keyhole bridges, and rich acetate colorways (notably the legendary **LEMTOSH**, **MILTZEN**, **DAHVEN**, **ARTHUR**, **NEBB**, and **ZOLMAN**). Worn by generations of cultural figures (Andy Warhol, Johnny Depp, Allen Ginsberg, Buddy Holly).
- **Retail & Pricing**: Direct-to-consumer luxury e-commerce and global flagship shops (New York, London, Paris, Tokyo, Milan, Rome, Seoul). Default currency: `USD` (`$340.00`–`$360.00`).

## Where the frames are
- Eyeglasses collection URL:
  - `https://moscot.com/collections/eyeglasses` (116 frames)
- Sunglasses collection URL:
  - `https://moscot.com/collections/sunglasses` (174 frames)
- Best-selling collections:
  - `https://moscot.com/collections/best-selling-eyeglasses` (55 frames)
  - `https://moscot.com/collections/best-selling-sunglasses` (72 frames)
- New collections:
  - `https://moscot.com/collections/new-eyeglasses` (6 frames)
  - `https://moscot.com/collections/new-sunglasses` (20 frames)
- Total catalog size:
  - 116 optical + 174 sun = **290 unique frames** (0 overlap between optical and sun URLs, as sun versions have dedicated handles such as `lemtosh-sun`).
- Frames per page, and how paging works:
  - HTML listing displays 26 cards per page (`card-product`) with standard `link[rel=next]` pagination.
  - Shopify collection JSON endpoints (`/collections/<cat>/products.json?limit=250`) return the entire 116 optical and 174 sun frames in **single requests** without pagination.

## Which version of the site
- Country or language to track: `US` / global English storefront, prices in USD `$`.
- Platform: Shopify.

## One filter at a time
- Collections:
  - Eyeglasses: `/collections/eyeglasses`
  - Sunglasses: `/collections/sunglasses`
  - Best-selling: `/collections/best-selling-eyeglasses`, `/collections/best-selling-sunglasses`
  - New: `/collections/new-eyeglasses`, `/collections/new-sunglasses`

## On a product page / collection data
- Architecture & Extraction Options:
  - **Zero-Product-Page Scraping via Collection Products JSON (Recommended)**:
    - Avoids downloading over 600 Megabytes of heavy PDP HTML (each PDP is ~2.1MB).
    - Captures the complete 290-frame catalog, all variant colors and sizes, explicit material and shape tags, and bestsellers in just **4 polite HTTP requests**.
    - Each product record contains:
      - Title: `title` (e.g. `LEMTOSH`, `MILTZEN`, `DAHVEN`, `ARTHUR`)
      - Canonical link: `/products/<handle>`
      - Price: `variants[0].price` (e.g. `340.00` $\rightarrow$ `$340.00`)
      - Options: 100% of products follow `('Color', 'Size')`, so `variant.option1` cleanly provides the pure colorway name (e.g. `Light Grey`, `Brown Smoke`, `Flesh`, `Matte Tortoise`, `Ruby`, `Bamboo`) without needing regex size stripping.
      - Material tags: Explicit Shopify product tags `material-acetate`, `material-metal`, `material-acetate/metal`.
      - Shape tags: Explicit Shopify product tags `shape-square`, `shape-round`, `shape-aviator`, `shape-cateye`.
      - Primary image: `images[0].src`
      - Narrative description: `body_html` provides frame heritage, acetate gauge, rivets, and bridge details.
- Price shown: yes. Currency: `USD` (`$`). Typical range: $340.00 – $360.00.
- Colours:
  - Rich palette of 146 unique colorways: `Black`, `Tortoise`, `Flesh` (iconic vintage crystal nude), `Blonde`, `Brown Smoke`, `Bark`, `Ink`, `Bamboo`, `Butterscotch`, `Spot Tortoise`, `Classic Havana`, `Ruby`, `Emerald`, `Cognac`, `Cinnamon`, `Olive Green`, `Sage`, `Sapphire`, `Navy`.

## Strategy for Crawler
1. **Store Config Entry (`store_configs.yaml`)**:
   - `id: moscot`
   - `name: Moscot`
   - `domain: moscot.com`
   - `base_url: https://moscot.com`
   - `country: US`
   - `currency: USD`
   - `default_brand: Moscot`
   - `tier: creator`
   - `delay_s: 2.0`
2. **Collections**:
   - Eyeglasses: `https://moscot.com/collections/eyeglasses/products.json?limit=250` (category: `Optique`)
   - Sunglasses: `https://moscot.com/collections/sunglasses/products.json?limit=250` (category: `Solaire`)
   - Best-selling Eyeglasses: `https://moscot.com/collections/best-selling-eyeglasses/products.json?limit=250` (flag: `is_bestseller`)
   - Best-selling Sunglasses: `https://moscot.com/collections/best-selling-sunglasses/products.json?limit=250` (flag: `is_bestseller`)
   - New Eyeglasses: `https://moscot.com/collections/new-eyeglasses/products.json?limit=250` (flag: `is_new`)
   - New Sunglasses: `https://moscot.com/collections/new-sunglasses/products.json?limit=250` (flag: `is_new`)
3. **Product Pages**:
   - `enabled: false` (Zero-Product-Page scraping captures 100% of frames, variants, specs, and badges cleanly and politely).

## Live Crawl Verification (2026-10-02)
- **Engine**: Zero-Product-Page scraping via Shopify collection products JSON endpoints (`/collections/eyeglasses`, `/collections/sunglasses`, `/collections/best-selling-eyeglasses`, `/collections/best-selling-sunglasses`, `/collections/new-eyeglasses`, `/collections/new-sunglasses`).
- **Results**:
  - Total frames crawled: **290** (116 optical, 174 sun, 0 overlap).
  - Dropped frames: **0** (100% catalog retention).
  - Best-sellers flagged: **127** models.
  - New arrivals flagged: **26** models.
  - Duration: ~15 seconds across 6 polite requests (`delay_s: 2.0`).
- **Taxonomy Tagging Yield**:
  - **Material**: 160 acetate, 26 metal.
  - **Product Type**: 174 sun, 116 optical (100% coverage).
  - **Shape**: square (112), round (93), aviator (27), geometric (20), rectangle (11), cat_eye (5), browline (2), oversized (2), rimless (2).
  - **Colors**: blue (415), tortoiseshell (367), brown (328), green (324), black (319), grey (223), orange (200), gold (117), pink (109), silver (83), clear (72), pastel (70), red (65), beige (59), purple (50).
