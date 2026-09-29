# Plan: acetate laminations (colour combinations) and best-sellers, from the Etnia catalog

## Context
Two cadrage items from Module 1 (§2.2):
- detect recurring acetate combinations ("bi-couches, tri-couches : rose + rouge + crème"), which later feed the Studio's combination suggestions (Module 3);
- identify best-sellers.

Both can come from Etnia pages we already crawl, with zero LLM.

Verified read-only on saved pages plus 2 live GETs (2026-09-29):
- **Layers are not in the swatch.** Swatch `HV/BL` is labelled just "Havana". The full name "Havana/Blue" sits in the product page's try-on widget JSON, `<script type="application/json" data-vto-carousel>`: `frames[].variants[] = {variantLabel: "Havana/Blue", sizes: [{frameId: "5 KORE 54O HVBL"}]}`.
- **Codes line up exactly.** The frameId's last token `HVBL` is the swatch code `HV/BL` without its slash. About 60 % of labelled variants have two layers (e.g. Havana/Blue, Coral/Green, Black/Zebra); none had three in the sample. Some swatches (KORE PU, TQ) have no widget entry, so they get no layers.
- **Best-sellers** come from the variant-level filter `filter.v.m.custom.best_seller` (values `1` "Yes" and `0` "No"). `?filter.v.m.custom.best_seller=1` on optical lists 25 of 315 frames over 2 pages, with a `link[rel=next]` that keeps the filter.
  - The product breadcrumb "Bestsellers" is misleading: KORE shows it but is not in the filter.
  - The filtered card's `?variant=` pointed at PABLO's default swatch, so a colour-level best-seller cannot be confirmed. The flag is **frame-level** only.

Decision (user): a two-layer variant gets a colour tag per layer, plus a combination tag, plus Bicolore (`two_tone`).

## 1. Laminations

### Extraction (`collectors/stores/config.py`, `parser.py`)
- `VariantsRule.layers: Literal["vto_carousel"] | None`: a named opt-in reader, like the `description_specs: true` precedent, since the source is JSON in a script and not CSS.
- New pure function `vto_layers(tree) -> dict[str, list[str]]`:
  - reads every `script[data-vto-carousel]`, maps `alnum(last token of frameId)` → `variantLabel.split("/")` (stripped, empties dropped);
  - bad JSON or a missing key is skipped, never raised.
- `parse_variants(tree, rule)` adds `"layers": ["Havana", "Blue"]` to a variant when its `alnum(code)` has an entry with **2 or more** layers (single-colour entries add nothing).
- Result in `flags["variants"]`: `{"code": "HV/BL", "color": "Havana", "in_stock": true, "layers": ["Havana", "Blue"]}`. Order is kept as the store writes it.

### Storage: product_tags, not taxonomy.yaml
- A new **non-taxonomy tag dimension `lamination`**, on the same footing as `audience` and `product_type` (tagger `CATEGORY_TAGS`). Not in `taxonomy.yaml`:
  - combinations are combinatorial (19 families → 171 pairs);
  - the taxonomy also drives the LLM schema and Google Trends keywords;
  - press text rarely names exact pairs.
- The raw ordered layers stay in `flags` (the evidence). The tag is the queryable, countable form. No migration: existing columns and the unique key `(product, dimension, code, supplier_code)` fit.

### Tagging (`collectors/stores/tagger.py`, rules v8)
For a variant with `layers`, each layer label is matched like a colour spec (`_spec_color`: same synonyms, store aliases and longest match), then:

| tag | dimension / code | supplier_code | field | when |
|---|---|---|---|---|
| main colour (as today) | color / tortoiseshell | HV/BL | `variant` | swatch label matches |
| each layer's family | color / blue (and tortoiseshell, already there) | HV/BL | `variant-layer` | layer maps to a family |
| Bicolore | color / two_tone | HV/BL | `variant-layers` | 2+ layers whose known families are not all the same |
| combination | lamination / `blue+tortoiseshell` | HV/BL | `variant-layers` | every layer maps and there are 2+ distinct families |

- **Combination code:** distinct families, sorted and joined with `+` (at most 40 characters, otherwise skipped). Havana/Blue and Blue/Havana are one combination; front/back order stays in `flags`.
- **"Black/Zebra":** black plus two_tone. There is no combination tag, because Zebra has no family (it is not guessed).
- **Three layers:** handled by the same rule, e.g. `pink+red+white`.
- **Colour tiers:** colour tags keep family and hex (the `two_tone` hex included). Lamination tags carry no colour tier columns.
- **Effect on counts:** Etnia's shelf share for blue, green and the others rises where they are a layer (intended). `two_tone` gets shelf data comparable with its press mentions. The Tunisian stores have no variants, so nothing changes for them or for "Marché Tunisien".

## 2. Best-sellers

### Extraction (`config.py`, `base.py`)
- `Facet` gains two options:
  - `only: list[str] | None`: the value labels to list; the others are never requested.
  - `flag: str | None`: an identifier; when set, the pass writes `flags[flag]` instead of `raw_specs[name]`.
- `facet_pass` with `flag`:
  - every product listed under an `only` value gets `flags[flag] = True`;
  - if every page of the pass loaded, the rest of that listing's products get `False`;
  - if a page failed, the rest are left **unset** (unknown), never a false `False`.
- Still one filter per request.
- `store_configs.yaml` (Etnia) adds `- { name: "Best-seller", param: "filter.v.m.custom.best_seller", only: ["Yes"], flag: is_bestseller }`. That is about 4 extra requests per crawl (optical 2 pages, sun ~2).
- `flags["is_bestseller"]` goes through the existing `crawl()` merge and `StoreSyncService` unchanged. It is not a tag (it's a product fact, not a taxonomy attribute).

### API and UI
- **`api/main.py::_retail_presence`:**
  - new `retail_bestseller_count` (active tagged products with `is_bestseller`);
  - the sample gets `is_bestseller`;
  - sample order becomes in stock → best-seller → store rank, still round-robin per store.
- **`frontend/lib/types.ts`:** `RetailProduct.is_bestseller?`, `TrendDetail.retail_bestseller_count?`.
- **`frontend/components/RetailPresence.tsx`:**
  - a "Best-seller" pill on the product card, next to "Épuisé", reusing `.pill` plus a new `.retail-bestseller` class in `screens.css` (brand tokens, AA contrast, both themes);
  - "dont N best-sellers" in the counts line when N > 0.
- **Laminations UI:** not in this step. The data becomes queryable here. The natural next surface is an "Associations fréquentes" block on colour trend pages ("Bleu : avec Écaille 40, Noir 12…"), to be planned once there is a second brand.

## 3. Tests (offline)
- **`tests/test_store_etnia.py`** (extend the replay):
  - product pages get a trimmed `data-vto-carousel` script: KORE Havana/Blue plus Blue/Honey, one swatch with no entry, one single-colour entry;
  - the listing form gets best_seller Yes/No inputs, plus a paged best-seller listing.
  - Assertions:
    - `layers` joined by code;
    - no `layers` for a single-colour or unlisted swatch;
    - `is_bestseller` True for listed frames and False for the rest;
    - the "No" value is never requested;
    - a failed best-seller page leaves the others unset;
    - the existing robots guard still holds (never two `filter.` params).
- **`tests/test_tagger.py` (v8):**
  - Havana/Blue gives tortoiseshell, blue and two_tone, all coded HV/BL, plus lamination `blue+tortoiseshell`;
  - Blue/Havana gives the same combination code;
  - Black/Zebra gives black plus two_tone, with no lamination;
  - same-family layers give no two_tone and no lamination;
  - three layers work;
  - no `layers` means today's output, unchanged.
- **`tests/test_color_tiers.py`:** tags from one variant code across dimensions persist together; a re-sync and a retag are idempotent, with no duplicates.
- **Config validation (`test_store_etnia.py`):** a bad `flag` identifier, an empty `only`, or an unknown `layers` value is rejected at load time.
- **`tests/test_api.py`:** `retail_bestseller_count`, `is_bestseller` in the sample, best-sellers ahead of non-best-sellers within a store.
- **Frontend:** `tsc` and eslint clean; a visual check of the pill in light and dark.

## 4. Apply (after commit)
1. Re-crawl Etnia (`crawl-store etniabarcelona.com`, about 21 min, run by you), since layers and best-sellers need fresh pages. The crawl tags on save.
2. `retag-products`: moves the Tunisian stores' tags to v8 (no change in their matching).
3. The `etnia_check.py` report gains: top combinations (`lamination` codes by frame count), the share of two-layer variants, and best-sellers per shape and colour.

## Verification
- `pytest` fully green.
- After the crawl:
  - about 25 optical best-sellers plus the sun ones flagged;
  - the check script lists the top combinations (expected to be led by Havana pairings);
  - `select code, count(*) from product_tags where dimension='lamination' group by code` matches it;
  - `/tendances/color/blue` presence counts rise, and best-seller pills appear in the sample.
- "Marché Tunisien" is unchanged.
