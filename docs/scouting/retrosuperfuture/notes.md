# Retrosuperfuture (RSF): scouting notes

Site: https://retrosuperfuture.com   Scouted by: Ahmed & Antigravity   Date: 2026-10-03

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: no (robots.txt explicitly allows public storefront, products, collections; standard Shopify terms)

## Where the frames are
- Optical collection URL:
  - In-stock core RSF: `https://retrosuperfuture.com/collections/all?filter.v.availability=1&filter.p.vendor=RETROSUPERFUTURE&filter.p.product_type=Eyewear&filter.p.m.rsf.category=Optical` (13 pages, ~310 frames)
  - All in-stock optical (including MM6, Marni, 8000): `https://retrosuperfuture.com/collections/all?filter.v.availability=1&filter.p.product_type=Eyewear&filter.p.m.rsf.category=Optical` (22 pages, ~528 frames)
  - Shapes gallery: `https://retrosuperfuture.com/collections/rsf-shape-optical` (56 optical shapes)

- Sun collection URL:
  - In-stock core RSF: `https://retrosuperfuture.com/collections/all?filter.v.availability=1&filter.p.vendor=RETROSUPERFUTURE&filter.p.product_type=Eyewear&filter.p.m.rsf.category=Sunglass` (19 pages, ~455 frames)
  - All in-stock sunglasses (including MM6, Marni, 8000): `https://retrosuperfuture.com/collections/all?filter.v.availability=1&filter.p.product_type=Eyewear&filter.p.m.rsf.category=Sunglass` (35 pages, ~840 frames)
  - Shapes gallery: `https://retrosuperfuture.com/collections/rsf-shape-sun` (68 sun shapes), `https://retrosuperfuture.com/collections/rsf-belli-shapes` (98 shapes)
  - Collaborations: `https://retrosuperfuture.com/collections/mm6-shapes`, `https://retrosuperfuture.com/pages/marni`, `https://retrosuperfuture.com/pages/8000`

- Roughly how many frames (optical / sun):
  - In-stock core RSF brand: ~310 optical + ~455 sun = ~765 products (32 pages total).
  - All in-stock eyewear (RSF + MM6 + Marni + 8000): ~528 optical + ~840 sun = ~1,368 products (57 pages total).
- Frames per page, and how paging works:
  - 24 frames per page.
  - Pagination works natively with query param `?page=2`, `?page=3` (or following next link `nav.rsf-plp-pagination a:last-of-type`).
- Frame names show in View Source (Ctrl+U):
  - YES! In `p.rsf-card-product__title` (e.g. `<p class="rsf-card-product__title">Caro Refined</p>`) and `img.rsf-card-product__slide-img[alt]` (e.g. `alt="Caro Refined - Retrosuperfuture -"`).
  - Note: The reason frame names were not found initially on `rsf-belli-shapes` was because that page is a gallery of Shape families (linking to `/collections/caro-rsf-sun`), whereas PLP collection pages (`/collections/all?...`) render individual colorway product cards.

## Which version of the site
- Country or language to track: IT / EUR (Milan, Italy, English UI, prices in EUR).
- Platform: Shopify (Online Store 2.0 with custom RSF theme).

## One filter at a time
- Filters offered (Shopify faceted navigation parameters):
  - Availability: `filter.v.availability=1` (In stock) / `filter.v.availability=0`
  - Category: `filter.p.m.rsf.category=Sunglass` / `filter.p.m.rsf.category=Optical`
  - Vendor: `filter.p.vendor=RETROSUPERFUTURE` / `MARNI` / `MM6` / `8000` / `BRIKO` / `DIESEL`
  - Product Type: `filter.p.product_type=Eyewear` / `Accessory` / `Apparel & Accessories`
  - Shape: `filter.p.m.rsf.shape=Round` / `Square` / `Cat Eye` / `Aviator` / `Mask`
  - Material: `filter.p.m.rsf.material=Acetate` / `Metal` / `Combined` / `Tuttolente` / `Injection`
  - Style: `filter.p.m.rsf.style=Essential` / `Signature` / `Studio` / `Special`
- URL after ticking a single value:
  - `https://retrosuperfuture.com/collections/all?filter.p.product_type=Eyewear&filter.p.m.rsf.category=Sunglass`
  - `https://retrosuperfuture.com/collections/all?filter.p.m.rsf.material=Acetate`

## On a product page / listing card
- Architecture: Zero-Product-Page capable! Every listing card contains:
  - Canonical link: `a.rsf-card-product__link` with `url_regex: '(/products/[^/?#]+)'`
  - Name: `p.rsf-card-product__title` (e.g. "Caro Refined", "Flat Top Black", "Carino Canarino")
  - Price: `span.rsf-card-product__price` (e.g. "189EUR", "199EUR")
  - Image: `img.rsf-card-product__slide-img` (`src` and `data-src`)
  - Material: Class attribute `rsf-card-product--material-acetate`
  - Description: `img.rsf-card-product__slide-img[alt]`
- Price shown: yes. Currency: EUR.
- Colours:
  - Card title contains Model Name + Color Name (e.g. "Carino Canarino", "America Black", "Caro Azure", "Cocca Panna").
  - On product detail page: Product code (e.g. `Product Code Size R: NVA`), lens width (e.g. `54 mm`), size (e.g. `R (54)`).
- Details listed:
  - Material in card class: `rsf-card-product--material-acetate`, `rsf-card-product--material-metal`, `rsf-card-product--material-combined`.
  - PDP description: "Designed for FW19 collection, Caro is a wide, geometric silhouette that blends 1960s Italian classicism with 1990s grunge aesthetic... thick, sturdy acetate structure... Lens Width: 52 mm, Frame Side: 145 mm, Product Code: NVA".
- Badges:
  - Sold out: `a.rsf-card-product__chip--tl[data-rsf-find-stockist]` ("Sold out · Find a stockist")
  - In stock: `button.rsf-card-product__chip--br[data-rsf-cart-add]`
  - Best sellers: Curated collection at `/collections/best-seller-in-stock`

## Strategy for Crawler
1. **Zero-Product-Page Crawling**: Scrape listing pages directly.
2. **Collection URLs**:
   - In-stock core RSF sunglasses: `/collections/all?filter.v.availability=1&filter.p.vendor=RETROSUPERFUTURE&filter.p.product_type=Eyewear&filter.p.m.rsf.category=Sunglass` (category: Solaire, 19 pages)
   - In-stock core RSF optical: `/collections/all?filter.v.availability=1&filter.p.vendor=RETROSUPERFUTURE&filter.p.product_type=Eyewear&filter.p.m.rsf.category=Optical` (category: Optique, 13 pages)
   - Best-sellers enrichment: `/collections/best-seller-in-stock` (flag: is_bestseller)
3. **Selectors**:
   - `product`: `li.rsf-card-product`
   - `link`: `a.rsf-card-product__link`
   - `name`: `p.rsf-card-product__title`
   - `price`: `span.rsf-card-product__price`
   - `image_url`: `img.rsf-card-product__slide-img`
   - `flags.material`: `{ css: ".rsf-card-product", attr: "class", regex: 'rsf-card-product--material-([a-z]+)' }`
   - `flags.out_of_stock`: `{ css: "a[data-rsf-find-stockist]", exists: true }`
   - `flags.description`: `{ css: "img.rsf-card-product__slide-img", attr: "alt" }`
4. **Pagination**:
   - `pagination: { param: page, max_pages: 20 }`

## Crawl Results
- Live crawl executed: 2026-10-02
- Status: 760 products crawled, 760 inserted, 0 dropped, 302 best-sellers flagged
- Offline test suite: 448 tests passing (100% green)
- Taxonomy retagged: RULES_VERSION = 24 (461 acetate, 368 color, 760 product_type)
