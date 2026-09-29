# Alain Mikli: automated first pass

Site: <https://www.alainmikli.com/>  ·  2026-09-29  ·  **Verdict: Hard (low value: a showcase, not a catalog)**

- **robots.txt:** 63 rules for us. Notable: `Allow: /`, `Allow: /*/products/account`, `Allow: /*/products/orders`, `Allow: /*/products/checkout`, `Allow: /*/collections/account`, `Allow: /*/collections/orders`, `Allow: /*/collections/checkout`, `Allow: /*/pages/checkout`, `Allow: /blogs/*account`, `Allow: /blogs/*orders`, `Allow: /blogs/*checkout`, `Allow: /*/blogs/*account` Sitemaps: 1.

- **Homepage:** https://www.alainmikli.com/ (373 KB). Platform hints: shopify.

- **Listing candidates from the homepage menu:** [Products](https://www.alainmikli.com/collections/alain-mikli-red)

- **Listing** https://www.alainmikli.com/collections/alain-mikli-red (657 KB): 0 product-like links in the served HTML; JSON-LD types: none.

- **Paging:** no paging signal found (single page, or loaded by script).

- **Product page:** none tried: the listing has no product links in the served HTML, so the frames are probably built by script.

## Second look (targeted)

- `/collections/all` (656 KB, final URL https://www.alainmikli.com/collections/all): 0 frame links in the served HTML, e.g. []; paging: no rel=next.

## Second look, from Ahmed's notes (2026-09-29)

- **The real page is the locale one:** `/fr/collections/alain-mikli-red` (the first pass used the non-locale URL). It answers 200 and
  is allowed by robots.txt. It is the only gallery of frames on the site, with no paging and no filters.
- **What the served HTML holds:** no frame links as anchors, but Shopify's embedded product data lists **12 frames** (model codes
  such as `0A03553`, `0A05520`; vendor "Alain Mikli"; type "Eyewear") with the price set to **0.0** (hidden: price on request) and
  a product URL of the form `/fr/products/alain-mikli-<code>`. Image file names carry the model and a **colour code**
  (`0A03553__0486__P21`; four distinct codes here: `0001`, `0002`, `0002S4`, `0486`), but there is no legend for them and no colour name on the page.
- **Data quality:** the product text is unreliable for our tagger. Ahmed's example: `0A03553` shows a plain red frame while its
  description talks about "le rouge et le noir nacré iconiques". Colours would have to come from the images (image
  classification, a later phase), not from the text.

## Verdict: Hard, low value

- **What the pages show:** a 12-frame showcase with no price, no colour names, no shape or material fields, and descriptions that
  contradict the images. Nothing for a text-based crawl to tag except the model code.
- **Next:** park it. Revisit only if the client supplies a catalog with its colour legend, or when image-based colour reading
  exists. A crawl would also need a new rule to read the embedded product blob, which is not worth building for 12 frames.
