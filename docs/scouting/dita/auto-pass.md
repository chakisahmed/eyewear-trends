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

## Second look, from Ahmed's notes (2026-09-30)

- **The first pass tried a collection page as a product page** (it picked `/en-tn/collections/mens-optical`); the real product page is `/en-tn/products/<slug>`.
- **Locale changes the price:** Evercharm is $834.75 on `/en-tn`, $795 on `/en-gb` and `/en-fr`; no `/en-us` (the US store is the root). The prefix is part of each product's URL, so it must be chosen before the first crawl.
- **Paging** is an `<a rel="next">` anchor (3 pages, 40 per page, 81 frames); cards are `<product-item>`.
- **Filters:** `filter.v.m.vdp.frame_shape` and `filter.v.m.vdp.frame_composition` (including the site's typo "Titanuim"), one at a time; the URL in the notes uses `sort_by` and a price range, both forbidden.
- **Product data:** JSON-LD offers give the SKU, price and stock per colourway; the colour name is `Frame - Finish / Lens`, so the frame colour needs a two-level split (" / " then " - ").

## Verdict: Promising

- **What the pages show:** the third Etnia-class Shopify brand: server pages, `rel=next`, one-at-a-time shape and material filters, SKU, price and stock per colourway in structured data, colour names of the form `Frame - Finish / Lens`.
- **Next:** decide the locale (`/en-tn` as in the notes, or a neutral `/en-fr` or `/en-gb`); then the config: a nested colour split (a small generic addition) and shape aliases (Polyangular, Navigator, Diamond) from the first crawl's report.
