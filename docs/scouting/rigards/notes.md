# <rigards>: scouting notes

Site: <https://...>   Scouted by: <name>   Date: <yyyy-mm-dd>

## Access
- Works in my browser: yes / no
- Login, age gate or cookie click needed before frames show: no / describe
- Terms of use forbid automated access: no / quote the sentence and the page

## Where the frames are
- Optical collection URL:
- Sun collection URL:
- Roughly how many frames (optical / sun):
- Frames per page, and how paging works (next link, `?page=2`, `/page/2/`, load more):
- Frame names show in View Source (Ctrl+U): yes / no

## Which version of the site
- Country or language to track (the site may redirect by location; pick a Europe or US version):
- Platform, if you can tell (search the page source for `shopify`, `wp-content`, `prestashop`, `magento`):

## One filter at a time
- Filters offered (shape / colour / material / gender ...):
- URL after ticking a single value (paste it):

## On a product page
- Price shown: yes / no ("price on request")   Currency:
- Colours: swatches / names / codes. One example, copied exactly:
- Details listed (shape, material, gender, lens ...): one example, copied exactly:
- Badges (best-seller, new, sold out) and where they appear:

## Anything else

## Checks (Claude, 2026-09-30, in the browser: about 25 page views, 1.5 s apart; the notes above are still blank)
- **The "Natural materials" submenu** (from your screenshot) has six entries: Solid wood, .925 Sterling silver, Genuine copper, Nature horn, Aluminium-magnesium, Special editions. They are **`/pages/…` story pages** (`/pages/wood`, `/silver`, `/copper`, `/horn`, `/aluminium`, `/special-edition`), about 100 KB each:
  a paragraph about the material and **no frame at all** (0 product links, 0 images in the main section, one empty page-builder section). The parent "Natural materials" (`/pages/collection`) is empty too.
- **The shop has collections, but they are empty.** The collections sitemap lists 9 (`real-copper`, `stainless-steel`, `aluminum-magnesium`, `pure-beta-titanium`, `genuine-horn`, `special-editions`, `solid-wood-1`, `925-sterling-silver-1`, `stainless-steel-1`): **each serves 0 product links** (about 105 KB, no `rel=next`).
  The site index lists **no products sitemap** (only pages, collections, blogs and an "agentic discovery" file): Shopify writes one when a shop has published products, so **no product is published**. Platform Shopify (theme "Pacific"), storefront locale `en-TN`.
- **Conclusion:** the public site is a brand and material showcase; the frames are not listed, priced or tagged anywhere we can read. This looks like a wholesale or "find a retailer" brand. Nothing to crawl.

