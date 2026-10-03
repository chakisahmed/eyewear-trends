# Kirk & Kirk: scouting notes

Site: <https://kirkandkirk.com>   Scouted by: Chaki & Antigravity   Date: 2026-10-02

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: no 
- robots.txt: standard WordPress/Yoast `robots.txt`. Collections (`/glasses/`, `/sunglasses/`) and products (`/product/`) are fully allowed.
  - Allowed by crawler bot user-agent: yes (`status: 200` with `EyewearTrendsBot/0.1`).

## Where the frames are
- Optical collection URL: <https://kirkandkirk.com/glasses/>
- Sun collection URL: <https://kirkandkirk.com/sunglasses/>
- Roughly how many frames (optical / sun):
  - Optical: **28** unique models
  - Sun: **8** unique models
  - Total catalog: **36** models
- Frames per page, and how paging works: single page per collection (no pagination needed, all frames render directly).
- Frame names show in View Source (Ctrl+U): yes (server-rendered WooCommerce / Elementor shortcode).

## Which version of the site
- Country or language to track: English (`en`), base domain `https://kirkandkirk.com`.
- Brand & Heritage: Country code `GB` (British independent creator brand founded in London/Brighton, UK by Jason and Karen Kirk; handmade in France and Italy from bespoke 10mm lightweight Italian acrylic in saturated kaleidoscope hues).
- Default currency: `GBP` (`£490.00` – `£595.00`).
- Platform: WordPress / WooCommerce / Elementor (`wp-content`).

## On a listing card (`div.kak-card[data-cat-name]`)
- Product card selector: `div.kak-card[data-cat-name]` (filters out editorial celebrity photo blocks `.celebrity-wrapper`).
- Link: `a.kak-product` -> canonical URL `'(/product/[^/?#]+)'`.
- Model name: `a.kak-product` (e.g. `Emma`, `Evan`, `Layla`, `Stanley`, `Yvonne`).
- Price shown: yes (`£490.00`, `£525.00`, `£595.00` in `.kak-card-price .woocommerce-Price-amount`). Currency: `GBP` (`£`).
- Primary image: `img.kak-card__image--default` (`src`).
- Shape & Editorial description: `img.kak-card__image--default[title]` embeds silhouette hints (e.g. "gentle roundness", "Aviator", "geometric", "upswept", "hexagonal").
- Colours / Swatches / Variants:
  - Rows: `.kak-card-controls .kak-card-controls__pill`
  - Code & Color name: `img.kak-card-controls__dot[title]` (e.g. `Jungle`, `Smoke`, `Glacier`, `Indigo`, `Admiral`, `Jet`, `Candy`, `Carmine`)
  - Swatch: `img.kak-card-controls__dot[src]` (high-res 100x100 PNG color chips)

## Anything else
- **Card-level extraction efficiency**:
  - Because collection listing cards supply 100% of required fields (name, canonical URL, price in GBP, high-res image, editorial description/shape, and all colorway variants with swatches), **Kirk & Kirk can be crawled in just 2 polite HTTP requests** (`product_pages.enabled: false`).
- **Catalog count**: exactly 36 models (28 optical, 8 sun).

## Status: Implemented & Tracked
- Config: `kirkandkirk.com` in `backend/app/collectors/stores/store_configs.yaml`
- Offline unit tests: `backend/tests/test_store_kirk_and_kirk.py` (3 passed, full suite 435 passed)
- Live crawl: 35 products crawled (28 optical, 7 sun; 0 conflicts)
- Tags yield: 35 product_type (100%), 35 color (100%), 15 shape (42.9%)
