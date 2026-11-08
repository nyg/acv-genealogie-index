import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from report import parishless_localities  # noqa: E402


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
