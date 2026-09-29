# Eyewear Trend Intelligence: Build Plan

## Context
From the handwritten note: an **AI-powered app that tracks the latest eyewear trends**. It covers aesthetics, demand and fashion, broken down by **frame form (shape) and colors**, and shows the results on a **dashboard**. Data comes from **blogs, articles, eyewear stores and social media posts**. The idea and the prompt can still be expanded later.

- **One eyewear retailer uses the app (single tenant):** Noé & Noah. It is an internal tool for their buying and merchandising team.
- **French is the primary language.** The UI, AI summaries and reports are in French. Sources and search queries are **both French and English**.
- It is a real product. The stack is a Python API (FastAPI) with a Next.js frontend.
- The LLM sits behind a provider interface (`app/extraction/llm.py`). The default implementation uses the Anthropic SDK with `claude-sonnet-5`.

## Core idea: how the pipeline works
```
Collect (FR+EN) -> Extract (LLM) -> Normalize to taxonomy -> Score trends -> Dashboard (FR)
```
The key design choice is a **fixed, language-neutral taxonomy** (`backend/app/taxonomy/taxonomy.yaml`). The LLM reads French or English text and can only answer with its codes, which structured output enforces through Literal enums. The UI shows French labels, so "lunettes œil de chat" and "cat-eye glasses" count as the same trend. Each entry also carries bilingual search keywords.

## Architecture (as built)
```
backend/app/
  taxonomy/        taxonomy.yaml + loader/normalizer
  collectors/      rss_blogs.py, news_gdelt.py, google_trends.py, backfill.py,
                   feeds.yaml (feeds, news queries, archive backfill), base.py (robots.txt, trafilatura)
  extraction/      llm.py (provider interface), schema.py (generated from taxonomy), service.py, prompts/ (versioned)
  scoring/         trends.py (weekly momentum + status), summary.py (French weekly summary)
  api/main.py      FastAPI routes (overview, trends, demand, mentions, sources, demo, CSV export, jobs)
  jobs/            pipeline.py (recorded as JobRun, live step progress), scheduler.py (daily 06:00 Europe/Paris)
  collectors/stores/  Phase 2 store catalogs: store_configs.yaml (one entry per domain, CSS-only rules),
                   config.py, parser.py (JSON-LD first, CSS fallback), base.py (async crawler), tagger.py
                   (rule-based taxonomy tags) - none of these touch the DB or an LLM; service.py persists
  migrations/      Alembic, applied automatically at startup
  demo.py, cli.py  click CLI: run, backfill, refresh-search, crawl-store, retag-products, seed-demo, clear-demo
frontend/          Next.js 16 App Router, React 19, plain CSS design tokens (light/dark),
                   hand-written SVG charts with table views. See docs/ui-plan.md and docs/design-brief.md
design/kimi/       HTML mockups A–F the frontend was ported from
```
**Database:** SQLite by default, Postgres in docker-compose. Tables:
- `sources`
- `documents`
- `products` (store catalog items, upserted by url)
- `product_tags` (product → taxonomy code links from the rule-based tagger, with provenance; color tags carry three tiers: `color_family` (Palier 1), `color_hex` (Palier 2, from the taxonomy) and `supplier_code` (Palier 3, a store's own variant code, from the crawler and never stored in the YAML))
- `mentions` (the evidence behind every trend)
- `search_interest`
- `trend_snapshots`
- `job_runs`
- `weekly_summaries`

Foreign keys: `documents` → `sources`, `products` → `sources`, `product_tags` → `products`, `mentions` → `documents`. The trend tables are joined on `(dimension, code)` in code.

**Sources:**
- **Feeds:** 17 RSS feeds. Trade press: Optique Mag, Vision Monday, Invision. FR and EN fashion media: Vogue, GQ, Grazia, M Le Monde, WWD, Hypebeast and others.
- **News:** GDELT news queries, best effort (rate-limited on the current network).
- **Search:** Google Trends for France.
- **Sitemap press:** Acuité (French optical trade press, no RSS), collected daily from its XML sitemap (`sitemap_news.py`). Only `/actualites/lunettes/`, with a 7-day window on each article's own date, at most 10 new articles per run.
- **Stores:** Outika (outika-eyewear.tn), MyKenza (mykenza.tn, sunglasses) and LaMode (lamode.tn, designer prescription frames), all Tunisia, via `crawl-store`, run manually. Free: no LLM.
- **Archives:** a one-off backfill of the trade press from sitemaps and paged feeds. It only collects, and the CLI prints the Claude cost of analysing what it collected before anything is spent.

**Trend score:**
- **Volume:** the sum of source weights over the week's mentions.
- **Momentum:** growth versus the previous 4-week average, blended 30 % with Google Trends growth.
- **Tone:** the balance of rising versus declining mentions, pooled over 4 weeks.
- **Statuses:**
  - `en_hausse`: rising.
  - `au_pic`: the 4-week least-squares slope flattens after a sustained rise.
  - `stable`
  - `en_baisse`: momentum ≤ −25 %, or at least half of the mentions describe the look as fading.
  - `faible` ("Peu de données"): fewer than 5 weighted mentions in 4 weeks. It overrides every other status.
- **Summary:** it only calls out trends backed by enough data. Weak signals are listed as "à surveiller".

## Phased roadmap
- **Phase 0–1 (done: backend):** taxonomy, collectors, extraction, scoring, API, Alembic migrations, tests (61 passing).
- **Phase 1 (done: dashboard):** the UI was designed first (Figma, then the Kimi mockups) and ported to Next.js. Screens:
  - Overview
  - Tendances with trend detail
  - Demande
  - Sources
  - Printable weekly report (`/rapport`)

  The UI also has dark mode, CSV export, demo data, and a manual refresh that shows live progress.
- **Phase 1.5 (in progress: data depth):** backfill the trade press archives (about 12 weeks). Then run the Claude analysis on the backfilled articles, a one-off cost of a few dollars, so trends have enough history to leave "Peu de données".
- **Phase 2 (in progress: store catalogs, zero LLM):**
  - Step 1 (done): config-driven crawler foundation. `ScrapedProduct` contract, validated YAML rules per domain (CSS only, XPath refused), schema.org JSON-LD first with CSS fallback, async crawler with robots.txt, `StoreSyncService` upsert by url. Crawling modules have no DB or LLM imports; an AST test enforces this.
  - Step 2 (done): Outika config and the `crawl-store` CLI. First live crawl: 222 products. Data-quality fixes: a price ≤ 0 counts as missing (Outika publishes 0.00 for sold-out items), stock status comes from the page and not the JSON-LD (which says "InStock" for sold-out items), categories captured, empty flags stored as SQL NULL.
  - Step 3 (done): rule-based tagging (`tagger.py` → `product_tags`) and "Présence en boutique" on the trend detail page: SKU count, price by currency, product sample.
  - Step 4 (in progress): second store, MyKenza (mykenza.tn), a multi-brand store (Ray-Ban, Loewe…). Shapes come from its JSON-LD description ("Forme : Oeil de Chat – Style : … – Matière du cadre : …"), which the new opt-in `description_specs` reads into `raw_specs`. Three general parser additions came with it:
    - the price is read from `offers.priceSpecification` (the sale price, not the ListPrice),
    - `@id` references in the JSON-LD graph are resolved (Yoast's `"image": {"@id": …}`),
    - lazy-load `data:` placeholder images are ignored.

    Tagger rules v2: frame-material and gender spec labels, plus store vocabulary aliases in specs only (acier/inox → metal, carey → tortoiseshell). `taxonomy.yaml` is untouched.
  - Step 5 (discount signal): `products.list_price` (migration 76b043af5674), read from JSON-LD `priceSpecification` (ListPrice / StrikethroughPrice) or a CSS rule, always from the same source as the selling price, and kept only when above it. Markdown is read **relative to each store's usual markdown** (MyKenza runs a store-wide -25 to -50 % sale). Stores without list prices are excluded. A declining attribute discounted at least 10 pts deeper than usual is a "déstockage" stock risk. Shown on the trend detail page (`retail_markdown`), in the report and in the weekly summary's input.
  - Step 6 (third store): LaMode "Cadres optiques", about 183 designer prescription frames. The shape comes from the "Forme Lunette" feature (tagger rules v4). Its "VISAGE" rows (recommended face shapes) are deliberately ignored. It gives no discount signal: its JSON-LD has no list price.
  - Step 7 (3-tier colors, migration a41c7d9e2b56, tagger rules v5): color tags carry family, hex and an optional supplier/variant code. A crawler that exposes variants writes `flags["variants"] = [{"code": "HV/BL", "color": "Havana"}, …]`; each label the tagger recognises gives one tag per code, so two codes of one family coexist. Uniqueness is `(product, dimension, code, supplier_code)` plus a partial unique index for uncoded tags (SQL treats NULLs as distinct). Existing tags were backfilled by `retag-products`; no store exposed variant codes yet.
  - Gaps per product type (done): opportunities and risks are computed within the prescription shelf and the sunglasses shelf separately (product_type tags), while store discount baselines stay store-wide. A shelf with no comparable data is skipped. Sunglasses-only attributes (shield / wraparound frames, tinted lenses) are never prescription opportunities. First real result: aviator is rising in the press but only 3 % of the prescription shelf.
  - Scouting (2026-09-27):
    - lunettek.com has ideal structured specs (Forme, Couleur, Matériau), but its catalog is dormant: 48 of 48 sampled products are out of stock and all images date from 2021.
    - lamode.tn titles are brand plus model, with no shape.
    - luneti.tn is rendered in the browser (Next.js), with no product HTML for our crawler.
    - easylunettes.fr refuses the crawler (HTTP 405).
  - Lesson: Outika product names are model names (EVAN, ADONIA) with no shape words, so shapes cannot be tagged for this store. **Store selection criterion from now on: descriptive product titles or specs.** Image-based shape detection stays in Phase 4, because it needs a vision model.
- **Shelf vs. Signal, first version (done):** computed opportunities and stock risks, in the printable report (page 2, "Marché Tunisien") and in the weekly summary's input (`scoring/retail.py`). A dimension is only compared when enough products carry it and the stores' own vocabulary for it is mostly understood (≤ 30 % unrecognised values); today that means shape and material, but not colour (internal SKU codes) or style (Sport / Classique / Tendance).
- **Shelf vs. Signal on the overview (done):** a "Presse vs rayons tunisiens" block on the Vue d'ensemble page, with opportunities and stock risks per shelf, one row per attribute (for example "absent des rayons optique et solaire"), each linking to its trend page. It is hidden without store data and never breaks the page if the endpoint fails.
- **Phase 3:** social media: **Facebook, Instagram and Pinterest**, through a licensed data provider or the platforms' official APIs. Scraping them directly breaks their ToS.
- **Phase 4:**
  - Compare trends with Noé & Noah's own catalog and sales data.
  - Image-based trend detection.
  - Email alerts.

## Verification
- `pytest`: taxonomy, scoring math, API, migrations, sources/demo, backfill, store crawling, tagging and CLI (all offline, using httpx mock transports).
- Extraction eval: 30–50 hand-labeled FR/EN articles (not done yet).
- End-to-end: `python -m app.cli run` (or "Actualiser les données" in the UI), then check the dashboard.

## Decisions
- **Retailer country: Tunisia.** French stays the UI language. The Google Trends geo stays `FR` (`market_geo`) as a proxy. Checked on 2026-09-27 over 12 months: 12 French shape keywords had non-zero weeks in France (e.g. "lunettes rondes" 54/54 weeks, "lunettes masque" 50/54), but only 0–1 of 54 weeks in Tunisia. Even plain "lunettes" was non-zero on only a third of days. Tunisian search volume is below Google's reporting threshold.
- **LLM budget: $5 initial top-up.** That is about 500 article analyses at ~$0.01 each. The per-run cap `max_extract_per_run` is 100 (about $1), so a single run cannot use the whole balance.
- **Social media: Facebook, Instagram, Pinterest** (Phase 3).

## Open decisions
- Catalog and sales data access for Phase 4.
- Social media data provider or API access for Facebook, Instagram and Pinterest.
