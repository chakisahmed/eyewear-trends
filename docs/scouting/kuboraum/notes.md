# <kuboraum>: scouting notes

Site: <www.kuboraum.com>   Scouted by: <ahmed>   Date: <9/30/2026>

## Access
- Works in my browser: yes 
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: no

## Where the frames are
- Optical collection URL: https://www.kuboraum.com/collections/sun-mask
- Sun collection URL: https://www.kuboraum.com/collections/optical-mask
- Roughly how many frames (optical / sun): huge, does not use pagination everything gets loaded in the pages
- Frames per page, and how paging works (next link, `?page=2`, `/page/2/`, load more):
- Frame names show in View Source (Ctrl+U): yes

## Which version of the site
- Country or language to track (the site may redirect by location; pick a Europe or US version): 
- Platform, if you can tell (search the page source for `shopify`, `wp-content`, `prestashop`, `magento`): wp-content

## One filter at a time
- Filters offered (shape / colour / material / gender ...):
- URL after ticking a single value (paste it):
filters available: ALL
B2
E15
E16
E21
url is fixed
## On a product page
- Price shown: no   Currency: none
- Colours: swatches / names / codes. One example, copied exactly:
- Details listed (shape, material, gender, lens ...): one example, copied exactly:
- MASK
E15 SILVER
CODE: E15 SI
MATERIAL: Metal, Nylon, Acetate
COLOR: Silver + Black Matt
LENS: Grey

LENS WIDTH: 144 mm
TEMPLE LENGTH: 145 mm

KUBORAUM ARE MASKS THAT ARE DESIGNED ON THE FACE OF ITS WEARERS TO HIGHLIGHT THEIR PERSONALITY AND CHARACTER. MASK IS SYNONYMOUS WITH MOCKERY AND GAME. KUBORAUM MASKS ARE SYNONYMOUS WITH PROTECTION AND SHELTER; THEY ARE CUBICAL ROOMS WHERE WE SHELTER OURSELVES, FREE TO LIVE OUR INTIMACY AND LOOK AT THE WORLD TROUGH TWO LENSES. ALL MASKS ARE ENTIRELY DREAMED IN BERLIN HANDMADE IN ITALY
- Badges (best-seller, new, sold out) and where they appear:

## Anything else

## Checks (Claude, 2026-09-30, in the browser: 14 collection pages and 26 product pages, 1.5 s apart)
- **Your two collection URLs are swapped in the notes above:** `/collections/optical-mask/` is the optical one (**473** cards, 123 model codes) and `/collections/sun-mask/` the sun one (**363** cards, 117 model codes).
  Each card is one **model + colour** page (`/masks/e21-gorgone/`, `-2`, `-3` when a colour name repeats).
- **137 pages are in both collections** (frames sold with clear or tinted lenses), so the catalog is **699 distinct pages**, not 836. The pages themselves do not say optical or sun ("MASK" only); the only signal is which collection lists them.
- **No paging, no server filters:** everything is in one 0.8 to 1 MB page; the buttons (ALL, B2, E15...) are **model codes** that hide cards with JavaScript (`data-tags`), so there is no URL per filter and nothing to request. The menu's other collections
  (Acetate 467, Metal 134, Acetate and Metal 84, Rimless 54, Machinery 29, Hydromechanics 28...) all overlap the two main ones (699 distinct in total, none outside).
- **No price, no JSON-LD Product, no badges**, no gender, **no shape** anywhere. The product page has a "Request a retailer" button instead of a cart.
- **The product page has clean labelled lines** (`.new-description`, `<span class="bold">LABEL:</span> value<br>`): `CODE` (`D71 VP`), `MATERIAL` (`ACETATE & METAL`, `METAL + ACETATE TEMPLE TIPS`, `HIGH DENSITY ACETATE`), `COLOR` (`Violet Petal`, `GOLD + BLACK MATT`, `WATER, HANDCRAFT FINISHING`),
  `TEMPLES COLOR`, `LENS` (`CLEAR`, `GREY`, `24H LIGHT AQUAMARINE`), `BRIDGE`, `LENS WIDTH`, `TEMPLE LENGTH`. The case of the values varies from page to page. Some sizes are placeholders (`BRIDGE: 00 mm`, `LENS WIDTH: 99 mm`).
- **Colours** are mostly ordinary words (Silver, Gold, Rosegold, Black Shine, Black Matt, Havana, Yellow Havana, Champagne, Gun Metal, Light Gold) with some marketing names (Violet Petal, Rain Forest, Pithoprakta, Sky, Water).
- **Weight:** 699 pages of about 113 KB (listings excluded): roughly 80 MB and 700 requests, about 18 minutes at 1.5 s. robots.txt allows everything, no crawl delay.
