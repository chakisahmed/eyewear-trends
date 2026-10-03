# Oliver Goldsmith: scouting notes

Site: <https://www.olivergoldsmith.com>   Scouted by: chaki   Date: 2026-10-02

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no 
- Terms of use forbid automated access: no 
- robots.txt from `olivergoldsmith.com`:
  ```text
  Standard Shopify robots.txt (allows /collections/*, /products/*, disallows /checkout, /cart, /admin)
  ```
- **Crucial Rate-Limiting Discovery**:
  - Sequential requests to individual product pages (`/products/<slug>`) trigger Shopify **HTTP 429 Too Many Requests**.
  - In contrast, collection listing pages (`/collections/glasses`, `/collections/sunglasses`) return **HTTP 200 OK** reliably and swiftly.
  - **Strategy**: Just like *Cutler and Gross* and *Kirk & Kirk*, Oliver Goldsmith is implemented using **Zero-Product-Page scraping** (`product_pages.enabled: false`), capturing the entire catalog in **only 3 polite HTTP requests** in ~5 seconds!

## Brand Identity & Origin
- **Brand**: Oliver Goldsmith (OG)
- **Origin**: London, UK (`country: GB`). Founded in London in 1926 by P. Oliver Goldsmith.
- **Aesthetic**: Iconic British heritage brand that pioneered sunglasses as fashion in the mid-20th century. Framed style legends including Audrey Hepburn (*Breakfast at Tiffany's* Manhattan frame), Michael Caine (*The Italian Job* Lord frame), Peter Sellers, Grace Kelly, and John Lennon.
- **Craftsmanship**: Premium Italian cotton acetate, handmade in Italy.
- **Retail & Pricing**: Direct-to-consumer e-commerce in GBP (`£365`–`£395`).

## Where the frames are
- Optical collection URL: <https://www.olivergoldsmith.com/collections/glasses> (40–47 optical frames, 1 page)
  *(Note: `/collections/readers-by-claire-goldsmith` is a sub-selection of 23 readers; `/collections/glasses` represents the complete optical range)*
- Sun collection URL: <https://www.olivergoldsmith.com/collections/sunglasses> (57 sunglasses across 2 pages)
- Total catalog size: **~97–104 frames**.
- Frames per page, and how paging works:
  - 50 cards per page.
  - Paging selector: `pagination.next: "a.pagination__next"` (`?page=2`). Terminates naturally on page 2.
- Frame names show in View Source (Ctrl+U): yes (Shopify Liquid server-rendered HTML).

## Platform & Market
- Platform: Shopify
- Country: `GB` (United Kingdom)
- Default Currency: `GBP`

## Listing Card Architecture (`product-block.product-block`)
- **Card selector**: `product-block.product-block:not(.col-promo-box)` (cleanly excludes editorial promotional banners like the Ego shop box).
- **Link**: `a.product-link` (`url_regex: '(/products/[^/?#]+)'`)
- **Model Name**: `div.product-block__title` (e.g. `Manhattan`, `Hep`, `Vivian`, `Sophia`, `Hillman`, `Collins`, `Lord`)
- **Price**: `div.price__default` (`£365` / `£395` $\rightarrow$ `365.0` / `395.0 GBP`)
- **Image**: `img` (`https://www.olivergoldsmith.com/cdn/shop/files/...`)
- **New Badge**: `span.product-label` (matches `(?i)new` $\rightarrow$ `is_new: True`)
- **Rich Shape & Material Extraction from Image Alt (`flags.description`)**:
  The primary image's `alt` attribute explicitly details the frame's silhouette and material:
  - *"Oliver Goldsmith Manhattan sunglasses in Dark Tortoiseshell, front view of the **round frame** with green lenses"* $\rightarrow$ `shape: round`
  - *"Oliver Goldsmith Vivian sunglasses in Tangerine, front view of the **rounded square frame** with green lenses"* $\rightarrow$ `shape: square, round`
  - *"Oliver Goldsmith Sophia sunglasses in Slate Storm, front view of the **oval frame** with pink gradient lenses"* $\rightarrow$ `shape: oval`
  - *"Oliver Goldsmith Hillman sunglasses in Military, front view of the **squared aviator** with grey gradient lenses"* $\rightarrow$ `shape: aviator`
  - *"Oliver Goldsmith Collins sunglasses in Moss, front view of the **angular** olive frame..."* $\rightarrow$ `shape: geometric`
  - *"Hep Sunglasses with Dark Tortoise **acetate frame**"* $\rightarrow$ `material: acetate`
- **Variant Color Swatches on Cards**:
  Each card embeds variant color chips:
  - `span.product-block-options__item[data-option-item]`
  - Swatch names: `Dark Tortoiseshell`, `Black`, `Jungle`, `Bahama`, `Tokyo 50`, `Maple`, `Dark Olive`, `Mocha`, `Tangerine`, `Rouge`, `Anchor`, `Blackgold`, `Amberfleck`, `Slate Storm`, `Wakame`, `Military`, `Moss`, `Etaupe`

## Tagger Vocabulary Plan (v23)
- **Shape Aliases**:
  - `squared aviator` $\rightarrow$ `aviator`
- **Color Aliases**:
  - `tangerine` $\rightarrow$ `orange`
  - `tokyo 50`, `tortoise 50`, `dark tortoiseshell`, `earth tortoise`, `amberfleck` $\rightarrow$ `tortoiseshell`
  - `night sea`, `bahama`, `anchor` $\rightarrow$ `blue`
  - `rainwater` $\rightarrow$ `clear`
  - `wakame`, `plankton`, `military` $\rightarrow$ `green`
  - `blacksilver`, `blackgold`, `black cat` $\rightarrow$ `black`
  - `slate storm` $\rightarrow$ `grey`
  - `etaupe` $\rightarrow$ `beige`
  - `rouge` $\rightarrow$ `red`
