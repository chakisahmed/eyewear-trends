# Cubitts: automated first pass

Site: <https://cubitts.com/>  ·  2026-09-29  ·  **Verdict: Promising**

- **robots.txt:** 63 rules for us. Notable: `Allow: /`, `Allow: /*/products/account`, `Allow: /*/products/orders`, `Allow: /*/products/checkout`, `Allow: /*/collections/account`, `Allow: /*/collections/orders`, `Allow: /*/collections/checkout`, `Allow: /*/pages/checkout`, `Allow: /blogs/*account`, `Allow: /blogs/*orders`, `Allow: /blogs/*checkout`, `Allow: /*/blogs/*account` Sitemaps: 1.

- **Homepage:** https://cubitts.com/ (477 KB). Platform hints: shopify.

- **Listing candidates from the homepage menu:** [spectacles](https://cubitts.com/collections/spectacles), [Bespoke frames](https://cubitts.com/pages/made-to-measure-and-bespoke), [Bestsellers](https://cubitts.com/collections/bestselling-glasses), [Sunglasses](https://cubitts.com/collections/sunglasses), [Brydon](https://cubitts.com/products/brydon-sunglass), [Shop](https://cubitts.com/collections/shop-all), [Lens replacements](https://cubitts.com/products/lens-replacement-service), [Frame services](https://cubitts.com/collections/services)

- **Listing** https://cubitts.com/collections/spectacles (755 KB): 0 product-like links in the served HTML; JSON-LD types: none.

- **Paging:** `rel=next` -> https://cubitts.com/collections/spectacles?page=2; page numbers up to 2. Count text: 117 items.

- **Product page:** none tried: the listing has no product links in the served HTML, so the frames are probably built by script.

## Second look (targeted)

- Frame links in the served listing: 20 distinct (pattern `^/products/`), e.g. https://cubitts.com/products/laystall, https://cubitts.com/products/coley.

- Product page https://cubitts.com/products/laystall: JSON-LD Product name='Laystall' price=175.0 GBP color=None material=None sku=None; detail words: color, colour, frame, lens, shape, size; swatch/variant-like elements: 25; price visible; first swatch labels: ['Amber']; Shopify variants blob in the page.

## Second look, from Ahmed's notes (2026-09-30)

- **Paging corrected:** 6 pages for the 117 spectacles and 7 for the 132 sunglasses (the first pass had seen only two page numbers), all plain `?page=N`
  with `rel=next`, about 1.3 MB each. What looks like infinite scroll is the same pages loaded by script.
- **Colours and variants:** colour swatches are `input[name="Colour"]` with plain names; a variant is size / colour / prescription (Dalmeny: 20 variants,
  5 colours). Price is GBP (`£175`), the notes' "euros" is a slip.
- **Best-sellers:** the sort filter is `filter.p.m.custom.sort_by`, forbidden by robots.txt; the plain collection `/collections/bestselling-glasses`
  (16 frames) is allowed and would flag them.
- **Filters worth using:** shape (5 values) and material (4); one at a time.

## Verdict: Promising

- **What the pages show:** the second Etnia-class brand after Barton Perreira: Shopify, UK store in GBP, server-rendered pages with `rel=next`, product-level
  shape and material filters, plain colour names, and a plain best-sellers collection.
- **Next:** write the config (two collections, shape and material passes, colour swatches as variants, a best-sellers listing flag, name aliases for
  the colours). One small generic addition is needed: a listing URL that only flags its products. Nothing about sizes.
