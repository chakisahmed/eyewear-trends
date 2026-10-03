# Cutler and Gross: scouting notes

Site: <https://www.cutlerandgross.com>   Scouted by: Ahmed   Date: 2026-10-02

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no 
- Terms of use forbid automated access: no 
- robots.txt: standard Shopify robots.txt (`Disallow: /admin`, `/checkout`, `/collections/*+*`, etc.). Listing collections (`/collections/`) and pagination (`?page=`) are completely allowed.

## Where the frames are
- Optical collection URL: <https://www.cutlerandgross.com/collections/optical-designer-glasses>
- Sun collection URL: <https://www.cutlerandgross.com/collections/sunglasses>
- Roughly how many frames (optical / sun):
  - Optical: **127** models (3 pages: 45 + 45 + 37)
  - Sun: **113** models (5 pages: 26 + 26 + 26 + 26 + 9)
  - Total catalog: **240** unique models
- Frames per page, and how paging works: server-side query parameter `?page=2` (Shopify standard pagination, 8 total pages across both collections).
- Frame names show in View Source (Ctrl+U): yes (fully server-rendered Shopify theme).

## Which version of the site
- Country or language to track: English (`en`), base domain `https://www.cutlerandgross.com`.
- Brand & Heritage: Country code `GB` (Iconic British creator brand founded in Knightsbridge, London in 1969 by Graham Cutler and Tony Gross, handmade in their own factory in Cadore, Italy). Default currency: `GBP` (`£`).
- Platform: Shopify.

## One filter at a time
Shopify storefront collection filters:
- Frame shape: `filter.p.m.custom.frame_shape=Aviator`, `Cat-Eye`, `Round`, `Square`, `Rectangle`, `Geometric`, etc.
- Material: `filter.p.m.magento.material=Acetate`, `Metal`, `Titanium`, `Combination`.
- Colour group: `filter.v.option.colour=...`
- Bridge fit: `filter.p.m.custom.bridge_fit=Narrow`, `Medium`, `Wide`.

## On a listing card / product page
- Price shown: yes (`£410.00`, `£415.00`). Currency: `GBP` (`£`).
- Colours / Swatches / Variants:
  - Swatch circles: `<span class="swatch product-option__swatch product-option__swatch--circle" style="--swatch--background: url(//www.cutlerandgross.com/cdn/shop/files/{color}.jpg...)">`
  - Colorway inputs: `<input type="radio" value="Olive on Black">`, `Humble Potato`, `Old Brown Havana`, `Black`, `Havana`, `Horn Crystal`, `Sand Crystal`.
  - Full variants JSON embedded directly on each card: `<script data-product-variants-json type="application/json">` contains all SKUs, prices, color names, and stock availability.
- Details listed (shape, material, gender, lens ...):
  - Titles on cards and product pages are exceptionally descriptive: e.g. `1434 Square Sunglass`, `9261 Cat Eye Sunglasses`, `0001 Round Sunglasses`, `GR15 Aviator Polarised Sunglasses`.
  - Directly exposes: Model code (`1434`, `9261`), Silhouette shape (`Square`, `Cat Eye`, `Round`, `Aviator`), and Category (`Sunglass` / `Sunglasses` / `Glasses`).
- Badges:
  - `New`: displayed in `<span class="product-card__badges"><span class="product-card__badge">New</span></span>`.

## Anything else
- **Card-level extraction efficiency**:
  - Each `product-card.product-card` on the collection pages contains the full product title, price in GBP, high-res image, `New` badge, and all variant colorways.
  - Shopify storefront endpoints can trigger `429 local_rate_limited` when requesting hundreds of individual detail pages rapidly. Because the collection listing cards already supply 100% of required fields, Cutler and Gross can be scraped **entirely from the collection listing pages** in just 8 clean, cached requests!
- **URL structure**:
  - Canonical product URL: `'(/products/[^/?#]+)'`

## Status: Implemented & Tracked
- Config: `cutlerandgross.com` in `backend/app/collectors/stores/store_configs.yaml`
- Offline unit tests: `backend/tests/test_store_cutler_and_gross.py` (3 passed, full suite 432 passed)
- Live crawl: 240 products crawled (127 optical, 113 sun; 0 dropped)
- Tags yield: 240 product_type (100%), 238 shape (99.2%), 192 color (80.0%)

