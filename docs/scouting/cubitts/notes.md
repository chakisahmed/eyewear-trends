# <Cubits>: scouting notes

Site: <[https:](https://cubitts.com/)>   Scouted by: <Me>   Date: <9/30/2026>

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no [already denied]
- Terms of use forbid automated access: no

## Where the frames are
- Optical collection URL: https://cubitts.com/collections/spectacles
- Sun collection URL: https://cubitts.com/collections/sunglasses
- Roughly how many frames (optical / sun): 117/132
- Frames per page, and how paging works (next link, `?page=2`, `/page/2/`, load more): infinite scroll , triggered after scrolling past 20 items but increments ?page=
- Frame names show in View Source (Ctrl+U): yes
  inside <a class="product-card__link font-mobile-ui-14 font-desktop-ui-14" href="/products/albion">Albion</a>
## Which version of the site
- Country or language to track (the site may redirect by location; pick a Europe or US version): UK
- Platform, if you can tell (search the page source for `shopify`, `wp-content`, `prestashop`, `magento`): shopify

## One filter at a time
- Filters offered (shape / colour / material / gender ...):
- Filter by


Shape 5

Colour 16

Size 5

Material 4

Thickness 2

Bridge fit 6

Sort by [Bestsellers

New in

Clip-on compatible]
- URL after ticking a single value (paste it):
https://cubitts.com/collections/spectacles?filter.p.m.custom.shape=Square
## On a product page
- Price shown: yes  Currency: euros
- Colours: swatches / names / codes. One example, copied exactly: ?variant=56863724437885
Dalmeny
£175
with ZEISS prescription lenses
Sharp as a blade. Straight as an arrow. Blade temple design was originally made for helmets, the military and the sporting. Dalmeny’s blade sides, however, demand neither headgear nor athletic prowess (should you possess neither). A striking silhouette with futuristic flair that wraps pleasingly around the head, like the warm embrace of a loved one.

Read less

Details
Premium Mazzucchelli cellulose acetate
Pin-drilled signature Cubitts rivets
3/4 charniere hinges with Teflon coated screws
ZEISS ClearView Lenses, with DuraVision® coatings and UV protection
Ultra-strong grooved aluminium protective case
Refillable lens cleaner and Jim Moir designed cleaning cloth
Two-year warranty on frames and lenses, plus a 30-day no-quibble return
Complimentary frame rehab after a year
- Details listed (shape, material, gender, lens ...): one example, copied exactly: 
- Badges (best-seller, new, sold out) and where they appear:
doesn not show, only way to know a product is bestseller is it appears in sorted list  by it
## Anything else

## Status
- **Crawler config written** (Step 16, `docs/phase2-step16-cubitts-plan.md`), tested offline. **Not yet crawled**: `python -m app.cli crawl-store cubitts.com`
  (about 12 minutes, about 200 MB) from a terminal, then `retag-products`.

## Checks (Claude, 2026-09-30, in the browser: about 20 page views, 1.5 s apart)
- **Currency is GBP, not euros**: the product page shows `£175` and its structured data says `GBP`.
- **Paging is plain server pages.** The "infinite scroll" only loads the same `?page=N` pages, and each carries `<link rel="next">`:
  optical is 6 pages (20 + 20 + 20 + 20 + 20 + 17 = **117**), sun is 7 pages (**132**), about 1.3 MB per page. Cards are `.product-card`, links
  `a.product-card__link`, so a normal crawler follows `rel=next`.
- **Filter parameters** (product level, one value per request, spaces as `%20`): `filter.p.m.custom.shape` (Square, Round, Oval, Cat-eye,
  Aviator), `filter.p.m.custom.material` (Acetate, Steel, Titanium, Combination), `filter.p.m.custom.thickness`, `filter.p.m.custom.bridge_fit`.
  Colour and size are variant filters (`filter.v.option.colour`, `filter.v.option.size`) with 16 and 5 grouped values; not needed, the colours are on the product page.
- **Best-sellers cannot come from the "Bestsellers" sort:** it is `filter.p.m.custom.sort_by=Bestsellers`, and robots.txt forbids any collection URL
  containing `sort_by` (the rule `/collections/*sort_by*` matches it). But **`/collections/bestselling-glasses` is a plain collection**: 16 frames, one page.
  Listing it and flagging those frames is allowed. (The same goes for "New in": we date arrivals ourselves from the crawls.)
- **Colours are plain names**: on the product page `input[name="Colour"]` has values such as `Khaki`, `Black`, `Slate`, `Dark Turtle`, `Haze`.
- **A variant is size / colour / prescription** (`M|Medium / Khaki / Prescription`, SKU `DAL-OPT-R-KHA-RX`): Dalmeny has 20 variants, 5 colours. Sizes and
  prescription are options of one product, not separate products, so no "one product per model" rule is needed here.
- **JSON-LD offers carry price and stock per variant but no SKU or colour field**; the colour is inside the offer name, the SKU is in Shopify's
  analytics data. Simplest reliable source: the colour swatch inputs, with the colour name as the code.
- **Details are marketing bullets** ("Premium Mazzucchelli cellulose acetate"), not a table; shape and material come from the filters.
- **Not settled:** the market to track (UK, GBP: a European brand catalog, fine) and whether the frames' fit options (bridge fit) matter.
