import pytest

from app.extraction.schema import extraction_model
from app.taxonomy import load_taxonomy


@pytest.fixture(scope="module")
def tax():
    return load_taxonomy()


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("Œil de chat", ("shape", "cat_eye")),
        ("oeil-de-chat", ("shape", "cat_eye")),
        ("cat eye", ("shape", "cat_eye")),
        ("écaille", ("color", "tortoiseshell")),
        ("Tortoiseshell", ("color", "tortoiseshell")),
        ("havana", ("color", "tortoiseshell")),
        ("titane", ("material", "titanium")),
        ("Titanium", ("material", "titanium")),
        ("sans monture", ("shape", "rimless")),
        ("rimless", ("shape", "rimless")),
    ],
)
def test_fr_and_en_synonyms_map_to_same_code(tax, term, expected):
    assert tax.normalize(term) == expected


def test_unknown_term(tax):
    assert tax.normalize("chaussures") is None


def test_every_item_has_bilingual_queries(tax):
    for item, fr, en in tax.keyword_pairs():
        assert fr and en, item.code


def test_colors_have_swatches(tax):
    assert all(it.hex for it in tax.items["color"].values())


# --- color families v2 (2026-09-29): blue, red, green, grey, white, pink, purple, orange; bold = Multicolore ------

@pytest.mark.parametrize(("term", "code"), [
    ("bleu marine", "blue"), ("navy", "blue"), ("turquoise", "blue"),
    ("bordeaux", "red"), ("burgundy", "red"),
    ("kaki", "green"), ("khaki", "green"), ("olive", "green"),
    ("gris", "grey"), ("charcoal", "grey"),
    ("ivoire", "white"), ("off-white", "white"),
    ("fuchsia", "pink"), ("rose", "pink"),
    ("aubergine", "purple"), ("plum", "purple"),
    ("jaune", "orange"), ("mustard", "orange"),
    ("rose gold", "gold"), ("yellow gold", "gold"), ("or rose", "gold"),       # metal finishes, not hues
    ("rose poudré", "pastel"), ("vert d'eau", "pastel"), ("lavender", "pastel"),
    ("gun metal", "silver"), ("honey", "brown"),
    ("multicolore", "bold"), ("neon", "bold"),
])
def test_color_families_v2(tax, term, code):
    assert tax.normalize(term, "color") == ("color", code)


def test_bold_is_the_multicolor_family_and_no_longer_holds_named_hues(tax):
    bold = tax.get("color", "bold")
    assert bold.multicolor and [c for c, it in tax.items["color"].items() if it.multicolor] == ["bold"]
    assert not {"rouge", "vert", "jaune", "red", "green", "yellow", "cobalt"} & set(bold.synonyms_fr + bold.synonyms_en)
    assert tax.to_public()["color"]["items"][-3] == {"code": "bold", "label": "Multicolore / Vives", "hex": bold.hex,
                                                      "multicolor": True}


def test_color_family_hexes_are_distinct(tax):
    hexes = [it.hex for it in tax.items["color"].values()]
    assert len(hexes) == len(set(hexes))


def test_extraction_schema_only_accepts_taxonomy_codes():
    Model = extraction_model()
    ok = Model.model_validate({
        "is_relevant": True, "language": "fr",
        "shape": [{"code": "cat_eye", "stance": "rising", "evidence": "l'œil de chat revient"}],
        "summary_fr": "x",
    })
    assert ok.shape[0].code == "cat_eye"
    with pytest.raises(ValueError):
        Model.model_validate({"is_relevant": True, "language": "fr",
                              "shape": [{"code": "triangle", "stance": "rising", "evidence": "?"}], "summary_fr": ""})
