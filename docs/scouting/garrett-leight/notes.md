# Garrett Leight California Optical (GLCO): scouting notes

Site: <https://www.garrettleight.com>   Scouted by: Ahmed & Antigravity   Date: 2026-10-02

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: no (Shopify robots.txt explicitly states: `"Shopify storefront. Public product, collection, page, blog, policy, cart, and localized HTML is crawlable."` and provides agent instructions at `https://www.garrettleight.com/agents.md`).
- robots.txt from `https://www.garrettleight.com/robots.txt`:
  ```text
  # Shopify storefront. Public product, collection, page, blog, policy, cart, and localized HTML is crawlable.
  # Agent instructions: https://www.garrettleight.com/agents.md
  # UCP discovery: https://www.garrettleight.com/.well-known/ucp
  # UCP/MCP endpoint: https://www.garrettleight.com/api/ucp/mcp
  User-agent: *
  Disallow: /admin
  Disallow: /cart
  Disallow: /orders
  Disallow: /checkouts/
  Disallow: /checkout
  Disallow: /collections/*sort_by*
  ```
- Compliance & Crawling architecture:
  - Standard Shopify endpoints are completely open under `robots.txt`.
  - Zero-Product-Page scraping via Shopify collection `products.json?limit=250` endpoints allows collecting 100% of the eyewear catalog in just 5 polite requests without hitting HTML 429 rate limits or parsing heavy DOM markup.

## Brand Identity & Heritage
- **Brand**: Garrett Leight California Optical (GLCO)
- **Origin**: Venice Beach, Los Angeles, California, USA (`country: US`). Founded in 2010 by Garrett Leight, son of Larry Leight (the founder of Oliver Peoples).
- **Aesthetic**: Laid-back, effortless Southern California style inspired by vintage American design, music, art, and coastal culture. Known for refined, easy-to-wear proportions, custom-designed acetate plaques, subtle rivet details, multi-barrel hinges, and translucent pastel and warm tortoise acetates.
- **Materials & Craftsmanship**:
  - Premium cured cellulose acetate sourced from heritage Italian maker Mazzucchelli 1849 and Japanese heritage suppliers.
  - Custom filigree wire cores, vintage-inspired drop hinges, and pure titanium elements in mixed-media frames.
  - Hand-finished by master craftspeople.
- **Dual Brand Lines on Storefront**:
  1. **GLCO (Garrett Leight California Optical)**: The core contemporary Californian line (125 frames, $395–$455 USD).
  2. **Mr. Leight**: The elevated ultra-luxury collaboration line created by Garrett Leight and his father Larry Leight. Handcrafted in Sabae (Fukui Prefecture, Japan) using titanium, 18k gold plating, and vintage Japanese cured acetate (30 frames, $595–$685 USD).
- **Iconic Flagship Silhouettes**:
  - **HAMPTON**: The definitive P3 round silhouette that launched the brand in 2010; vintage-inspired round acetate frame with keyhole bridge.
  - **KINNEY**: Classic square-proportioned acetate frame with keyhole bridge and versatile, timeless styling.
  - **BROOKS**: Refined square retro silhouette with distinctive beveling and California cool sensibility.
  - **WILSON**: Iconic round Windsor-rim frame featuring cured acetate wrapping a thin metal frame and filigree metal temples.
  - **HARDING**: Bold 60s-inspired masculine square optical and sun frame inspired by Arthur Miller.
  - **CLUNE**: Compact, perfectly proportioned circular retro frame with keyhole bridge.
  - **CALABAR**: Thick, commanding 1960s-inspired wayfarer frame with bevel cuts.

## Where the frames are
- Primary collections on storefront:
  - Optical collections:
    - GLCO Eyeglasses: `https://www.garrettleight.com/collections/eyeglasses/products.json?limit=250` (63 frames, 100% `Optical`)
    - Mr. Leight Eyeglasses: `https://www.garrettleight.com/collections/mr-leight-eyeglasses/products.json?limit=250` (14 frames, 100% `Optical`)
    - Total Optical: **77 unique frames**
  - Sun collections:
    - GLCO Sunglasses: `https://www.garrettleight.com/collections/sunglasses/products.json?limit=250` (62 frames, 100% `Sunglasses`)
    - Mr. Leight Sunglasses: `https://www.garrettleight.com/collections/mr-leight-sunglasses/products.json?limit=250` (14 frames, 100% `Sunglasses`)
    - Mr. Leight Sunglasses (ML line): `https://www.garrettleight.com/collections/ml-sunglasses/products.json?limit=250` (15 frames, captures Mulberry collection models `doheny-sl` and `laurel-sl`)
    - Total Sun: **78 unique frames**
- Flag collections for enrichment:
  - Best Sellers: `https://www.garrettleight.com/collections/bestsellers/products.json?limit=250` (17 frames, `flag: is_bestseller`)
  - Forever Classics: `https://www.garrettleight.com/collections/forever-classics/products.json?limit=250` (12 frames, `flag: is_bestseller`)
  - New Eyeglasses: `https://www.garrettleight.com/collections/new-eyeglasses/products.json?limit=250` (6 frames, `flag: is_new`)
  - New Sunglasses: `https://www.garrettleight.com/collections/new-sunglasses/products.json?limit=250` (5 frames, `flag: is_new`)
- Total Eyewear Catalog:
  - 77 Optical + 78 Sun = **155 unique eyewear frames** (125 GLCO, 30 Mr. Leight).
  - 0 non-eyewear items in these collections (all clips, cleaning kits, cases, and apparel are segregated in `/collections/sun-clips` and `/collections/extras`).
- Paging:
  - Each collection returns the entire set in **1 request** (`?limit=250`).

## Which version of the site
- Country / Language: `US` / English global storefront.
- Currency: `USD` (`$`).
- Platform: Shopify storefront (`www.garrettleight.com`).

## One filter at a time & Product Tags
- Structured tags present on product records:
  - **Material tags**:
    - `material:acetate` (109 frames)
    - `material:metal` (43 frames)
    - `material:combo` (19 frames — mixed acetate windsor rims and metal frame/temples)
  - **Shape tags**:
    - `shape:square` (61 frames)
    - `shape:round` (44 frames)
    - `shape:rectangle` (14 frames)
    - `shape:aviator` (14 frames)
    - `shape:oval` (7 frames)
    - `shape:geometric` (6 frames)
    - `shape:cat eye` (5 frames)
    - `shape:octagonal` (3 frames)
  - **Color tags**:
    - `colors:Tortoise` (75 frames)
    - `colors:Brown` (74 frames)
    - `colors:Black` (68 frames)
    - `colors:Translucent` (54 frames)
    - `colors:Grey` (41 frames)
    - `colors:Green` (40 frames)
    - `colors:Silver` (23 frames)
    - `colors:Gold` (20 frames)
    - `colors:Blonde` (17 frames)
    - `colors:Pewter` (15 frames)
    - `colors:Pink` (14 frames)
    - `colors:Beige` (12 frames)
    - `colors:Red` (10 frames)
    - `colors:Blue` (8 frames)
  - **Badges & Classifications**:
    - `collection:Classics` (14 frames)
    - `collection:new` (13 frames)
    - `collection:Mr. Leight` (17 frames)
    - `size:medium` (71), `size:large` (47), `size:small` (13)

## On a product record (`products.json`)
- Examples inspected:
  - **KINNEY SUN** (`/products/kinney-sun-1`):
    - Title: `KINNEY SUN`
    - Brand: `GLCO`
    - Price: `$395.00`
    - Tags: `['colors:Beige', 'colors:Black', 'colors:Brown', 'colors:Tortoise', 'collection:Classics', 'material:acetate', 'shape:square', 'Sunglasses']`
    - Variants (6):
      - `2007-49-BIO-CHAM/G15` | `Bio Champagne/G15` ($395.00)
      - `2007-49-BIO-MST/PGN` | `Bio Matte Spotted Tortoise/Pure Green` ($395.00)
      - `2007-49-BIO-BT/PGRN` | `Bio Butterscotch/Pure Green` ($395.00)
  - **HAMPTON** (`/products/hampton`):
    - Title: `HAMPTON`
    - Brand: `GLCO`
    - Price: `$395.00`
    - Tags: `['colors:Beige', 'colors:Black', 'colors:Brown', 'colors:Tortoise', 'Eyeglasses', 'material:acetate', 'shape:round']`
    - Variants (8):
      - `1001-46-BIO-BK` | `Bio Black`
      - `1001-46-BIO-CHAM` | `Bio Champagne`
      - `1001-46-BIO-MST` | `Bio Matte Spotted Tortoise`
  - **WILSON M** (`/products/wilson-m`):
    - Title: `WILSON M`
    - Brand: `GLCO`
    - Price: `$455.00`
    - Tags: `['material:combo', 'shape:round', 'Eyeglasses', 'colors:Gold', 'colors:Tortoise']`
    - Material: combo (cured acetate rim wrapped on metal chassis)
- Pricing Analysis:
  - Min: `$150.00` (archive sale frames)
  - Max: `$685.00` (Mr. Leight titanium sun frames)
  - Catalog Average: **`$407.68 USD`**

## Strategy for Crawler
1. **Store Config Entry (`store_configs.yaml`)**:
   - `id: garrettleight`
   - `name: Garrett Leight`
   - `domain: garrettleight.com`
   - `base_url: https://www.garrettleight.com`
   - `country: US`
   - `default_brand: Garrett Leight`
   - `default_currency: USD`
   - `delay_s: 2.0`
   - `listing.url_regex: '(/products/[^/?#]+)'`
2. **Collection URLs**:
   ```yaml
   listing:
     urls:
       - { url: "/collections/eyeglasses/products.json?limit=250", categories: "Optique" }
       - { url: "/collections/mr-leight-eyeglasses/products.json?limit=250", categories: "Optique" }
       - { url: "/collections/sunglasses/products.json?limit=250", categories: "Solaire" }
       - { url: "/collections/mr-leight-sunglasses/products.json?limit=250", categories: "Solaire" }
       - { url: "/collections/ml-sunglasses/products.json?limit=250", categories: "Solaire" }
       - { url: "/collections/bestsellers/products.json?limit=250", flag: "is_bestseller" }
       - { url: "/collections/forever-classics/products.json?limit=250", flag: "is_bestseller" }
       - { url: "/collections/new-eyeglasses/products.json?limit=250", flag: "is_new" }
       - { url: "/collections/new-sunglasses/products.json?limit=250", flag: "is_new" }
   ```
3. **Parser Enhancements (`parser.py`)**:
   - Support `shape:<value>` tags (in addition to existing `shape-<value>`) so `shape:square`, `shape:round`, `shape:aviator`, `shape:rectangle` are ingested into `flags["description"]`.
   - Brand name normalization: map vendor `GLCO` to `"Garrett Leight"` (or keep Mr. Leight vendor for the collaboration line).
   - Material assignment:
     - `material:acetate` or `material:combo` -> `acetate`
     - `material:metal` or `titanium` -> `metal`
     - Default for GLCO frames without an explicit material tag: `acetate`.
4. **Taxonomy & Color Aliases (`tagger.py`)**:
   - Bump `RULES_VERSION = 30`.
   - Add GLCO signature colorway aliases to `SPEC_ALIASES['color']`:
     - `true demi` -> `tortoiseshell`
     - `olio` -> `green`
     - `cyprus fade`, `cyprus` -> `green`
     - `cola` -> `brown`
     - `willow` -> `green`
     - `brew` -> `brown`
     - `sandstorm` -> `beige`
     - `himalayan salt` -> `pink`
     - `strawberry jam` -> `red`
     - `douglas fir` -> `green`
     - `pinewood` -> `green`
     - `pure glass` -> `clear`
     - `oakmoss` -> `green`
     - `barolo` -> `red`
     - `sea glass` -> `green`
     - `truffle` -> `brown`
     - `java drift` -> `brown`
     - `sandalwood drift` -> `beige`
     - `kelp` -> `green`
     - `prosecco` -> `beige`
     - `stillwater` -> `blue`
     - `driftwood` -> `beige`
     - `pewter` -> `grey`
     - `basalt` -> `grey`
     - `hunter` -> `green`
     - `limu` -> `green`
     - `serpentine` -> `green`
     - `lipstick` -> `red`
     - `fig` -> `purple`

## Live Crawl Validation (2026-10-02)
- **Execution**: `python -m app.cli crawl-stores --force garrettleight.com` followed by `python -m app.cli retag-products`.
- **Crawl Metrics**:
  - Total products found & inserted: **155 frames**
  - Updated / Reactivated: `0`
  - Dropped / Conflicts: **0 dropped** (100% success rate)
- **Catalog Breakdown**:
  - Brand line breakdown:
    - **Garrett Leight (GLCO)**: **125 frames** (80.6%)
    - **Mr. Leight**: **30 frames** (19.4%)
  - Category breakdown:
    - **Optique (Eyeglasses)**: **77 frames** (49.7%)
    - **Solaire (Sunglasses)**: **78 frames** (50.3%)
  - Material breakdown:
    - **Acetate**: **130 frames** (83.9%)
    - **Metal / Titanium**: **25 frames** (16.1%)
  - Flags / Merchandising badges:
    - **Bestsellers**: **22 frames** flagged (`is_bestseller = True`, e.g. Hampton, Kinney, Brooks, Wilson M)
    - **New Arrivals**: **20 frames** flagged (`is_new = True`)
  - Price distribution:
    - Min: `$150.00`
    - Max: `$685.00`
    - Average: **`$427.61 USD`**
- **Taxonomy Tagging Coverage (Rules v30)**:
  - Product type: 155/155 (**100.0%**)
  - Material: 155/155 (**100.0%**)
  - Color: 154/155 (**99.4%**)
  - Shape: 147/155 (**94.8%**)
  - Top color families: `tortoiseshell` (342), `green` (336), `gold` (236), `brown` (220), `black` (199), `grey` (190), `blue` (101), `clear` (95), `two_tone` (67), `beige` (60).
- **Unit Test Suite**:
  - `backend/tests/test_store_garrett_leight.py`: 5 tests passing
  - `backend/tests/test_store_crawlers.py`: 55 tests passing (updated to 24 stores)
  - Full test suite: **478 passed in 137.24s** (100% green).
