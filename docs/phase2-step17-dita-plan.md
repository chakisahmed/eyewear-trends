# Step 17: Dita, the fifth creator brand (USA, Shopify, `/en-fr` storefront, prices in USD)

## Context
Scouting (`docs/scouting/dita/`, your notes plus my checks) makes Dita the third Etnia-class Shopify brand. The locale is settled: **`/en-fr`** (the neutral international
storefront, $795 for Evercharm against $834.75 on `/en-tn`). The prefix is part of every stored URL, so it is fixed from the first crawl. Everything the crawler needs already
exists except **one small generic addition**: a two-level colour split.

What the `/en-fr` pages show (checked in the browser, 2026-09-30):
- Optical `/en-fr/collections/optical`: **81** frames; sun `/en-fr/collections/sunglasses`: **91**. Both are 3 pages of 40, about 1.1 MB each, paging by an
  **`<a rel="next">` anchor** (not a `<link>`). Cards are `<product-item>` elements with two anchors each.
- Card links in the plain listing are clean (`/en-fr/products/laurhyn`) but on filtered pages Shopify appends tracking parameters
  (`/en-fr/products/ashium?_pos=1&_fid=18b6c785d&_ss=c`): the URL identity must be cut with `url_regex`, or every filter value would miss its frame.
- Filters (variant-level metafields, but the same for every colour of a frame), one value per request: `filter.v.m.vdp.frame_shape` (Aviator, Browline, Cat-Eye, Diamond,
  Navigator, Polyangular, Round, Square; sun adds Shield) and `filter.v.m.vdp.frame_composition` (Acetate, Titanium, Titanium/Acetate; optical also has the site's typo "Titanuim").
  Frame colour, lens colour, size, gender and price filters exist and are not used. robots.txt forbids `sort_by` and several `filter` parameters in one URL (the price range adds two).
- Product page (about 740 KB): JSON-LD `Product` (name "LAURHYN", brand "DITA Eyewear") with **one offer per colourway**: `name`, `sku` (`DTX204-A-01`), `price` (595), `priceCurrency` (USD),
  `availability`. The offer name is `option1 / option2` = **frame colour / lens colour**, and the frame colour is itself `Frame - Finish[ - Finish]`:
  `Yellow Gold - Black - Shiny Silver / Dark Grey to Clear Gradient`, `Brushed White Gold / Brown - Brown Gradient`. So the frame colour is the first token of the first part.
- No sizes as separate products (size is a filter attribute; models such as `lineage-68` and `lineage-68x` are distinct optical and sun frames).
- The two "best-selling" collections list the **whole** catalog in sales order (81 and 93 frames), so they cannot flag best-sellers. "New releases" is a real subset (9 optical frames): a possible
  `is_new_release` flag later, no consumer yet.
- Weight: about 6 listing pages + about 30 filter pages + 172 product pages: roughly 165 MB and 230 requests, about 7 minutes.

## 1. One generic, opt-in addition: a nested colour split (`config.py`, `parser.py`)
`ColorSplit.then: ColorSplit | None`: after the first split picks its part, the chosen part is split again and the colour is a part of that. For Dita:
```yaml
variants:
  json_ld_offers: true
  color_split: { sep: " / ", color: 0, then: { sep: " - ", color: 0 } }
```
`Yellow Gold - Black - Shiny Silver / Dark Grey to Clear Gradient` -> first split: `Yellow Gold - Black - Shiny Silver` (frame) and `Dark Grey to Clear Gradient` (lens); then: `Yellow Gold`. `variant["parts"]` keeps the first-level
parts, `variant["subparts"]` the second-level ones (only when the chosen part has several), so the finish and the lens colour stay available for later and are **not tagged now**. A name without the requested
part loses its colour rather than getting a wrong one, as in Step 15. Barton's single-level split is unchanged.

## 2. Store entry (`store_configs.yaml`, after Cubitts)
```yaml
dita.com:
  name: "Dita"
  base_url: "https://dita.com"
  lang: en
  country: US                        # the brand's home market, a catalog and not the Tunisian lens; the storefront is /en-fr, priced in USD
  delay_s: 1.5
  listing:
    urls:
      - { url: "/en-fr/collections/optical", categories: "Optique" }
      - { url: "/en-fr/collections/sunglasses", categories: "Solaire" }
    pagination: { next: "a[rel=next]", max_pages: 20 }              # 3 pages of 40 each
    product: "product-item"
    link: "a[href*='/products/']"
    url_regex: '(/en-fr/products/[^/?#]+)'                          # drops the ?_pos=&_fid=&_ss= tracking that filtered pages add
    facets:
      - { name: "Shape", param: "filter.v.m.vdp.frame_shape" }
      - { name: "Materials", param: "filter.v.m.vdp.frame_composition" }
  product_pages: { enabled: true, max_products: 400 }
  variants:
    json_ld_offers: true
    color_split: { sep: " / ", color: 0, then: { sep: " - ", color: 0 } }
```
No `default_brand` (the JSON-LD says "DITA Eyewear"), no best-seller listing (see above), no `name_strip` or `model_regex`. Design choice to confirm: **`country: US`** although the storefront is French, so the catalog
counts as the brand's own US catalog like Barton Perreira, and the retail heading says "États-Unis".

## 3. Tagger rules v13 (`tagger.py`)
Specs and variants only, from labels that are known now (the facet values and names seen on `/en-fr`):
- material: `titanuim` -> titanium (the site's own typo, next to the correct "Titanium" in the same filter).
- colour: `white gold` -> gold. Today "White Gold" and "Brushed White Gold" tag **gold and white** (the taxonomy matches the two words separately), and white is wrong for a metal finish; the longer alias consumes the phrase, as "pink gold" does.
- shape (proposed, veto welcome): `polyangular` -> geometric and `diamond` -> geometric. **`Navigator` is left unmapped** (a squared double-bridge aviator? not certain): your call.
- Not guessed, waiting for the first crawl's report: `Smoked Pearl`, `Swanshell`, `Burnt Timber`, `Ink Swirl` and any others. Already matched as they are: Black Glass, Yellow Gold, Silver, Future Dusk Blue, Crystal Clear (clear), Tortoise Haze (tortoiseshell), Matte Black, Black Iron.

## 4. Tests (offline, markup trimmed from the real pages, MockTransport, the real robots.txt rules)
- **Generic:** `split_color` with `then` (two-level, three-part frame colour, a single part, a missing part gives no colour, `parts` and `subparts`, a nested split on an unsplit chosen part), config validation of the nesting, existing single-level tests unchanged.
- **Dita fixtures:** optical and sun listings (`<product-item>` with two anchors, an `a[rel=next]` anchor over 3 pages), filter forms that also hold the frame colour, lens colour, size and price inputs (never requested), filtered pages whose links carry the tracking
  parameters, product pages with JSON-LD offers named as on the real pages.
- **Assertions:** canonical `https://dita.com/en-fr/products/laurhyn` (the tracking parameters cut); name, brand "DITA Eyewear", price and USD; SKUs verbatim as Palier 3; the frame colour only (`Yellow Gold`, not the finish or the lens), e.g. `Black Glass - Silver / Grey to Clear Gradient` -> black; "White Gold" tags gold and not white;
  shape and material from the filters (Cat-Eye -> cat_eye, "Titanium/Acetate" -> both, "Titanuim" -> titanium); pages 2 and 3 followed; no request with `sort_by`, `+`, two `filter.` parameters, the price, colour, size or lens filters; report complete; the filtered pages' frames are the same products as the plain listing's.
- **Shipped config:** eight stores, `US` for Dita; the suite stays green (392 today).

## 5. Files
`backend/app/collectors/stores/config.py`, `parser.py`, `store_configs.yaml`, `tagger.py`; tests `test_store_dita.py` (new), `test_store_barton.py` (nested-split unit tests live with the split tests), `test_store_crawlers.py`, `test_tagger.py`;
docs: Step 17 in `docs/build-plan.md`, `docs/phase2-step17-dita-plan.md`, status in `docs/scouting/dita/notes.md`. No frontend change (`US` is named).

## Order of work
1. The nested split and the Dita entry with tests; suite green; commit (not pushed).
2. Rules v13, docs; commit.
3. **You run** `python -m app.cli crawl-store dita.com` (about 7 minutes, about 165 MB), then `retag-products`. After the pending Barton, Cubitts and repair crawls (one crawl at a time).
4. I read the result read-only: coverage per facet, colour names with no family (aliases for you to approve), prices, and that the Tunisian shelf did not move.

## Verification
`pytest` fully green; after the crawl, Dita frames show in "Présence en boutique" with USD prices, colour pages list them with the brand's SKUs, and the Sources panel lists Dita with its crawl status.

## Not in this part
The lens colour and finish as tags, the "New releases" flag, best-seller ranks, the other candidate brands (E.B. Meyrowitz is next), and any change to how crawls are scheduled.

## As built
- No differences from the plan. The generic addition is `ColorSplit.then` (`config.py`) applied by `split_color` (`parser.py`), which now loops over the levels: `parts` for the first level, `subparts` for the
  next ones, and a name without the requested part loses its colour.
- Tests: `tests/test_store_dita.py` (the crawl on real page shapes, including the tracking parameters on filtered pages and the filters that must never be requested), the nested-split unit tests in
  `tests/test_store_barton.py`, `tests/test_tagger.py` (v13), the shipped-config test (eight stores). The suite went from 392 to 402 tests.
- **Expected colour coverage before aliases**: Black Glass, Matte Black, Black Iron, Black Palladium -> black; Yellow Gold, White Gold, Brushed White Gold -> gold; Silver -> silver; Future Dusk Blue -> blue; Crystal Clear -> clear;
  Tortoise Haze -> tortoiseshell. **Untagged until approved:** Smoked Pearl, Swanshell, Burnt Timber, Ink Swirl and any others the crawl reports.
- **Shape labels waiting for you:** `Navigator` (unmapped on purpose).
