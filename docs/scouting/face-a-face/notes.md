# Face à Face: scouting notes

Site: <https://www.faceaface-paris.com/>   Scouted by: Ahmed   Date: 2026-10-01
## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: no

## Where the frames are
- Optical collection URL: https://www.faceaface-paris.com/en/optical
- Sun collection URL: https://www.faceaface-paris.com/en/sun (note: /en/sunglass returns 404)
- Roughly how many frames (optical / sun): 107 optical / 12 sun (119 models total; ~500+ colorway SKUs)
- Frames per page, and how paging works (next link, `?page=2`, `/page/2/`, load more): 50 per page via server query parameter `?Page=2` (capitalized `Page`)
- Frame names show in View Source (Ctrl+U): yes

## Which version of the site
- Country or language to track (the site may redirect by location; pick a Europe or US version): en (/en/optical and /en/sun)
- Platform, if you can tell (search the page source for `shopify`, `wp-content`, `prestashop`, `magento`): Umbraco (.NET CMS; robots.txt: Disallow: /umbraco/)

## One filter at a time
- Filters offered (shape / colour / material / gender ...): Style (FEMININE, MASCULINE, UNISEX), Collection (Out of Office, Face a Face, Bocca, Alium), Material (TITANIUM, ACETATE, ALUMINIUM, STAINLESS STEEL, NYLON), Color (12 colors). No shape filter.
- URL after ticking a single value (paste it):
https://www.faceaface-paris.com/en/optical?CategoryId=57119&StyleNames=MASCULINE&MaterialIds=3&PageSize=50&Page=1

## On a product page
- Price shown: yes / no ("price on request")   Currency: no ("price on request", B2B optician distribution)
- Colours: swatches / names / codes. One example, copied exactly:
Active color in slider caption:
  <span class="slider-caption__color--name">BLACK</span>
  <span class="slider-caption__color--code">100</span>
Sibling colorways linked via `.product-list-item[href*="colorCode="]`.
- Details listed (shape, material, gender, lens ...): one example, copied exactly:
Inside `section.product-specification .specs__container`:
  Name: friday 2
  Material: acetate
  Style: feminine
  Front Type: full rim
  Size: 50 22 mm
  Temple Length: 142 mm
  Nosepad: no
- Badges (best-seller, new, sold out) and where they appear: none

## Anything else
- Card URLs on listing pages include port `:443` (e.g. `https://www.faceaface-paris.com:443/en/optical/...`) and default `?colorCode=...`.
  The canonical URL regex `(/en/(?:optical|sun)/[^/]+/[^/]+/[^/?#]+)` cleanly strips both.

