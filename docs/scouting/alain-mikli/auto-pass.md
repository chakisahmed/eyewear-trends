# Alain Mikli: automated first pass

Site: <https://www.alainmikli.com/>  ·  2026-09-29  ·  **Verdict: Hard**

- **robots.txt:** 63 rules for us. Notable: `Allow: /`, `Allow: /*/products/account`, `Allow: /*/products/orders`, `Allow: /*/products/checkout`, `Allow: /*/collections/account`, `Allow: /*/collections/orders`, `Allow: /*/collections/checkout`, `Allow: /*/pages/checkout`, `Allow: /blogs/*account`, `Allow: /blogs/*orders`, `Allow: /blogs/*checkout`, `Allow: /*/blogs/*account` Sitemaps: 1.

- **Homepage:** https://www.alainmikli.com/ (373 KB). Platform hints: shopify.

- **Listing candidates from the homepage menu:** [Products](https://www.alainmikli.com/collections/alain-mikli-red)

- **Listing** https://www.alainmikli.com/collections/alain-mikli-red (657 KB): 0 product-like links in the served HTML; JSON-LD types: none.

- **Paging:** no paging signal found (single page, or loaded by script).

- **Product page:** none tried: the listing has no product links in the served HTML, so the frames are probably built by script.

## Second look (targeted)

- `/collections/all` (656 KB, final URL https://www.alainmikli.com/collections/all): 0 frame links in the served HTML, e.g. []; paging: no rel=next.

## Verdict: Hard

- **What the pages show:** Shopify, but the 656 KB collection pages contain **no product links at all** in the served HTML (`/collections/all` and the `alain-mikli-red` line): the grid is loaded by script, typically a filter or search app.

- **Next:** Only with a saved, fully loaded page and the client's help (a catalog export or feed); we do not fetch the app's own data endpoints.
