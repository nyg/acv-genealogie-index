import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

from pdf_pages import load_pdf_pages, parse_pdf_pages, parse_range  # noqa: E402


def test_range_keeps_descending_pagination():
    # When
    first, last = parse_range("468-400")

    # Then
    assert (first, last) == (468, 400)


def test_single_page_is_a_range():
    # When
    first, last = parse_range("12")

    # Then
    assert (first, last) == (12, 12)


def test_parts_get_kind_and_events():
    # Given
    entries = {"Eb 92/2": {"pdfPages": 671, "parts": [
        {"pdf": "355-452", "content": "Décès 1708-1757", "pages": "281-378"},
        {"pdf": "454-513", "content": "Répertoire des décès 1708-1757"},
    ]}}

    # When
    parts = parse_pdf_pages(entries)["Eb 92/2"]["parts"]

    # Then
    assert [(part["kind"], part["kinds"], part["pages"]) for part in parts] == [
        ("registre", ["deces"], [281, 378]),
        ("repertoire", ["deces"], None),
    ]


def test_register_part_must_have_one_pdf_page_per_register_page():
    # Given
    entries = {"Eb 92/1": {"pdfPages": 502, "parts": [{"pdf": "12-324", "content": "Baptêmes", "pages": "1-318"}]}}

    # When
    with pytest.raises(ValueError) as error:
        parse_pdf_pages(entries)

    # Then
    assert "318 pages du registre pour 313 pages du PDF" in str(error.value)


def test_parts_must_not_overlap():
    # Given
    entries = {"Eb 92/7": {"pdfPages": 98, "parts": [
        {"pdf": "5-46", "content": "Décès"},
        {"pdf": "46-58", "content": "Répertoire des décès"},
    ]}}

    # When
    with pytest.raises(ValueError) as error:
        parse_pdf_pages(entries)

    # Then
    assert "chevauchant" in str(error.value)


def test_part_may_sit_inside_the_previous_one_when_pages_carry_two_numbers():
    # Given
    entries = {"Eb 15/1": {"pdfPages": 470, "parts": [
        {"pdf": "399-418", "content": "Baptêmes 1616-1618", "pages": "338-357"},
        {"pdf": "400-417", "content": "Mariages 1616-1618", "pages": "72-89"},
        {"pdf": "420-470", "content": "Répertoire des mariages"},
    ]}}

    # When
    parts = parse_pdf_pages(entries)["Eb 15/1"]["parts"]

    # Then
    assert [part["pdf"] for part in parts] == [[399, 418], [400, 417], [420, 470]]


def test_manual_page_map_names_registers_with_a_pdf():
    # Given
    registers = load_pdf_pages(ROOT / "data" / "manual" / "pdf-pages.json")
    with_pdf = {record["f"]["Cote"] for path in (ROOT / "data" / "raw" / "davel-vd").glob("[!_]*.json")
                for record in json.loads(path.read_text(encoding="utf-8")) if record.get("pdf")}

    # When
    unknown = set(registers) - with_pdf

    # Then
    assert not unknown


def test_manual_page_counts_match_the_pdf_profiles():
    # Given
    registers = load_pdf_pages(ROOT / "data" / "manual" / "pdf-pages.json")
    profiles = json.loads((ROOT / "data" / "raw" / "davel-vd" / "_pdf_profiles.json").read_text(encoding="utf-8"))

    # When
    mismatches = {cote: (register["pdfPages"], profiles[cote]["pages"]) for cote, register in registers.items()
                  if cote in profiles and register["pdfPages"] != profiles[cote]["pages"]}

    # Then
    assert not mismatches


def test_anchors_may_follow_a_descending_pagination():
    # Given
    entries = {"Eb 92/6": {"pdfPages": 405, "parts": [
        {"pdf": "182-343", "content": "Décès", "pages": "277-116", "anchors": [[200, 259]]},
    ]}}

    # When
    parts = parse_pdf_pages(entries)["Eb 92/6"]["parts"]

    # Then
    assert parts[0]["anchors"] == [[200, 259]]


def test_anchor_cannot_put_more_register_pages_than_pdf_pages():
    # Given
    entries = {"Ed 92/1": {"pdfPages": 507, "parts": [
        {"pdf": "6-454", "content": "Naissances", "pages": "1-384", "anchors": [[192, 150]]},
    ]}}

    # When
    with pytest.raises(ValueError) as error:
        parse_pdf_pages(entries)

    # Then
    assert "repère p. 192 → PDF 150" in str(error.value)


def test_spread_part_holds_two_register_pages_per_pdf_page():
    # Given
    entries = {"Ed 15/2": {"pdfPages": 236, "parts": [
        {"pdf": "5-202", "content": "Naissances", "pages": "1-368", "spread": True, "anchors": [[177, 100]]},
    ]}}

    # When
    parts = parse_pdf_pages(entries)["Ed 15/2"]["parts"]

    # Then
    assert (parts[0]["spread"], parts[0]["roman"]) == (True, False)


def test_spread_part_may_end_on_the_right_hand_page_of_its_last_image():
    # Given
    entries = {"Ed 3/2": {"pdfPages": 246, "parts": [
        {"pdf": "5-213", "content": "Naissances", "pages": "1-367", "spread": True, "anchors": [[364, 212]]},
    ]}}

    # When
    parts = parse_pdf_pages(entries)["Ed 3/2"]["parts"]

    # Then
    assert parts[0]["pages"] == [1, 367]


def test_spread_part_cannot_hold_more_than_two_register_pages_per_pdf_page():
    # Given
    entries = {"Ed 15/2": {"pdfPages": 236, "parts": [
        {"pdf": "5-202", "content": "Naissances", "pages": "1-368", "spread": True, "anchors": [[177, 60]]},
    ]}}

    # When
    with pytest.raises(ValueError) as error:
        parse_pdf_pages(entries)

    # Then
    assert "repère p. 177 → PDF 60" in str(error.value)
