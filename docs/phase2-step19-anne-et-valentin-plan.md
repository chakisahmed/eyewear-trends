# Step 19: Anne & Valentin, the seventh creator brand (France, custom CMS, presence-only), shape, material and colourways

Scouting: `docs/scouting/anne-et-valentin/` (notes and live checks, 2026-10-01). 19 concept collection hubs, custom platform, presence-only (no consumer price), clean specs, editorial shape descriptions, and inline swatches with reference codes and hex layers.

## What the pages show
- Optical `/fr/optique/<concept>` (16 concepts, **109** models) and sun `/fr/solaire/<concept>` (3 concepts with active models: juxtapoz, sunny-bold, sunset, **30** models; walaland is currently empty and excluded). Total catalog: **139** unique models.
- Cards are `main ul > li` containing `a[href^='/fr/optique/...']` or `a[href^='/fr/solaire/...']`, with `picture img` and model name inside `i`. No pagination parameters (`?page=` or `next` links): each concept lists its full model line on one page.
- Product page (`<article>`):
  - Model name: `h1` ("VELISKA", "JEREFLECHIS", "VASSIA").
  - Hero image: `#visu img` or `picture img`.
  - Editorial description (`article > p`): every sampled model opens with its architectural shape and attitude ("Octogonale. Douce. Tonique...", "Grande pantos (mais moins grande qu’elle le croit)...", "Petite ovale. Plus cute que cute...", "Rectangle moyen, étiré, affirmé...").
  - Specs (`dl`):
    - `dl#dim`: `Dimensions : Calibre : 46 mm Nez : 24 mm Branche : 145 mm`
    - `dl`: `Matière : Acétate` (or Métal / Combiné)
    - `dl`: `Fabrication : France`
  - Variants (`ul#cou li`):
    - `data-c`: e.g. `VELISKA_26A40` -> variant code `26A40` (Palier 3).
    - `data-a`: e.g. `VELISKA 26A40`.
    - Swatches carry child `<i>` elements with inline background hex values for acetate layers/accents (`style="background:#A890BA"`).
- Pricing: **Presence-only** (no consumer price displayed on the site, as for Morel).

## Architectural Decisions
1. **Catalog entry points**:
   - `listing.urls`: 16 optical concept hubs with `categories: "Optique"` and 3 sun concept hubs with `categories: "Solaire"`.
2. **Card & Canonical links**:
   - `product`: `main ul > li`
   - `link`: `a`
   - `url_regex`: `(/fr/(?:optique|solaire)/[^/]+/[^/?#]+)`
3. **Product page specs & flags**:
   - `specs`: `rows: "article dl:has(dt)"`, `key: "dt"`, `value: "dd"` (`Matière :` maps to `material` via `SPEC_DIMENSIONS`).
   - `flags`: `description: { css: "article > p", scope: page }`.
4. **Tagger rules v16 (`tagger.py`)**:
   - Match `flags.get("description")` against `idx["_spec_shape"]` with `skip_ambiguous=True`.
   - The opening shape words ("octogonale" -> `geometric`, "pantos" -> `round`, "ovale" -> `oval`, "rectangle" -> `rectangle`) are already exact synonyms in `taxonomy.yaml`.
   - Matching only `_spec_shape` prevents figurative copy (like "Personnalité en acier trempé") from polluting materials.
5. **Variants**:
   - `rows: "ul#cou li"`
   - `code: { attr: "data-c", regex: '^(?:.*_)?([0-9A-Z]+)$' }`
   - `label: { attr: "data-a" }`

## Store Entry (`store_configs.yaml`, `anneetvalentin.com`, `country: FR`)
```yaml
  anneetvalentin.com:
    name: "Anne & Valentin"
    base_url: "https://anneetvalentin.com"
    lang: fr
    country: FR
    default_brand: "Anne & Valentin"
    default_currency: EUR
    delay_s: 1.5
    listing:
      urls:
        - { url: "/fr/optique/alpha", categories: "Optique" }
        - { url: "/fr/optique/bakkelite", categories: "Optique" }
        - { url: "/fr/optique/balloon", categories: "Optique" }
        - { url: "/fr/optique/fold", categories: "Optique" }
        - { url: "/fr/optique/formacolor", categories: "Optique" }
        - { url: "/fr/optique/hypercut", categories: "Optique" }
        - { url: "/fr/optique/krafties", categories: "Optique" }
        - { url: "/fr/optique/metro", categories: "Optique" }
        - { url: "/fr/optique/minimalist", categories: "Optique" }
        - { url: "/fr/optique/onthedot", categories: "Optique" }
        - { url: "/fr/optique/pictogram", categories: "Optique" }
        - { url: "/fr/optique/prismatiks", categories: "Optique" }
        - { url: "/fr/optique/punchline", categories: "Optique" }
        - { url: "/fr/optique/puzzle", categories: "Optique" }
        - { url: "/fr/optique/simplecut", categories: "Optique" }
        - { url: "/fr/optique/symboliques", categories: "Optique" }
        - { url: "/fr/solaire/juxtapoz", categories: "Solaire" }
        - { url: "/fr/solaire/sunny-bold", categories: "Solaire" }
        - { url: "/fr/solaire/sunset", categories: "Solaire" }
      product: "main ul > li"
      link: "a"
      url_regex: '(/fr/(?:optique|solaire)/[^/]+/[^/?#]+)'
    product_pages:
      enabled: true
      max_products: 400
    fields:
      name: { css: "article h1", scope: page }
      image_url: { css: "#visu img, picture img", attr: ["src", "data-src"], scope: page }
    flags:
      description: { css: "article > p", scope: page }
    specs:
      rows: "article dl:has(dt)"
      key: "dt"
      value: "dd"
    variants:
      rows: "ul#cou li"
      code: { attr: "data-c", regex: '^(?:.*_)?([0-9A-Z]+)$' }
      label: { attr: "data-a" }
```

## Tests (`test_store_anne_et_valentin.py`)
- Mock responses for concept listing hubs and product pages using `MockTransport`.
- Canonical URLs normalized, categories set to Optique or Solaire.
- Name "VELISKA", brand "Anne & Valentin", presence-only (price None).
- Specs: `Matière : Acétate` -> tagged `acetate`; dimensions preserved in `raw_specs`.
- Shape: description "Octogonale..." tags `geometric`; description "Grande pantos..." tags `round`.
- Variants: `26A40`, `26A41` captured as Palier 3 codes.
- Suite remains 100% green.

## After the first live crawl (2026-10-01)
- **139 products crawled and inserted** (109 optical, 30 sunglasses) across all 19 active concept hubs, 0 dropped, 0 conflicts. Yield: 100%.
- **897 variant swatches** ingested with clean supplier codes (Palier 3) in `product_tags.supplier_code` and inline hex swatches.
- **Product types**: 109 optical, 30 sun (100% tagged).
- **Materials**: 126 acetate, 28 metal, 18 titanium (combinations tagged for both).
- **Shapes**: 115 frames tagged for shape (round 54, geometric 21, rectangle 18, square 17, oversized 10, butterfly 11, oval 5, wayfarer 5, aviator 3, shield 3, browline 1, rimless 1).
- **Shape aliases added in v16**: `papillonnante`/`papillonnant` -> butterfly, `trapezoidale` -> wayfarer, `hexagone`/`octogone` -> geometric, `bandeau` -> shield. Models without shape tags either have blank descriptions or purely poetic texts.
- **Catalog Status**: Recorded in `store_crawls` with status `ok` ("À jour"), baseline established. Tunisian retail shelf metrics completely unaffected.

