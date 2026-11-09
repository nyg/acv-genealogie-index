import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from places import corrected_entries, localities_from_note, note_periods, parish_name_mismatches, parish_period, repair_parish_names, spelling_key, union_periods  # noqa: E402

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


ROCHE = "Noville [90], puis Roche [114 bis] 1776/1821-1837; annexe d'Yvorne [143] dès 1837, Villeneuve [136] 1845-1863 et Yvorne"
ROCHE_PARISHES = {"90": ["Noville"], "114 bis": ["Roche"], "136": ["Villeneuve"], "143": ["Yvorne"]}


def test_a_parish_cited_for_a_closed_period_is_bounded_to_it():
    # When
    periods = [parish_period("Arzier [5] ; annexe de Genolier[58] 1846-1849", number) for number in ("5", "58")]

    # Then
    assert periods == [None, [(1846, 1849)]]


def test_a_parish_cited_for_several_periods_is_bounded_to_each():
    # When
    period = parish_period("Mézières [79], puis Syens [89] 1842-1846 et dès 1864", "89")

    # Then
    assert period == [(1842, 1846), (1864, None)]


def test_a_parish_followed_by_another_is_bounded_to_the_years_the_other_leaves():
    # When
    period = parish_period("Mézières [79], puis Syens [89] 1842-1846 et dès 1864", "79")

    # Then
    assert period == [(None, 1842), (1846, 1864)]


def test_a_parish_cited_twice_is_left_unbounded():
    # When
    period = parish_period("Cronay [40]; Orzens (Cronay) [40] 1846-1863", "40")

    # Then
    assert period is None


def test_an_annex_that_became_a_parish_is_bounded_to_the_years_before():
    # Given
    description = "Dépendance médiévale de Peney, puis annexe de Sainte-Croix [121] en 1540, paroisse de Bullet [19] dès1663"

    # When
    periods = [parish_period(description, number) for number in ("121", "19")]

    # Then
    assert periods == [[(1540, 1663)], [(1663, None)]]


def test_each_parish_of_a_succession_is_bounded_to_its_years():
    # When
    periods = [parish_period(ROCHE, number, ROCHE_PARISHES) for number in ("90", "114 bis", "143", "136")]

    # Then
    assert periods == [[(None, 1776)], [(1776, 1837)], [(1837, 1845), (1863, None)], [(1845, 1863)]]


def test_a_parish_named_again_with_years_also_gets_those_years():
    # Given
    description = "Annexe de Bercher [14] jusqu'en 1724, puis de Pailly [99] dès 1725 et de Bercher dès 1846"

    # When
    period = parish_period(description, "14", {"14": ["Bercher"]})

    # Then
    assert period == [(None, 1724), (1846, None)]


def test_a_parish_named_again_without_years_is_left_unbounded():
    # Given
    description = "Aubonne [8] jusqu'en 1846, puis Saint-Livres [122] et de nouveau Aubonne"

    # When
    period = parish_period(description, "8", {"8": ["Aubonne"]})

    # Then
    assert period is None


def test_an_exception_bounds_the_excepted_parish_only():
    # When
    periods = [parish_period("Château-d'Œx [23], sauf 1846-1863 Rossinière [117]", number) for number in ("23", "117")]

    # Then
    assert periods == [None, [(1846, 1863)]]


def test_a_parish_a_place_was_detached_from_is_bounded_until_then():
    # When
    period = parish_period("Savigny [125] (détaché de Lutry [78] en 1598)", "78")

    # Then
    assert period == [(None, 1598)]


def test_a_damaged_period_leaves_the_parish_unbounded():
    # Given
    descriptions = ["Rances [113] jusqu'en 1662 et 184F!849, Montcherand [82] 1679-1844", "Montagny [81] jusqu'en 1834 et 1846 1849, Champvent [22] 1834-1846 et dès 1849"]

    # When
    periods = [parish_period(description, number) for description, number in zip(descriptions, ("113", "81"))]

    # Then
    assert periods == [None, None]


def test_a_note_listing_an_annex_with_its_years_bounds_it_to_them():
    # Given
    qualifiers = ["annexe (jusqu'en 1663)", "annexe (1837-1845 et dès 1863)", "(1837-1849 1863-1868)", "adjonction en 1936"]

    # When
    periods = [note_periods(qualifier) for qualifier in qualifiers]

    # Then
    assert periods == [[(None, 1663)], [(1837, 1845), (1863, None)], [(1837, 1849), (1863, 1868)], [(1936, None)]]


def test_own_registers_kept_with_an_annex_widen_its_years():
    # When
    period = note_periods("annexe 1811-1837 avec registres propres 1720-1821")

    # Then
    assert period == [(1720, 1837)]


def test_a_note_with_other_years_or_none_leaves_the_annex_unbounded():
    # Given
    qualifiers = ["annexe (1765-1833) mais registres 1770-1838 sous Palézieux", "annexe (détaché en 1713)", "annexe"]

    # When
    periods = [note_periods(qualifier) for qualifier in qualifiers]

    # Then
    assert periods == [None, None, None]


def test_an_annex_of_a_series_note_gets_the_years_of_the_note():
    # Given
    note = "Paroisse de Noville :\nAnnexes : Chessel (1529-1728 et dès 1837), Roche (1582-1821), avec registres distincts 1776-1821, puis séparés."

    # When
    periods = {locality["name"]: note_periods(locality["qualifier"]) for locality in localities_from_note(note)}

    # Then
    assert periods == {"Chessel": [(1529, 1728), (1837, None)], "Roche": [(1582, 1821)]}


def test_years_of_two_sources_add_up_unless_one_gives_none():
    # When
    periods = [union_periods([(None, 1776)], [(1582, 1821)]), union_periods([(1846, 1849)], None), union_periods([(1837, 1845)], [(1863, None)])]

    # Then
    assert periods == [[(None, 1821)], None, [(1837, 1845), (1863, None)]]
