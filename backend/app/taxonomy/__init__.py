"""Load the taxonomy and normalize free text (FR or EN) to language-neutral codes."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

TAXONOMY_PATH = Path(__file__).with_name("taxonomy.yaml")


@dataclass(frozen=True)
class Item:
    dimension: str
    code: str
    label_fr: str
    synonyms_fr: tuple[str, ...]
    synonyms_en: tuple[str, ...]
    query_fr: str
    query_en: str
    hex: str | None = None
    multicolor: bool = False  # a color family with no single hue ("Multicolore"): drawn as a gradient, hex is a fallback


@dataclass(frozen=True)
class ColorTier:
    """The three tiers of a frame color (stakeholder schema, 2026-09-29).

    family: Palier 1, the taxonomy color code (`black`, `tortoiseshell`).
    hex: Palier 2, the taxonomy's hex for that family. A default, not a measured shade of one product.
    supplier_code: Palier 3, a commercial variant or supplier material code ("HV/BL"). Never in the YAML: it is
    ingested per product by a crawler, so it is only carried here."""

    family: str
    hex: str
    supplier_code: str | None = None


MAX_SUPPLIER_CODE = 60
_HEX = re.compile(r"^#[0-9a-f]{6}$")


def clean_supplier_code(raw: object) -> str | None:
    """Palier 3 as stored: whitespace collapsed, case kept (codes are the store's own), None when empty."""
    if not isinstance(raw, str):
        return None
    code = " ".join(raw.split())[:MAX_SUPPLIER_CODE]
    return code or None


@dataclass
class Taxonomy:
    dimension_labels: dict[str, str]
    items: dict[str, dict[str, Item]] = field(default_factory=dict)

    @property
    def dimensions(self) -> list[str]:
        return list(self.items)

    def codes(self, dimension: str) -> list[str]:
        return list(self.items[dimension])

    def get(self, dimension: str, code: str) -> Item:
        return self.items[dimension][code]

    def label(self, dimension: str, code: str) -> str:
        return self.items[dimension][code].label_fr

    def color_tier(self, code: str, supplier_code: str | None = None) -> ColorTier:
        """Palier 1 + 2 for a color family, with the Palier 3 code a crawler supplied (if any)."""
        item = self.items["color"][code]
        assert item.hex, code  # load_taxonomy guarantees a hex on every color
        return ColorTier(family=item.code, hex=item.hex, supplier_code=clean_supplier_code(supplier_code))

    def normalize(self, term: str, dimension: str | None = None) -> tuple[str, str] | None:
        """Map a free-text term (FR or EN) to (dimension, code), or None if unknown."""
        needle = _fold(term)
        dims = [dimension] if dimension else self.dimensions
        for dim in dims:
            for item in self.items[dim].values():
                if needle == _fold(item.code) or needle == _fold(item.label_fr):
                    return dim, item.code
                if any(needle == _fold(s) for s in item.synonyms_fr + item.synonyms_en):
                    return dim, item.code
        return None

    def keyword_pairs(self, dimension: str | None = None) -> list[tuple[Item, str, str]]:
        """Bilingual search keywords: (item, fr_query, en_query)."""
        dims = [dimension] if dimension else self.dimensions
        return [(it, it.query_fr, it.query_en) for d in dims for it in self.items[d].values()]

    def to_prompt(self) -> str:
        """Compact, deterministic rendering for the LLM system prompt (cache-friendly)."""
        lines: list[str] = []
        for dim, items in self.items.items():
            lines.append(f"## {dim}")
            for it in items.values():
                syn = ", ".join(it.synonyms_fr + it.synonyms_en)
                lines.append(f"- {it.code}: {syn}")
        return "\n".join(lines)

    def to_public(self) -> dict:
        return {
            dim: {
                "label": self.dimension_labels[dim],
                "items": [
                    {"code": it.code, "label": it.label_fr, "hex": it.hex, **({"multicolor": True} if it.multicolor else {})}
                    for it in items.values()
                ],
            }
            for dim, items in self.items.items()
        }


def _fold(text: str) -> str:
    """Lowercase, strip accents and punctuation so 'Œil-de-chat' == 'oeil de chat'."""
    text = text.lower().replace("œ", "oe").replace("æ", "ae")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


fold = _fold  # public: the same folding for store product tagging (collectors/stores/tagger.py)


@lru_cache
def load_taxonomy(path: Path = TAXONOMY_PATH) -> Taxonomy:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    tax = Taxonomy(dimension_labels={})
    for dim, spec in raw["dimensions"].items():
        tax.dimension_labels[dim] = spec["label_fr"]
        tax.items[dim] = {
            code: Item(
                dimension=dim,
                code=code,
                label_fr=v["fr"],
                synonyms_fr=tuple(v.get("synonyms_fr", [])),
                synonyms_en=tuple(v.get("synonyms_en", [])),
                query_fr=v["query"]["fr"],
                query_en=v["query"]["en"],
                hex=v.get("hex"),
                multicolor=bool(v.get("multicolor", False)),
            )
            for code, v in spec["items"].items()
        }
    for code, item in tax.items.get("color", {}).items():
        if not (item.hex and _HEX.match(item.hex)):
            raise ValueError(f"taxonomy color {code!r} needs a #rrggbb hex (Palier 2), got {item.hex!r}")
    return tax
