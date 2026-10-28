import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from scopearchiv import creation_dates, justificative_segments  # noqa: E402


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
