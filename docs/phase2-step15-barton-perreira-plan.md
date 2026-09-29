# Step 15: Barton Perreira, the third creator brand (USA, Shopify, with price)

## Context
Scouting (`docs/scouting/barton-perreira/`) found the closest match to Etnia so far: Shopify, US store in USD, about 116 optical and 122
sun products, `rel=next` paging, shape and material facets, and per-colourway SKU, price and stock in structured data. Nothing about the
crawler's design is new except three small things: reading variants from JSON-LD, splitting a compound colour name, and one product per
model when a model is sold as one product per size. Morel (Step 12) is the template for the workflow.

What the pages showed (verified in the browser and in the saved pages):
- Cards are `<product-item>` elements linking `/products/<slug>`; 54 per page; `<link rel="next">` gives `?page=2`, `?page=3`.
- Facets, same on both collections: `filter.v.m.filter.shape` (Aviator, Butterfly, Cat Eye, **Cateye**, Hexagonal, Rectangle, Round,
  Square) and `filter.v.m.filter.material` (Acetate, Mixed Materials, Titanium). robots.txt forbids `sort_by`, two `filter` parameters in
  one URL, and `+` in a path: the crawler already requests one filter, no sort, and `%20` for spaces.
- Product page: JSON-LD `Product` with **one `Offer` per colourway**: `name` (the colour string), `sku`, `price`, `priceCurrency`, per-colourway `availability`.
- Colour strings are compound, **front / lens / temples / metal finish**: optical Euclid `Absinthe / Clear / Chestnut / Antique Gold`; sun Lamarr
  `Heroine Chic / Smolder (AR)` (frame / lens). Names mix plain colours with marketing names.
- **Sizes are separate products for some models** (`norton-46` and `norton-48`, `cassady-47`, `-50`, `-53`, `princeton-46` and `-49`).
- Cost: a single-filter page is heavy (23 products = 4.5 MB, about 195 KB per product), so a crawl downloads roughly 150 MB. Acceptable
  weekly at one request every 1.5 s; noted in the config.

## 1. Generic additions (opt-in, other stores unchanged)
- **`VariantsRule.json_ld_offers: bool`** (`config.py`, `parser.py`): variants read from the product's JSON-LD offers instead of markup:
  `code` = `sku`, `color` = the offer `name`, `in_stock` from `availability`. `rows` and `code` become optional; the validator requires
  exactly one source (markup rows + code, or `json_ld_offers`). `parse_product_page` passes the matched raw JSON-LD node to a new pure
  `offer_variants(node, split)`. Price is read only through the existing price path (it is public here, unlike Morel's).
- **`VariantsRule.color_split: {sep: " / ", color: 0}`**: `variant["color"]` = that part of the compound name; when the name has more than one
  part, all parts are kept as `variant["parts"]` (front, lens, temples, finish) for later, **not tagged now**. Only the frame colour becomes a
  colour tag: feeding front and temples into `layers` would pollute the lamination combinations, which mean acetate layers (Etnia).
- **`ListingRule.model_regex`**: a regex with one group giving a product's model key (`^https://[^/]+/products/(.+?)(?:-\d{2})?$`). The crawler
  keeps the **first** product of each key in listing order and skips the later ones (`norton-48` after `norton-46`). Skipped products still
  count as listed (they are on the shelf, so nothing is ever dropped because of the skip) but are not fetched or stored. Effect: one frame per
  model, so a model with three sizes does not count three times in "Présence en boutique", pairings or best-sellers. Cost: the other sizes'
  colourways are not read (they are normally the same colours). This is the one design choice to confirm.

## 2. Store entry (`store_configs.yaml`, `barton-perreira` next to Morel)
```yaml
bartonperreira.com:
  name: "Barton Perreira"
  base_url: "https://bartonperreira.com"
  lang: en
  country: US            # a brand catalog, not the Tunisian market lens
  default_brand: "Barton Perreira"
  delay_s: 1.5
  listing:
    urls:
      - { url: "/collections/optical-collection", categories: "Optique" }
      - { url: "/collections/sunglass-collection", categories: "Solaire" }
    pagination: { next: "link[rel=next]", max_pages: 20 }      # 3 pages of 54 each
    product: "product-item"
    link: "a[href^='/products/']"
    model_regex: '^https://[^/]+/products/(.+?)(?:-\d{2})?$'
    facets:     # one filter per request, never sort_by (robots.txt); each pass downloads ~4 MB pages: ~150 MB per crawl
      - { name: "Shape", param: "filter.v.m.filter.shape" }
      - { name: "Materials", param: "filter.v.m.filter.material" }
  product_pages: { enabled: true, max_products: 400 }
  variants: { json_ld_offers: true, color_split: { sep: " / ", color: 0 } }
```
No `specs` rule (the page's "Frame Material - Zyl" line is unstructured; the material facet covers it), no best-seller filter exists.

## 3. Tagger rules v11 (`tagger.py`)
- `SPEC_ALIASES` (specs only, like the Almond and Ruthenium ones): `cateye` -> cat_eye ("Cat Eye" already matches; "Cateye" is a second facet value for the same shape).
- Variant colour aliases, only names that are unambiguous colours: `chestnut` and `espresso` -> brown. The marketing names (`Heroine Chic`, `Smolder`,
  `Coy`, `Julep`, `Matte Dusk`, `Hickory Gradient`, `Absinthe`, `Champagne`...) are **not guessed**: after the first crawl a report lists the
  front colours with no family and their frame counts, and the aliases are added from that list (as for Etnia and Morel), which you can veto.
- Everything else reuses what exists: `Shape` and `Materials` spec labels, variant colour tags with the SKU as Palier 3, `two_tone` not triggered.

## 4. Frontend and docs
- Country names (`RetailPresence.tsx`, `CatalogStatus.tsx`): add `US` ("États-Unis") so the "Présence en boutique" heading and the Sources panel name the market; also `GB` ("Royaume-Uni") for the next UK brands.
- `docs/build-plan.md` Step 15, `docs/scouting/barton-perreira/notes.md` (crawl status), a plan file `docs/phase2-step15-barton-perreira-plan.md`.

## 5. Tests (offline, markup trimmed from the real pages, MockTransport, the real robots.txt rules)
- **Generic:** `offer_variants` (sku, name, availability, price ignored for variants, missing or malformed JSON-LD gives `[]`), `color_split` (1, 2 and 4 parts, spaces, an empty part), the config validator (one source only), `model_regex` (first of a model kept, later sizes skipped but listed, models without a size suffix untouched, the `report.listed` keeps every product so nothing is dropped).
- **Barton fixtures:** optical and sun listings (`product-item` cards, `rel=next`), a page 2, the two filter forms with the duplicate "Cat Eye" and "Cateye", filtered pages, product pages (Euclid with four-part names, Lamarr with two-part names and `(AR)`, one out-of-stock colourway).
- **Assertions:** canonical `https://bartonperreira.com/products/euclid`; price 670 USD; brand "Barton Perreira"; SKUs kept verbatim as Palier 3; the front colour only becomes the colour (`Hickory Gradient / Clear / ...` is one colour tag, not "clear"); `parts` kept; a sold-out colourway is `in_stock: false` and a frame is out of stock only when every colourway is; shape `Cateye` and `Cat Eye` both give cat_eye; material from the facet; no request ever carries `sort_by`, `+`, or two `filter.` parameters; sizes of one model give one product; the report is complete.
- **Shipped config:** six stores, `US` for Barton, the suite stays green (364 today).

## Order of work
1. Generic additions and the Barton entry with tests (offline). Suite green. Commit (not pushed).
2. Rules v11, frontend country names, docs. Commit.
3. **You run** `python -m app.cli crawl-store bartonperreira.com` (about 20 minutes and about 150 MB), then `retag-products`.
4. I read the result read-only: coverage per facet, front colours with no family (the alias list to approve), sizes deduped, prices, a check that
   "Marché Tunisien" still lists only the three Tunisian stores. Aliases go in as v12 if you approve them.

## Verification
`pytest` fully green; after the crawl, Barton frames show in "Présence en boutique" with USD prices and "États-Unis", colour pages list them with the
brand's SKUs, and nothing on the Tunisian shelf moved.

## Not in this part
Reading the lens colour, temples and finish as tags, sizing, the other candidate brands (Cubitts and Dita are next), and any change to how crawls are scheduled.

## As built (differences from the plan)
- **`name_strip`** (new generic option, `ScraperConfig`): a regex removed from the end of every product name. The cards and the JSON-LD
  both say "Banks (48)": with one product per model the size is not part of the frame's name, so Barton uses `\\s*\\(\\d{2}\\)$`.
- **No `cateye` alias was needed**: the taxonomy already lists it as a synonym of cat eye, so "Cat Eye" and "Cateye" both tag it.
- **`hickory` -> brown** joined `chestnut` and `espresso` in the v11 aliases: "Hickory Gradient" was tagged only Bicolore (the taxonomy's
  synonym "gradient"); it is now brown and Bicolore.
- Tests: `tests/test_store_barton.py` (real page shapes and the generic pieces), `tests/test_tagger.py` (v11), the shipped-config test
  (six stores). The suite went from 364 to 381 tests.
