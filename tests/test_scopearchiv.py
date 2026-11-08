import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from scopearchiv import creation_dates, justificative_segments, series_arrondissement_names  # noqa: E402


def test_creation_dates_in_us_order_become_day_month_year():
    # When
    dates = creation_dates({"Creation date(s)": "1/6/1876 - 12/30/1928"})

    # Then
    assert dates == "06.01.1876 - 30.12.1928"


def test_creation_dates_with_years_only_stay_as_they_are():
    # When
    dates = creation_dates({"Creation date(s)": "1882 - 1996"})

    # Then
    assert dates == "1882 - 1996"


def box(title):
    return {"slug": "sa-1", "title": title, "scope": "", "start": "1889-01-01", "end": "1890-12-31", "dates": "1889-1890"}


def test_listed_content_keeps_a_missing_part_remark_in_its_label():
    # When
    segments = justificative_segments(box("- Mariages A et B 1890\n- Naissances 1889-1890 (Il manque les naissances A)"))

    # Then
    assert [(segment["label"], segment["kinds"], segment["start"], segment["end"]) for segment in segments] == [
        ("Pièces justificatives : Mariages A et B", ["pj", "mariage"], "1890-01-01", "1890-12-31"),
        ("Pièces justificatives : Naissances (Il manque les naissances A)", ["pj", "naissance"], "1889-01-01", "1890-12-31"),
    ]


def test_listed_content_ignores_act_numbers_between_its_dates():
    # When
    segments = justificative_segments(box("- Mariages 1940 (Nos 51-102)-1942 (Nos 1-20)"))

    # Then
    assert [(segment["label"], segment["start"], segment["end"]) for segment in segments] == [
        ("Pièces justificatives : Mariages", "1940-01-01", "1942-12-31"),
    ]


def test_listed_content_on_one_line_is_split_at_each_dash():
    # When
    segments = justificative_segments(box("Aigle (arrondissement d'état civil)") | {
        "scope": "Aigle (arrondissement de l'état civil): - Naissances 1965 (No 1-110)-1967 (No 90-137) - Mariages 1965-1966 - Décès 1965-1966 - Sous-séries diverses relatives à l'état civil 1965-1967.",
    })

    # Then
    assert [(segment["label"], segment["start"], segment["end"]) for segment in segments] == [
        ("Pièces justificatives : Naissances", "1965-01-01", "1967-12-31"),
        ("Pièces justificatives : Mariages", "1965-01-01", "1966-12-31"),
        ("Pièces justificatives : Décès", "1965-01-01", "1966-12-31"),
    ]


def test_listed_content_split_by_backslash_dashes():
    # When
    segments = justificative_segments(box("Aubonne (arrondissement de l'état civil): \\ - Mariages 1951-1954 \\ - Naissances 1953-1954"))

    # Then
    assert [(segment["label"], segment["kinds"]) for segment in segments] == [
        ("Pièces justificatives : Mariages", ["pj", "mariage"]),
        ("Pièces justificatives : Naissances", ["pj", "naissance"]),
    ]


def test_sb_324_box_takes_the_arrondissement_of_its_series():
    # Given
    series = {"slug": "sa-2", "parent": "sa-1", "f": {"Title": "Aigle (arrondissement d'état civil)"}}
    district = {"slug": "sa-1", "parent": None, "f": {"Title": "District Est-vaudois"}}
    piece = {"slug": "sa-3", "parent": "sa-2", "f": {"Title": "Aigle (arrondissement d'état civil)"}}

    # When
    names = series_arrondissement_names(piece, {"sa-1": district, "sa-2": series})

    # Then
    assert names == ["Aigle"]


def test_sb_324_series_also_offers_the_first_locality_it_comprises():
    # Given
    series = {"slug": "sa-2", "parent": None, "f": {
        "Title": "Saint-Saphorin-sur-Morges (arrondissement d'état civil)",
        "Notes": "Arrondissement créé le 1er janvier 1876. Comprend: - Colombier - Aclens - Clarmont",
    }}
    piece = {"slug": "sa-3", "parent": "sa-2", "f": {"Title": "Saint-Saphorin-sur-Morges (arrondissement d'état civil)"}}

    # When
    names = series_arrondissement_names(piece, {"sa-2": series})

    # Then
    assert names == ["Saint-Saphorin-sur-Morges", "Colombier"]


def test_listed_content_drops_the_arrondissement_before_a_colon():
    # When
    segments = justificative_segments(box("Lausanne (arrondissement d'état civil)") | {
        "scope": "Lausanne (arrondissement de l'état civil): Naissances 1955 - No 2061 - 2308 - Naissances 1956 No 1-380.",
    })

    # Then
    assert [(segment["label"], segment["start"]) for segment in segments] == [
        ("Pièces justificatives : Naissances", "1955-01-01"),
        ("Pièces justificatives : Naissances", "1956-01-01"),
    ]


def test_listed_content_ignores_act_numbers_written_without_parentheses():
    # When
    segments = justificative_segments(box("Lausanne (arrondissement d'état civil)") | {"scope": "Lausanne (arrondissement de l'état civil): Mariages 1965- No 1001-1120."})

    # Then
    assert [(segment["label"], segment["start"], segment["end"]) for segment in segments] == [
        ("Pièces justificatives : Mariages", "1965-01-01", "1965-12-31"),
    ]


def test_miscellaneous_pieces_take_their_kinds_from_the_text_after_the_colon():
    # When
    segments = justificative_segments(box("- Mariages 1936-1950\n- Pièces diverses relatives à l'état civil 1942-1943, 1946, 1948, 1950: principalement constatations de décès, divorces, rectifications de nom"))

    # Then
    assert [(segment["label"], segment["kinds"], segment["start"], segment["end"], segment["dates"]) for segment in segments] == [
        ("Pièces justificatives : Mariages", ["pj", "mariage"], "1936-01-01", "1950-12-31", "1936-1950"),
        ("Pièces justificatives : Pièces diverses relatives à l'état civil (principalement constatations de décès, divorces, rectifications de nom)",
         ["pj", "deces"], "1942-01-01", "1950-12-31", "1942-1943, 1946, 1948, 1950"),
    ]


def test_miscellaneous_pieces_without_act_kinds_are_divers():
    # When
    segments = justificative_segments(box("- Pièces diverses relatives à l'état civil 1910-1919: principalement divorces, rectifications de nom"))

    # Then
    assert [(segment["kinds"], segment["start"], segment["end"]) for segment in segments] == [(["pj", "divers"], "1910-01-01", "1919-12-31")]


def test_miscellaneous_pieces_dated_after_the_colon():
    # When
    segments = justificative_segments(box("- Pièces diverses relatives à l'état civil: rectifications de nom 1879"))

    # Then
    assert [(segment["label"], segment["start"], segment["end"], segment["dates"]) for segment in segments] == [
        ("Pièces justificatives : Pièces diverses relatives à l'état civil (rectifications de nom)", "1879-01-01", "1879-12-31", "1879"),
    ]
