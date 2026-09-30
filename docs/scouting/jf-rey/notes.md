# jf-rey: scouting notes

Site: <https://www.jfrey.fr/>   Scouted by: ahmed  Date: 9/30/2026

## Access
- Works in my browser: no
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: only two lines found in robots.txt

## Where the frames are
note: the website buttons are unconsistent:
glasses show : https://www.jfrey.fr/en/catalog-men-en/, https://www.jfrey.fr/en/catalog-women-en/, https://www.jfrey.fr/en/kids-catalogue/
sunglasses when clicked directly shows: https://www.jfrey.fr/en/womens-sun-catalog-2/, the same page also contains btoh men and women (no kids)
- Optical collection URL:
- Sun collection URL:
- Roughly how many frames (optical / sun): limited in sunglasses; for glasses (optical) a "view more styles" button needs to be clicked, url unchanged.
- frame name and color code shown 
- Frames per page, and how paging works (next link, `?page=2`, `/page/2/`, load more):
- Frame names show in View Source (Ctrl+U): yes / no

## Which version of the site
- Country or language to track (the site may redirect by location; pick a Europe or US version): fr
- Platform, if you can tell: wp-content

## One filter at a time
- Filters offered (shape / colour / material / gender ...):
- URL after ticking a single value (paste it):
no filter picker
## On a product page
- Price shown: no  Currency:
- Colours: swatches / names / codes. One example, copied exactly:
- Details listed (shape, material, gender, lens ...): one example, copied exactly:
- Badges (best-seller, new, sold out) and where they appear:
no colors shown
## Anything else
the site seems to be badly designed and unconsistencies in the nav bar functionality

## Checks (Claude, 2026-09-30, in the browser: 3 page views)
- **robots.txt is two lines: `User-agent: *` and `Crawl-delay: 10`.** The site asks for **10 seconds between requests**, and we honour it (our default is 1.5 s): a crawl would run at
  `delay_s: 10`, so about 4 listing pages plus one page per model, roughly 35 minutes for a couple of hundred models.
- **"View more styles" loads nothing.** Clicking it made no request and changed no count: all 63 men's models (`/en/jf3157/` ...) are already in the served HTML, and the
  button only reveals rows. So one plain page per range holds every model, and no script is needed.
- **A model is a carousel of colourways labelled `MODEL - colour code`** (`JF3157 - 9955`, `JF3157 - 0029`...): 273 colour codes for the 63 men's models. The codes are
  the only colour information: no names anywhere, on the listing or on the model page (`COL. 0029` headings). Without a legend, a colour code cannot become a colour family.
- **The model page** (286 KB) gives: the model name (`og:title` "JF3157 | JFREY Eyewear Design"), the size (`Size : L`), the colour codes, a **free-text design paragraph**
  ("a combined frame in stainless steel and acetate with a contemporary geometric design ... tortoiseshell patterns ..."), a short feature list ("Men's style", "Combined frame",
  "Acetate full ring glasses") and measurements. **No price, no JSON-LD, no filters.**
- **Sun**: `womens-sun-catalog-2` holds men's and women's sunglasses together (no kids), so the audience of a sun frame is not on the listing.
- "Works in my browser: no" in your notes: I read it as "not smoothly" (the navigation is inconsistent); the pages load and answer a plain request.
