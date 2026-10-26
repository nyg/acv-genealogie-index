import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from places import arrondissement_history, localities_from_note, parish_name, split_official_locality  # noqa: E402
from scope_parser import parse_date_range, parse_scope_content  # noqa: E402


def test_french_date_range_widens_partial_dates():
    # When
    start, end = parse_date_range("1626 juillet 13 - 1630 janvier")

    # Then
    assert (start, end) == ("1626-07-13", "1630-01-31")


def test_date_range_ignores_text_after_comma():
    # When
    start, end = parse_date_range("1804 mai 18 - 1862, lacunes pour la période du 30 juin 1831 au 1er janvier 1849")

    # Then
    assert (start, end) == ("1804-05-18", "1862-12-31")


def test_date_range_reads_day_month_year_sentences():
    # When
    start, end = parse_date_range("Registre ouvert entre le 18 janvier 1999 et le 3 avril 2001")

    # Then
    assert (start, end) == ("1999-01-18", "2001-04-03")


def test_two_events_sharing_pages_both_get_the_pages():
    # Given
    scope = "Baptêmes (1728 juillet 27 - 1767 avril 5) et Naissances (1752 juillet 31 - 1767 avril 1), pp.1-365;\nMariages (tête-bêche) (1727 décembre 30 - 1767 juillet 21), pp.tête-bêche 1-65."

    # When
    segments = parse_scope_content(scope)

    # Then
    assert [(s.label, s.kinds, s.pages, s.head_to_tail) for s in segments] == [
        ("Baptêmes", ["naissance"], "pp.1-365", False),
        ("Naissances", ["naissance"], "pp.1-365", False),
        ("Mariages", ["mariage"], "pp.tête-bêche 1-65", True),
    ]


def test_section_headers_apply_to_following_lines():
    # Given
    scope = "Paroisse réformée de Cheseaux:\nBaptêmes (1575 février 13 - 1614 janvier 9), pp. 0-58;\nSullens annexe de la paroisse réformée de Cheseaux:\nMariages (1574 mai 4 - 1614 mars 6), pp. 271-301;"

    # When
    segments = parse_scope_content(scope)

    # Then
    assert [s.section for s in segments] == ["Paroisse réformée de Cheseaux", "Sullens annexe de la paroisse réformée de Cheseaux"]


def test_marriage_announcements_are_not_marriages():
    # When
    segments = parse_scope_content("Annonces de mariages célébrés ailleurs (1799 août 11 - 1811 octobre 28), pp. 37-90.")

    # Then
    assert (segments[0].kinds, segments[0].foreign) == (["annonce"], True)


def test_reconnaissance_is_not_a_birth():
    # When
    segments = parse_scope_content("Reconnaissances (1880 - 1890)")

    # Then
    assert segments[0].kinds == ["reconnaissance"]


def test_parish_name_prefers_annex_name():
    # When
    name = parish_name("Registres paroissiaux de Donatyre annexe de la paroisse réformée d'Avenches.")

    # Then
    assert name == "Donatyre"


def test_parish_name_keeps_article():
    # When
    name = parish_name("Registres de la paroisse réformée et de la commune de Château-d'Oex.")

    # Then
    assert name == "Château-d'Oex"


def test_localities_keep_their_period():
    # When
    localities = localities_from_note("Paroisse d'Aigle :\nComprend : Corbeyrier jusqu'en 1840 et 1846-1865, Leysin jusqu'en 1702.\nAnnexe : Yvorne (1846).")

    # Then
    assert localities == [
        {"name": "Corbeyrier", "qualifier": "jusqu'en 1840 et 1846-1865"},
        {"name": "Leysin", "qualifier": "jusqu'en 1702"},
        {"name": "Yvorne", "qualifier": "annexe (1846)"},
    ]


def test_official_locality_moves_trailing_article_to_front():
    # When
    name, context = split_official_locality("Chaux (La) (Sainte-Croix)")

    # Then
    assert (name, context) == ("La Chaux", "(Sainte-Croix)")


def test_arrondissement_history_follows_changes():
    # When
    history = arrondissement_history({"1876": "Agiez", "1912": "Agiez", "1928": "Agiez > Orbe (dès 01.04.1940)", "1960": "Orbe"})

    # Then
    assert history == [("Agiez", "1876"), ("Orbe", "01.04.1940")]
