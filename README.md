# Noé & Noah · Tendances lunettes

Internal AI trend-intelligence dashboard for the Noé & Noah buying team (French UI, FR + EN sources).
It collects press, news and Google Trends data, extracts eyewear attributes (shape, color, material,
style) with Claude, scores weekly trends, and shows them in a Next.js dashboard.

```
backend/    FastAPI + SQLAlchemy + Alembic (collectors, Claude extraction, scoring, API)
frontend/   Next.js 16 (App Router) dashboard, design system in app/styles/
design/     Approved HTML mockups (A–F) + shared.css / shell.js they were built on
docs/       Build plan, UI plan, design brief
```

## Run it locally

**Backend** (Python 3.12+), from `backend/`:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev,trends]"
.venv/Scripts/python -m uvicorn app.api.main:app --port 8000
```

- The database (SQLite by default, `DATABASE_URL` for Postgres) is migrated automatically on start.
- Claude extraction needs `ANTHROPIC_API_KEY` (or an `ant auth login` profile).
- Demo data: `python -m app.cli seed-demo`, or the "Charger la démo" button in the empty dashboard.
- Tests: `.venv/Scripts/python -m pytest`

**Frontend** (Node 20+), from `frontend/`:

```bash
npm install
npm run dev
```

Open http://localhost:3000. The frontend proxies `/api/*` to the backend; set `API_URL` if it
is not on `http://127.0.0.1:8000`.

## Pages

| Route | Screen |
|---|---|
| `/` | Vue d'ensemble: KPIs, AI weekly summary, top trends per dimension, declines, latest sources |
| `/tendances?dim=&weeks=` | Tendances: weekly mentions chart, share of voice (+ color palette), attribute table |
| `/tendances/[dimension]/[code]` | Détail: stats, mentions and Google Trends charts, tone, brands, evidence |
| `/demande?dim=` | Demande: Google Trends interest, France vs Monde, per attribute |
| `/sources` | Sources: every analysed extract, filterable, paginated |
| `/rapport` | One-page A4 report (print / PDF), always light |

"Actualiser les données" runs the full pipeline (collection **and Claude extraction**, which uses API
credit) and refreshes the page when it finishes.
