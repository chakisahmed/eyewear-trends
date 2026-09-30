# <Brand>: scouting notes

Site: <https://...>   Scouted by: <name>   Date: <yyyy-mm-dd>

## Access
- Works in my browser: yes / no
- Login, age gate or cookie click needed before frames show: no (accepted necessary only)
- Terms of use forbid automated access: no

## Where the frames are
- Optical collection URL: https://dita.com/en-tn/collections/optical
- Sun collection URL: https://dita.com/en-tn/collections/sunglasses
- Roughly how many frames (optical / sun): 81/89
- Frames per page, and how paging works (next link, `?page=2`, `/page/2/`, load more): 40, ?page=2
- Frame names show in View Source (Ctrl+U): yes / no
yes
## Which version of the site
- Country or language to track (the site may redirect by location; pick a Europe or US version): en-tn
- Platform, if you can tell (search the page source for `shopify`, `wp-content`, `prestashop`, `magento`): shopify

## One filter at a time
- Filters offered (shape / colour / material / gender ...): Filters

Product type
Frame Shape
Frame Color
Lens Color
Frame Material
Frame Size
Gender
Price
- URL after ticking a single value (paste it): sort_by=manual&filter.v.m.vdp.frame_shape=Cat-Eye&filter.v.price.gte=&filter.v.price.lte=

## On a product page
- Price shown: yes Currency: $
- Colours: swatches / names / codes. One example, copied exactly:
- Details listed (shape, material, gender, lens ...): one example, copied exactly:
- Badges (best-seller, new, sold out) and where they appear:
EVERCHARM
$834.75 USD
SKU: DTS754-A-03

Select Color:
Color:
Swanshell - Rose Gold

Black Glass - Silver

Tortoise Haze - White Gold

Swanshell - Rose Gold

Lens color:
Dark Grey to Peach Gradient

HIGH QUALITY JAPANESE ACETATE FRAME AND TEMPLES WITH CUSTOM WIRE CORE
CUSTOM 4-PIECE TITANIUM LENS PIERCINGS DITA PROPRIETARY TITANIUM HEX SCREW 5-BARREL HINGE
100% UVA AND UVB LENS WITH ANTI-REFLECTIVE COATING
MADE IN JAPAN
## Anything else

## Checks (Claude, 2026-09-30, in the browser: about 10 page views, 1.5 s apart)
- **The storefront decides the price.** The same frame, Evercharm, is **$834.75 on `/en-tn`** and **$795 on `/en-gb` and `/en-fr`** (all in USD). There is no
  `/en-us` path (404); the US store is the site root. Your notes chose `en-tn`. That URL prefix is part of every product's identity in our database, so the locale
  has to be settled **before the first crawl**: changing it later would duplicate every frame.
- **Paging is an `<a rel="next">` anchor**, not a `<link>`: `/en-tn/collections/optical` has 40 cards per page and 3 pages (40 + 40 + 1 = 81, the count shown).
  The "load more" control loads these same `?page=N` pages. Cards are `<product-item>` elements.
- **Filters** (all variant-level metafield filters, but the same for every colour of a frame): `filter.v.m.vdp.frame_shape` (Aviator, Browline, Cat-Eye, Diamond,
  Navigator, Polyangular, Round, Square), `filter.v.m.vdp.frame_composition` (Acetate, Titanium, Titanium/Acetate, and the site's typo **"Titanuim"**), plus frame
  colour, lens colour, size, gender and price. The URL in the notes cannot be used as written: `sort_by` is forbidden by robots.txt and so is a URL with several
  `filter` parameters (the price range adds two). One value alone works: `?filter.v.m.vdp.frame_shape=Cat-Eye`.
- **Structured data is complete.** The product's JSON-LD has one offer per colourway with `name`, `sku` (`DTS754-A-01`), `price` (834.75), `priceCurrency` and
  `availability`. The offer name is `Frame - Finish / Lens`: `Black Glass - Silver / Grey to Clear Gradient`, `Tortoise Haze - White Gold / Brown`,
  `Swanshell - Rose Gold / Dark Grey to Peach Gradient`. So the **frame colour is the first part before " - "**, the metal finish is the second, and the lens
  colour follows the "/" (it is also a separate option). Only the frame colour would become the colour tag.
- **Size:** Evercharm has 3 variants (colour x lens), no size options; sizes look like a filter attribute, not separate products (to confirm on a few more frames).
- **Not settled:** the locale (above), and the cost of a crawl (about 1.3 MB per listing page, 40 frames per page).
