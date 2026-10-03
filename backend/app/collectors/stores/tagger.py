"""Rule-based taxonomy tagging of store products: zero LLM, no database.

A product's name, categories and raw_specs are matched against taxonomy.yaml synonyms (FR + EN):
- text is accent-folded (the taxonomy's own `fold`), matches are whole words, longest phrase first,
  and a matched span is consumed ("papillon relevé" -> cat_eye, not also butterfly);
- raw_specs are field-scoped: a "Materials" value is only matched against materials, and so on;
- in free text (name, categories) a few ambiguous synonyms are ignored ("or" = gold in French, but
  also the English word); they still count inside a scoped spec ("Couleur: Or").
Categories also give non-taxonomy tags: audience (men/women/unisex), product_type (optical/sun); multi-layer
acetate variants give `lamination` tags (a combination of color families, e.g. "blue+tortoiseshell").

Color tags carry the three-tier schema: family (Palier 1, the taxonomy code) and hex (Palier 2, the taxonomy's hex
for it) are attached automatically. Palier 3, a commercial variant code such as "HV/BL", comes from the crawler as
`flags["variants"] = [{"code": "HV/BL", "color": "Havana / Blue"}]`: each variant's color label is matched like a
"Couleur" spec and the tag it produces keeps that variant's code. A variant whose label matches no family produces
no tag (a code is never guessed into a family); it stays in flags.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.taxonomy import Taxonomy, clean_supplier_code, fold, load_taxonomy

RULES_VERSION = 16  # stored with each tag; bump when the rules below change, then run retag-products
# v2: frame-material and gender spec labels, store vocabulary aliases (mykenza.tn, lunettek.com)
# v3: "Rond" / "Ronds" (masculine forms, MyKenza) -> round
# v4: "Forme Lunette" and similar frame-shape labels (lamode.tn). Its "VISAGE" rows (recommended face
#     shapes) are deliberately NOT a label: a face shape is not the frame's shape.
# v5: color tags carry family + hex (Palier 1-2) and, from flags["variants"], the variant code (Palier 3).
#     Matching is unchanged; retag-products backfills the new columns on existing tags.
# v6: Etnia Barcelona's shape filter labels, each one shape: "PANTOS SQUARE" -> square (not also round, via
#     "pantos"), "CAT-EYE/BUTTERFLY" -> cat_eye (not also butterfly). PEAR and OTHER stay untagged.
# v7: taxonomy color families v2 (blue, red, green, grey, white, pink, purple, orange; bold = Multicolore) plus
#     store jargon Army / Petrol. Color words that are also model names or everyday words (Rose, Orange,
#     Marine, Olive…) only count in specs and variants. Bronze, Copper and Zebra stay untagged: a metal tone or
#     a pattern, not a hue.
# v8: multi-layer acetate variants (flags["variants"][].layers, e.g. ["Havana", "Blue"]): a color tag per layer,
#     Bicolore (two_tone), and a non-taxonomy `lamination` tag ("blue+tortoiseshell"), all with the variant code.
# v9: front / temple material spec labels (morel.com). Its "Type" (Rimmed / Semi-rimless / Rimless) is deliberately
#     NOT a label: "semi-rimless" would match rimless.
# v10: Morel vocabulary from its first crawl, specs and variants only: "Almond" -> oval, "Ruthenium" -> grey.
# v11: Barton Perreira, variants only: the plain colour names "Chestnut", "Espresso" and "Hickory" -> brown ("Hickory
#      Gradient" is also Bicolore: "gradient" is a taxonomy synonym). Its marketing colour names are not guessed: they
#      are added from the crawl's report of front colours with no family. ("Cateye", its second shape spelling, is
#      already a taxonomy synonym.)
# v12: Cubitts, specs only: the material filter value "Steel" -> metal ("stainless steel" already was).
# v13: Dita, specs and variants only: the site's own typo "Titanuim" -> titanium (it sits beside the correct "Titanium" in
#      one filter); "White Gold" -> gold (it used to tag gold AND white: a metal finish is not white); the shapes
#      Polyangular and Diamond -> geometric. ("Navigator" was left unmapped here; v15 maps it.)
# v14: E.B. Meyrowitz, specs only: its "Build" line is the frame's shape, so the label "Build" -> shape; "Rounded" ->
#      round and "Ovular" -> oval ("Rectangular", "Soft Rectangular" and "Teardrop" are taxonomy synonyms already).
#      Its other detail lines (Top Line, Bridgework, Rim Structure) have no taxonomy dimension: stored, not tagged.
# v15: Dita's shape "Navigator" -> aviator (its own copy calls it an aviator with a square lens; 30 frames). E.B. Meyrowitz's
#      colour names from its first crawl, variants only: Demi-Blonde -> tortoiseshell; Dark Mottle, Copper Mottle, Cinnamon,
#      Ochre -> brown; Moss, Jade -> green; Midnight, Atlantic, Cyan, Aqua -> blue; Shadow, Cloud -> grey; Barley, Savannah,
#      Desert Sun -> beige; Saffron, Sunshine, Sunburst -> orange (the taxonomy's orange / yellow family). Left untagged on
#      purpose: Jello, Opal, Mirage, Bonfire, Lava, Mountain Rain and the placeholder "Colour 8".
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v19: Lafont, specs, description, and variants: match description against _spec_material (e.g. "acetate", "metal");
#      shape alias ("p3", "round"); Lafont color code ("100", "black").
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v19: Lafont, specs, description, and variants: match description against _spec_material (e.g. "acetate", "metal");
#      shape alias ("p3", "round"); Lafont color code ("100", "black").
# v20: Cutler and Gross, variants only: olive on black -> two_tone; humble potato, old brown havana,
#      oil havana -> tortoiseshell; smoke quartz -> grey; horn crystal, sand crystal, smoke crystal -> clear;
#      obsidian -> black; rhodium -> silver; rhubarb -> red; saffron horn -> orange.
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v19: Lafont, specs, description, and variants: match description against _spec_material (e.g. "acetate", "metal");
#      shape alias ("p3", "round"); Lafont color code ("100", "black").
# v20: Cutler and Gross, variants only: olive on black -> two_tone; humble potato, old brown havana,
#      oil havana -> tortoiseshell; smoke quartz -> grey; horn crystal, sand crystal, smoke crystal -> clear;
#      obsidian -> black; rhodium -> silver; rhubarb -> red; saffron horn -> orange.
# v21: Kirk & Kirk, shape and variants: shape aliases ("roundness", "round"), ("upswept", "cat_eye"),
#      ("aviators", "aviator"), ("angular", "geometric"), ("circular", "round");
#      color aliases: admiral, capri, indigo, lagoon, ocean, royal -> blue; apple, jungle, juniper, meadow -> green;
#      candy -> pink; carmine, chilli, matte vamp, passion -> red; citrus, corn, melon -> orange;
#      coffee, earth, walnut -> brown; glacier -> clear; iris, prince -> purple; jet -> black;
#      secret, smoke, stone -> grey; tiger -> tortoiseshell.
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v19: Lafont, specs, description, and variants: match description against _spec_material (e.g. "acetate", "metal");
#      shape alias ("p3", "round"); Lafont color code ("100", "black").
# v20: Cutler and Gross, variants only: olive on black -> two_tone; humble potato, old brown havana,
#      oil havana -> tortoiseshell; smoke quartz -> grey; horn crystal, sand crystal, smoke crystal -> clear;
#      obsidian -> black; rhodium -> silver; rhubarb -> red; saffron horn -> orange.
# v21: Kirk & Kirk, shape and variants: shape aliases ("roundness", "round"), ("upswept", "cat_eye"),
#      ("aviators", "aviator"), ("angular", "geometric"), ("circular", "round");
#      color aliases: admiral, capri, indigo, lagoon, ocean, royal -> blue; apple, jungle, juniper, meadow -> green;
#      candy -> pink; carmine, chilli, matte vamp, passion -> red; citrus, corn, melon -> orange;
#      coffee, earth, walnut -> brown; glacier -> clear; iris, prince -> purple; jet -> black;
#      secret, smoke, stone -> grey; tiger -> tortoiseshell.
# v22: Theo (Belgium), specs and variants: color aliases for Theo's fluorescent, automotive, and poetic shades:
#      fluo orange, fluo yellow -> orange (Orange / Jaune); fluo red -> red, fluo purple -> purple;
#      delft ware blue, electric blue, targa blue -> blue; sanremo green -> green;
#      rosso cavallino -> red; ecail, ecaille -> tortoiseshell; citrus black, dark night -> black.
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v19: Lafont, specs, description, and variants: match description against _spec_material (e.g. "acetate", "metal");
#      shape alias ("p3", "round"); Lafont color code ("100", "black").
# v20: Cutler and Gross, variants only: olive on black -> two_tone; humble potato, old brown havana,
#      oil havana -> tortoiseshell; smoke quartz -> grey; horn crystal, sand crystal, smoke crystal -> clear;
#      obsidian -> black; rhodium -> silver; rhubarb -> red; saffron horn -> orange.
# v21: Kirk & Kirk, shape and variants: shape aliases ("roundness", "round"), ("upswept", "cat_eye"),
#      ("aviators", "aviator"), ("angular", "geometric"), ("circular", "round");
#      color aliases: admiral, capri, indigo, lagoon, ocean, royal -> blue; apple, jungle, juniper, meadow -> green;
#      candy -> pink; carmine, chilli, matte vamp, passion -> red; citrus, corn, melon -> orange;
#      coffee, earth, walnut -> brown; glacier -> clear; iris, prince -> purple; jet -> black;
#      secret, smoke, stone -> grey; tiger -> tortoiseshell.
# v22: Theo (Belgium), specs and variants: color aliases for Theo's fluorescent, automotive, and poetic shades:
#      fluo orange, fluo yellow -> orange (Orange / Jaune); fluo red -> red, fluo purple -> purple;
#      delft ware blue, electric blue, targa blue -> blue; sanremo green -> green;
#      rosso cavallino -> red; ecail, ecaille -> tortoiseshell; citrus black, dark night -> black.
# v23: Oliver Goldsmith (UK), description shape and variants: shape alias ("squared aviator", "aviator");
#      color aliases: tangerine -> orange; tokyo 50, tortoise 50, dark tortoiseshell, earth tortoise,
#      amberfleck -> tortoiseshell; night sea, bahama, anchor -> blue; rainwater -> clear;
#      wakame, plankton, military -> green; blacksilver, blackgold, black cat -> black;
#      slate storm -> grey; etaupe -> beige; rouge -> red.
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v19: Lafont, specs, description, and variants: match description against _spec_material (e.g. "acetate", "metal");
#      shape alias ("p3", "round"); Lafont color code ("100", "black").
# v20: Cutler and Gross, variants only: olive on black -> two_tone; humble potato, old brown havana,
#      oil havana -> tortoiseshell; smoke quartz -> grey; horn crystal, sand crystal, smoke crystal -> clear;
#      obsidian -> black; rhodium -> silver; rhubarb -> red; saffron horn -> orange.
# v21: Kirk & Kirk, shape and variants: shape aliases ("roundness", "round"), ("upswept", "cat_eye"),
#      ("aviators", "aviator"), ("angular", "geometric"), ("circular", "round");
#      color aliases: admiral, capri, indigo, lagoon, ocean, royal -> blue; apple, jungle, juniper, meadow -> green;
#      candy -> pink; carmine, chilli, matte vamp, passion -> red; citrus, corn, melon -> orange;
#      coffee, earth, walnut -> brown; glacier -> clear; iris, prince -> purple; jet -> black;
#      secret, smoke, stone -> grey; tiger -> tortoiseshell.
# v22: Theo (Belgium), specs and variants: color aliases for Theo's fluorescent, automotive, and poetic shades:
#      fluo orange, fluo yellow -> orange (Orange / Jaune); fluo red -> red, fluo purple -> purple;
#      delft ware blue, electric blue, targa blue -> blue; sanremo green -> green;
#      rosso cavallino -> red; ecail, ecaille -> tortoiseshell; citrus black, dark night -> black.
# v23: Oliver Goldsmith (UK), description shape and variants: shape alias ("squared aviator", "aviator");
#      color aliases: tangerine -> orange; tokyo 50, tortoise 50, dark tortoiseshell, earth tortoise,
#      amberfleck -> tortoiseshell; night sea, bahama, anchor -> blue; rainwater -> clear;
#      wakame, plankton, military -> green; blacksilver, blackgold, black cat -> black;
#      slate storm -> grey; etaupe -> beige; rouge -> red.
# v24: Retrosuperfuture (Italy), shape and color aliases: "flat top" -> square;
#      "azure" -> blue, "canarino" -> orange, "panna" -> white, "petrolium" -> blue,
#      "burnt havana" -> tortoiseshell, "spotted havana" -> tortoiseshell.
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v19: Lafont, specs, description, and variants: match description against _spec_material (e.g. "acetate", "metal");
#      shape alias ("p3", "round"); Lafont color code ("100", "black").
# v20: Cutler and Gross, variants only: olive on black -> two_tone; humble potato, old brown havana,
#      oil havana -> tortoiseshell; smoke quartz -> grey; horn crystal, sand crystal, smoke crystal -> clear;
#      obsidian -> black; rhodium -> silver; rhubarb -> red; saffron horn -> orange.
# v21: Kirk & Kirk, shape and variants: shape aliases ("roundness", "round"), ("upswept", "cat_eye"),
#      ("aviators", "aviator"), ("angular", "geometric"), ("circular", "round");
#      color aliases: admiral, capri, indigo, lagoon, ocean, royal -> blue; apple, jungle, juniper, meadow -> green;
#      candy -> pink; carmine, chilli, matte vamp, passion -> red; citrus, corn, melon -> orange;
#      coffee, earth, walnut -> brown; glacier -> clear; iris, prince -> purple; jet -> black;
#      secret, smoke, stone -> grey; tiger -> tortoiseshell.
# v22: Theo (Belgium), specs and variants: color aliases for Theo's fluorescent, automotive, and poetic shades:
#      fluo orange, fluo yellow -> orange (Orange / Jaune); fluo red -> red, fluo purple -> purple;
#      delft ware blue, electric blue, targa blue -> blue; sanremo green -> green;
#      rosso cavallino -> red; ecail, ecaille -> tortoiseshell; citrus black, dark night -> black.
# v23: Oliver Goldsmith (UK), description shape and variants: shape alias ("squared aviator", "aviator");
#      color aliases: tangerine -> orange; tokyo 50, tortoise 50, dark tortoiseshell, earth tortoise,
#      amberfleck -> tortoiseshell; night sea, bahama, anchor -> blue; rainwater -> clear;
#      wakame, plankton, military -> green; blacksilver, blackgold, black cat -> black;
#      slate storm -> grey; etaupe -> beige; rouge -> red.
# v24: Retrosuperfuture (Italy), shape and color aliases: "flat top" -> square;
#      "azure" -> blue, "canarino" -> orange, "panna" -> white, "petrolium" -> blue,
#      "burnt havana" -> tortoiseshell, "spotted havana" -> tortoiseshell.
# v25: Spektre (Italy), color aliases: "tobacco" -> brown, "avory" -> white, "fuchsia" -> pink.
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v19: Lafont, specs, description, and variants: match description against _spec_material (e.g. "acetate", "metal");
#      shape alias ("p3", "round"); Lafont color code ("100", "black").
# v20: Cutler and Gross, variants only: olive on black -> two_tone; humble potato, old brown havana,
#      oil havana -> tortoiseshell; smoke quartz -> grey; horn crystal, sand crystal, smoke crystal -> clear;
#      obsidian -> black; rhodium -> silver; rhubarb -> red; saffron horn -> orange.
# v21: Kirk & Kirk, shape and variants: shape aliases ("roundness", "round"), ("upswept", "cat_eye"),
#      ("aviators", "aviator"), ("angular", "geometric"), ("circular", "round");
#      color aliases: admiral, capri, indigo, lagoon, ocean, royal -> blue; apple, jungle, juniper, meadow -> green;
#      candy -> pink; carmine, chilli, matte vamp, passion -> red; citrus, corn, melon -> orange;
#      coffee, earth, walnut -> brown; glacier -> clear; iris, prince -> purple; jet -> black;
#      secret, smoke, stone -> grey; tiger -> tortoiseshell.
# v22: Theo (Belgium), specs and variants: color aliases for Theo's fluorescent, automotive, and poetic shades:
#      fluo orange, fluo yellow -> orange (Orange / Jaune); fluo red -> red, fluo purple -> purple;
#      delft ware blue, electric blue, targa blue -> blue; sanremo green -> green;
#      rosso cavallino -> red; ecail, ecaille -> tortoiseshell; citrus black, dark night -> black.
# v23: Oliver Goldsmith (UK), description shape and variants: shape alias ("squared aviator", "aviator");
#      color aliases: tangerine -> orange; tokyo 50, tortoise 50, dark tortoiseshell, earth tortoise,
#      amberfleck -> tortoiseshell; night sea, bahama, anchor -> blue; rainwater -> clear;
#      wakame, plankton, military -> green; blacksilver, blackgold, black cat -> black;
#      slate storm -> grey; etaupe -> beige; rouge -> red.
# v24: Retrosuperfuture (Italy), shape and color aliases: "flat top" -> square;
#      "azure" -> blue, "canarino" -> orange, "panna" -> white, "petrolium" -> blue,
#      "burnt havana" -> tortoiseshell, "spotted havana" -> tortoiseshell.
# v25: Spektre (Italy), color aliases: "tobacco" -> brown, "avory" -> white, "fuchsia" -> pink.
# v26: Ahlem (France / USA), color aliases: "dry pampa" -> beige, "smoky quartz" -> grey,
#      "old fashioned rose" -> pink, "light turtle", "yellow turtle" -> tortoiseshell,
#      "peony", "peony gold" -> pink, "ashmilk" -> grey, "storm" -> grey, "g15" -> green.
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v19: Lafont, specs, description, and variants: match description against _spec_material (e.g. "acetate", "metal");
#      shape alias ("p3", "round"); Lafont color code ("100", "black").
# v20: Cutler and Gross, variants only: olive on black -> two_tone; humble potato, old brown havana,
#      oil havana -> tortoiseshell; smoke quartz -> grey; horn crystal, sand crystal, smoke crystal -> clear;
#      obsidian -> black; rhodium -> silver; rhubarb -> red; saffron horn -> orange.
# v21: Kirk & Kirk, shape and variants: shape aliases ("roundness", "round"), ("upswept", "cat_eye"),
#      ("aviators", "aviator"), ("angular", "geometric"), ("circular", "round");
#      color aliases: admiral, capri, indigo, lagoon, ocean, royal -> blue; apple, jungle, juniper, meadow -> green;
#      candy -> pink; carmine, chilli, matte vamp, passion -> red; citrus, corn, melon -> orange;
#      coffee, earth, walnut -> brown; glacier -> clear; iris, prince -> purple; jet -> black;
#      secret, smoke, stone -> grey; tiger -> tortoiseshell.
# v22: Theo (Belgium), specs and variants: color aliases for Theo's fluorescent, automotive, and poetic shades:
#      fluo orange, fluo yellow -> orange (Orange / Jaune); fluo red -> red, fluo purple -> purple;
#      delft ware blue, electric blue, targa blue -> blue; sanremo green -> green;
#      rosso cavallino -> red; ecail, ecaille -> tortoiseshell; citrus black, dark night -> black.
# v23: Oliver Goldsmith (UK), description shape and variants: shape alias ("squared aviator", "aviator");
#      color aliases: tangerine -> orange; tokyo 50, tortoise 50, dark tortoiseshell, earth tortoise,
#      amberfleck -> tortoiseshell; night sea, bahama, anchor -> blue; rainwater -> clear;
#      wakame, plankton, military -> green; blacksilver, blackgold, black cat -> black;
#      slate storm -> grey; etaupe -> beige; rouge -> red.
# v24: Retrosuperfuture (Italy), shape and color aliases: "flat top" -> square;
#      "azure" -> blue, "canarino" -> orange, "panna" -> white, "petrolium" -> blue,
#      "burnt havana" -> tortoiseshell, "spotted havana" -> tortoiseshell.
# v25: Spektre (Italy), color aliases: "tobacco" -> brown, "avory" -> white, "fuchsia" -> pink.
# v26: Ahlem (France / USA), color aliases: "dry pampa" -> beige, "smoky quartz" -> grey,
#      "old fashioned rose" -> pink, "light turtle", "yellow turtle" -> tortoiseshell,
#      "peony", "peony gold" -> pink, "ashmilk" -> grey, "storm" -> grey, "g15" -> green.
# v27: Moscot (USA / New York), clean option1 color extraction, shape-<silhouette> tag handling and color aliases: "flesh" -> beige, "bark" -> brown, "butterscotch" -> orange,
#      "spot tortoise", "tokyo tortoise", "antique tortoise", "heritage tortoise", "burnt tortoise",
#      "matte tortoise" -> tortoiseshell; "g-15", "g-15 fade" -> green; "umber-crystal" -> brown;
#      "brown smoke" -> brown, "blue smoke" -> blue.
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v19: Lafont, specs, description, and variants: match description against _spec_material (e.g. "acetate", "metal");
#      shape alias ("p3", "round"); Lafont color code ("100", "black").
# v20: Cutler and Gross, variants only: olive on black -> two_tone; humble potato, old brown havana,
#      oil havana -> tortoiseshell; smoke quartz -> grey; horn crystal, sand crystal, smoke crystal -> clear;
#      obsidian -> black; rhodium -> silver; rhubarb -> red; saffron horn -> orange.
# v21: Kirk & Kirk, shape and variants: shape aliases ("roundness", "round"), ("upswept", "cat_eye"),
#      ("aviators", "aviator"), ("angular", "geometric"), ("circular", "round");
#      color aliases: admiral, capri, indigo, lagoon, ocean, royal -> blue; apple, jungle, juniper, meadow -> green;
#      candy -> pink; carmine, chilli, matte vamp, passion -> red; citrus, corn, melon -> orange;
#      coffee, earth, walnut -> brown; glacier -> clear; iris, prince -> purple; jet -> black;
#      secret, smoke, stone -> grey; tiger -> tortoiseshell.
# v22: Theo (Belgium), specs and variants: color aliases for Theo's fluorescent, automotive, and poetic shades:
#      fluo orange, fluo yellow -> orange (Orange / Jaune); fluo red -> red, fluo purple -> purple;
#      delft ware blue, electric blue, targa blue -> blue; sanremo green -> green;
#      rosso cavallino -> red; ecail, ecaille -> tortoiseshell; citrus black, dark night -> black.
# v23: Oliver Goldsmith (UK), description shape and variants: shape alias ("squared aviator", "aviator");
#      color aliases: tangerine -> orange; tokyo 50, tortoise 50, dark tortoiseshell, earth tortoise,
#      amberfleck -> tortoiseshell; night sea, bahama, anchor -> blue; rainwater -> clear;
#      wakame, plankton, military -> green; blacksilver, blackgold, black cat -> black;
#      slate storm -> grey; etaupe -> beige; rouge -> red.
# v24: Retrosuperfuture (Italy), shape and color aliases: "flat top" -> square;
#      "azure" -> blue, "canarino" -> orange, "panna" -> white, "petrolium" -> blue,
#      "burnt havana" -> tortoiseshell, "spotted havana" -> tortoiseshell.
# v25: Spektre (Italy), color aliases: "tobacco" -> brown, "avory" -> white, "fuchsia" -> pink.
# v26: Ahlem (France / USA), color aliases: "dry pampa" -> beige, "smoky quartz" -> grey,
#      "old fashioned rose" -> pink, "light turtle", "yellow turtle" -> tortoiseshell,
#      "peony", "peony gold" -> pink, "ashmilk" -> grey, "storm" -> grey, "g15" -> green.
# v27: Moscot (USA / New York), clean option1 color extraction, shape-<silhouette> tag handling and color aliases: "flesh" -> beige, "bark" -> brown, "butterscotch" -> orange,
#      "spot tortoise", "tokyo tortoise", "antique tortoise", "heritage tortoise", "burnt tortoise",
#      "matte tortoise" -> tortoiseshell; "g-15", "g-15 fade" -> green; "umber-crystal" -> brown;
#      "brown smoke" -> brown, "blue smoke" -> blue.
# v28: Warby Parker (USA) color aliases: striped sassafras, striped cypress, saltwater matte, oak barrel,
#      brushed ink, cactus crystal, laguna crystal, seaweed crystal, rose water, eastern bluebird fade,
#      black walnut, honeydew, canopy, ristretto, tamarind, marzipan.
# v16: Anne & Valentin, shape from description: flags["description"] (opening editorial sentences like
#      "Octogonale. Douce..." -> geometric, "Grande pantos..." -> round, "Petite ovale..." -> oval).
#      Only matched against _spec_shape with skip_ambiguous=True to avoid figurative language affecting
#      materials or colors. Added shape alias ("papillon", "cat_eye").
# v17: Face à Face: audience words in CATEGORY_TAGS ("feminine", "feminin" -> women, "masculine", "masculin" -> men);
#      allow tuple targets in SPEC_DIMENSIONS and map "style": ("style", "audience") so "Style: feminine" tags
#      audience: women; map "front type": "shape" for semi-rimless -> rimless; SPEC_ALIASES["material"]
#      ("aluminium", "metal"), ("aluminum", "metal").
# v18: Kuboraum, specs and variants only: rosegold -> gold, gun metal / gunmetal -> grey,
#      antique light gold -> gold.
# v19: Lafont, specs, description, and variants: match description against _spec_material (e.g. "acetate", "metal");
#      shape alias ("p3", "round"); Lafont color code ("100", "black").
# v20: Cutler and Gross, variants only: olive on black -> two_tone; humble potato, old brown havana,
#      oil havana -> tortoiseshell; smoke quartz -> grey; horn crystal, sand crystal, smoke crystal -> clear;
#      obsidian -> black; rhodium -> silver; rhubarb -> red; saffron horn -> orange.
# v21: Kirk & Kirk, shape and variants: shape aliases ("roundness", "round"), ("upswept", "cat_eye"),
#      ("aviators", "aviator"), ("angular", "geometric"), ("circular", "round");
#      color aliases: admiral, capri, indigo, lagoon, ocean, royal -> blue; apple, jungle, juniper, meadow -> green;
#      candy -> pink; carmine, chilli, matte vamp, passion -> red; citrus, corn, melon -> orange;
#      coffee, earth, walnut -> brown; glacier -> clear; iris, prince -> purple; jet -> black;
#      secret, smoke, stone -> grey; tiger -> tortoiseshell.
# v22: Theo (Belgium), specs and variants: color aliases for Theo's fluorescent, automotive, and poetic shades:
#      fluo orange, fluo yellow -> orange (Orange / Jaune); fluo red -> red, fluo purple -> purple;
#      delft ware blue, electric blue, targa blue -> blue; sanremo green -> green;
#      rosso cavallino -> red; ecail, ecaille -> tortoiseshell; citrus black, dark night -> black.
# v23: Oliver Goldsmith (UK), description shape and variants: shape alias ("squared aviator", "aviator");
#      color aliases: tangerine -> orange; tokyo 50, tortoise 50, dark tortoiseshell, earth tortoise,
#      amberfleck -> tortoiseshell; night sea, bahama, anchor -> blue; rainwater -> clear;
#      wakame, plankton, military -> green; blacksilver, blackgold, black cat -> black;
#      slate storm -> grey; etaupe -> beige; rouge -> red.
# v24: Retrosuperfuture (Italy), shape and color aliases: "flat top" -> square;
#      "azure" -> blue, "canarino" -> orange, "panna" -> white, "petrolium" -> blue,
#      "burnt havana" -> tortoiseshell, "spotted havana" -> tortoiseshell.
# v25: Spektre (Italy), color aliases: "tobacco" -> brown, "avory" -> white, "fuchsia" -> pink.
# v26: Ahlem (France / USA), color aliases: "dry pampa" -> beige, "smoky quartz" -> grey,
#      "old fashioned rose" -> pink, "light turtle", "yellow turtle" -> tortoiseshell,
#      "peony", "peony gold" -> pink, "ashmilk" -> grey, "storm" -> grey, "g15" -> green.
# v27: Moscot (USA / New York), clean option1 color extraction, shape-<silhouette> tag handling and color aliases: "flesh" -> beige, "bark" -> brown, "butterscotch" -> orange,
#      "spot tortoise", "tokyo tortoise", "antique tortoise", "heritage tortoise", "burnt tortoise",
#      "matte tortoise" -> tortoiseshell; "g-15", "g-15 fade" -> green; "umber-crystal" -> brown;
#      "brown smoke" -> brown, "blue smoke" -> blue.
# v28: Warby Parker (USA) color aliases: striped sassafras, striped cypress, saltwater matte, oak barrel,
#      brushed ink, cactus crystal, laguna crystal, seaweed crystal, rose water, eastern bluebird fade,
#      black walnut, honeydew, canopy, ristretto, tamarind, marzipan.
# v29: Jacques Marie Mage (USA) 10mm acetate default material and color aliases: argyle, bourbon,
#      bloodstone, agar, beluga, darjeeling, amarena, frost, vanta, auburn, taupe, rover, solar,
#      tempest, charbon, suntan, himalaya, viridian, stallion.

AMBIGUOUS_FREE_TEXT = frozenset({"or", "bold", "wrap", "wire", "xl", "sport",
                                 "rose", "marine", "orange", "olive", "sage", "honey", "lemon", "wine", "cherry", "plum", "slate"})
SPEC_DIMENSIONS: dict[str, str | tuple[str, ...]] = {  # folded raw_specs key -> dimension(s) its value is matched against
    "materials": "material", "material": "material", "matiere": "material", "matieres": "material",
    "materiau": "material", "materiaux": "material", "matiere du cadre": "material",
    "front material": "material", "temple material": "material", "matiere face": "material",
    "matiere branches": "material", "matiere des branches": "material",
    "materiau du cadre": "material", "matiere de la monture": "material", "materiau de la monture": "material",
    "gender": "audience", "genre": "audience", "sexe": "audience", "le sexe": "audience",
    "color": "color", "colour": "color", "couleur": "color", "coloris": "color",
    "forme": "shape", "shape": "shape", "build": "shape", "forme lunette": "shape", "forme de lunette": "shape",
    "forme monture": "shape", "forme de la monture": "shape",
    "front type": "shape",
    "style": ("style", "audience"),
}
# Store vocabulary the taxonomy does not list (taxonomy.yaml also feeds the LLM prompt and Google
# Trends, so it stays untouched). Only applied to scoped spec values, never to names or categories.
# "Plastique" is deliberately absent: it could be acetate or injected TR90.
SPEC_ALIASES = {  # dimension -> (folded phrase, code)
    "material": (("acier inoxydable", "metal"), ("acier", "metal"), ("inox", "metal"), ("stainless steel", "metal"),
                 ("steel", "metal"),  # Cubitts' filter value
                 ("titanuim", "titanium"),  # Dita's typo, in its own filter
                 ("aluminium", "metal"), ("aluminum", "metal")),  # Face à Face
    "color": (("carey", "tortoiseshell"),  # Hawkers' word for tortoiseshell
              ("army", "green"), ("petrol", "blue"),  # Etnia's color names
              ("ruthenium", "grey"),  # Morel: a dark grey metal plating
              ("chestnut", "brown"), ("espresso", "brown"), ("hickory", "brown"),  # Barton Perreira
              ("white gold", "gold"),  # Dita: a metal finish, so not also "white"
              # E.B. Meyrowitz's marketing colour names
              ("demi blonde", "tortoiseshell"),
              ("dark mottle", "brown"), ("copper mottle", "brown"), ("cinnamon", "brown"), ("ochre", "brown"),
              ("moss", "green"), ("jade", "green"),
              ("midnight", "blue"), ("atlantic", "blue"), ("cyan", "blue"), ("aqua", "blue"),
              ("shadow", "grey"), ("cloud", "grey"),
              ("barley", "beige"), ("savannah", "beige"), ("desert sun", "beige"),
              ("saffron", "orange"), ("sunshine", "orange"), ("sunburst", "orange"),
              # Kuboraum finishes
              ("rosegold", "gold"),
              ("gunmetal", "grey"),
              ("antique light gold", "gold"),
              # Lafont
              ("100", "black"),
              # Cutler and Gross
              ("olive on black", "two_tone"),
              ("humble potato", "tortoiseshell"),
              ("old brown havana", "tortoiseshell"),
              ("smoke quartz", "grey"),
              ("horn crystal", "clear"),
              ("sand crystal", "clear"),
              ("smoke crystal", "clear"),
              ("oil havana", "tortoiseshell"),
              ("obsidian", "black"),
              ("rhodium", "silver"),
              ("rhubarb", "red"),
              ("saffron horn", "orange"),
              # Kirk & Kirk
              ("admiral", "blue"),
              ("apple", "green"),
              ("candy", "pink"),
              ("capri", "blue"),
              ("carmine", "red"),
              ("chilli", "red"),
              ("citrus", "orange"),
              ("coffee", "brown"),
              ("corn", "orange"),
              ("earth", "brown"),
              ("glacier", "clear"),
              ("indigo", "blue"),
              ("iris", "purple"),
              ("jet", "black"),
              ("jungle", "green"),
              ("juniper", "green"),
              ("lagoon", "blue"),
              ("matte vamp", "red"),
              ("meadow", "green"),
              ("melon", "orange"),
              ("ocean", "blue"),
              ("passion", "red"),
              ("prince", "purple"),
              ("royal", "blue"),
              ("secret", "grey"),
              ("smoke", "grey"),
              ("stone", "grey"),
              ("tiger", "tortoiseshell"),
              ("walnut", "brown"),
              # Theo (Belgium)
              ("fluo orange", "orange"),
              ("fluo yellow", "orange"),
              ("fluo red", "red"),
              ("fluo purple", "purple"),
              ("delft ware blue", "blue"),
              ("electric blue", "blue"),
              ("targa blue", "blue"),
              ("sanremo green", "green"),
              ("rosso cavallino", "red"),
              ("ecail", "tortoiseshell"),
              ("ecaille", "tortoiseshell"),
              ("citrus black", "black"),
              ("dark night", "black"),
              # Oliver Goldsmith (UK)
              ("tangerine", "orange"),
              ("tokyo 50", "tortoiseshell"),
              ("tortoise 50", "tortoiseshell"),
              ("dark tortoiseshell", "tortoiseshell"),
              ("earth tortoise", "tortoiseshell"),
              ("amberfleck", "tortoiseshell"),
              ("night sea", "blue"),
              ("bahama", "blue"),
              ("anchor", "blue"),
              ("rainwater", "clear"),
              ("wakame", "green"),
              ("plankton", "green"),
              ("military", "green"),
              ("blacksilver", "black"),
              ("blackgold", "black"),
              ("black cat", "black"),
              ("slate storm", "grey"),
              ("etaupe", "beige"),
              ("rouge", "red"),
              # Retrosuperfuture (Italy)
              ("azure", "blue"),
              ("canarino", "orange"),
              ("panna", "white"),
              ("petrolium", "blue"),
              ("burnt havana", "tortoiseshell"),
              ("spotted havana", "tortoiseshell"),
              # Spektre (Italy)
              ("tobacco", "brown"),
              ("avory", "white"),
              ("fuchsia", "pink"),
              # Ahlem (France / USA)
              ("dry pampa", "beige"),
              ("smoky quartz", "grey"),
              ("old fashioned rose", "pink"),
              ("light turtle", "tortoiseshell"),
              ("yellow turtle", "tortoiseshell"),
              ("peony gold", "pink"),
              ("peony", "pink"),
              ("ashmilk", "grey"),
              ("storm", "grey"),
              ("g15", "green"),
              # Moscot (USA / New York)
              ("flesh", "beige"),
              ("bark", "brown"),
              ("butterscotch", "orange"),
              ("spot tortoise", "tortoiseshell"),
              ("tokyo tortoise", "tortoiseshell"),
              ("antique tortoise", "tortoiseshell"),
              ("heritage tortoise", "tortoiseshell"),
              ("burnt tortoise", "tortoiseshell"),
              ("matte tortoise", "tortoiseshell"),
              ("g 15", "green"),
              ("g 15 fade", "green"),
              ("umber crystal", "brown"),
              ("brown smoke", "brown"),
              ("blue smoke", "blue"),
              # Warby Parker (USA)
              ("striped sassafras", "brown"),
              ("striped cypress", "brown"),
              ("saltwater matte", "blue"),
              ("oak barrel", "brown"),
              ("brushed ink", "blue"),
              ("cactus crystal", "green"),
              ("laguna crystal", "blue"),
              ("seaweed crystal", "green"),
              ("rose water", "pink"),
              ("eastern bluebird fade", "blue"),
              ("black walnut", "brown"),
              ("honeydew", "green"),
              ("canopy", "green"),
              ("ristretto", "brown"),
              ("tamarind", "brown"),
              ("marzipan", "beige"),
              # Jacques Marie Mage (USA)
              ("argyle", "tortoiseshell"),
              ("bourbon", "brown"),
              ("bloodstone", "red"),
              ("agar", "tortoiseshell"),
              ("beluga", "black"),
              ("darjeeling", "brown"),
              ("amarena", "red"),
              ("frost", "clear"),
              ("vanta", "black"),
              ("auburn", "brown"),
              ("taupe", "beige"),
              ("rover", "green"),
              ("solar", "orange"),
              ("tempest", "grey"),
              ("charbon", "black"),
              ("suntan", "beige"),
              ("himalaya", "clear"),
              ("viridian", "green"),
              ("stallion", "black")),
    "shape": (("rond", "round"), ("ronds", "round"),  # masculine forms; the taxonomy lists ronde / rondes
              ("p3", "round"),  # Lafont: P3 / panto shape
              ("pantos square", "square"), ("cat eye butterfly", "cat_eye"),  # Etnia's one-shape labels
              ("almond", "oval"),  # Morel: a softly pointed oval
              ("polyangular", "geometric"), ("diamond", "geometric"),  # Dita's shape filter
              ("rounded", "round"), ("ovular", "oval"),  # E.B. Meyrowitz's "Build" line
              ("navigator", "aviator"),  # Dita: an aviator with a square lens
              # Anne & Valentin editorial shape forms
              ("papillonnante", "butterfly"), ("papillonnant", "butterfly"),
              ("trapezoidale", "wayfarer"), ("hexagone", "geometric"),
              ("octogone", "geometric"), ("bandeau", "shield"),
              # Kirk & Kirk editorial shape words
              ("roundness", "round"),
              ("upswept", "cat_eye"),
              ("aviators", "aviator"),
              ("angular", "geometric"),
              ("circular", "round"),
              # Oliver Goldsmith shape words
              ("squared aviator", "aviator"),
              # Retrosuperfuture shape words
              ("flat top", "square")),
}
CATEGORY_TAGS = {  # (dimension, code) -> folded category words, FR + EN
    ("audience", "men"): ("homme", "hommes", "man", "men", "masculine", "masculin"),
    ("audience", "women"): ("femme", "femmes", "woman", "women", "feminine", "feminin"),
    ("audience", "unisex"): ("mixte", "unisex", "unisexe"),
    ("product_type", "optical"): ("optique", "lunettes de vue", "vue", "eyeglasses", "optical"),
    ("product_type", "sun"): ("solaire", "solaires", "lunettes de soleil", "soleil", "sunglasses", "sun"),
}


@dataclass(frozen=True)
class Tag:
    dimension: str  # taxonomy dimension, or "audience" / "product_type"
    code: str
    field: str  # where it matched: "name" | "categories" | "spec:<key>"
    term: str  # the folded phrase that matched
    color_family: str | None = None  # Palier 1, color tags only (equals `code` today)
    color_hex: str | None = None  # Palier 2, the taxonomy's hex for the family
    supplier_code: str | None = None  # Palier 3, from the crawler's variants


Index = tuple[tuple[str, str], ...]  # (folded phrase, code), longest phrase first


_cache: dict[int, tuple[Taxonomy, dict[str, Index]]] = {}  # id -> (taxonomy kept alive, indexes)


def _indexes(taxonomy: Taxonomy) -> dict[str, Index]:
    hit = _cache.get(id(taxonomy))
    if hit and hit[0] is taxonomy:
        return hit[1]
    out: dict[str, Index] = {}
    for dim, items in taxonomy.items.items():
        pairs = {(fold(term), it.code) for it in items.values()
                 for term in (*it.synonyms_fr, *it.synonyms_en, it.label_fr, it.code)}
        out[dim] = tuple(sorted(((p, c) for p, c in pairs if p), key=lambda pc: (-len(pc[0].split()), -len(pc[0]), pc[0])))
    longest_first = lambda pairs: tuple(sorted(pairs, key=lambda pc: (-len(pc[0].split()), -len(pc[0]), pc[0])))
    out["_categories"] = longest_first((fold(w), f"{d}/{c}") for (d, c), words in CATEGORY_TAGS.items() for w in words)
    # spec values: taxonomy synonyms + store aliases; "audience" specs use the category words
    for dim in taxonomy.items:
        out[f"_spec_{dim}"] = longest_first({*out[dim], *SPEC_ALIASES.get(dim, ())})
    out["_spec_audience"] = longest_first((fold(w), c) for (d, c), words in CATEGORY_TAGS.items() if d == "audience" for w in words)
    _cache[id(taxonomy)] = (taxonomy, out)
    return out


def _match(text: str, index: Index, *, skip_ambiguous: bool) -> list[tuple[str, str]]:
    """(code, phrase) for every whole-word phrase found in folded text, consuming matched spans."""
    padded, found = f" {fold(text)} ", []
    for phrase, code in index:
        if skip_ambiguous and phrase in AMBIGUOUS_FREE_TEXT:
            continue
        needle = f" {phrase} "
        if needle in padded:
            found.append((code, phrase))
            padded = padded.replace(needle, " | ")
    return found


MAX_LAMINATION_CODE = 40  # product_tags.code


def _tag_layers(add, color_index: Index, code: str, layers: list[str]) -> None:
    """A multi-layer acetate variant ("Havana/Blue", code HV/BL): a color tag per layer's family, Bicolore
    (two_tone) unless every layer is the same known family, and a `lamination` tag when every layer has a family:
    its code is the distinct families sorted and joined ("blue+tortoiseshell"), so Havana/Blue and Blue/Havana are
    one combination (the store's layer order stays in flags). A layer with no family (Zebra) is never guessed."""
    families: list[str] = []
    complete = True
    for layer in layers:
        found = _match(layer, color_index, skip_ambiguous=False)
        complete &= bool(found)
        for family, term in found:
            add("color", family, "variant-layer", term, code)
            if family not in families:
                families.append(family)
    term = fold(" / ".join(layers))[:100]
    if not (complete and len(families) == 1):
        add("color", "two_tone", "variant-layers", term, code)
    combination = "+".join(sorted(families))
    if complete and len(families) >= 2 and len(combination) <= MAX_LAMINATION_CODE:
        add("lamination", combination, "variant-layers", term, code)


def tag_product(name: str, flags: dict | None, taxonomy: Taxonomy | None = None) -> list[Tag]:
    """All tags for one product. The first source to find a (dimension, code) is kept as provenance,
    in order of reliability: scoped specs, then categories, then the name."""
    taxonomy = taxonomy or load_taxonomy()
    idx = _indexes(taxonomy)
    dims = [d for d in idx if not d.startswith("_")]
    flags = flags or {}
    tags: dict[tuple[str, str, str | None], Tag] = {}

    def add(dim: str, code: str, field: str, term: str, supplier_code: str | None = None) -> None:
        key = (dim, code, supplier_code)
        if key in tags:
            return
        if dim == "color":
            tier = taxonomy.color_tier(code, supplier_code)
            tags[key] = Tag(dim, code, field, term, tier.family, tier.hex, tier.supplier_code)
        else:
            tags[key] = Tag(dim, code, field, term, supplier_code=clean_supplier_code(supplier_code))

    specs = flags.get("raw_specs")
    for key, value in (specs.items() if isinstance(specs, dict) else ()):
        target_dims = SPEC_DIMENSIONS.get(fold(str(key)))
        if not target_dims:
            continue
        if isinstance(target_dims, str):
            target_dims = (target_dims,)
        for dim in target_dims:
            if f"_spec_{dim}" in idx and isinstance(value, str):
                for code, term in _match(value, idx[f"_spec_{dim}"], skip_ambiguous=False):
                    add(dim, code, f"spec:{key}", term)

    desc = flags.get("description")
    if isinstance(desc, str):
        for code, term in _match(desc, idx["_spec_shape"], skip_ambiguous=True):
            add("shape", code, "description", term)

    material = flags.get("material")
    if isinstance(material, str):
        for code, term in _match(material, idx["_spec_material"], skip_ambiguous=False):
            add("material", code, "material", term)

    categories = flags.get("categories")
    if isinstance(categories, str):
        for dim_code, term in _match(categories, idx["_categories"], skip_ambiguous=False):
            dim, code = dim_code.split("/")
            add(dim, code, "categories", term)
        for dim in dims:
            for code, term in _match(categories, idx[dim], skip_ambiguous=True):
                add(dim, code, "categories", term)

    for dim in dims:
        for code, term in _match(name or "", idx[dim], skip_ambiguous=True):
            add(dim, code, "name", term)

    # Palier 3: a variant's label decides its family, its code rides along on the tag. Once a family has coded
    # tags, the uncoded tag of that family (from the name or a spec) adds nothing and is dropped.
    for variant in flags.get("variants") if isinstance(flags.get("variants"), list) else ():
        if not isinstance(variant, dict):
            continue
        code, label = clean_supplier_code(variant.get("code")), variant.get("color")
        if code and isinstance(label, str):
            for family, term in _match(label, idx["_spec_color"], skip_ambiguous=False):
                add("color", family, "variant", term, code)
        layers = [x for x in variant.get("layers") or () if isinstance(x, str)] if isinstance(variant.get("layers"), list) else []
        if code and len(layers) >= 2:
            _tag_layers(add, idx["_spec_color"], code, layers)
    coded = {(d, c) for d, c, s in tags if s}
    for key in [k for k in tags if k[2] is None and k[:2] in coded]:
        del tags[key]

    return sorted(tags.values(), key=lambda t: (t.dimension, t.code, t.supplier_code or ""))
