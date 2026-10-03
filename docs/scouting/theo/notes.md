# Theo: scouting notes

Site: <https://www.theo.be> (redirect from `http://theo.eu`)   Scouted by: chaki   Date: 2026-10-02

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no (the optician portal at `https://www.jules2.theo.be/` is password-protected for B2B accounts, but the consumer catalog on `https://www.theo.be` is public)
- Terms of use forbid automated access: no
- robots.txt from `theo.be`:
  ```text
  (empty, length 0 — zero disallow rules)
  ```
- CDN / Web Server: Webflow CMS backed by Cloudflare edge caching (`cf-cache-status: HIT`, `server: cloudflare`). Polite delay (1.5s) is fully respected with standard browser User-Agent.

## Brand Identity & Origin
- **Brand**: Theo Eyewear (*"theo loves you"*)
- **Founders**: Wim Somers & Patrick Hoet (founded 1989)
- **Origin**: Antwerp, Belgium (`country: BE`)
- **Aesthetic**: World-famous avant-garde Belgian eyewear pioneer known for saturated neon/fluorescent colorways, witty asymmetric cuts, dual-color acetate lamination, laser-cut titanium, and bold geometric profiles.
- **Retail Model**: Sold strictly through independent optical boutiques and style opticians globally; no direct-to-consumer online shopping (retail prices are `None`).

## Site Architecture & The "Tricky" Navigation
The user-facing site features a multi-tiered sliding side drawer:
1. **Tier 1 (Main drawer)**: `collections`
2. **Tier 2 (Families drawer)**: Slides out with 9 creative design families (`tubes`, `friskos`, `isolines`, `flow`, `waves`, `glues`, `locks`, `clin d oeil`, `bourbon way`).
3. **Tier 3 (Model preview drawer)**: Selecting a family slides open a 3rd drawer panel with model cards (e.g. `yg`, `yh`, `yi` with "10 colours" and an orange "browse collection" button linking to `/families/<family-slug>`).

Frontend technologies include **Webflow**, **Barba.js** (PJAX client-side transitions), and **GSAP Flip**, which can make manual web scraping look complex. However, **all HTML rendered by the server is 100% static, semantic, and clean**.

## URL Taxonomy
- **Family Collection Pages**: `https://www.theo.be/families/<family_slug>`
- **Model ("Mother") Pages**: `https://www.theo.be/mothers/<model_slug>`

In Theo's CMS taxonomy, **"mothers"** represent the parent silhouette models, each spawning multiple "child" colorway variants.

## Active Catalog Size (9 Families, 48 Models)

Every family page lists all its constituent models in static HTML:

| Family Slug | Model Count | Active Models | Design Story / Theme |
|---|---|---|---|
| `/families/bourbon-way` | 6 | `YG`, `YH`, `YI`, `YJ`, `YK`, `YL` | Inspired by vintage French *Portes-clés de Bourbon* |
| `/families/clin-d-oeil` | 4 | `APPLE`, `EYE`, `PIPE`, `SKY` | Surrealism tribute (*"Ceci n'est pas une theo"*, Magritte homage) |
| `/families/glues` | 6 | `LOCTITE`, `PATTEX`, `PRITT`, `SCOTCH`, `TEC7`, `VELPON` | Bold acetate silhouettes named after adhesive brands |
| `/families/flow` | 6 | `BREATH`, `CHEER`, `EAT`, `FEEL`, `SLEEP`, `SPEAK` | Continuous organic flow lines |
| `/families/friskos` | 6 | `BELLO`, `LOLLY`, `POPSI`, `SCOOPY`, `SOLEO`, `STOX` | Playful ice-pop geometric profiles |
| `/families/tubes` | 5 | `CANAE`, `NEXAE`, `SYNAE`, `TUBAE`, `UNAE` | Motion tubes (*"From the rain into the sun"*) |
| `/families/isolines` | 5 | `ISOBAR`, `ISOBATH`, `ISOHEL`, `ISOHYPSE`, `ISOTHERM` | Topographic contour lines |
| `/families/waves` | 5 | `BOTTOM TURN`, `DROP KNEE`, `DUCK DIVE`, `FLOATER RIDE`, `KICK OUT` | Fluid surf contours |
| `/families/locks` | 5 | `CLAMP`, `CLICK`, `GRIP`, `HOOK`, `SEAL` | Industrial lock and clasp details |

**Total core catalog**: **48 unique models** (~450–550 colorway variants).

## Granular Variant Data on Product Pages (`/mothers/<slug>`)

Each mother page (`div.product-item.is--wide`) exposes rich variant information:
- **Exact Colorway Formula**: Extracted cleanly from `a.save-icon[data-model]` or `img[alt]`:
  - `APPLE 003 MM ELECTRIC BLUE + TRANSPARENT DELFT WARE BLUE`
  - `APPLE 004 BLUESEY RED + RED LINED`
  - `APPLE 007 DARK NIGHT + BLUE RED ECAIL` (tortoise / écaille)
  - `APPLE 009 SANREMO GREEN + TRANSPARENT PINK`
  - `APPLE 012 CITRUS BLACK + BROWN RED`
  - `APPLE 014 FLUO ORANGE + ORANGE GIVREE`
  - `APPLE 015 FLUO YELLOW + DALMATIAN`
  - `APPLE 016 FLUO RED + PANTY`
  - `APPLE 018 ITALIAN BLUE FRANCORCHAMPS + GREENLINED n25/2`
  - `APPLE 019 ITALIAN ROSSO CAVALLINO + DARK BURGUNDY n26/1`
  - `APPLE 020 TARGA BLUE + SOLID PORCELAIN BLUE n25/2`
  - `APPLE 022 FLUO PURPLE + GREEN HAVANA n26/1`
- **Variant Code**: Numeric color sequence (e.g. `003`, `004`, `007` or `3`, `4`, `7`).
- **High-Res Front Image**: `https://cdn.prod.website-files.com/6565eaa9b5c9ed170d25b41a/...`
- **Dual-tone Lamination**: Many colorways feature `+`, splitting into primary and secondary accent shades.

## On a Product Page
- **Price shown**: no (creator brand showroom, wholesale B2B via `jules2.theo.be`, optician locator for end consumers).
- **Default Currency**: `EUR` (Belgium / Eurozone).
- **Colours**: Swatches & high-res photos for all variants; color naming is bilingual/poetic (e.g., `FLUO ORANGE`, `TRANSPARENT DELFT WARE BLUE`, `ECAIL`, `SANREMO GREEN`).
- **Badges**: None (no sale/discount badges).
