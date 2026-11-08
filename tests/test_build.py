import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from build import data_json, keep_date_if_unchanged, parish_segments  # noqa: E402


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
