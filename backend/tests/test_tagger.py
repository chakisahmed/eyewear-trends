"""Rule-based product tagging (zero LLM): folding, field scoping, ambiguity, longest match, categories."""

from app.collectors.stores.tagger import Tag, tag_product


def codes(tags: list[Tag]) -> set[tuple[str, str]]:
    return {(t.dimension, t.code) for t in tags}


def test_spec_value_is_folded_and_scoped_to_its_dimension():
    tags = tag_product("ADONIA", {"raw_specs": {"Gender": "Men", "Materials": "ACÉTATE", "Color": "Noir"}})
    assert codes(tags) == {("material", "acetate"), ("color", "black"), ("audience", "men")}  # Gender -> audience since v2
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


# --- rules v2 (mykenza / lunettek vocabulary) ----------------------------------------------------

def test_rules_version_3_rond_alias_still_applies():
    from app.collectors.stores.tagger import RULES_VERSION
    assert RULES_VERSION >= 3


def test_masculine_rond_maps_to_round_in_specs_only():
    assert codes(tag_product("X", {"raw_specs": {"Forme": "Rond"}})) == {("shape", "round")}
    assert codes(tag_product("X", {"raw_specs": {"Forme": "Ronds"}})) == {("shape", "round")}
    assert codes(tag_product("Rond point", None)) == set()  # free text: no alias


def test_frame_material_labels_and_steel_alias():
    for key in ("Matière du cadre", "Matériau du Cadre", "Matière de la monture"):
        assert codes(tag_product("X", {"raw_specs": {key: "Acier Inoxydable, TR90"}})) == {("material", "metal"), ("material", "tr90")}, key
    assert ("material", "metal") in codes(tag_product("X", {"raw_specs": {"Materials": "Inox"}}))
    assert codes(tag_product("X", {"raw_specs": {"Matière du cadre": "Plastique"}})) == set()  # acetate or injected: no guess


def test_store_aliases_only_apply_in_scoped_specs():
    assert ("color", "tortoiseshell") in codes(tag_product("X", {"raw_specs": {"COULEUR": "carey, Vert bouteille"}}))
    assert ("color", "tortoiseshell") not in codes(tag_product("Carey model", None))  # free text: no alias
    assert ("material", "metal") not in codes(tag_product("Acier edition", None))


def test_audience_from_gender_specs():
    assert codes(tag_product("X", {"raw_specs": {"Le sexe": "Femme, Homme"}})) == {("audience", "women"), ("audience", "men")}
    assert codes(tag_product("X", {"raw_specs": {"Gender": "Men"}})) == {("audience", "men")}


def test_mykenza_description_sample():
    from app.collectors.stores.parser import description_specs
    specs = description_specs("Lunette de soleil pour Femme de la Marque : Loewe – Forme : Oeil de Chat – "
                              "Style : Tendance – Matière du cadre : Plastique")
    got = codes(tag_product("Lunette de Soleil Femme Loewe LW40128I 01A", {"raw_specs": specs, "categories": "Lunette de Soleil Femme"}))
    assert got == {("shape", "cat_eye"), ("audience", "women"), ("product_type", "sun")}


# --- rules v4 (lamode.tn) ------------------------------------------------------------------------

def test_rules_version_4_forme_lunette_is_a_shape_label():
    from app.collectors.stores.tagger import RULES_VERSION
    assert RULES_VERSION >= 4  # 5 since the color tiers (test_color_tiers.py)
    assert codes(tag_product("X", {"raw_specs": {"Forme Lunette": "Cat-Eye"}})) == {("shape", "cat_eye")}
    assert codes(tag_product("X", {"raw_specs": {"Forme de la monture": "Carrée"}})) == {("shape", "square")}


def test_rules_version_6_etnia_shape_labels_give_one_shape_each():
    from app.collectors.stores.tagger import RULES_VERSION
    assert RULES_VERSION >= 6
    shape = lambda v: codes(tag_product("KORE", {"raw_specs": {"Forme": v}}))
    assert shape("PANTOS SQUARE") == {("shape", "square")}                   # not also round (pantos)
    assert shape("CAT-EYE/BUTTERFLY") == {("shape", "cat_eye")}              # not also butterfly
    assert shape("PANTOS") == {("shape", "round")} and shape("PILOT") == {("shape", "aviator")}
    assert shape("RECTANGULAR") == {("shape", "rectangle")}
    assert shape("PEAR") == shape("OTHER") == set()
    assert codes(tag_product("Pantos square edition", None)) == {("shape", "round"), ("shape", "square")}  # alias: specs only


def test_rules_version_7_color_families_v2_on_store_vocabulary():
    from app.collectors.stores.tagger import RULES_VERSION
    assert RULES_VERSION >= 7
    family = lambda label: {c for d, c in codes(tag_product("X", {"variants": [{"code": "C", "color": label}]}))}
    expected = {  # Etnia's color names that had no family before v7
        "blue": ["Blue", "Blue Denim", "Dark Blue", "Sky Blue", "Turquoise", "Petrol"], "grey": ["Grey", "Dark Grey"],
        "white": ["White"], "red": ["Bordeaux", "Red"], "green": ["Green", "Army"], "pink": ["Pink", "Fuchsia"],
        "purple": ["Purple", "Violet", "Aubergine"], "orange": ["Orange", "Coral", "Lemon", "Yellow"],
        "silver": ["Gun Metal"], "brown": ["Honey"], "gold": ["Pink Gold", "Rose Gold"]}
    for code, labels in expected.items():
        for label in labels:
            assert family(label) == {code}, label
    for label in ("Bronze", "Copper", "Zebra"):  # a metal tone or a pattern, not a hue: untagged on purpose
        assert family(label) == set(), label


def test_color_words_that_are_also_names_only_count_in_specs():
    assert codes(tag_product("Lunettes ROSE C2", None)) == set()
    assert codes(tag_product("ORANGE sunglasses", None)) == set()
    assert codes(tag_product("X", {"raw_specs": {"Couleur": "Rose"}})) == {("color", "pink")}
    assert codes(tag_product("Monture bleue", None)) == {("color", "blue")}                   # unambiguous words still count


# --- rules v8: acetate layers -> a color per layer, Bicolore, and a lamination combination -----------------

def layered(*layers: str, code: str = "HV/BL", color: str | None = None) -> set[tuple]:
    variant = {"code": code, "color": color or layers[0], "layers": list(layers)}
    return {(t.dimension, t.code, t.supplier_code) for t in tag_product("X", {"variants": [variant]})}


def test_rules_version_8_two_layers_give_both_colors_bicolore_and_a_combination():
    from app.collectors.stores.tagger import RULES_VERSION
    assert RULES_VERSION >= 8
    assert layered("Havana", "Blue") == {("color", "tortoiseshell", "HV/BL"), ("color", "blue", "HV/BL"),
                                         ("color", "two_tone", "HV/BL"), ("lamination", "blue+tortoiseshell", "HV/BL")}
    assert ("lamination", "blue+tortoiseshell", "BL/HV") in layered("Blue", "Havana", code="BL/HV")  # order-free code


def test_a_layer_with_no_family_is_never_guessed_into_a_combination():
    assert layered("Black", "Zebra", code="BK/ZE") == {("color", "black", "BK/ZE"), ("color", "two_tone", "BK/ZE")}


def test_same_family_layers_are_neither_bicolore_nor_a_combination():
    assert layered("Havana", "Tortoise") == {("color", "tortoiseshell", "HV/BL")}


def test_three_layers_and_no_layers():
    got = layered("Pink", "Red", "Cream", code="PK/RD/CR")                  # the cadrage's rose + rouge + crème
    assert ("lamination", "beige+pink+red", "PK/RD/CR") in got and ("color", "two_tone", "PK/RD/CR") in got
    plain = {(t.dimension, t.code, t.supplier_code) for t in tag_product("X", {"variants": [{"code": "BK", "color": "Black"}]})}
    assert plain == {("color", "black", "BK")}                             # no layers: unchanged from v7
    assert layered("Havana") == {("color", "tortoiseshell", "HV/BL")}       # one layer is not a lamination


def test_rules_version_10_morel_vocabulary_in_specs_and_variants_only():
    from app.collectors.stores.tagger import RULES_VERSION
    assert RULES_VERSION >= 10
    assert codes(tag_product("X", {"raw_specs": {"Shape": "Almond"}})) == {("shape", "oval")}
    assert codes(tag_product("X", {"variants": [{"code": "RU01", "color": "Ruthenium"}]})) == {("color", "grey")}
    assert codes(tag_product("Almond edition", None)) == set()                  # free text: no alias


def test_face_shape_is_never_a_frame_shape():
    """LaMode lists VISAGE (recommended face shapes: Ovale, Rond...) next to Forme Lunette."""
    specs = {"Forme Lunette": "Carrée", "Genre": "Femmes", "VISAGE": "Rond", "Magasin": "Magasin Centre X"}
    assert codes(tag_product("Lunettes de Vue Femme GUCCI GG1003OA", {"raw_specs": specs})) == {
        ("shape", "square"), ("audience", "women")}                         # no round, no oval from VISAGE


def test_rules_version_11_barton_perreira_colour_names_in_variants_and_both_cat_eye_spellings():
    from app.collectors.stores.tagger import RULES_VERSION
    assert RULES_VERSION >= 11
    assert codes(tag_product("X", {"raw_specs": {"Shape": "Cateye"}})) == {("shape", "cat_eye")}
    assert codes(tag_product("X", {"raw_specs": {"Shape": "Cat Eye"}})) == {("shape", "cat_eye")}
    for label in ("Chestnut", "Espresso", "Hickory"):
        assert codes(tag_product("X", {"variants": [{"code": "C", "color": label}]})) == {("color", "brown")}, label
    assert codes(tag_product("Chestnut hickory espresso", None)) == set()                       # colour aliases: specs and variants only
