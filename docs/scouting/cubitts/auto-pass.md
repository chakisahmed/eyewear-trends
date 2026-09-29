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

## Verdict: Promising

- **What the pages show:** Shopify, GBP prices. Frames are in the served HTML (about 117 spectacles, 2 listing pages, `rel=next`). Product page has JSON-LD `Product` with price, colour swatches (25 variant elements, labels like `Amber`) and a Shopify variants blob.

- **Next:** Fill `notes.md`; check the colour swatch labels on one saved product page. Likely the closest match to Etnia's setup.
