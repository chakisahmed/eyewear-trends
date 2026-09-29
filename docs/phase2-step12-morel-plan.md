# Plan: Morel (morel.com), second creator brand

## Context
The cadrage wants creator and manufacturer brands only; Etnia Barcelona is the only one so far. Woodys is blocked by a Sucuri JavaScript bot challenge (not bypassed; it's a client ask). Ana Hickmann and Carolina Herrera publish no catalog of their own. Morel is the one directly crawlable candidate.

Scouted read-only on 2026-09-29 (about 15 requests, our User-Agent, 2 s apart).

**Access**
- Open: Cloudflare with no challenge (only passive captcha scripts for forms).
- robots.txt allows catalog pages and blocks the same Shopify patterns as Etnia (`sort_by`, `+`).

**Platform and listings**
- Shopify, `/en/` catalog.
- Listings: `/en/collections/optical` (fewer than 8 pages of 48 cards, so at most 336 frames) and `/en/collections/sunglasses` (48+ cards).
- Cards are `product-card` elements; the name is in `a.product-title`; the next page is in `link[rel=next]`.
- Card links look like `/en/collections/optical/products/agathe1`.

**Filters** (variant-level colour, product-level gender and material)
- `filter.p.m.mymorel.gender`: Man, Woman.
- `filter.p.m.mymorel.material`: Acetate, Combined, Stainless steel, Titanium, Wood.
- `filter.v.m.mymorel.color_name`: 16 bilingual labels (Bleu/Blue, Noir/Black, Gris/Gray…). All 16 already map to taxonomy families.
- There is **no** best-seller filter and no try-on layer data.

**Product pages**
- No JSON-LD Product.
- No price is shown to shoppers. Prices exist only in Shopify's analytics metadata; the decision is not to use them.
- A spec table (`div.accordion__content table tr`, `<strong>` key and value cell) gives Shape (e.g. Hexagonal), Front material, Temple material, Gender, Type, sizes and a UDI code.
- Colour variants are radios labelled with the code only ("BM02 AGATHE 1").
- Product tags confirm the colours at frame level ("Couleur primaire_Bleu / Noir / Rouge") but not which code is which.

**Code ↔ colour link, proven**
- `?filter.v.m.mymorel.color_name=Red` links AGATHE 1's variant id `64359734378873`. That is RP01 in Shopify's variant list (`ShopifyAnalytics.meta.product.variants[{id, public_title: "RP01 AGATHE 1"}]`), not its default BM02.
- So the colour filter states which variant code has which colour. Nothing is decoded from the code, even though BM02, NV03 and RP01 look like colour initials.

**Decisions (user)**
- Presence only, no price: Morel frames show "Prix non affiché". Analytics prices are never read.
- Link colours to codes: full Palier 1–3.

## 1. Generic crawler additions (all opt-in, Etnia unchanged)
- **`parser.canonical_url`:** joins **all** capture groups of `url_regex`. `'(/en)/collections/[^/]+(/products/[^/?#]+)'` gives `/en/products/agathe1`. Etnia's single group is unaffected.
- **`ListingItem.variant_id`:** the `variant` query parameter of the raw card link, read before canonicalisation. `parse_listing` fills it.
- **`Facet.per_variant: bool`** (only for variant-level filters):
  - the pass also records `flags["variant_colors"][variant_id] = label` for each listed card that carries a `variant`;
  - the product-level `raw_specs[name]` label stays as today, so a frame still counts in that colour even if only one of its variants is linked.
- **`VariantsRule.ids: Literal["shopify_analytics"] | None`:** a named reader like `layers: vto_carousel`.
  - It reads `var meta = {...}` (`meta.product.variants[{id, public_title}]`) and puts `"id"` on each variant.
  - The join applies the variants rule's own `code` regex to `public_title`, so "RP01 AGATHE 1" matches code "RP01".
  - Only `id` and `public_title` are read, never `price`.
- **`base.crawl` merge:** a page variant whose `id` has a listing colour gets `variant["color"] = label` (the page's own label wins if present). `variant_colors` is dropped from the final flags; it only serves as the join.

## 2. Morel config (`collectors/stores/store_configs.yaml`)
```yaml
morel.com:
  name: "Morel"
  base_url: "https://morel.com"
  lang: en
  country: FR                      # a brand catalog: not a Tunisian shelf; "Présence en boutique" names France
  default_brand: "Morel"
  delay_s: 1.5
  listing:
    urls:
      - { url: "/en/collections/optical", categories: "Optique" }
      - { url: "/en/collections/sunglasses", categories: "Solaire" }
    pagination: { next: "link[rel=next]", max_pages: 20 }
    product: "product-card"
    link: "a.product-title"
    url_regex: '(/en)/collections/[^/]+(/products/[^/?#]+)'
    facets:
      - { name: "Gender", param: "filter.p.m.mymorel.gender" }
      - { name: "Materials", param: "filter.p.m.mymorel.material" }
      - { name: "Couleur", param: "filter.v.m.mymorel.color_name", per_variant: true }
  product_pages: { enabled: true, max_products: 800 }
  fields:
    name: { css: "a.product-title" }
  specs: { rows: "div.accordion__content table tr", key: "td:first-child strong", value: "td:nth-child(2)" }
  variants:
    rows: "label[for*='-option1-']"          # "BM02 AGATHE 1"
    code: { regex: '^(\S+)' }                # BM02 (Palier 3)
    ids: shopify_analytics
```
- No `default_currency`: with no price, the currency stays empty, so no fake "EUR" appears.
- About 7–8 listing pages, about 16 colour passes, 2 gender and 5 material passes (≈ 40 requests), plus ≤ ~450 product pages. About 12–15 minutes at 1.5 s.

## 3. Tagger rules v9 (`collectors/stores/tagger.py`)
- `SPEC_DIMENSIONS`: "front material" and "temple material" (plus FR "matière face" and "matière branches") map to material.
- **Deliberately not mapped:**
  - "Type" (Rimmed / Semi-rimless / Rimless): "semi-rimless" would wrongly match `rimless`. Its values are reported after the first crawl, then decided.
  - "Combined": no family.
- Shape comes from the spec "Shape" (already a known label). Hexagonal → geometric, Panto → round and Butterfly → butterfly already map. Unmatched shapes are listed by the check script after the crawl, for aliases in a later step.

## 4. Tests (offline, `tests/test_store_morel.py`, markup trimmed from the real pages)
- **Fixtures:**
  - a listing with `product-card` cards, `a.product-title`, `link[rel=next]` and the three filter forms;
  - colour-filtered pages whose card links carry `?variant=`;
  - product pages with the spec table, code-only radios, a `var meta = {...}` analytics script (with prices present), and no JSON-LD.
- **Assertions:**
  - canonical `https://morel.com/en/products/agathe1`, with both collections deduplicated;
  - specs parsed; `variants` carry codes and ids;
  - RP01 gets "Red" from the Red pass;
  - BM02 and NV03 get their colours from their own passes;
  - a frame with two variants of one colour still has the colour as a frame-level spec;
  - **price is None and currency is None** (analytics prices ignored);
  - brand "Morel";
  - never two `filter.` parameters in one request, and no `sort_by` or `+`.
- **Tagger:** Palier 1–3 colour tags (e.g. red/RP01), material from "Front material", geometric from "Hexagonal".
- **Generic:** multi-group `canonical_url`; `variant_id` parsing; the analytics reader tolerates a missing or malformed `meta`; `per_variant` on a card without `variant` records nothing.
- `test_shipped_config` covers five stores.

## 5. Apply
1. `crawl-store morel.com` (run by you; about 12–15 min).
2. `retag-products`, to move all stores to v9.
3. Generalise the check script to take a store name, then run it for Morel. It reports:
   - coverage per spec;
   - the Shape and Type value distribution;
   - linked vs unlinked variant codes;
   - colour families;
   - that "Marché Tunisien" still lists the 3 Tunisian stores only.

## Verification
- `pytest` fully green.
- After the crawl:
  - most variants carry a colour;
  - `supplier_code` values such as RP01 are stored;
  - Morel shows in "Présence en boutique", with "France" in the section note and "Prix non affiché" on its cards;
  - no Morel price in the database.
