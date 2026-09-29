# Design brief: Noé & Noah trend dashboard

You are a senior product designer and front-end engineer. Design and code a **production-quality internal web dashboard**. Output **one self-contained HTML file** per request (inline `<style>` and `<script>`, no build step). The HTML will later be ported to Next.js + Tailwind v4, so keep the markup semantic, the CSS variable-based and the components clearly separated.

## 1. Product
- **Client:** Noé & Noah, an eyewear retailer (optical frames + sunglasses). Single tenant, internal tool.
- **Users:** the buying and merchandising team. They open it every Monday and in buying meetings to decide which frames to stock.
- **What it does:** an AI reads fashion press, news, eyewear stores and social media in French and English every day, and extracts eyewear attributes: **frame shape, color, material and style**. It scores each attribute weekly (mention volume, growth vs the previous 4 weeks, Google Trends search interest) and writes a weekly summary in French.
- **UI language: French** (fr-FR). Number format `1 284`, `+42 %` (narrow space before %), dates `21 sept. 2026`.
- **Tone:** premium, calm and data-dense but airy. Think Linear or Stripe dashboard quality, with a fashion touch. No stock illustrations or emoji.

## 2. Brand
- Logo: a coral "N" monogram above the wordmark **NOÉ & NOAH** (wide geometric sans, uppercase). Use `<img src="brand/noe-noah-logo-coral.png" alt="Noé & Noah">` (transparent PNG, 618×325), about 120 px wide in the sidebar.
- Fonts (Google Fonts): **Montserrat** 600/700 for headings and big numbers, **Inter** 400/500/600 for everything else. Use `font-variant-numeric: tabular-nums` on figures.

### Tokens (use exactly these CSS custom properties)
| token | light | dark |
|---|---|---|
| --brand-blue | #2157A1 | #4A7FCC |
| --brand-coral | #DC8B71 | #E59C84 |
| --surface-page | #F7F6F3 | #121417 |
| --surface-card | #FFFFFF | #1A1D21 |
| --surface-subtle | #F1EFEA | #22262B |
| --surface-sidebar | #2157A1 | #15325C |
| --surface-sidebar-active | #1A4885 | #1E4273 |
| --text-primary | #14171C | #F3F4F6 |
| --text-secondary | #4E5561 | #C2C7D0 |
| --text-muted | #7B8290 | #8A919C |
| --text-on-brand | #FFFFFF | #FFFFFF |
| --text-on-brand-muted | #C9D6EC | #A9BCDB |
| --text-link | #2157A1 | #7FA6E0 |
| --border | #E4E2DD | #2A2E34 |
| --border-strong | #CFCCC5 | #3A3F47 |
| --status-up / --status-up-bg | #0CA30C / #E7F6E7 | #0CA30C / #16301A |
| --status-peak / --status-peak-bg | #FAB219 / #FEF4DC | #FAB219 / #3A2E10 |
| --status-stable / --status-stable-bg | #8A919C / #EEF0F2 | #8A919C / #262A30 |
| --status-down / --status-down-bg | #D03B3B / #FBE9E9 | #D03B3B / #3A1B1B |
| --banner-demo-bg | #FBEDE7 | #3A2620 |
| --chart-grid | #ECEAE5 | #2A2E34 |
| --series-1…6 | #2157A1 #EB6834 #1BAF7A #EDA100 #E87BA4 #008300 | #4A7FCC #D95926 #199E70 #C98500 #D55181 #008300 |

- Spacing is a 4-px scale (4, 8, 12, 16, 20, 24, 32, 40).
- Radius: 6 for controls, 12 for cards, 999 for pills.
- Card shadow in light mode: `0 1px 3px rgba(20,23,28,.06), 0 4px 12px rgba(20,23,28,.05)`. In dark mode: border only, no shadow.
- **Dark mode:** define dark values under `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {…} }` and again under `:root[data-theme="dark"]`. Add a working theme toggle in the sidebar that sets `data-theme` on `<html>`.
- Coral is an accent only (logo, active-nav marker, AI icon, quote bar). **Never use coral for text on white** (contrast is too low).

## 3. Hard rules for data display (non-negotiable)
1. **Status is never color alone.** Every status badge shows an icon, the value and a tinted background. **The value text is always `--text-primary`; only the icon takes the status color** (status colors on their tints fail WCAG AA, e.g. yellow on cream is 1.7:1):
   - ↑ en hausse (momentum ≥ +25 %)
   - ▲ au pic (near its 8-week high after a real climb, but growth has slowed or stopped)
   - → stable
   - ↓ en baisse (mention volume ≤ −25 %, OR most recent coverage calls it fading). For the second case, show why, e.g. "↓ 100 % d'avis en recul" instead of a volume percentage.
2. **Never use a dual-axis chart.** Mentions and Google Trends interest are always separate charts.
3. Chart series use `--series-1…6` in that fixed order, with at most 6 series (fold the rest into "Autres"). A color always follows the same entity when filters change.
4. **Sparklines and small charts must not exaggerate noise.** Never stretch a series to its own min and max. Use a vertical range of at least 60 % of the series' peak, centered on the data and never below 0: `span = max(hi − lo, 0.6 × hi, 1)`, `min = max(0, (hi + lo) / 2 − span / 2)`. A stable 8, 8, 9, 8 must look almost flat, while 3 → 14 still fills the height.
5. Charts need a legend when there are 2+ series. Also direct-label the line ends when there are 4 or fewer series. Thin 2-px lines, recessive grid (`--chart-grid`), and a hover crosshair with a tooltip listing every series for that week.
6. Frame **colors** (écaille, doré…) are shown as round swatch chips with a 1-px `--border-strong` ring, so white and clear colors stay visible. **Chart lines for the color dimension are drawn in the color's real hex** (stakeholder requirement, 2026-09-29: the "noir" curve is black, never the palette blue). Contrast guard: a hex under 3:1 against the card in the current theme (ivory or clear on white, black or tortoiseshell on the dark card) gets a soft halo in `--text-secondary` behind the line, plus a ring on markers and legend lines (`lib/chroma.ts`, `.halo` in `shared.css`). Two series that share one hex (France vs Monde) are told apart by a dashed second line. Shapes, materials and styles keep `--series-1…6`.
7. Text uses text tokens, never series or status colors.
8. Every chart has a "Vue tableau" toggle that shows the same data as an accessible table.
9. Charts are hand-written **inline SVG** (no chart library), responsive via `viewBox`.

## 4. App shell (every screen)
- **Sidebar**, 240 px, `--surface-sidebar`:
  - Logo at the top.
  - Navigation with 20-px line icons (Lucide style, inline SVG): **Vue d'ensemble · Tendances · Demande · Sources**.
  - The active item gets a 3-px coral bar on the left and the `--surface-sidebar-active` background.
  - Footer: "Mis à jour il y a 3 h" + "26 sept. 2026 · 06:02", then the "Mode sombre" toggle.
- **Main area** (`--surface-page`, 32-px padding). **Cap the content at 1,280 px wide, centered**, so on wide screens labels, sparklines and badges stay close together:
  - Top bar: page title (Montserrat 28/700) plus a one-line subtitle.
  - Top-bar controls on the right: week selector ("Semaine du 21 sept." with a chevron), a secondary button **Exporter** (download icon, opens a small menu: "Tableau (CSV)", "Rapport PDF"), and a primary blue button **Actualiser les données** (refresh icon).
  - When clicked, the primary button becomes a disabled "Collecte en cours…" state with a spinner.
- **Demo banner** under the top bar: `--banner-demo-bg` background, 1-px coral border, AI sparkle icon, the text "Données de démonstration : les tendances affichées sont fictives en attendant la première collecte." and a "Retirer la démo" link.
- **Responsive:** desktop first (1440). At 768 px or less, the sidebar collapses into a top bar with the logo and a hamburger that opens a drawer, grids become one column, and tables scroll horizontally inside their card.

## 5. Components to design and reuse
- **KPI tile:** uppercase label (11 px, letter-spacing 0.06em, muted), big value (Montserrat 28/700), small detail line.
- **Trend row:** a 36-px visual slot, the label (single line, ellipsis), an 8-week sparkline (72×24, `--series-1`, dot on the last point) and a status badge. The whole row is clickable, with a subtle hover.
  - The visual slot shows a **frame-shape glyph** for shapes: small inline SVG line drawings of two lenses and a bridge (cat-eye, round, rectangle, aviator, oversize, geometric/hexagonal).
  - It shows a **color swatch** for colors, and a neutral dot for materials and styles.
  - *Sans monture* (rimless) is drawn as frameless lenses: thin dashed lens outlines with only the bridge and temples solid.
- **Status badge**, **chip/pill**, **tabs** (underline style, blue 2-px underline when active), **select**, **source card**, **empty state**, **skeleton loader** and **error card** (with a "Réessayer" button).
- **Source card:** source name (600) · date · language pill (FR/EN) · external-link icon, then a verbatim quote with a 3-px coral left bar. Below it, an "Résumé IA" line in secondary text and attribute chips.

## 6. Screens
Build the requested screen with this realistic demo data.

### A. Vue d'ensemble
1. **KPI row:**
   - Articles analysés **1 284** (+86 cette semaine)
   - Mentions d'attributs **4 912** (+312 cette semaine)
   - Sources suivies **47** (FR 21 · EN 26)
   - En attente d'analyse **12** (Prochaine collecte à 06:00)
2. **Card "Résumé de la semaine":** AI sparkle icon in coral, pill "Généré par IA · Claude", and on the right "Basé sur 312 mentions · 26 sept.". The bullets:
   - Œil de chat : +68 % de mentions, portée par la presse FR et EN. C'est la forme la plus citée de la semaine.
   - Transparent / cristal : +52 %, souvent associé aux montures oversize en acétate.
   - Matières recyclées et biosourcées : +47 %, un signal en hausse continue depuis 6 semaines.
   - L'écaille atteint un pic (+9 %) : toujours très présente, mais sa croissance ralentit.
   - Rectangulaire fine (−38 %) et style Y2K (−41 %) reculent nettement.

   Close the card with a highlighted action box: "**À faire côté achats :** renforcer l'œil de chat et l'oversize en acétate transparent ou écaille ; limiter les réassorts de rectangulaires fines."
3. **"Tendances de la semaine"** (note: "Classées par momentum sur 4 semaines · les attributs en baisse sont listés plus bas"): a 2×2 grid of cards (Formes, Couleurs, Matières, Styles), each with its top 5 attributes by momentum, **never including attributes that are en baisse** (those appear only in the "En baisse" card), and a "Voir tout →" link:
   - **Formes:** Œil de chat +68 % ↑ · Oversize +41 % ↑ · Géométrique +37 % ↑ · Aviateur +9 % ▲ · Ronde / Panto +3 % →
   - **Couleurs:** Transparent / Cristal #E8EEF2 +52 % ↑ · Marron / Cognac #6B4226 +34 % ↑ · Écaille #8B5A2B +9 % ▲ · Doré #C9A227 +6 % → · Noir #1A1A1A +1 % →
   - **Matières:** Recyclé / Biosourcé +47 % ↑ · Acétate +29 % ↑ · Titane +15 % ▲ · Bois / Corne +2 % → · Métal −4 % →
   - **Styles:** Rétro / Vintage +38 % ↑ · Statement +33 % ↑ · Luxe +11 % ▲ · Minimaliste −6 % → · Geek-chic / Intello −8 % →
4. **Bottom row:**
   - Card "En baisse": Pastel −44 %, Y2K −41 %, Rectangulaire fine −38 %, Sans monture −27 %.
   - Card "Dernières sources", with 4 one-line quotes:
     - Vogue France FR: « L'œil de chat revient en force cet automne… »
     - GQ EN: « Clear frames are the quiet It-accessory of the season. »
     - Harper's Bazaar EN: « Recycled acetate is no longer niche… »
     - Madmoizelle FR: « Adieu les petites lunettes rectangulaires… »

### B. Tendances (`?dim=shape`)
- **Filter row:** tabs Formes · Couleurs · Matières · Styles, plus a period select (8 / 12 / 26 semaines).
- **Main line chart:** weekly weighted mentions over 12 weeks for the top 6 attributes of the tab, with crosshair tooltip, legend and direct labels. Make up plausible series consistent with section A. For example, Œil de chat goes from 3 to 14 per week, and Rectangulaire from 10 to 4.
- **Right panel:** horizontal bars of "Part de voix cette semaine" (%). On the Couleurs tab, add a "Palette de la semaine" strip where each real swatch's width follows its share.
- **Table:** Attribut, Part, Mentions (sem.), Momentum (badge), Statut, and a "Détail →" link.

### C. Détail d'une tendance (Œil de chat)
- **Header:** glyph, "Œil de chat", badge ↑ +68 %, and the subtitle "Forme de monture · en hausse depuis 5 semaines".
- **Stat tiles:** Mentions cette semaine **14**, Moyenne 4 sem. **8,3**, Part des formes **21 %**, Intérêt de recherche FR **62/100**.
- **Two charts side by side:**
  1. "Mentions par semaine", 12 weeks, 1 series, so no legend box.
  2. "Intérêt de recherche Google" with 2 lines, France and Monde, on a 0–100 scale.
- **Tonalité des mentions:** a 100 % stacked bar (en hausse 71 %, neutre 24 %, en recul 5 %) with labels.
- **Marques citées:** chips (Gucci, Jimmy Fairly, Ray-Ban, Celine, Krys).
- **Evidence list:** 4 source cards.

### D. Demande (`?dim=shape`)
- A grid of small cards (3 per row), one per attribute and sorted by growth. Each card has the label, a badge, and a mini chart with France and Monde lines (0–100, same scale), plus the legend "France / Monde".
- A note card explains: « L'intérêt Google Trends est relatif (0–100) : 100 = pic de popularité du mot-clé sur la période. Les mots-clés sont suivis en français et en anglais. »

### E. Sources
- **Filter row:** Dimension, Attribut, Langue (Toutes/FR/EN), Type (Presse, Actualités, Boutique, Réseaux sociaux), Période.
- **Result count** ("15 extraits"), always equal to the items the list and pagination actually show, filtered or not.
- A list of 6 source cards, then pagination.

### F. Rapport PDF (`/rapport`)
- An A4 print-optimized page, always in the light theme, with an `@media print` stylesheet.
- **Header:** logo, "Rapport tendances lunettes", "Semaine du 21 septembre 2026".
- **Content:** the summary, a compact table of top trends per dimension with badges, the declining trends, and 3 key quotes.
- **Footer:** "Généré automatiquement · Noé & Noah · page 1/1".

## 7. Quality bar
- Pixel-perfect alignment, a consistent 24-px grid gap and generous white space.
- Hover and focus states on every interactive element. Keyboard focus ring: 2 px `--brand-blue` with 2-px offset.
- WCAG AA contrast for all text. Icons in buttons carry `aria-label` or visible text.
- Check both themes visually before answering. Nothing overflows at 1440, 1024 or 390 px.

## 8. Shared design system (screens B–F)
The design system already exists in two shared files, attached below the brief with screen A's page markup as the reference:
- **`shared.css`**: all tokens (light + dark), the app shell, and the components (card, KPI tile, trend row, badge, pill, swatch, tabs, buttons, select…).
- **`shell.js`**: theme toggle, mobile drawer, demo banner, export menu, refresh button, frame-shape glyphs (`<span data-glyph="cat-eye|oversize|geometric|aviator|round|rectangle|square|rimless">`) and sparklines (`<svg class="spark" data-points="…">`).

Rules:
- **Link them; never copy them.** Put `<link rel="stylesheet" href="shared.css">` in `<head>` (after the Google Fonts link) and `<script src="shell.js"></script>` at the end of `<body>`, before the page's own script. **Do not repeat any CSS rule from shared.css or any code from shell.js.** Duplicating them wastes the output budget.
- **Do copy the shell markup** from the screen A reference (mobile top bar, sidebar, top bar, demo banner), keeping every `id` that shell.js relies on. Change only the page title, subtitle and the active nav item.
- Use the existing classes before creating new ones. The page's own `<style>` holds **only** CSS for components that shared.css lacks (charts, tables, filters, small multiples…), written with the same tokens.
- The page's own `<script>` holds **only** this screen's data and behavior.
- Do not re-derive the design system: spend your effort on the new screen's content, charts and interactions.

## 9. Output format
Reply with **only** one ```html code block containing the complete file. For screens B–F, the file links `shared.css` and `shell.js` (section 8) instead of repeating the token block and shell code.
