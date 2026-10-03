# Lafont: scouting notes

Site: <https://www.lafont.com>   Scouted by: chaki   Date: 2026-10-02

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: no
- robots.txt from `lafont.com`:
  ```text
  User-agent: *
  Disallow:

  # Sitemap 
  Sitemap: https://www.lafont.com/sitemap.xml
  ```
  *(Completely open; zero crawl restrictions)*

## Where the frames are
- Optical collection URL: <https://www.lafont.com/eyeglasses>
- Sun collection URL: <https://www.lafont.com/sunglasses> *(note: `/sunglasses/` with trailing slash 301-redirects to `/sunglasses` without trailing slash)*
- Roughly how many frames (optical / sun):
  - Optical: 111 models on `/eyeglasses` (~550–700 colorway variants)
  - Sun: 11 models on `/sunglasses` (~50–70 colorway variants)
  - Total: 122 models (~600–750 colorway SKUs)
- Frames per page, and how paging works: All frames load on a single page per collection (no pagination or infinite scroll needed; static server-rendered HTML).
- Frame names show in View Source (Ctrl+U): yes (Apache / Debian server-rendered PHP).

## Which version of the site
- Country or language to track: English (`https://www.lafont.com/eyeglasses` and `https://www.lafont.com/sunglasses`). French is toggled via session cookie `/langue/change/fr`.
- Country code: `FR` (Parisian heritage brand, manufactured in Oyonnax, Jura, France with "Origine France Garantie" label). Default currency: `EUR`.
- Platform: Custom PHP/Apache web application.

## One filter at a time
Available under `#filter` / `.filter_mosaic`:
- **Audience / Style**:
  - Man: `/catalog/style/5`
  - Woman: `/catalog/style/6`
  - Unisex: `/catalog/style/7`
  - 7–12 years old: `/catalog/style/3`
- **Shape**:
  - Aviator: `/catalog/shape/14`
  - Cat-eye: `/catalog/shape/6`
  - Flat rectangle: `/catalog/shape/8`
  - Geometric: `/catalog/shape/12`
  - Half-eye: `/catalog/shape/5`
  - Oval: `/catalog/shape/4`
  - P3: `/catalog/shape/9`
  - Rectangular: `/catalog/shape/2`
  - Round: `/catalog/shape/3`
  - Square: `/catalog/shape/7`
- **Material**:
  - Acetate: `/catalog/material/10`
  - Combination: `/catalog/material/11`
  - Metal: `/catalog/material/9`
  - Titanium: `/catalog/material/12`
- **Color (17 standardized families)**:
  - Beige: `/catalog/color/2`
  - Black: `/catalog/color/10`
  - Blue: `/catalog/color/3`
  - Brown: `/catalog/color/9`
  - Crystal: `/catalog/color/4`
  - Golden: `/catalog/color/5`
  - Green: `/catalog/color/15`
  - Grey: `/catalog/color/7`
  - Horn: `/catalog/color/17`
  - Orange: `/catalog/color/11`
  - Panther (Animal/Leopard): `/catalog/color/12`
  - Pink: `/catalog/color/13`
  - Purple: `/catalog/color/16`
  - Red: `/catalog/color/14`
  - Silver: `/catalog/color/1`
  - Tortoiseshell: `/catalog/color/6`
  - Yellow: `/catalog/color/8`
- **Size**:
  - Small: `/catalog/size/1`
  - Medium: `/catalog/size/2`
  - Large: `/catalog/size/3`

## On a product page
- Price shown: no ("price on request", luxury B2B optician distribution). Currency: `EUR`.
- Colours: swatches / names / codes:
  - Colors are not given text names on product pages; they are identified exclusively by **numeric reference codes** (`100`, `3100`, `3223`, `5201`) and **swatch thumbnail images** (`src="/image.php?img=/colors/{code}.jpg"`).
  - Lafont specializes in complex creative acetate laminations:
    - `100`: Solid Black
    - `3100`: Two-tone diagonal split (Navy Blue top / Salmon Pink bottom)
    - `3199`: Terrazzo / confetti mosaic acetate
    - `3223`: Gradient / ombré (Deep purple fading into seafoam/teal)
    - `5201`: Multi-layer marbled floral tortoiseshell pattern
    - `7093`: Two-tone block (Burgundy top / Lilac bottom)
    - `7166`: Textured lace/marble purple pattern
  - Sibling colorway variants link directly to `/catalog/article/{CODE}` (e.g. `/catalog/article/DELE100`, `/catalog/article/DELE5201`).
- Details listed (shape, material, gender, lens ...):
  - Model Name: `h1.title_article` (e.g. `Delicate`, `Clic`).
  - Size: `h2.taille_article` (e.g. `Size 54`).
  - Description: `<div class="info_article"> p` — rich editorial paragraph highlighting silhouette, material, and lamination styling:
    - *DELICATE*: "An easy addition to any eyeglass wardrobe DELICATE offers a sleek rectangle silhouette in an array of Lafont acetate colors." (`shape: rectangle`, `material: acetate`).
    - *CLIC*: "P3 perfection. The new CLIC offers a playful two-tone metal option in a classic silhouette." (`shape: p3`, `material: metal`, `lamination: two_tone`).
  - Technical data in `.technique .info_tech ul.edi li`:
    - Eye height: `40`
    - Eye width: `54`
    - Bridge: `15`
    - Temple length: `137`
    - Effective diameter: `60`
    - Lens base: `4`
  - Listing card image `alt` attribute:
    `alt="Glasses Lafont: DELICATE - 100- Acetate"` explicitly contains model name, color code, and material.
- Badges:
  - `New`: displayed as `<p>New</p>` in model cards.
  - `Origine France Garantie`: certified French manufacturing (Jura / Oyonnax).

## Anything else
- **URL structure**:
  - Listing collections: `/eyeglasses` and `/sunglasses`
  - Article detail pages: `/catalog/article/{ARTICLE_CODE}` (e.g. `/catalog/article/DELE5201`, `/catalog/article/CLIC5729I`)
  - Canonical URL regex: `'(/catalog/article/[A-Z0-9]+)'`
- **Data Strategy**:
  - Storing swatch URLs (`https://www.lafont.com/image.php?img=/colors/{code}.jpg`) in `flags["variants"]` preserves visual lamination textures for the radar.
  - The 17 color facets provide standard color family tags without requiring fragile color name scraping.
