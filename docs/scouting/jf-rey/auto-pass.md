# J.F. Rey: automated first pass

Site: <https://www.jfrey.fr/en/>  ·  2026-09-29  ·  **Verdict: Promising**

- **robots.txt:** 0 rules for us. Nothing that restricts catalog pages.

- **Homepage:** https://www.jfrey.fr/en/ (480 KB). Platform hints: woocommerce, wordpress.

- **Listing candidates from the homepage menu:** [GLASSES](https://www.jfrey.fr/en/), [Men’s Glasses](https://www.jfrey.fr/en/catalog-men-en/), [Women’s Glasses](https://www.jfrey.fr/en/catalog-women-en/), [SUNGLASSES](https://www.jfrey.fr/en/womens-sun-catalog-2/), [SUNGLASSES](https://www.jfrey.fr/en/collection-solaire/), [SLEDGE](https://www.jfrey.fr/en/sledge-collection/), [SATURN](https://www.jfrey.fr/en/saturn-collection/), [PRISMA](https://www.jfrey.fr/en/prisma_collection/)

- **Listing** https://www.jfrey.fr/en/ (480 KB): 0 product-like links in the served HTML (path prefix `/en/sledge-collection`); JSON-LD types: {'Organization': 1, 'ImageObject': 2, 'WebSite': 1, 'SearchAction': 1, 'PropertyValueSpecification': 1, 'EntryPoint': 1, 'BreadcrumbList': 1, 'ListItem': 1, 'WebPage': 1, 'ReadAction': 1}.

- **Paging:** a 'load more' control.

- **Product page:** none tried: the listing has no product links in the served HTML, so the frames are probably built by script.

## Second look (targeted)

- Catalog page https://www.jfrey.fr/en/catalog-men-en/ (995 KB): 63 frame links in the served HTML (pattern `/en/<model code>/`), e.g. ['https://www.jfrey.fr/en/jf3157/', 'https://www.jfrey.fr/en/jf3156/']; paging: no signal.

- Frame page https://www.jfrey.fr/en/jf3157/: no JSON-LD Product; detail words: color, frame, lens, material, size; swatch/variant-like elements: 0; no price text.

## Second look, from Ahmed's notes (2026-09-30)

- **robots.txt asks for `Crawl-delay: 10`** (10 s between requests): honoured, so a crawl runs at `delay_s: 10`, about 35 minutes for a couple of hundred models.
- **Every model is already in the served HTML** (63 men's models on `/en/catalog-men-en/`); "View more styles" only reveals rows, it fetches nothing. Women's, kids' and sun pages work the same way.
- **Colours are opaque codes** (`JF3157 - 9955`, `COL. 0029`): 273 codes for the 63 men's models, no colour names anywhere, so no colour family can be tagged.
- **The model page** has the name (`og:title`), the size, the colour codes and a free-text design paragraph and feature list (material and shape are only in that text). **No price, no JSON-LD, no filters.**

## Verdict: Medium (presence-only, low value)

- **What the pages show:** a large, easy-to-read catalog (about 60 models per range, several colourways each) with **no price, no colour names, no structured data**. Audience and type come from which
  catalog page a model is on (except sun, which mixes men and women); material and shape only from a marketing paragraph.
- **Next:** park it unless the client wants French independent brands for presence, or supplies the colour-code legend. If pursued: config at `delay_s: 10`, and one small new tagger feature (read the design paragraph for
  shape and material only, never colour).
