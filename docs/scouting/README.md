# Scouting candidate brands

How a brand goes from the client's list (`docs/reference-brands.md`) to a crawler config like Etnia's or Morel's
(`backend/app/collectors/stores/store_configs.yaml`). One folder per brand under this one: `cubitts/`, `dita/`, ...

## Scope rules
- **Asia is excluded** (cadrage, 2.1). Do not scout Asian brands.
- **No bypassing.** A site that answers a browser but blocks automated requests (403, a challenge page, a redirect loop) is
  not crawled by working around it. Its folder still gets your saved pages so the structure can be judged, and the way
  forward is a catalog feed or the client's go-ahead with our user agent allowlisted:
  `EyewearTrendsBot/0.1 (+internal retail trend monitoring)`.
- **Polite:** one collection, a handful of pages, `robots.txt` first.

## What goes in a brand folder
| File | What | Who |
|---|---|---|
| `notes.md` | the short questionnaire below (copy `_template/notes.md`) | you |
| `robots.txt` | the site's robots file, saved as is | you or the first pass |
| `listing-1.html`, `listing-2.html` | page 1 and page 2 of one collection (optical or sun) | you |
| `product-1.html`, `product-2.html` | a product page with several colours; one with a badge (best-seller, new) or sold out | you |
| `auto-pass.md` | what the automated first pass found (robots, platform, structure, a verdict) | first pass |

Save pages in Chrome or Edge with **Save as > Webpage, HTML only**. Saved `.html` files are git-ignored (size, and they
are the brands' content); the notes and `robots.txt` are committed.

## The three things a saved page cannot tell me
1. Does the frame list appear in **View Source** (Ctrl+U)? Search for a product name there. If it shows on screen but not in
   the source, the site builds the list with JavaScript and needs a different approach.
2. Tick **one** filter (shape, colour or material): how does the address bar change? Paste the URL. Combined filters are
   usually forbidden by `robots.txt`, so one at a time.
3. How many frames per collection, how many per page, and how paging works (next link, `?page=2`, `/page/2/`, "load more").

## Verdicts used in `auto-pass.md`
- **Promising**: frames and links are in the served HTML, paging is visible, the product page carries structured data.
- **Medium**: partly there; needs a look at a saved page to decide.
- **Hard**: the list seems to be built by JavaScript, or the site is a brand page rather than a catalog.
- **Blocked**: the site refuses an automated client. Rule above.

## Order
1. First pass (automated, read-only, about four requests per site): `auto-pass.md` in each folder, summary in `first-pass.md`.
2. You fill `notes.md` for the brands worth pursuing and add saved pages where the first pass says "needs a look".
3. I write the config and offline tests, as for Morel (Step 12), and you run the first crawl.
