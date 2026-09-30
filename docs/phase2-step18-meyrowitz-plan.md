# Step 18: E.B. Meyrowitz, the sixth creator brand (UK, Shopify, GBP), colour, shape and price

Scouting: `docs/scouting/eb-meyrowitz/` (the checks are mine, 2026-09-30; your notes, filled in afterwards, showed the "Finer details" block I had missed). One small generic addition (a spec row without a value selector), one config entry, tagger v14 and tests.

## What the pages show
- Optical `/collections/spectacles` (65 products, 6 pages of 12) and sun `/collections/sunglasses` (58, 5 pages), `<link rel="next">` paging, about 320 KB a page. No product is in both. The filters are **tag paths**, not query parameters (`/collections/sunglasses/shape-rectangular`, `colour-olive`; optical shapes: ovular, rectangular, rounded): not used, the product page gives more.
- **Each colourway is its own product** ("The Grosvenor in Olive"): 123 products, **27 models**. Cards are `div.product-grid-item` with `h3.product-grid-item__heading a`; links are collection-scoped
  (`/collections/spectacles/products/x`), the canonical URL is `/products/x`.
- The card price says "From £1,250.00"; the page's `p.product-showcase__price` says `£1,250.00` (`£1,350.00` for sun). No JSON-LD, SKU, material or gender. Stock is not readable.
- **"Finer details"** on every product page (27 of 27 models, four `<p class="products-details__description"><span>Label</span> Value</p>` lines, the same on each colourway): **Build** = the frame's shape (Rectangular 8 models, Rounded 13, Soft Rectangular 4, Ovular 1, Teardrop 1), Top Line, Bridgework and Rim Structure (kept, not tagged: no taxonomy dimension).
- The colour is in the name (the page's hidden `h1`, present twice), after "in" (written "In" on some pages). Names with no family: 22 of 37 colours (see below).

## Decisions (yours, 2026-09-30: "go with your defaults")
1. **A colourway counts as a frame** (123 references for 27 models), not a model-level catalog from the "Colours:" switcher. The switcher can omit the current colour ("The New Yorker In Colour 8" lists six others but not itself),
   has typos ("Champagnee"), and single-colour models have none; the URL handle is not the model key either (9 of 123 handles disagree with the displayed name: "The Garrick in Dark Mottle" is at `...-in-black`).
2. **The full name as shown** ("The Grosvenor in Olive"), not the model name: ten cards named "The Grosvenor" would be indistinguishable.
3. **No stock, no badges** (Special Edition 16, Limited Release 6, New 6 could become a flag later).

## The entry (`store_configs.yaml`, `ebmeyrowitz.com`, `country: GB`)
`default_brand` and `default_currency: GBP`; both listings with `link[rel=next]`; `url_regex: '(/products/[^/?#]+)'`; name from the card link, price from the product page; variants from the hidden `h1`
with `code` and `label` = `(?i)\s+in\s+(.+)$` (the store's own colour name is the supplier code, as for Cubitts). `specs` reads the Finer details rows (`p.products-details__description`, key `span`, **no `value` selector**: the value is the row's text after the key, the new optional behaviour of `SpecsRule.value`). Tagger **v14**: the label "Build" is a shape; "Rounded" -> round and "Ovular" -> oval (Rectangular, Soft Rectangular and Teardrop -> aviator are taxonomy words). No facets, flag listings, `model_regex` or `name_strip`.
About 135 requests, 40 MB, about 4 minutes.

## Tests (`test_store_meyrowitz.py`, offline, MockTransport, the real robots rules)
Colourways as frames named as shown, prefix cut; page price in GBP (not the card's "From"); one variant per product and the switcher ignored; "In" with a capital and a handle that disagrees with the name;
colour tags agree (name and variant give one family) and no family for "Colour 8"; shape from Build (Rounded, Soft Rectangular, Ovular, Teardrop...), all four lines kept in raw_specs, no material or audience invented; a spec row without a value selector; tagger tests for Build; no filter, sort or `+` request; shipped-entry checks. Nine stores now ship.

## After the first live crawl
You run `python -m app.cli crawl-store ebmeyrowitz.com` then `retag-products` (after a DB backup). I read the result read-only: 123 frames, prices, colour coverage, the Tunisian shelf unchanged, and the colour names with no family
(Aqua, Atlantic, Barley, Bonfire, Cinnamon, Copper Mottle, Cyan, Dark Mottle, Demi Blonde, Desert Sun, Jade, Jello, Lava, Midnight, Moss, Ochre, Opal, Saffron, Savannah, Shadow, Sunburst, Sunshine) as proposed aliases for your approval (tagger v15).
