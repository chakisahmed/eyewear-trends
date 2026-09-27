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
  migrations/      Alembic, applied automatically at startup
  demo.py, cli.py  (run, backfill, seed-demo, clear-demo)
frontend/          Next.js 16 App Router, React 19, plain CSS design tokens (light/dark),
                   hand-written SVG charts with table views. See docs/ui-plan.md and docs/design-brief.md
design/kimi/       HTML mockups A–F the frontend was ported from
```
**Database:** SQLite by default, Postgres in docker-compose. Tables:
- `sources`
- `documents`
- `products` (empty until Phase 2)
- `mentions` (the evidence behind every trend)
- `search_interest`
- `trend_snapshots`
- `job_runs`
- `weekly_summaries`

Foreign keys: `documents` → `sources`, `products` → `sources`, `mentions` → `documents`. The trend tables are joined on `(dimension, code)` in code.

**Sources:**
- **Feeds:** 17 RSS feeds. Trade press: Optique Mag, Vision Monday, Invision. FR and EN fashion media: Vogue, GQ, Grazia, M Le Monde, WWD, Hypebeast and others.
- **News:** GDELT news queries, best effort (rate-limited on the current network).
- **Search:** Google Trends for France.
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
- **Phase 2:** store crawlers for about 5 retailers, extracting attributes from titles, specs and images into `products`.
- **Phase 3:** social media: **Facebook, Instagram and Pinterest**, through a licensed data provider or the platforms' official APIs. Scraping them directly breaks their ToS.
- **Phase 4:**
  - Compare trends with Noé & Noah's own catalog and sales data.
  - Image-based trend detection.
  - Email alerts.

## Verification
- `pytest`: taxonomy, scoring math, API, migrations, sources/demo and backfill (offline, using an httpx mock transport).
- Extraction eval: 30–50 hand-labeled FR/EN articles (not done yet).
- End-to-end: `python -m app.cli run` (or "Actualiser les données" in the UI), then check the dashboard.

## Decisions
- **Retailer country: Tunisia.** French stays the UI language. The Google Trends geo is still `FR` (`market_geo`). Switching it to `TN` is pending a check that Tunisian search volume for eyewear keywords is not too low to read.
- **LLM budget: $5 initial top-up.** That is about 500 article analyses at ~$0.01 each. The per-run cap (`max_extract_per_run`, 500) should be lowered so a single run cannot use the whole balance.
- **Social media: Facebook, Instagram, Pinterest** (Phase 3).

## Open decisions
- Catalog and sales data access for Phase 4.
- Social media data provider or API access for Facebook, Instagram and Pinterest.
