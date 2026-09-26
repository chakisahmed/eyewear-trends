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
