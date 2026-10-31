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


def test_pages_written_before_the_dates_are_read():
    # Given
    scope = "Mariages: Pages 138-143 et 178-181 (1598 octobre 22 - 1605 janvier 20);\nBaptêmes: Pages 146-177 (1586 février 23 - 1599 octobre 21)."

    # When
    segments = parse_scope_content(scope)

    # Then
    assert [(s.label, s.kinds, s.start, s.end, s.pages) for s in segments] == [
        ("Mariages", ["mariage"], "1598-10-22", "1605-01-20", "Pages 138-143 et 178-181"),
        ("Baptêmes", ["naissance"], "1586-02-23", "1599-10-21", "Pages 146-177"),
    ]


def test_hyphenated_words_stay_in_the_label():
    # Given
    scope = "Mariages tête-bêche (1726 décembre 31 - 1781 avril 27), pp. 201-242;"

    # When
    segments = parse_scope_content(scope)

    # Then
    assert [(s.label, s.kinds, s.pages, s.head_to_tail) for s in segments] == [
        ("Mariages tête-bêche", ["mariage"], "pp. 201-242", True),
    ]


def test_part_listing_replaces_the_summary_it_repeats():
    # Given
    scope = "\n".join([
        "Baptêmes (1643 juillet 1 - 1713 avril 23), pp. 1-53; pp. 66-100 et 105-314;",
        "Mariages (1643 juillet 1 - 1659 octobre 7), pp.tête-bêche 0-14;",
        "Partie1",
        "Pages 1 à 53: Baptêmes (1643 juillet 1 - 1659 octobre 26).",
        "Pages 66 à 314: Baptêmes (1659 novembre 20 - 1713 avril 23).",
        "Partie 2",
        "Pages 0 à 14, tête-bêche: Mariages (1643 juillet 1 - 1659 octobre 7).",
    ])

    # When
    segments = parse_scope_content(scope)

    # Then
    assert [(s.label, s.start, s.end, s.pages, s.head_to_tail) for s in segments] == [
        ("Baptêmes", "1643-07-01", "1659-10-26", "Pages 1 à 53", False),
        ("Baptêmes", "1659-11-20", "1713-04-23", "Pages 66 à 314", False),
        ("Mariages", "1643-07-01", "1659-10-07", "Pages 0 à 14, tête-bêche", True),
    ]


def test_part_listing_keeps_the_summary_lines_it_does_not_cover():
    # Given
    scope = "\n".join([
        "Décès (1798 janvier 17 - 1821 juin 30), p. 99 et pp.tête-bêche 101-171.",
        "Partie 1:",
        "Pages 0-41",
        "Partie 2:",
        "Page 98: copie de la demande de la municipalité;",
        "Page 99: registre mortuaire (1816-1822).",
    ])

    # When
    segments = parse_scope_content(scope)

    # Then
    assert [(s.label, s.start, s.end, s.pages, s.section) for s in segments] == [
        ("Décès", "1798-01-17", "1821-06-30", "p. 99 et pp.tête-bêche 101-171", ""),
        ("registre mortuaire", "1816-01-01", "1822-12-31", "Page 99", ""),
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
