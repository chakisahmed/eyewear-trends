# Barton Perreira: scouting notes

Site: <https://bartonperreira.com>   Scouted by: Ahmed (answers) and the first pass (checks)   Date: 2026-09-29

## Access
- Works in my browser: yes
- Login, age gate or cookie click needed before frames show: no
- Terms of use forbid automated access: not checked (still to read)

## Where the frames are
- Optical collection URL: <https://bartonperreira.com/collections/optical-collection>
- Sun collection URL: <https://bartonperreira.com/collections/sunglass-collection>
- Roughly how many frames (optical / sun): about 116 / 122 "products" (see "Sizes" below: a size may be its own product)
- Frames per page, and how paging works: 54 links per page, `rel=next` (`?page=2`), 3 pages per collection
- Frame names show in View Source (Ctrl+U): yes (the pages are large because every variant is embedded)

## Which version of the site
- Country or language to track: US store, USD prices, English
- Platform: Shopify

## One filter at a time
- Filters offered: shape (Aviator, Butterfly, Cat Eye, Cateye, Hexagonal, Rectangle, Round, Square) and material (Acetate,
  Mixed Materials, Titanium), the same on both collections
- URL pattern given: `?sort_by=manual&filter.v.m.filter.shape=<shape>&filter.v.m.filter.material=<material>`
- **What robots.txt allows** (`Disallow` rules): `sort_by` is forbidden, and so is a URL with two `filter` parameters
  (`/collections/*filter*&*filter*`), and a `+` in the path. So the pattern above cannot be used as is. What can be requested
  is **one filter, no `sort_by`, spaces written `%20`**: `/collections/optical-collection?filter.v.m.filter.shape=Round`.
  "Cat Eye" and "Cateye" are two separate filter values for the same shape.

## On a product page (Euclid, and Lamarr for a sun frame)
- Price shown: yes, USD (Euclid $670; the theme says "Sale price" but `compare_at_price` is empty, so it is the normal price)
- Colours: one entry per colourway, with a SKU (Euclid: `EUCLAF5301`, `EUCLAF5302`, `EUCLAF5303`; Lamarr: `LAMA5001` to `LAMA5005`)
  - Euclid (optical, four parts): `Hickory Gradient / Clear / Hickory Gradient / Pewter`, `Black / Clear / Black / Pewter`,
    `Absinthe / Clear / Chestnut / Antique Gold`
  - Lamarr (sun, two parts): `Heroine Chic / Smolder (AR)`, `Black / Noir (AR)`, `Acacia Tortoise / Espresso (AR)`, `Coy / Desert Lilac (AR)`, `Champagne / Julep (AR)`
  - Reading: **front / lens / temples / metal finish**. On a sun frame the second part is the lens colour (`(AR)` = anti-reflective); on
    an optical frame it is `Clear`. The third and fourth parts appear on mixed-material frames such as the Euclid (titanium temples,
    metal finish `Pewter`, `Antique Gold`). The first part is the colour of the frame.
- Details listed: `Frame Material - Zyl`, `Lens Material - CR-39 w/ Anti-Reflective Coating`, `Eye Size - 50.5mm`,
  `Bridge Size - 21mm`, `Temple Length - 145mm`. The shape is in the title ("Bold Cateye Sunglasses") and in the filters.
- Badges (best-seller, new, sold out): stock is per colourway (`InStock` / `OutOfStock` in the structured data); no best-seller flag seen

## Status
- **Crawler config written** (Step 15, `docs/phase2-step15-barton-perreira-plan.md`), tested offline. **Not yet crawled**: the first live crawl
  (`python -m app.cli crawl-store bartonperreira.com`, about 20 minutes and 150 MB) is run from a terminal, then `retag-products`.

## Anything else
- The description of the Euclid: "titanium temples encased in translucent acetate".
- Sizes: the earlier page was `Banks (48)`, so a model may exist as one product per size (`Banks (48)`, `Banks (52)`?). To check before counting frames.
