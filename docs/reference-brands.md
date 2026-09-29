# Reference brands: candidate list and web domains

The client said any brand can be picked. This is the list they gave, with each brand's web domain. Nothing here is crawled
yet; Etnia Barcelona and Morel are the two creator brands already tracked (`backend/app/collectors/stores/store_configs.yaml`).

**Scope rule:** the cadrage (section 2.1) excludes **Asia** as a market ("hors cible actuelle": morphological and stylistic
specifics), so Asian brands are not scouted or crawled. Two brands on the client's list are Japanese and are set aside
below; they stay listed so the client can see why.

Domains were checked with **one plain HTTP request each on 2026-09-29** (our user agent, `https://<domain>/`, redirects
followed). The last column says what an automated client gets, which is not the same as what a browser gets, and it decides
what is possible next. See "How to read the check".

## Major and designer brands

| Brand | Domain | Plain HTTP check |
|---|---|---|
| Ray-Ban | `www.ray-ban.com` | 403, bot-blocked |
| Oakley | `www.oakley.com` | 403, bot-blocked |
| Persol | `www.persol.com` | 200 (redirects to `/en-us`) |
| Oliver Peoples | `www.oliverpeoples.com` | 200 (redirects to `/en-us`) |
| Maui Jim | `www.mauijim.com` | redirect loop (`/US/en_US/`) |
| Gucci | `www.gucci.com` | redirect loop |
| Prada / Prada Linea Rossa | `www.prada.com` (Linea Rossa is a line of Prada eyewear, same site) | redirect loop |
| Tom Ford | `www.tomfordfashion.com` (the bare domain gets 403, the `www.` host answers) | 200 |
| Chanel | `www.chanel.com` | 403, bot-blocked |
| Versace | `www.versace.com` | 403, bot-blocked |
| Burberry | `www.burberry.com` (redirects to `int.burberry.com`) | 200 |
| Michael Kors | `www.michaelkors.com` | 200 |
| Giorgio Armani / Emporio Armani | `www.armani.com` (both labels live on it) | 200 |
| Dolce & Gabbana | `www.dolcegabbana.com` (redirects to a country site) | 200 |

## Independent and craft eyewear brands

| Brand | Domain | Plain HTTP check |
|---|---|---|
| Barton Perreira (USA) | `bartonperreira.com` | 200 |
| Dita (USA) | `dita.com` | 200 |
| J.F. Rey (France) | `jfrey.fr` (`jfrey.com` redirects to `www.jfrey.fr/en/`) | 200 |
| Alain Mikli (France) | `www.alainmikli.com` (`mikli.com` does not answer) | 200 |
| Kuboraum (Germany / Italy) | `www.kuboraum.com` | 200 |
| Rigards (handmade horn and metal frames) | `www.rigards.com` | 200 |
| Cubitts (UK) | `cubitts.com` | 200 |
| E.B. Meyrowitz (UK) | `ebmeyrowitz.com` | 200 |
| Silhouette (Austria) | `www.silhouette.com` | 200 |

## Set aside: outside the target markets (Asia)

| Brand | Domain | Why |
|---|---|---|
| Masunaga (Japan) | `masunaga1905.com` (`masunaga.com` does not answer) | Japanese brand: Asia is an excluded market (cadrage, 2.1) |
| Eyevan 7285 (Japan) | `eyevan.com` | Japanese brand: Asia is an excluded market (cadrage, 2.1) |

Both answered a plain request (200), so this is a scope decision, not a technical one. If the client wants either brand
studied anyway, that changes the cadrage and should come from them. For the others on the list, the origin is European or
American (Maui Jim is Hawaiian; Silhouette is Austrian; Kuboraum is German and Italian).

**Scouting:** how a brand is scouted, and the first-pass results for the nine independent brands, are in
`docs/scouting/` (`README.md`, `first-pass.md`, one folder per brand).

## How to read the check
- **200**: the site answers an automated client. It still has to be scouted (does it list frames with colours and shapes, is
  it a catalog or only a brand page, what do `robots.txt` and the markup allow) before a crawler config is written.
- **403, bot-blocked** (Ray-Ban, Oakley, Chanel, Versace) and **redirect loop** (Maui Jim, Gucci, Prada): the site is up but
  refuses a plain automated client. This is the same situation as Woodys (a bot challenge). The rule stays: **no bypassing** a
  challenge. The way forward is a catalog export or feed from the client, or their written go-ahead and allowlisting of our
  user agent (`EyewearTrendsBot/0.1 (+internal retail trend monitoring)`).
- A brand's own site is not always a shop: several big houses sell eyewear through a licensee (for example the Safilo and
  Luxottica ranges), so the useful catalog may live on another domain. Scouting decides that.
- The check says nothing about pricing, licensing or whether crawling is welcome; it only says what answered.

## Suggested order for scouting (my read, not a client decision)
1. **Independent brands that answered 200**: Cubitts, Dita, Barton Perreira, Kuboraum, Rigards, Silhouette, J.F. Rey,
   Alain Mikli, E.B. Meyrowitz (nine, once the two Japanese brands are set aside). They are design-led, small catalogs, and
   each could be a config like Etnia's or Morel's. Cubitts and Dita are the likeliest to expose colour and shape details.
2. **Designer houses that answered 200** (Persol, Oliver Peoples, Burberry, Michael Kors, Armani, Dolce & Gabbana, Tom Ford):
   larger, regional and localised, so more work per brand; worth choosing one or two.
3. **Blocked or looping** (Ray-Ban, Oakley, Chanel, Versace, Maui Jim, Gucci, Prada): only with the client's help, as above.
