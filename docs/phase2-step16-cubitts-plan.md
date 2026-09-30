# Step 16: Cubitts, the fourth creator brand (UK, Shopify, with price)

## Context
Scouting (`docs/scouting/cubitts/`, your notes plus my checks) makes Cubitts the second Etnia-class brand after Barton Perreira: Shopify, UK store in
GBP, plain server pages with `rel=next`, product-level shape and material filters, plain colour names, and an allowed best-sellers collection. Barton
Perreira (Step 15) already added everything the crawler needed; this step needs **one small generic addition** and a config.

What the live pages showed (checked in the browser, 2026-09-30):
- Cards are `<product-card class="product-card">` elements with `a.product-card__link`; 20 per page. Optical `/collections/spectacles`: 6 pages, **117**
  frames. Sun `/collections/sunglasses`: 7 pages, **132**. Every page has `<link rel="next">` (the "infinite scroll" only loads these same pages). About 1.3 MB per page.
- Filters (one value per request, `%20` for spaces): `filter.p.m.custom.shape` (Square, Round, Oval, Cat-eye, Aviator) and `filter.p.m.custom.material`
  (Acetate, Steel, Titanium, Combination). Product level, so every colour of a frame shares them. The "Bestsellers" sort is `filter.p.m.custom.sort_by`, which
  robots.txt forbids (`/collections/*sort_by*`): never requested.
- **Best-sellers**: `/collections/bestselling-glasses` is a plain collection with 16 frames, all optical. Sun frames have no such list.
- Product page (about 550 KB): JSON-LD `Product` with `name` ("Clayton", no "Sunglass" or "Spectacles" suffix), brand "Cubitts", price 175 **GBP**; offers carry no SKU
  or colour field. Colours are the swatch inputs `input.product-color-swatch__radio[name="Colour"]` with `value` = the colour name (`Khaki`, `Dark Turtle`,
  `Celadon`, `Crimson Wash`, `Beechwood Fade`). A variant is size / colour / prescription (Dalmeny: 20 variants, 5 colours): sizes are options, not products.
  The swatches carry no availability attribute; they also carry `data-color-hex` (the store's own hex), not used now.
- Weight: about 13 listing pages + about 35 filter pages + 249 product pages: roughly 200 MB and 300 requests, about 12 minutes.

## 1. One generic, opt-in addition: a listing that only flags (`config.py`, `base.py`)
```yaml
- { url: "/collections/bestselling-glasses", flag: is_bestseller }
```
- `ListingUrl.flag` (an identifier, like `Facet.flag`; not combinable with `categories`). Such a listing is **enrichment only**, processed after the main listings: every
  product it lists that is already in the main listings gets `flags[flag] = True`. It never adds a product and never counts as presence (`report.listed`), so a
  frame that is only in the best-sellers list is ignored, and nothing is ever dropped because of it.
- **True or unset, never False.** The list covers one shelf (optical only here), so "not on the list" does not mean "not a best-seller". Flags are replaced on every crawl,
  so a frame that leaves the list loses its True at the next complete crawl. (The Etnia filter pass sets False; this one cannot honestly.)
- A page of it that cannot be fetched is a `FacetGap(facet="Best-sellers", flag="is_bestseller")` (already built in Step 14): the crawl is `incomplete`, the drops are unaffected,
  and `carry_over` keeps each frame's previous flag instead of erasing it.

## 2. Store entry (`store_configs.yaml`, after Barton Perreira)
```yaml
cubitts.com:
  name: "Cubitts"
  base_url: "https://cubitts.com"
  lang: en
  country: GB                           # a brand catalog, not the Tunisian market lens
  delay_s: 1.5
  listing:
    urls:
      - { url: "/collections/spectacles", categories: "Optique" }
      - { url: "/collections/sunglasses", categories: "Solaire" }
      - { url: "/collections/bestselling-glasses", flag: is_bestseller }
    pagination: { next: "link[rel=next]", max_pages: 20 }      # 6 and 7 pages
    product: "product-card"
    link: "a.product-card__link"
    facets:        # product-level filters, one per request; never the sort_by filter (robots.txt); each page ~1.3 MB
      - { name: "Shape", param: "filter.p.m.custom.shape" }
      - { name: "Materials", param: "filter.p.m.custom.material" }
  product_pages: { enabled: true, max_products: 400 }
  variants:
    rows: "input.product-color-swatch__radio[name='Colour']"
    code: { attr: value }               # the store's own colour name is its identity for the colour (Palier 3)
    label: { attr: value }
```
No `default_brand` (the JSON-LD says Cubitts), no `specs` rule (the details are marketing bullets), no `model_regex` or `name_strip` (sizes are options, names are clean).
Two design choices to confirm: the **code is the colour name** (`Khaki`), not the SKU's colour token (`KHA`): the SKU lives only in Shopify's analytics data, and the name is
unique per product; and **stock stays per product** (no availability on the swatches).

## 3. Tagger rules v12 (`tagger.py`)
- `SPEC_ALIASES` material (specs only): `steel` -> metal (the filter value "Steel"; "stainless steel" already exists).
- "Cat-eye", "Oval", "Aviator", "Acetate", "Titanium" already match; "Combination" stays untagged, as at Etnia.
- Colour names are **not guessed**: `Khaki`, `Black` and similar are matched by the taxonomy as they are; names like `Celadon`, `Haze`, `Beechwood Fade`, `Crimson Wash` get their family
  from the first crawl's report of colours with no family (v13 if you approve them), as for Etnia, Morel and Barton. (The store's own `data-color-hex` could classify unknown names by
  nearest family later; not done now, it is inference rather than a name.)

## 4. Tests (offline, markup trimmed from the real pages, MockTransport, the real robots.txt rules)
- **Generic:** `ListingUrl.flag` validation (identifier, no `categories` with it, plain string entries unchanged); flag listing: True on frames present in the main listings, a frame only in the
  flag list is ignored (no product, not in `report.listed`), multi-page flag list, a failing page gives a `FacetGap` with the flag while `report.complete` stays true, and `sync`'s carry-over keeps the old
  flag; the main listings' order in the config does not matter.
- **Cubitts fixtures:** `product-card` cards with `a.product-card__link`, 3 pages per collection with `rel=next`, filter forms that also contain the `sort_by` filter and the colour and size
  filters (which must not be requested), filtered pages, the best-sellers page, product pages with JSON-LD (no SKU) and swatch inputs.
- **Assertions:** canonical `https://cubitts.com/products/albion`; name "Albion", brand "Cubitts", price 175 GBP; category Optique or Solaire; variants `code = colour name`; a colour with a known family
  gets its tag with the name as supplier code; shape "Cat-eye" gives cat_eye and material "Steel" gives metal; best-seller True only on the optical frames in the flag list and unset elsewhere
  (sun frames included); no request carries `sort_by`, `+`, two `filter.` parameters, or the best-sellers filter; the report is complete; pages 2 and 3 are followed.
- **Shipped config:** seven stores, `GB` for Cubitts; the suite stays green (381 today).

## 5. Files
`backend/app/collectors/stores/config.py`, `base.py`, `store_configs.yaml`, `tagger.py`; tests `test_store_cubitts.py` (new), `test_store_crawlers.py`, `test_tagger.py`;
docs: Step 16 in `docs/build-plan.md`, `docs/phase2-step16-cubitts-plan.md`, status in `docs/scouting/cubitts/notes.md`. No frontend change (`GB` is already named).

## Order of work
1. The generic listing flag and the Cubitts entry with tests; suite green; commit (not pushed).
2. Rules v12, docs; commit.
3. **You run** `python -m app.cli crawl-store cubitts.com` (about 12 minutes, about 200 MB), then `retag-products`. It needs the lock: run it after the pending Barton and repair crawls.
4. I read the result read-only: coverage per facet, best-sellers flagged, colour names with no family (aliases for you to approve), prices, and that the Tunisian shelf did not move.

## Verification
`pytest` fully green; after the crawl, Cubitts frames show in "Présence en boutique" with GBP prices and "Royaume-Uni", the best-seller pill appears on the 16 listed frames,
and the Sources panel lists Cubitts with its crawl status.

## Not in this part
Reading the store's colour hex, bridge fit or thickness, per-colour stock, sun best-sellers (the store has no list), and the other candidate brands (Dita and E.B. Meyrowitz are next).

## As built
- No differences from the plan. The generic addition is `ListingUrl.flag` (`config.py`, `base.py` `flag_pass`); a flag listing is validated (identifier, no `categories`, at
  least one main listing), processed after the main listings, and its failed page is recorded as a `FacetGap` named after the flag.
- **Expected colour coverage before aliases** (the taxonomy's own matching on names seen on Cubitts pages): Khaki -> green, Black -> black, Slate -> grey, Caramel -> brown,
  Crimson Wash -> red, Crystal -> clear. **Untagged until approved:** Dark Turtle, Haze, Celadon, Ink Wash, Beechwood Fade, Bone, Sepia Wash, Indigo Wash, Sienna Wash. The first crawl's
  report ranks all unknown names by frame count for the v13 alias list.
- Tests: `tests/test_store_cubitts.py` (the crawl on real page shapes and the generic flag listing), `tests/test_tagger.py` (v12), the shipped-config test (seven stores). The suite went from 381 to 392 tests.
