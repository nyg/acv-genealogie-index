import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from report import misnamed_parishes, parishless_localities, split_genuine  # noqa: E402


def test_a_line_continuing_another_entry_is_not_a_parishless_locality():
    # Given
    table = [
        {"locality": "Petit Vaux, soit", "description": "Morges [86]", "parishes": ["86"]},
        {"locality": "Vaux-Dessous (Vaux-sur-Morges)", "description": "", "parishes": []},
        {"locality": "Novalles", "description": "_____", "parishes": []},
    ]
    corrections = {"Vaux-Dessous (Vaux-sur-Morges)": {"continues": "Petit Vaux, soit"}}

    # When
    orphans = parishless_localities(table, corrections)

    # Then
    assert [entry["locality"] for entry in orphans] == ["Novalles"]


def test_a_correction_giving_parishes_resolves_a_parishless_locality():
    # Given
    table = [{"locality": "Prilly", "description": "THIlyTîlôr", "parishes": []}]
    corrections = {"Prilly": {"description": "Prilly [110]", "parishes": ["110"]}}

    # When
    orphans = parishless_localities(table, corrections)

    # Then
    assert orphans == []


def test_parish_names_left_after_the_repair_and_the_corrections_are_listed():
    # Given
    table = [
        {"locality": "Vevey", "description": "VëvèyT[132]", "parishes": ["132"]},
        {"locality": "Servion", "description": "Mézières [12]", "parishes": ["12"]},
        {"locality": "Cremin", "description": "CllHilIés [43]", "parishes": ["43"]},
    ]
    corrections = {"Servion": {"description": "Mézières [79]", "parishes": ["79"]}}
    names = {"12": ["Begnins"], "43": ["Curtilles"], "79": ["Mézières"], "132": ["Vevey"]}

    # When
    rows = misnamed_parishes(table, corrections, names, {})

    # Then
    assert rows == [("Cremin", "CllHilIés", "43", "Curtilles")]


def test_a_segment_verified_as_genuine_is_not_listed_and_a_verified_segment_back_in_range_is_stale():
    # Given
    rows = [
        ("Eb 87/2", "un baptême", "1716-09-20", "1716-09-20", "1659-10-27", "1713-01-28"),
        ("Eb 105/7", "Décès", "1729-03-12", "1821-06-30", "1739-03-12", "1864-12-31"),
    ]
    genuine = [{"cote": "Eb 87/2", "segment": "un baptême", "reason": "p. 322"}, {"cote": "Eb 95/4", "segment": "Baptêmes forains", "reason": "pp. 230-239"}]

    # When
    unexplained, stale = split_genuine(rows, genuine)

    # Then
    assert [row[0] for row in unexplained] == ["Eb 105/7"]
    assert [entry["cote"] for entry in stale] == ["Eb 95/4"]
