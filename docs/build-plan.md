# Eyewear Trend Intelligence: Build Plan

## Context
From the handwritten note: an **AI-powered app that tracks the latest eyewear trends**. It covers aesthetics, demand and fashion, broken down by **frame form (shape) and colors**, and shows the results on a **dashboard**. Data comes from **blogs, articles, eyewear stores and social media posts**. The idea and the prompt can still be expanded later.

- **One eyewear retailer uses the app (single tenant):** Noé & Noah. It is an internal tool for their buying and merchandising team.
- **French is the primary language.** The UI, AI summaries and reports are in French. Sources and search queries are **both French and English**.
- It is a real product. The stack is a Python API (FastAPI) with a Next.js frontend.
- The LLM sits behind a provider interface (`app/extraction/llm.py`), with the Anthropic SDK as the default implementation.

## Core idea: how the pipeline works
```
Collect (FR+EN) -> Extract (LLM) -> Normalize to taxonomy -> Score trends -> Dashboard (FR)
```
The key design choice is a **fixed, language-neutral taxonomy** (`backend/app/taxonomy/taxonomy.yaml`). The LLM reads French or English text and can only answer with its codes, which structured output enforces through Literal enums. The UI shows French labels, so "lunettes œil de chat" and "cat-eye glasses" count as the same trend. Each entry also carries bilingual search keywords.

## Architecture (as built)
```
backend/app/
  taxonomy/        taxonomy.yaml + loader/normalizer
  collectors/      rss_blogs.py, news_gdelt.py, google_trends.py, feeds.yaml, base.py (robots.txt, trafilatura)
  extraction/      llm.py (provider interface), schema.py (generated from taxonomy), service.py, prompts/ (versioned)
  scoring/         trends.py (weekly momentum + status), summary.py (French weekly summary)
  api/main.py      FastAPI routes
  jobs/            pipeline.py, scheduler.py (daily 06:00 Europe/Paris)
  demo.py, cli.py
frontend/          Next.js 16 + Tailwind v4 (see docs/ui-plan.md)
```
**Database:** SQLite by default, Postgres in docker-compose. Tables: `sources`, `documents`, `products`, `mentions` (evidence behind every trend), `search_interest`, `trend_snapshots`, `weekly_summaries`.

**Trend score:** weighted mentions (source weight × stance weight), growth versus the previous 4-week average, blended 30 % with Google Trends growth. Statuses are en_hausse / au_pic / stable / en_baisse.

## Phased roadmap
- **Phase 0–1 (done: backend):** taxonomy, RSS + GDELT news + Google Trends collectors, extraction, scoring, API, tests.
- **Phase 1 (in progress):** dashboard UI, designed in Figma first. See `docs/ui-plan.md`.
- **Phase 2:** store crawlers for about 5 retailers, extracting attributes from titles, specs and images.
- **Phase 3:** social media. Reddit first, then Instagram/TikTok/Pinterest through a licensed data provider (scraping them directly breaks their ToS).
- **Phase 4:**
  - Compare trends with Noé & Noah's own catalog and sales data.
  - Image-based trend detection.
  - Email alerts.

## Verification
- `pytest`: taxonomy normalization and scoring math.
- Extraction eval: 30–50 hand-labeled FR/EN articles.
- End-to-end: `python -m app.cli run`, then check the dashboard.

## Open decisions
- Retailer country, which sets the Google Trends geo (currently `FR`).
- LLM budget.
- Catalog and sales data access for Phase 4.
- Social media data provider.
