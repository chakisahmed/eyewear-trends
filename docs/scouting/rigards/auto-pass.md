# Rigards: automated first pass

Site: <https://www.rigards.com/>  ·  2026-09-29  ·  **Verdict: Medium**

- **robots.txt:** 63 rules for us. Notable: `Allow: /`, `Allow: /*/products/account`, `Allow: /*/products/orders`, `Allow: /*/products/checkout`, `Allow: /*/collections/account`, `Allow: /*/collections/orders`, `Allow: /*/collections/checkout`, `Allow: /*/pages/checkout`, `Allow: /blogs/*account`, `Allow: /blogs/*orders`, `Allow: /blogs/*checkout`, `Allow: /*/blogs/*account` Sitemaps: 1.

- **Homepage:** https://www.rigards.com/ (98 KB). Platform hints: shopify.

- **Listing candidates from the homepage menu:** [NATURAL MATERIALS](https://www.rigards.com/pages/collection)

- **Listing** https://www.rigards.com/pages/collection (99 KB): 0 product-like links in the served HTML (path prefix `/pages`); JSON-LD types: none.

- **Paging:** no paging signal found (single page, or loaded by script).

- **Product page:** none tried: the listing has no product links in the served HTML, so the frames are probably built by script.

## Second look (targeted)

- `/collections/all` (101 KB, final URL https://www.rigards.com/collections/all): 0 frame links in the served HTML, e.g. []; paging: no rel=next.

## Second look (2026-09-30, from the submenu screenshot and browser checks): no catalog published

- The six "Natural materials" entries are story pages with no frames; the 9 collections in the sitemap are all empty, and there is no products sitemap. The shop publishes no product.

## Verdict: Medium, revised to **Nothing to crawl** (see the second look)

- **What the pages show:** Shopify. The menu's only collection link is a story page ("Natural materials"), and `/collections/all` serves no frame links (101 KB page). Probably a small catalog shown through page-builder sections or script.

- **Next:** A saved page of wherever the frames are listed, and View Source check for a frame name.
