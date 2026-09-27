"""Rule-based product tagging (zero LLM): folding, field scoping, ambiguity, longest match, categories."""

from app.collectors.stores.tagger import Tag, tag_product


def codes(tags: list[Tag]) -> set[tuple[str, str]]:
    return {(t.dimension, t.code) for t in tags}


def test_spec_value_is_folded_and_scoped_to_its_dimension():
    tags = tag_product("ADONIA", {"raw_specs": {"Gender": "Men", "Materials": "ACÉTATE", "Color": "Noir"}})
    assert codes(tags) == {("material", "acetate"), ("color", "black")}
    acetate = next(t for t in tags if t.code == "acetate")
    assert (acetate.field, acetate.term) == ("spec:Materials", "acetate")


def test_spec_scoping_keeps_values_in_their_dimension():
    # "Metal" under Couleur must not become a material; unknown spec keys are ignored
    assert codes(tag_product("X", {"raw_specs": {"Couleur": "Metal", "Pont": "Acetate"}})) == set()


def test_ambiguous_terms_only_count_in_scoped_specs():
    assert ("color", "gold") not in codes(tag_product("Monture or noir", None))        # "or" in free text: skipped
    assert ("color", "black") in codes(tag_product("Monture or noir", None))
    assert ("color", "gold") in codes(tag_product("X", {"raw_specs": {"Couleur": "Or"}}))
    assert codes(tag_product("Bold XL sport", None)) == set()


def test_longest_phrase_wins_and_consumes_its_span():
    got = codes(tag_product("Lunettes papillon relevé", None))
    assert ("shape", "cat_eye") in got and ("shape", "butterfly") not in got
    assert ("shape", "butterfly") in codes(tag_product("Lunettes papillon", None))


def test_whole_words_only():
    assert codes(tag_product("Rondelle Carrefour", None)) == set()  # "ronde", "carre" inside other words
    assert ("shape", "round") in codes(tag_product("Lunettes rondes", None))


def test_categories_map_fr_and_en_to_the_same_tags():
    fr = codes(tag_product("AYLAN C3", {"categories": "Homme, Optique"}))
    en = codes(tag_product("ADONIA", {"categories": "Eyeglasses, Man"}))
    assert fr == en == {("audience", "men"), ("product_type", "optical")}
    assert codes(tag_product("X", {"categories": "Femme, Solaire"})) == {("audience", "women"), ("product_type", "sun")}
    assert codes(tag_product("X", {"categories": "Sunglasses, Woman"})) == {("audience", "women"), ("product_type", "sun")}


def test_real_outika_products_give_no_shape_and_typos_do_not_match():
    for name in ("AYLAN C3", "ASSIL.S C2", "EVAN", "OUGARIT C3"):
        assert not {d for d, _ in codes(tag_product(name, None))}, name
    assert codes(tag_product("X", {"raw_specs": {"Materials": "Titanum"}})) == set()  # site typo, not titanium
    assert codes(tag_product("X", {"raw_specs": {"Materials": "Titane"}})) == {("material", "titanium")}


def test_first_source_is_kept_as_provenance_and_results_are_sorted():
    tags = tag_product("Monture acétate", {"raw_specs": {"Materials": "Acetate"}, "categories": "Femme, Solaire"})
    assert [(t.dimension, t.code, t.field) for t in tags] == [
        ("audience", "women", "categories"), ("material", "acetate", "spec:Materials"), ("product_type", "sun", "categories")]
    assert tag_product("", None) == [] and tag_product("X", {"raw_specs": "not a dict"}) == []
