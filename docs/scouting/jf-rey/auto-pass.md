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

## Verdict: Promising

- **What the pages show:** WordPress (the English site is `www.jfrey.fr/en/`). Catalog pages by range (`catalog-men-en`, `catalog-women-en`, sun): the men's page alone serves 63 frame links (`/en/<model code>/`) on one page. **No price and no JSON-LD**: presence-only, like Morel. Product pages mention colour and material in text.

- **Next:** A saved frame page: how are colours and materials written? Confirm all frames sit on one page per range.
