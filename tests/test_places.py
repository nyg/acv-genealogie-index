import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from places import corrected_entries, parish_name_mismatches, repair_parish_names, spelling_key  # noqa: E402

PARISHES = {
    "1": ["L'Abbaye"], "7": ["Assens (catholique)"], "8": ["Aubonne"], "12": ["Begnins"], "25": ["Cheseaux"], "39": ["Les Croisettes"],
    "44": ["Daillens", "Daillens (Penthalaz)"], "51": ["Echallens"], "54": ["L'Etivaz"], "66": ["Villette", "Grandvaux-Villette"],
    "71": ["Lausanne"], "73": ["Le Lieu"], "80": ["Le Mont-sur-Lausanne"], "91": ["Nyon"], "94": ["Orbe"], "108": ["Prangins"],
    "110": ["Prilly"], "132": ["Vevey"], "133": ["Vich"],
}


def test_doubled_letter_and_accents_share_a_spelling_key():
    # When
    keys = {spelling_key("Chessières"), spelling_key("Chesières"), spelling_key("CHESIERES")}

    # Then
    assert len(keys) == 1


def test_leading_article_and_final_s_share_a_spelling_key():
    # When
    vernands, vernand = spelling_key("Les Vernands"), spelling_key("Vernand")

    # Then
    assert vernands == vernand


def test_different_names_keep_different_spelling_keys():
    # When
    chessel, chesieres = spelling_key("Chessel"), spelling_key("Chesières")

    # Then
    assert chessel != chesieres


def test_article_is_only_dropped_as_a_separate_word():
    # When
    leysin = spelling_key("Leysin")

    # Then
    assert leysin == "leysin"


def test_damaged_names_take_the_name_of_the_cited_parish():
    # Given
    descriptions = ["VëvèyT[132]", "Priliy [110] vers 1720-1821, sinon Lausanne [71]", "Grandvaux-ViHelte [66]", "Vieh [133]", "Frangins [108]", "Dahlens [44]"]

    # When
    repaired = [repair_parish_names(description, PARISHES) for description in descriptions]

    # Then
    assert repaired == ["Vevey [132]", "Prilly [110] vers 1720-1821, sinon Lausanne [71]", "Grandvaux-Villette [66]", "Vich [133]", "Prangins [108]", "Daillens [44]"]


def test_words_around_a_repaired_name_are_kept():
    # When
    repaired = repair_parish_names("Nyon [91] avant 1590, puis Vieh [133], Frangins [108] 1675-1835 et Nyon", PARISHES)

    # Then
    assert repaired == "Nyon [91] avant 1590, puis Vich [133], Prangins [108] 1675-1835 et Nyon"


def test_an_elided_de_glued_to_the_name_gets_its_apostrophe():
    # When
    repaired = [repair_parish_names(description, PARISHES) for description in ("puis dAubonne [8] de 1837 à 1849", "annexe d'Orbe [94] 1846-1849")]

    # Then
    assert repaired == ["puis d'Aubonne [8] de 1837 à 1849", "annexe d'Orbe [94] 1846-1849"]


def test_letter_spacing_spurious_diacritics_and_damaged_articles_are_repaired():
    # Given
    descriptions = ["Annexe de Che seaux [25]", "Ässens (catholique) [7]", "puis Fes Croisettes [39] dès 1663", "paroisse de F'Étivaz [54] dès 1713"]

    # When
    repaired = [repair_parish_names(description, PARISHES) for description in descriptions]

    # Then
    assert repaired == ["Annexe de Cheseaux [25]", "Assens (catholique) [7]", "puis Les Croisettes [39] dès 1663", "paroisse de L'Etivaz [54] dès 1713"]


def test_an_accent_on_a_capital_is_not_damage():
    # When
    repaired = [repair_parish_names(description, PARISHES) for description in ("Échallens (protestant) [51]", "Échaliens (protestant) [51]")]

    # Then
    assert repaired == ["Échallens (protestant) [51]", "Échallens (protestant) [51]"]


def test_short_forms_and_articles_merged_into_de_are_not_damage():
    # Given
    descriptions = ["Le Mont [80]", "dépendant du Mont [80]", "Annexe du Lieu [73]", "Abbaye (L') [1]"]

    # When
    repaired = [repair_parish_names(description, PARISHES) for description in descriptions]

    # Then
    assert repaired == descriptions


def test_a_name_unlike_the_cited_parish_is_left_alone():
    # Given
    descriptions = ["Mézières [12]", "Nyon [91] et Duillier [108] dès 1672"]

    # When
    repaired = [repair_parish_names(description, PARISHES) for description in descriptions]

    # Then
    assert repaired == descriptions


def test_a_name_neither_of_the_parish_nor_of_one_of_its_villages_is_a_mismatch():
    # When
    mismatches = parish_name_mismatches("Mézières [12]; Nyon [91] et Duillier [108]; Vieh [133]", PARISHES, {"108": ["Duillier"]})

    # Then
    assert mismatches == [("12", "Mézières")]


def test_a_reference_without_a_name_is_a_mismatch():
    # When
    mismatches = parish_name_mismatches("[110] vers 1720-1821, sinon Lausanne [71]", PARISHES, {})

    # Then
    assert mismatches == [("110", "")]


def test_a_correction_restores_an_entry_the_parser_merged_into_the_line_above():
    # Given
    table = [{"locality": "Villy (Ollon) r//?r(Gill)", "description": "OllonJ92] Bursins [20]", "parishes": ["20"]}]
    vincy = {"locality": "Vincy (Gilly)", "description": "Bursins [20]", "parishes": ["20"]}
    corrections = {"Villy (Ollon) r//?r(Gill)": {"locality": "Villy (Ollon)", "description": "Ollon [92]", "parishes": ["92"], "followedBy": vincy}}

    # When
    entries = list(corrected_entries(table, corrections))

    # Then
    assert entries == [{"locality": "Villy (Ollon)", "description": "Ollon [92]", "parishes": ["92"]}, vincy]
