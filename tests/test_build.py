import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from build import _add_locality, data_json, keep_date_if_unchanged, parish_segments  # noqa: E402


def payload_generated_at(generated_at, units):
    return {"generatedAt": generated_at, "units": units}


def test_rebuilding_unchanged_data_keeps_its_generation_date(tmp_path):
    # Given
    previous = tmp_path / "data.json"
    previous.write_text(data_json(payload_generated_at("2026-11-08T19:11:31+00:00", [{"cote": "Eb 92/2"}])), encoding="utf-8")

    # When
    payload = keep_date_if_unchanged(payload_generated_at("2026-11-08T19:32:37+00:00", [{"cote": "Eb 92/2"}]), previous)

    # Then
    assert payload["generatedAt"] == "2026-11-08T19:11:31+00:00"


def test_rebuilding_changed_data_takes_the_new_generation_date(tmp_path):
    # Given
    previous = tmp_path / "data.json"
    previous.write_text(data_json(payload_generated_at("2026-11-08T19:11:31+00:00", [{"cote": "Eb 92/2"}])), encoding="utf-8")

    # When
    payload = keep_date_if_unchanged(payload_generated_at("2026-11-08T19:32:37+00:00", [{"cote": "Eb 92/3"}]), previous)

    # Then
    assert payload["generatedAt"] == "2026-11-08T19:32:37+00:00"


def test_first_build_takes_the_new_generation_date(tmp_path):
    # When
    payload = keep_date_if_unchanged(payload_generated_at("2026-11-08T19:32:37+00:00", []), tmp_path / "data.json")

    # Then
    assert payload["generatedAt"] == "2026-11-08T19:32:37+00:00"


def test_list_of_baptised_children_reads_as_a_baptism_index():
    # Given
    unit = {"slug": "eb-70-3", "scope": "Listes des enfants baptisés dans la paroisse entre environ 1641 et 1787.\nPartie 1.", "start": "1641-01-01", "end": "1787-12-31", "dates": "1641 - 1787"}

    # When
    segments = parish_segments(unit)

    # Then
    assert [(segment["kinds"], segment["label"], segment["start"], segment["end"]) for segment in segments] == [
        (["naissance"], "Listes des enfants baptisés dans la paroisse entre environ 1641 et 1787", "1641-01-01", "1787-12-31"),
    ]


def test_a_locality_linked_by_two_sources_takes_the_years_of_both():
    # Given
    place = {"localities": []}

    # When
    _add_locality(place, "Roche", "Noville [90], puis Roche [114 bis] 1776/1821-1837", "table des paroisses", [(None, 1776)])
    _add_locality(place, "Roche", "annexe (1582-1821)", "note de l'inventaire", [(1582, 1821)])

    # Then
    assert place["localities"] == [{"name": "Roche", "qualifier": "Noville [90], puis Roche [114 bis] 1776/1821-1837 · annexe (1582-1821)",
                                     "source": "table des paroisses, note de l'inventaire", "periods": [(None, 1821)]}]


def test_a_locality_linked_once_without_years_is_not_bounded():
    # Given
    place = {"localities": []}

    # When
    _add_locality(place, "Le Muids", "Arzier [5] ; annexe de Genolier [58] 1846-1849", "table des paroisses", [(1846, 1849)])
    _add_locality(place, "Le Muids", "", "note de l'inventaire")

    # Then
    assert place["localities"][0]["periods"] is None
