# Phase 2, step 4: second store — mykenza.tn (config + 3 small generic parser/tagger additions)

## Context
Outika gives no shapes, and lunettek.com has ideal specs but a dormant catalog (48 of 48 sampled products out of stock, all images from 2021). mykenza.tn was chosen instead. It is an active Tunisian multi-brand store (Ray-Ban, Loewe, …) with real TND prices and promotions valid until 28 Sept, and it states each frame's shape in its schema.org JSON-LD description. All of this is deterministic, with zero LLM calls.

## Findings (read-only GETs with our User-Agent, 2026-09-27)
- **robots.txt (Yoast):** `Disallow: /*?`, `/wp-admin/` and others. Pagination uses `/page/N/` paths, which are allowed. Product images come from `media.mykenza.tn`.
- **Catalog:** 3,373 products in total, including watches. Eyewear subcategories: Lunettes de soleil Homme (535) and Femme (646), which overlap for unisex frames. They are sorted newest first, 12 per page, with a `a.next.page-numbers` link.
- **Listing card (standard WooCommerce):**
  - Card: `li.product.type-product`, with `instock`/`outofstock` among its classes.
  - Link: `a.woocommerce-LoopProduct-link`. Its text carries promo noise ("Spray Offert - 50% …"), so the name comes from the title element instead.
  - Clean title: `.woocommerce-loop-product__title`.
  - Price: `.price` shows "249 DT 499 DT"; `parse_price` takes the first number, 249.
  - `img` is lazy-loaded: its `src` is a `data:image/svg+xml` placeholder.
- **Product JSON-LD (Yoast/Woo):**
  - `name` is clean, and `brand.name` is set (Loewe).
  - `image` is set, and `offers.availability` says InStock.
  - **The price has no `offers.price`.** It sits in `offers.priceSpecification[]`, e.g. `{price: "630", priceCurrency: "TND"}` (current price) and `{price: "900", priceType: ListPrice}` (price before discount).
  - **`description` is structured:** `… de la Marque : Loewe – Référence : LW40128I 01A – Forme : Oeil de Chat – Style : Tendance – Matière du cadre : Plastique – …`
- **Product pages have no stock message and no `.posted_in`.** Stock comes from the listing card class, and gender and sun/optical from the title ("Lunette de Soleil Femme …").

## Changes

### 1. Parser (`stores/parser.py`), generic
- **`json_ld_fields`: price fallback.** When the offer has no `price`/`lowPrice`, read `priceSpecification` (a dict or a list). Take the first entry whose `priceType` is not ListPrice, StrikethroughPrice or MSRP, along with its currency. The rule that a price ≤ 0 counts as missing still applies in `merge`.
- **Description specs (new, opt-in per store).** When `cfg.description_specs` is true, the JSON-LD `description` is split on `–`, `—`, `|`, `•`, `;` and newlines. Each `Label : value` part becomes an entry in `raw_specs`. Non-breaking spaces are normalised, labels are 2–40 characters, and a table `specs` value wins over a description value on the same key.
- **Image fallback.** A CSS `image_url` that isn't http(s) (for example a `data:` placeholder) is ignored rather than passed on. Today it would make `ScrapedProduct` validation fail and drop the whole product whenever the product page couldn't be fetched.

### 2. Config model (`stores/config.py`)
- **New field** `description_specs: bool = False` on `ScraperConfig`.

### 3. Tagger (`stores/tagger.py`), `RULES_VERSION` 1 → 2
- **Spec label aliases:** `matiere du cadre`, `materiau du cadre` and `matiere de la monture` go to material. `gender`, `genre`, `sexe` and `le sexe` go to audience, using the existing `CATEGORY_TAGS` words, so "Femme, Homme" gives both women and men.
- **Store vocabulary aliases (tagger-local; `taxonomy.yaml` untouched, so the LLM prompt and Google Trends don't change):** scoped to spec values only.
  - `acier`, `acier inoxydable`, `inox` and `stainless steel` go to material/metal.
  - `carey` (Hawkers' word for tortoiseshell) goes to color/tortoiseshell.
- **Deliberately unmapped:** `Plastique` stays untagged, because it could be acetate or injected TR90 and we won't guess.
- **Outika:** after `retag-products`, it also gains audience tags from `Gender`, identical to its category tags, so no visible change.

### 4. YAML entry (`store_configs.yaml`)
```yaml
  mykenza.tn:
    name: "MyKenza"
    base_url: "https://www.mykenza.tn"
    lang: fr
    country: TN
    default_currency: TND
    delay_s: 1.5
    description_specs: true            # JSON-LD description: "Forme : Oeil de Chat – Style : … – Matière du cadre : …"
    listing:
      urls: ["/categorie-produit/lunettes-cadres/lunettes/lunettes-homme/",
             "/categorie-produit/lunettes-cadres/lunettes/lunettes-femme/"]
      pagination: { next: "a.next.page-numbers", max_pages: 10 }   # /page/N/ paths; robots: Disallow /*?
      product: "li.product.type-product"                            # excludes the subcategory tiles
      link: "a.woocommerce-LoopProduct-link"
    product_pages:
      enabled: true                    # shape, brand and price live in the product-page JSON-LD
      max_products: 300
    fields:                            # CSS fallbacks; JSON-LD is primary
      name:      { css: ".woocommerce-loop-product__title" }        # clean, without the "Spray Offert - 50%" promo text
      price:     { css: ".price" }                                   # "249 DT 499 DT" -> 249 (current price)
      image_url: { css: "img", attr: ["data-lazy-src", "data-src", "src"] }   # data: placeholders ignored
    flags:
      out_of_stock: { css: ".outofstock", exists: true }            # class on the card itself (descendant-or-self)
      categories:   { css: ".woocommerce-loop-product__title", regex: '(?i)(lunettes? de (?:soleil|vue)(?:\s+(?:femme|homme|mixte))?)' }
```
- **Scope of the first crawl:** the 10 newest pages of each gender listing is about 240 listed products, and fewer after de-duplicating unisex frames. Product pages are capped at 300, so a crawl takes roughly 8–10 minutes at 1.5 s per request, with no LLM. Raising `max_pages` to 20 later covers more of the ~1,000-frame catalog.
- **Expected tags on the sample:**
  - The Loewe page gives shape `cat_eye` from `spec:Forme`, plus audience women and product_type sun.
  - Ray-Ban "SQUARE" gives `square` from its name as well as from Forme.

## Tests (offline; written first)
- **`test_store_crawlers.py`:**
  - `priceSpecification` handling: the sale price is picked and ListPrice ignored.
  - Description-spec parsing: the real separators and non-breaking spaces, and a table value winning over a description value.
  - A `data:` image is ignored while the product survives.
  - A **mykenza replay test**: the shipped config against markup trimmed from the real site. It has a listing with 2 subcategory tiles, 2 products and a next link, plus a page 2; a product page with the JSON-LD above; one out-of-stock card; and robots.txt with `Disallow: /*?`. It asserts:
    - Price 630 TND, not 900.
    - Brand Loewe, and the name without the promo text.
    - `raw_specs` Forme "Oeil de Chat".
    - `out_of_stock` flags.
    - Categories "Lunette de Soleil Femme".
    - The tiles are ignored and no `?` URL is ever requested.
  - The shipped-config test now expects `{outika-eyewear.tn, mykenza.tn}`.
- **`test_tagger.py`:**
  - The new spec labels, and the steel and carey aliases (in specs only).
  - Audience from `Le sexe` and `Gender`.
  - `Plastique` untagged, and `RULES_VERSION == 2`.
  - The mykenza sample gives `cat_eye`.
- **Existing tests:** all 110 still pass.

## Files
- **Modified:**
  - `backend/app/collectors/stores/parser.py`
  - `backend/app/collectors/stores/config.py`
  - `backend/app/collectors/stores/tagger.py`
  - `backend/app/collectors/stores/store_configs.yaml`
  - `backend/tests/test_store_crawlers.py`
  - `backend/tests/test_tagger.py`
  - `docs/build-plan.md`: step 4, and the lunettek finding.
- **No DB schema, API or frontend changes.**

## Your commands afterwards (not run by me)
1. `.venv/Scripts/python -m app.cli retag-products` re-tags Outika with rules v2.
2. `.venv/Scripts/python -m app.cli crawl-store mykenza.tn` takes about 8–10 minutes and prints progress lines.
3. Then open `/tendances/shape/cat_eye` or `/tendances/shape/square`. They should show the first shape-based Présence en boutique.
