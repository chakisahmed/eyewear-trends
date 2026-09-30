# Kuboraum: automated first pass

Site: <https://www.kuboraum.com/>  ·  2026-09-29  ·  **Verdict: Medium**

- **robots.txt:** 1 rules for us. Nothing that restricts catalog pages. Sitemaps: 1.

- **Homepage:** https://www.kuboraum.com/ (35 KB). Platform hints: wordpress.

- **Listing candidates from the homepage menu:** [OPTICAL MASK](https://www.kuboraum.com/collections/optical-mask/), [SUN MASK](https://www.kuboraum.com/collections/sun-mask/), [KUBORAUM X HAMBURGER BAHNHOF](https://www.kuboraum.com/collections/kuboraum-x-hamburger-bahnhof/), [ACETATE](https://www.kuboraum.com/collections/acetate/), [METAL](https://www.kuboraum.com/collections/metal/)

- **Listing** https://www.kuboraum.com/collections/optical-mask/ (1035 KB): 0 product-like links in the served HTML (path prefix `/masks/d71-violet-petal`); JSON-LD types: {'Organization': 1, 'ImageObject': 2, 'WebSite': 1, 'SearchAction': 1, 'PropertyValueSpecification': 1, 'EntryPoint': 1, 'BreadcrumbList': 1, 'ListItem': 2, 'CollectionPage': 1}.

- **Paging:** no paging signal found (single page, or loaded by script).

- **Product page:** none tried: the listing has no product links in the served HTML, so the frames are probably built by script.

## Second look (targeted)

- Frame links in the served listing: 473 distinct (pattern `^/masks/[^/]+/?$`), e.g. https://www.kuboraum.com/masks/d71-violet-petal/, https://www.kuboraum.com/masks/d71-rain-forest/.

- Product page https://www.kuboraum.com/masks/d71-violet-petal/: no JSON-LD Product; detail words: color, lens, material, rim, size; swatch/variant-like elements: 0; no price text.

## Second look (2026-09-30, from Ahmed's notes and browser checks)

- **Counts:** 473 optical cards and 363 sun cards, 137 of them in both: **699 distinct model-colour pages**. Everything is in one page per collection (no paging, filters are client-side model codes).
- **Product page:** labelled lines for material, colour, temple colour, lens, bridge, lens width and temple length; **no price, no shape, no gender, no badges, no JSON-LD**.

## Verdict: Medium (presence, colour, material and sizes; no price or shape)

- **What the pages show:** WordPress. The optical collection serves 473 links in one 1 MB page (`/masks/<model>-<colour>/`, one per colour, so colour is in the URL and name). **No price, no JSON-LD**: presence-only. Small robots.txt, nothing restrictive.

- **Next:** A saved product page and a look at how colour and rim type are written; decide whether model-colour pages or models are the unit.
