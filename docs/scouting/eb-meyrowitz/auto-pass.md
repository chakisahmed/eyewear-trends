# E.B. Meyrowitz: automated first pass

Site: <https://ebmeyrowitz.com/>  ·  2026-09-29  ·  **Verdict: Promising**

- **robots.txt:** 63 rules for us. Notable: `Allow: /`, `Allow: /*/products/account`, `Allow: /*/products/orders`, `Allow: /*/products/checkout`, `Allow: /*/collections/account`, `Allow: /*/collections/orders`, `Allow: /*/collections/checkout`, `Allow: /*/pages/checkout`, `Allow: /blogs/*account`, `Allow: /blogs/*orders`, `Allow: /blogs/*checkout`, `Allow: /*/blogs/*account` Sitemaps: 1.

- **Homepage:** https://ebmeyrowitz.com/ (319 KB). Platform hints: shopify.

- **Listing candidates from the homepage menu:** [SPECTACLES](https://ebmeyrowitz.com/collections/spectacles), [SUNGLASSES](https://ebmeyrowitz.com/collections/sunglasses), [ACCESSORIES](https://ebmeyrowitz.com/collections/accesories), [GIFT CARDS](https://ebmeyrowitz.com/collections/gift-cards), [VIEW ALL](https://ebmeyrowitz.com/collections/all)

- **Listing** https://ebmeyrowitz.com/collections/spectacles (319 KB): 12 product-like links in the served HTML (path prefix `/collections/spectacles/products`); JSON-LD types: none.

- **Paging:** `rel=next` -> https://ebmeyrowitz.com/collections/spectacles?page=2; page numbers up to 6.

- **Product page** https://ebmeyrowitz.com/collections/spectacles/products/the-aldwych-in-black: no JSON-LD Product; detail words on the page: color, colour, form, frame, shape, size; swatch-like elements: 0; price visible; cart button.

## Second look (2026-09-30, the client's notes were still blank)

- **Counts:** 65 spectacles (6 pages) and 58 sunglasses (5 pages), no filters. Each colourway is its own product: the 123 products are about **35 models**, 20 of them in several colours.
- **Colour is in the name** ("The Grosvenor in Olive"): 37 distinct colours, 15 already match a colour family, 22 are marketing names (Bonfire, Jello, Demi Blonde, Saffron...).
- **Price** is in the markup (`£1,250.00`), no JSON-LD and no SKU. **No shape, material or gender** anywhere.
- **Badges:** Special Edition 16, Limited Release 6, New 6.

## Verdict: Promising, small (colour and price only)

- **What the pages show:** an easy Shopify catalog: `rel=next` paging, price and colour readable from the markup with the crawler's existing features (one variant per product from the name, price from the page,
  no new generic code). About 4 minutes and 40 MB. But **only colour and price** come out: no shape, material or audience.
- **Next:** worth doing after the brands with shape and material data. One thing to decide: a colourway product counts as a frame, so the shelf shows 123 references for about 35 models (the Tunisian retailers
  list colourways as separate products too). The Colours switcher would allow a model-level catalog, at the cost of more machinery and no colour for single-colour models.
