# UI Plan: Noé & Noah trend dashboard

## Context
The backend already exists: taxonomy, collectors, Claude extraction, scoring and a FastAPI API, with 20 tests passing. The frontend is still an empty Next.js 16 scaffold. The user wants the UI **designed in Figma first, then coded from that design**, and the design planned before anything is drawn.

Decisions so far:
- **Client:** Noé & Noah, a single eyewear retailer.
- **Language:** the UI is in French.
- **Devices:** desktop first, but usable on mobile.
- **Extras in v1:** trend detail page, dark mode, a run-collection button with status, and export (CSV + PDF).

## 1. Brand and design tokens
Colors sampled from the logo:

| Token | Light | Dark | Use |
|---|---|---|---|
| `brand-blue` | `#2157A1` | `#4A7FCC` | sidebar, primary buttons, links, focus ring |
| `brand-coral` | `#DC8B71` | `#E59C84` | logo, active nav marker, highlights. **Never body text on white** (only ~2.6:1 contrast) |
| `surface-0` / `surface-1` | `#F7F6F3` / `#FFFFFF` | `#121417` / `#1A1D21` | page / card |
| `text-primary` / `secondary` / `muted` | `#14171C` / `#4E5561` / `#7B8290` | `#F3F4F6` / `#C2C7D0` / `#8A919C` | text |
| `border` | `#E4E2DD` | `#2A2E34` | dividers, card outlines |

- **Status colors** (fixed, and always shown with an icon and a label, never color alone):
  - en hausse ↑ good `#0CA30C`
  - au pic ▲ warning `#FAB219`
  - stable → gray
  - en baisse ↓ critical `#D03B3B`
- **Chart series:** use the dataviz reference categorical palette in fixed order, with `brand-blue` swapped into slot 1. Run `validate_palette.js` for light and dark. If the brand blue fails, keep the reference blue. Show at most 6 series, and fold the rest into "Autres".
- **Frame-color swatches:** colors from the taxonomy (écaille, doré…) appear only as swatch chips with a 1px ring, so light colors like `clear` stay visible. Chart lines never use them.
- **Typography:** Montserrat Semi Bold/Bold for headings, since it is closest to the wide geometric wordmark. Inter for body text, with tabular numbers for figures. *Confirm the brand font if Noé & Noah has one.*
- **Spacing:** 4-px scale, 12-px card radius, subtle shadow in light mode and border only in dark mode.

## 2. App shell (all pages)
- **Left sidebar (240 px, brand blue):**
  - Noé & Noah logo in white and coral at the top.
  - Navigation with icons: Vue d'ensemble · Tendances · Demande · Sources.
  - Active item gets a coral marker.
  - Bottom: last update ("Mis à jour il y a 3 h") and the dark-mode toggle.
- **Top bar:**
  - Page title.
  - Week selector ("Semaine du 21 sept. 2026").
  - **Actualiser les données** button, which shows a spinner and "Collecte en cours…" while running.
  - **Exporter** menu: CSV of the current table, or the weekly PDF report.
- **Demo banner:** a coral strip saying "Données de démonstration" whenever demo data is loaded.
- **Mobile (< 768 px):** the sidebar becomes a top bar with a menu drawer, cards stack in one column, and wide tables scroll inside their card.

## 3. Screens

**A. Vue d'ensemble (`/`)**
1. **KPI row, four stat tiles:** articles analysés, mentions, sources, en attente d'analyse.
2. **Résumé de la semaine card:** the AI text in French, with a "Généré par IA · Claude" badge and the date.
3. **Tendances en hausse:** four columns (Formes, Couleurs, Matières, Styles). Each column shows its top 5 rows: swatch or shape icon, label, 8-week sparkline, and momentum badge (+42 % ↑). Clicking a row opens the trend detail page.
4. **En baisse:** a compact list.
5. **Dernières sources:** a preview of 5 quotes with a "Voir tout" link.

**B. Tendances (`/tendances?dim=shape`)**
- Tabs for Formes · Couleurs · Matières · Styles, plus a period filter (8 / 12 / 26 semaines), all on one row.
- **Main line chart:** top 6 attributes over time, with a legend and direct labels. A crosshair tooltip lists every series for the hovered week.
- **Side panel:** a horizontal bar chart of each attribute's share this week.
- **Couleurs tab only:** a "Palette de la semaine" strip where each real swatch is sized by its share.
- **Table:** attribut, part, mentions, momentum, statut, and a link to the detail page. A "Vue tableau" toggle offers the table as an accessible alternative to the chart.

**C. Détail d'une tendance (`/tendances/[dimension]/[code]`)**
- **Header:** swatch or icon, label (e.g. "Œil de chat"), status badge, momentum.
- **Stat tiles:** mentions this week, 4-week average, share of the dimension, and French search interest.
- **Two separate charts, never on a dual axis:** mentions over time, and Google Trends interest France vs Monde.
- **Stance breakdown:** stacked bar of rising, neutral and declining mentions.
- **Brands mentioned together** with this trend.
- **Evidence list:** quote, source, FR/EN tag, date and link.

**D. Demande (`/demande?dim=shape`)**
- A grid of small cards, one per attribute, sorted by growth. Each card shows a mini chart with two lines, France and Monde, on the same 0–100 scale.
- A note explaining what Google Trends interest means.

**E. Sources (`/sources`)**
- Filter row: dimension, attribut, langue (FR/EN), type (presse / actualités / boutique / social), période.
- **Evidence cards:** quote, French summary, source, date, language tag, attribute chips and an external link.
- Pagination.

**F. Rapport PDF (`/rapport?week=`)**
- A print-optimized page (A4, light theme, logo) with the summary, the top trends per dimension, the declining trends and key quotes.
- The Exporter menu opens it and triggers print, so the user saves it as a PDF.

**States on every screen:**
- Loading skeletons.
- Empty state: "Aucune donnée pour l'instant", with buttons to *Lancer la première collecte* or *Charger la démo*.
- API error card with a retry button.

## 4. Figma workflow
1. **Create the file.** "Noé & Noah · Tendances lunettes" in the team plan `team::1051947534357986432`, then upload the logo.
2. **Page "Fondations":**
   - Color variables with Light/Dark modes and proper scopes.
   - Text styles.
   - Spacing variables.
   - The status and series palettes.
3. **Page "Composants":**
   - Nav item, button (primary / secondary / ghost), status badge.
   - Stat tile, trend row with sparkline, chart card, tabs and filter bar.
   - Evidence card, swatch chip, banner, empty state.
4. **Page "Écrans · Desktop 1440":** screens A–E, built from component instances with realistic French demo content.
5. **Page "Écrans · Mobile 390":** Vue d'ensemble and Détail.
6. **Dark mode:** one example screen (Vue d'ensemble) in dark mode.
7. **Review:** share screenshots and the Figma link, then iterate on feedback **before any frontend code**.

## 5. After design sign-off: implementation outline
- **Frontend (Next.js 16, App Router, Tailwind v4, Recharts):**
  - `app/layout.tsx` for the shell.
  - `app/page.tsx`, `app/tendances/page.tsx`, `app/tendances/[dimension]/[code]/page.tsx`, `app/demande/page.tsx`, `app/sources/page.tsx`, `app/rapport/page.tsx`.
  - `components/`: charts as client components, plus cards, badges and filters.
  - `lib/api.ts`: server fetch helper that calls `connection()` from `next/server`, because this Next version dropped the `dynamic` segment config.
  - `app/actions.ts`: server actions for "run collection".
  - Tokens as CSS variables in `app/globals.css`, with the dark theme applied through both `prefers-color-scheme` and `[data-theme]`.
- **Backend additions** in `backend/app/api/main.py`, reusing the existing scoring and models:
  - `GET /api/jobs/status` (running, last run, last report). Needs a small `job_runs` table updated by `run_pipeline` in `app/jobs/pipeline.py`.
  - `GET /api/trends/{dimension}/{code}`: detail series, stance counts, brands and evidence.
  - An 8-week `spark` array added to each `/api/overview` row.
  - `?week=` support on overview and trends.
  - `GET /api/export/{dimension}.csv`.
- **Logo:** copy it to `frontend/public/brand/`. Ask for an SVG or high-resolution version for the final build.

## Verification
- **Figma:** screenshot every screen, checking for clipped text, overlap and both themes. Run the chart palette through `validate_palette.js` for light and dark.
- **Code:**
  - `npm run build` and `npm run lint`.
  - Run the backend with `python -m app.cli seed-demo`, then open every page in the browser pane at 1440 px and 390 px, in both themes.
  - Click Actualiser and watch the status change.
  - Export the CSV and PDF.
  - Compare the result against the Figma screenshots.
- **Backend:** pytest cases for the new endpoints.

## Open items
- The Noé & Noah brand font, if any, and an SVG of the logo.
- Whether the PDF report needs extra content, such as buyer recommendations.
