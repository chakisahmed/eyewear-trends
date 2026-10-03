# Step 21: Kuboraum, the ninth creator brand (Germany, WordPress/Woo, presence-only)

Scouting: `docs/scouting/kuboraum/` (notes and live checks, 2026-10-01). Independent creator brand founded in Berlin (Kuboraum GmbH, DE 291441542), handmade in Italy. Known for monumental, sculptural acetate, geometric masks, and mixed-material architectural designs.

## What the pages show
- Optical `/collections/optical-mask/` (**473** items) and sun `/collections/sun-mask/` (**363** items). Total catalog: **699** distinct models (137 overlap frames sold with clear or tinted lenses).
- Pagination: none needed. All items are served in the initial server-rendered HTML page (no AJAX load or infinite scroll).
- Cards on listing pages: `div.mask-item` containing `a.mask-link`.
  - Canonical URL regex: `(/masks/[^/?#]+)`.
- Product page:
  - Heading: `h1` ("D71 VIOLET PETAL", "E15 SILVER", "B2 POP-GROTESQUE").
  - Technical specs inside `.new-description`:
    `<span class="bold">KEY:</span> VALUE <br>`
    - `CODE`: `D71 VP`, `E15 SI`, `B2 RM PQ`
    - `MATERIAL`: `ACETATE`, `ACETATE & METAL`, `Metal, Nylon, Acetate`
    - `COLOR`: `Violet Petal`, `Silver + Black Matt`, `ROSE MILK, HANDCRAFT FINISHING`, `RUTHENIUM + BLACK MATT`
    - `TEMPLES COLOR`: `Antique Light Gold + Brown`
    - `LENS`: `Clear`, `Grey`, `Electric Green`, `24H Pink`
    - `BRIDGE`: `20 mm`
    - `LENS WIDTH`: `52 mm`
    - `TEMPLE LENGTH`: `145 mm`
  - Variants:
    - Active model code and color are extracted from `.new-description` via deterministic regex rules:
      - `code`: `CODE:\s*(.+?)\s*MATERIAL:`
      - `label`: `COLOR:\s*(.+?)\s*(?:TEMPLES COLOR|LENS):`
- Pricing: **Presence-only** (no consumer price tag displayed, B2B optician network, "Request a retailer" call-to-action, `default_currency: EUR`).

## Architectural Decisions
1. **Catalog entry points & pagination**:
   - `urls`: `/collections/optical-mask/` (`categories: "Optique"`), `/collections/sun-mask/` (`categories: "Solaire"`).
   - No pagination parameter needed.
2. **Card & Canonical links**:
   - `product`: `div.mask-item`
   - `link`: `a.mask-link`
   - `url_regex`: `(/masks/[^/?#]+)`
3. **Specs parsing with tail text**:
   - Kuboraum's specs format has the key in `<span class="bold">Key:</span>` and the value in the following text node (`span.tail`).
   - Add `tail: bool = False` to `SpecsRule` in `config.py` and `parser.py`.
   - When `tail: true`, `key` is read from the element text and `value` from its `.tail`.
4. **Variants Rule**:
   - `rows: ".new-description"`
   - `code: { regex: 'CODE:\s*(.+?)\s*MATERIAL:' }`
   - `label: { regex: 'COLOR:\s*(.+?)\s*(?:TEMPLES COLOR|LENS):' }`
5. **Tagger rules v18 (`tagger.py`)**:
   - Bump `RULES_VERSION = 18`.
   - Add `SPEC_ALIASES["color"]`:
     - `("rosegold", "gold")`
     - `("gun metal", "grey")`, `("gunmetal", "grey")`
     - `("antique light gold", "gold")`

## Store Entry (`store_configs.yaml`, `kuboraum.com`, `country: DE`)
```yaml
  kuboraum.com:
    name: "Kuboraum"
    base_url: "https://www.kuboraum.com"
    lang: en
    country: DE
    default_brand: "Kuboraum"
    default_currency: EUR
    delay_s: 1.5
    listing:
      urls:
        - { url: "/collections/optical-mask/", categories: "Optique" }
        - { url: "/collections/sun-mask/", categories: "Solaire" }
      product: "div.mask-item"
      link: "a.mask-link"
      url_regex: '(/masks/[^/?#]+)'
    product_pages:
      enabled: true
      max_products: 800
    fields:
      name: { css: "h1", scope: page }
      image_url: { css: "img.gallery-image, img.main-image", attr: ["src", "data-src"], scope: page }
    specs:
      rows: ".new-description span.bold"
      tail: true
    variants:
      rows: ".new-description"
      code: { regex: 'CODE:\s*(.+?)\s*MATERIAL:' }
      label: { regex: 'COLOR:\s*(.+?)\s*(?:TEMPLES COLOR|LENS):' }
```

## Tests (`test_store_kuboraum.py`)
- Mock responses for optical and sun listing pages with `MockTransport`.
- Canonical URLs normalized.
- Specs extracted with `tail: true`: `MATERIAL: ACETATE & METAL` -> `acetate`, `metal`; `COLOR: Violet Petal` -> `purple`.
- Active variant extracted: code `D71 VP`, color `Violet Petal` -> `color: purple` with `supplier_code: D71 VP`.
- Shipped config tests updated for 12 stores.
