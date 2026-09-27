"""Rule-based taxonomy tagging of store products: zero LLM, no database.

A product's name, categories and raw_specs are matched against taxonomy.yaml synonyms (FR + EN):
- text is accent-folded (the taxonomy's own `fold`), matches are whole words, longest phrase first,
  and a matched span is consumed ("papillon relevé" -> cat_eye, not also butterfly);
- raw_specs are field-scoped: a "Materials" value is only matched against materials, and so on;
- in free text (name, categories) a few ambiguous synonyms are ignored ("or" = gold in French, but
  also the English word); they still count inside a scoped spec ("Couleur: Or").
Categories also give non-taxonomy tags: audience (men/women/unisex), product_type (optical/sun).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.taxonomy import Taxonomy, fold, load_taxonomy

RULES_VERSION = 4  # stored with each tag; bump when the rules below change, then run retag-products
# v2: frame-material and gender spec labels, store vocabulary aliases (mykenza.tn, lunettek.com)
# v3: "Rond" / "Ronds" (masculine forms, MyKenza) -> round
# v4: "Forme Lunette" and similar frame-shape labels (lamode.tn). Its "VISAGE" rows (recommended face
#     shapes) are deliberately NOT a label: a face shape is not the frame's shape.

AMBIGUOUS_FREE_TEXT = frozenset({"or", "bold", "wrap", "wire", "xl", "sport"})
SPEC_DIMENSIONS = {  # folded raw_specs key -> the only dimension its value is matched against
    "materials": "material", "material": "material", "matiere": "material", "matieres": "material",
    "materiau": "material", "materiaux": "material", "matiere du cadre": "material",
    "materiau du cadre": "material", "matiere de la monture": "material", "materiau de la monture": "material",
    "gender": "audience", "genre": "audience", "sexe": "audience", "le sexe": "audience",
    "color": "color", "colour": "color", "couleur": "color", "coloris": "color",
    "forme": "shape", "shape": "shape", "forme lunette": "shape", "forme de lunette": "shape",
    "forme monture": "shape", "forme de la monture": "shape",
    "style": "style",
}
# Store vocabulary the taxonomy does not list (taxonomy.yaml also feeds the LLM prompt and Google
# Trends, so it stays untouched). Only applied to scoped spec values, never to names or categories.
# "Plastique" is deliberately absent: it could be acetate or injected TR90.
SPEC_ALIASES = {  # dimension -> (folded phrase, code)
    "material": (("acier inoxydable", "metal"), ("acier", "metal"), ("inox", "metal"), ("stainless steel", "metal")),
    "color": (("carey", "tortoiseshell"),),  # Hawkers' word for tortoiseshell
    "shape": (("rond", "round"), ("ronds", "round")),  # masculine forms; the taxonomy lists ronde / rondes
}
CATEGORY_TAGS = {  # (dimension, code) -> folded category words, FR + EN
    ("audience", "men"): ("homme", "hommes", "man", "men"),
    ("audience", "women"): ("femme", "femmes", "woman", "women"),
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


def tag_product(name: str, flags: dict | None, taxonomy: Taxonomy | None = None) -> list[Tag]:
    """All tags for one product. The first source to find a (dimension, code) is kept as provenance,
    in order of reliability: scoped specs, then categories, then the name."""
    idx = _indexes(taxonomy or load_taxonomy())
    dims = [d for d in idx if not d.startswith("_")]
    flags = flags or {}
    tags: dict[tuple[str, str], Tag] = {}

    def add(dim: str, code: str, field: str, term: str) -> None:
        tags.setdefault((dim, code), Tag(dim, code, field, term))

    specs = flags.get("raw_specs")
    for key, value in (specs.items() if isinstance(specs, dict) else ()):
        dim = SPEC_DIMENSIONS.get(fold(str(key)))
        if f"_spec_{dim}" in idx and isinstance(value, str):
            for code, term in _match(value, idx[f"_spec_{dim}"], skip_ambiguous=False):
                add(dim, code, f"spec:{key}", term)

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

    return sorted(tags.values(), key=lambda t: (t.dimension, t.code))
