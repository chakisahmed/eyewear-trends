# Barton Perreira: automated first pass

Site: <https://bartonperreira.com/>  ·  2026-09-29  ·  **Verdict: Promising**

- **robots.txt:** 63 rules for us. Notable: `Allow: /`, `Allow: /*/products/account`, `Allow: /*/products/orders`, `Allow: /*/products/checkout`, `Allow: /*/collections/account`, `Allow: /*/collections/orders`, `Allow: /*/collections/checkout`, `Allow: /*/pages/checkout`, `Allow: /blogs/*account`, `Allow: /blogs/*orders`, `Allow: /blogs/*checkout`, `Allow: /*/blogs/*account` Sitemaps: 1.

- **Homepage:** https://bartonperreira.com/ (285 KB). Platform hints: shopify, wix.

- **Listing candidates from the homepage menu:** [Optical](https://bartonperreira.com/collections/optical-collection), [Women](https://bartonperreira.com/collections/the-womens-optical-collection), [Men](https://bartonperreira.com/collections/the-mens-optical-collection), [Sun](https://bartonperreira.com/collections/sunglass-collection), [Women](https://bartonperreira.com/collections/the-womens-sun-collection), [Summer 2026](https://bartonperreira.com/collections/summer-2026), [Collaborations](https://bartonperreira.com/collections/special-collaborations), [lamarr](https://bartonperreira.com/products/lamarr)

- **Listing** https://bartonperreira.com/collections/optical-collection (9442 KB): 55 product-like links in the served HTML (path prefix `/products`); JSON-LD types: {'BreadcrumbList': 1, 'ListItem': 2, 'Organization': 1}.

- **Paging:** `rel=next` -> https://bartonperreira.com/collections/optical-collection?page=2; page numbers up to 3. Count text: 116 products.

- **Product page** https://bartonperreira.com/products/banks-48: JSON-LD Product: name='Banks (48)', brand='Barton Perreira', price=530.0, currency=USD, color=None, material=None, sku='BANK4801', variants=0; detail words on the page: color, form, frame, material, shape, size; swatch-like elements: 18; price visible; cart button.

## Second look, from Ahmed's notes (2026-09-29)

Checked in the browser on the Euclid (optical) and Lamarr (sun) product pages and the sun collection; the filter and `robots.txt` findings
are from the saved optical page and `robots.txt`.

- **The filter URL in the notes is not usable as written.** `robots.txt` forbids `sort_by`, forbids two `filter` parameters in one URL
  (`/collections/*filter*&*filter*`) and a `+` in the path. Allowed: **one filter, no `sort_by`, spaces as `%20`**. Facets, identical on optical
  and sun: shape (Aviator, Butterfly, Cat Eye, **Cateye**, Hexagonal, Rectangle, Round, Square) and material (Acetate, Mixed Materials,
  Titanium). "Cat Eye" and "Cateye" are two values for one shape.
- **Sun collection:** 122 products, 54 links per page, `rel=next`, 3 pages; same structure as the optical one.
- **Product data is exactly what a variants reader needs:** the JSON-LD `Product` has one `Offer` per colourway with `name` (the colour
  string), `sku` (`EUCLAF5301`), `price` (670), `priceCurrency` (USD) and `availability` (per colourway), and Shopify's analytics blob lists
  the same variants (`public_title`, `sku`). So the colour, the supplier code (Palier 3) and stock come from the page, with no decoding.
- **Colour strings are compound: front / lens / temples / metal finish.** Optical Euclid: `Hickory Gradient / Clear / Hickory Gradient / Pewter`.
  Sun Lamarr: `Heroine Chic / Smolder (AR)` (frame / lens colour). The first part is the frame colour.
- **Colour names are marketing names**: `Heroine Chic`, `Smolder`, `Coy`, `Julep`, `Matte Dusk`, `Hickory Gradient`, `Absinthe` next to plain
  ones (`Black`, `Chestnut`, `Champagne`, `Pewter`, `Antique Gold`, `Acacia Tortoise`, `Espresso`). Only part of them match our colour
  families today; the rest need a Barton Perreira alias list, which is small work (a page's worth), like the Morel aliases.
- **Details:** frame material (`Zyl`), lens material, eye size, bridge, temple length are listed. Shape comes from the facet, and the title.
- **Cost of a crawl:** the listing pages are large (9.4 MB for the optical page 1, because every variant is embedded); about 3 pages per
  collection plus one page per facet value. Heavy but polite at one request every 1.5 s.
- **Open question:** a size may be its own product (`Banks (48)`), so the same model could count more than once. To check on a saved list.

## Verdict: Promising

- **What the pages show:** the closest match to Etnia so far: Shopify, US store, price in USD, per-colourway SKU and stock in structured
  data, shape and material facets, plain `rel=next` paging.
- **Next:** (1) confirm the size-per-product question; (2) read the terms of use; (3) I write the config: two collections, single-filter
  facet passes for shape and material, a variants reader on the structured data, a colour alias list; offline tests as for Morel.
