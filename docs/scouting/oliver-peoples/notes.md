# Oliver Peoples: scouting notes

Site: <https://www.oliverpeoples.com>   Scouted by: AI Assistant   Date: 2026-10-03

## Access
- Works in my browser: Yes
- Login, age gate or cookie click needed before frames show: No. Open storefront.
- Terms of use forbid automated access: Standard Luxottica/Shopify commercial terms; PDP HTML requests are rate-limited with HTTP 429 ("Too Many Requests"). However, client-side Algolia search and Shopify collection JSON endpoints are open and public.

## Where the frames are
- Optical collection URL: `https://www.oliverpeoples.com/en-us/collections/eyeglasses`
- Sun collection URL: `https://www.oliverpeoples.com/en-us/collections/sunglasses`
- Roughly how many frames (optical / sun):
  - Optical: 651 colorways (1,924 variant sizes)
  - Sun: 861 colorways (1,928 variant sizes)
  - Total catalog: 1,543 unique product colorways
- Frames per page, and how paging works:
  - Storefront uses client-side infinite scroll via Algolia InstantSearch (`<op-load-more-algolia>`).
  - Search / Collection API: Public Algolia index `production_products` (`app_id: 1RF8O2ZC7K`, API key `89e591cd3a3dbb000cf29b0df810cb15`).
  - Catalog can also be fetched via standard Shopify collection JSON: `https://www.oliverpeoples.com/en-us/collections/eyeglasses/products.json?limit=250&page=N` (3 pages for optical, 4 pages for sun).
- Frame names show in View Source (Ctrl+U): Yes, initial server-side hydration scripts and `<noscript>` list exist in HTML.

## Which version of the site
- Country or language to track: US (`/en-us`), currency USD ($).
- Platform: **Shopify** (Luxottica custom theme) + **Algolia InstantSearch** for faceted navigation and catalog search.

## One filter at a time
- Filters offered:
  - Frame Shape (`frame_shape_facet`): Round, Square, Rectangle, Cat Eye, Pilot.
  - Material (`meta.custom.material`): Acetate, Titanium, Metal, Steel, Injected, Horn, Gold.
  - Gender (`meta.custom.gender`): Unisex, Man, Woman.
  - Color (`meta.custom.macro_color` & `meta.custom.color`): 17 macro families (Black, Brown, Tortoise, Gold, Green, Blue, Grey, Silver, etc.) and hundreds of specific shade names ("Dark Mahogany", "Raintree", "Cocobolo", "Bark", "Semi-Matte Amber Tortoise").
  - Bridge Fit (`meta.custom.geofit`): High Bridge Fit, Low Bridge Fit.
- URL after ticking a single value: Client-side URL parameters managed by Algolia InstantSearch router.

## On a product page
- Price shown: Yes ($414.00, $454.00, etc.)   Currency: USD ($)
- Colours:
  - Each colorway is listed as its own individual product record with a composite handle (`0ov5186-1011` = Gregory Peck in Raintree; `0ov5183-1552` = O'Malley in Semi-Matte Amber Tortoise).
  - Algolia records supply both the commercial color name (`Raintree`, `Dark Mahogany`), color code (`1011`, `100773`), and macro color (`Brown`, `Tortoise`).
- Details listed:
  - Shape: Round / Square / Rectangle / Cat Eye / Pilot
  - Material: Acetate / Titanium / Metal
  - Frame Dimensions: `lens_width` (e.g. 47), `bridge_width` (e.g. 23), `temple_length` (e.g. 150), `frame_height` (e.g. 43), `frame_width` (e.g. 124)
  - Model Code: `model_code_display` (e.g. `OV5186`, `OV5183`, `OV5298U`)
  - Collection Family: Gregory Peck, O'Malley, Cary Grant, Fairmont, Finley, Sheldrake, Roger Federer, Takumi.
- Badges and where they appear:
  - Best Sellers: Included in collections `eyeglasses-must-have` (706 hits), `sun-must-have` (369 hits), and `collections-must-have`.
  - New Arrivals: Included in `eyeglasses-new-arrival`, `sun-new-arrivals`, and `meta.custom.newreleases == 'true'`.

## Anything else
- **Extraction Strategy**: To completely bypass PDP HTTP 429 rate limiting and capture 100% complete metadata (colors, materials, millimeter frame measurements, bestseller/new badges), the crawler can directly query the public Algolia InstantSearch endpoint `https://1RF8O2ZC7K-dsn.algolia.net/1/indexes/*/queries` partitioned across the 17 `meta.custom.macro_color` facets (each with <1,000 hits), completing a 100% full-catalog extraction in ~17 requests.
