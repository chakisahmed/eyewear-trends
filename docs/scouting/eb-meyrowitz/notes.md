# <e.b. meyrowitz>: scouting notes

Site: <https://ebmeyrowitz.com>   Scouted by: <me>   Date: <today>

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: no

## Where the frames are
- Optical collection URL:
- Sun collection URL:
- Roughly how many frames (optical / sun):
- Frames per page, and how paging works (next link, `?page=2`, `/page/2/`, load more):
https://ebmeyrowitz.com/collections/sunglasses?page=2
- Frame names show in View Source (Ctrl+U): yes

## Which version of the site
- Country or language to track (the site may redirect by location; pick a Europe or US version):
- Platform, if you can tell (search the page source for `shopify`, `wp-content`, `prestashop`, `magento`): shopify

## One filter at a time
- Filters offered (shape / colour / material / gender ...):
- URL after ticking a single value (paste it):
https://ebmeyrowitz.com/collections/sunglasses/shape-rectangular

## On a product page
- Price shown: yes / no ("price on request")   Currency:
- Colours: swatches / names / codes. One example, copied exactly:
- Details listed (shape, material, gender, lens ...): one example, copied exactly:
- Badges (best-seller, new, sold out) and where they appear:
The Tarfaya in Demi-Blonde
£1,350.00

A true veteran amongst the ranks, The Tarfaya offers a wholly unique build comfortably straddling design boundaries. As perfect for day-to-day wear as they are for evening exploits, this certainly is a versatile and eye-catching number.

Colours:

Bonfire
Demi-Blonde
Amber Mottle
Finer details
Top Line
Arched

Build
Rectangular

Bridgework
Keyhole

Rim Structure
Thick
## Anything else

## Checks (Claude, 2026-09-30, in the browser: about 40 page views, 1.2 to 1.5 s apart; the notes above were still blank)
- **Collections:** `/collections/spectacles` (**65** products, 6 pages of 12) and `/collections/sunglasses` (**58**, 5 pages), `<link rel="next">` paging, about 320 KB a page. Tag filters by path (see the correction below). Shopify, GBP.
- **Each colourway is its own product** ("The Grosvenor in Olive", "The Grosvenor in Jello"...). The 123 products are only **about 35 models**, 20 of them in several colours. A model page lists its
  sibling colourways in a "Colours:" switcher (`ul.product-showcase__frame--list`, links titled `Olive`, `Jello`...), but single-colour models have no switcher.
- **The colour is in the product name** (`h1`, hidden with `d-none` but present: "The Aldwych in Black"), so one variant per product can be read from the name. Names are 37 distinct colours, many marketing names:
  **15 of 37 already match a colour family** (Black, Navy, Olive, Crystal, Champagne, Yellow, Amber / Brown / Cherry / Orange Mottle, Marron, Semi-transparent Brown / Grey);
  22 do not (Aqua, Atlantic, Barley, Bonfire, Cinnamon, Copper Mottle, Cyan, Dark Mottle, Demi Blonde, Desert Sun, Jade, Jello, Lava, Midnight, Moss, Ochre, Opal, Saffron, Savannah, Shadow, Sunburst, Sunshine).
- **Price** is public in the markup (`p.product-showcase__price`: `£1,250.00`; the cards say "From £1,250.00"); **no JSON-LD, no SKU** (Shopify's analytics data has no variant title or SKU either).
- **CORRECTION (2026-09-30, after your notes): shape IS there.** Every product page has a "Finer details" block: Top Line, **Build** (Rectangular / Soft Rectangular / Rounded / Ovular / Teardrop), Bridgework, Rim Structure (27 of 27 models). The collection pages also have tag filters by path (`/collections/sunglasses/shape-rectangular`, `colour-…`), not query parameters. Material and gender are still absent.
- **No material or gender anywhere**; the product text gives dimensions ("139mm Width x 51mm Height x 140mm Temple Length") and "Available as: Ready-To-Wear, Sunglasses, Bespoke Commission".
- **Badges** on the cards: "Special Edition" (16), "Limited Release" (6), "New" (6): the brand's own curation, a possible flag later.
- **Weight:** 11 listing pages and 123 product pages of about 305 KB: roughly 40 MB and 135 requests, about 4 minutes.
