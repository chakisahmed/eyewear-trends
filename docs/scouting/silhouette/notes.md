# <Silhouette>: scouting notes

Site: silhouette.com   Scouted by: <name>   Date: <yyyy-mm-dd>

## Access
- Works in my browser: yes 
- Login, age gate or cookie click needed before frames show: accepted only necessary cookies
- Terms of use forbid automated access: no

## Where the frames are
- Optical collection URL: https://www.silhouette.com/en/sunglasses
- Sun collection URL: http://silhouette.com/en/optical-eyewear
- Roughly how many frames (optical / sun): 86 / 42 
- Frames per page, and how paging works (next link, `?page=2`, `/page/2/`, load more): "load more" button, static url
- Frame names show in View Source (Ctrl+U): yes

## Which version of the site
- Country or language to track (the site may redirect by location; pick a Europe or US version): us
- Platform, if you can tell (search the page source for `shopify`, `wp-content`, `prestashop`, `magento`): undetermined

## One filter at a time
- Filters offered (shape / colour / material / gender ...):
- URL after ticking a single value (paste it):

## On a product page
- Price shown: no
- Colours: swatches / names / codes. One example, copied exactly:
- Shape 8751
Frame colour 7000 Silver Grey
Lens colour Space Blue
- Details listed (shape, material, gender, lens ...): one example, copied exactly:
- Badges (best-seller, new, sold out) and where they appear:

## Anything else

## Checks (Claude, 2026-09-30: 1 page load in the browser, 7 plain requests with our user agent)
- **Your two collection URLs are swapped in the notes above:** `/en/sunglasses` is the sun collection and `/en/optical-eyewear` the optical one (86 optical / 42 sun by your count). Frames show as **model number, frame colour, lens colour** (`Shape 8751`, `Frame colour 7000 Silver Grey`,
  `Lens colour Space Blue`): "Shape" here is the **model number**, not a geometric shape.
- **The site is behind an AWS WAF bot challenge.** Plain requests with our user agent (`EyewearTrendsBot/0.1`) got `HTTP 202`, an empty body and the header `x-amzn-waf-action: challenge` on the optical listing, on `sitemap.xml` and on a sub-sitemap; the sun listing answered 200 once
  (772 KB), then was challenged too. The first pass on 2026-09-29 got through (homepage, sitemap, a sub-sitemap), so the challenge is either rate-based or newly on. **Nothing was done to get around it**, and I stopped requesting after seeing it.
- **What the page looks like in a browser** (the challenge is solved by a browser's own script): a Storyblok-built page (666 KB) with a "Filter and sort" panel (New arrivals, Virtual Try-On available, Rimless, Full-rim, Half-rim, shapes as sub-pages such as `/en/optical-eyewear/aviator`, `/cateye`, `/rectangular`, gender pages `/women`, `/men`)
  and a **"Show more" button on a static URL**. In the page I loaded, **no frame links were in the document** (0 results listed before any script ran): the frames are drawn by script, so even a plain 200 would not carry them.
- **No price** on the listing or the product page (your notes), no JSON-LD other than a breadcrumb.

## Verdict for the crawler
Not crawlable as it stands: a bot challenge on the pages we need, and frames built by script. The rule stays: no bypassing a challenge. The way forward is the client's feed or a written allowlisting of our user agent, or a saved product page per locale from you.

