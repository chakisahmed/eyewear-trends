# Silhouette: automated first pass

Site: <https://www.silhouette.com/>  ·  2026-09-29  ·  **Verdict: Medium**

- **robots.txt:** 1 rules for us. Nothing that restricts catalog pages. Sitemaps: 1.

- **Homepage:** https://www.silhouette.com/ (347 KB). Platform hints: none recognised.

- **Listing candidates from the homepage menu:** none found (menu may be built by JavaScript).

- **Listing:** no collection link found in the served HTML.

## Second look (targeted)

- Homepage (347 KB) markers: none recognised; anchors in served HTML: 98.

- Sitemap https://www.silhouette.com/sitemap.xml: 155 entries, e.g. ['https://www.silhouette.com/sitemap/de/pages.xml', 'https://www.silhouette.com/sitemap/de-AT/pages.xml', 'https://www.silhouette.com/sitemap/de-AT/sunglasses.xml'].

- Sub-sitemap https://www.silhouette.com/sitemap/de-AT/sunglasses.xml: 171 URLs, e.g. ['https://www.silhouette.com/at/de/sonnenbrillen/avior/8741/7210', 'https://www.silhouette.com/at/de/sonnenbrillen/dora-four/4093/9100', 'https://www.silhouette.com/at/de/sonnenbrillen/avior/8741/6040'].

## Verdict: Medium

- **What the pages show:** Custom platform (no recognised shop system) and no frame links in the served menu. But its **sitemaps list every product URL per locale** (for example 171 sunglasses in `de-AT`, shaped `/at/de/sonnenbrillen/<model>/<code>/<colour code>`).

- **Next:** A saved product page: is it complete in the served HTML? Choose the locale (`/gb/en/`?). A sitemap-driven crawl would be a new mode for our crawler.
