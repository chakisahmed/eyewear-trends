# Dita: automated first pass

Site: <https://dita.com/>  ·  2026-09-29  ·  **Verdict: Promising**

- **robots.txt:** 63 rules for us. Notable: `Allow: /`, `Allow: /*/products/account`, `Allow: /*/products/orders`, `Allow: /*/products/checkout`, `Allow: /*/collections/account`, `Allow: /*/collections/orders`, `Allow: /*/collections/checkout`, `Allow: /*/pages/checkout`, `Allow: /blogs/*account`, `Allow: /blogs/*orders`, `Allow: /blogs/*checkout`, `Allow: /*/blogs/*account` Sitemaps: 1.

- **Homepage:** https://dita.com/en-tn (593 KB). Platform hints: shopify.

- **Listing candidates from the homepage menu:** [Optical](https://dita.com/en-tn/collections/optical), [New Releases](https://dita.com/en-tn/collections/new-release-optical), [Best Sellers](https://dita.com/en-tn/collections/best-selling-optical), [Sunglasses](https://dita.com/en-tn/collections/sunglasses), [New Releases](https://dita.com/en-tn/collections/new-release-sunglasses), [Custom Lenses](https://dita.com/en-tn/collections/custom-lenses), [Custom Engraving](https://dita.com/en-tn/collections/custom-laser-engraving), [Limited Editions](https://dita.com/en-tn/collections/limited-editions)

- **Listing** https://dita.com/en-tn/collections/optical (1285 KB): 4 product-like links in the served HTML (path prefix `/en-tn/collections`); JSON-LD types: {'BreadcrumbList': 1, 'ListItem': 2, 'Organization': 1}.

- **Paging:** `rel=next` -> https://dita.com/en-tn/collections/optical?page=2; page numbers up to 3; a 'load more' control. Count text: 81 products.

- **Product page** https://dita.com/en-tn/collections/mens-optical: no JSON-LD Product; detail words on the page: color, form, frame, gender, lens, material, shape, size; swatch-like elements: 0; price visible; cart button.

## Second look (targeted)

- Frame links in the served listing: 40 distinct (pattern `^/en-tn/products/`), e.g. https://dita.com/en-tn/products/laurhyn, https://dita.com/en-tn/products/sahvana.

- Product page https://dita.com/en-tn/products/laurhyn: JSON-LD Product name='LAURHYN' price=624.75 USD color=None material=None sku='DTX204-A-01'; detail words: color, frame, lens, material, rim, shape, size; swatch/variant-like elements: 23; price visible; first swatch labels: ['White Gold', 'Silver', 'Smoked Pearl', 'White Gold']; Shopify variants blob in the page.

## Verdict: Promising

- **What the pages show:** Shopify. Frames are in the served HTML (80 product links on the optical page, about 81 frames, 3 pages, also a load-more control). JSON-LD `Product` with USD price and SKU; swatch labels like `White Gold`, `Silver`, `Smoked Pearl`. The site redirected us to the **Tunisian storefront (`/en-tn`)**.

- **Next:** Choose the locale to track (`/en-us` or a European one) and confirm the prices in it; then `notes.md`.
