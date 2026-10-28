import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from inventory_corrections import apply_corrections, unused_corrections  # noqa: E402

TITLE_TYPO = {"cote": "SB 23/1253", "field": "Title", "published": "Décès B 1880", "corrected": "Décès B 1907"}


def test_correction_replaces_the_published_text_of_its_cote():
    # Given
    records = [
        {"f": {"Ref. code": "SB 23/1253", "Title": "- Mariages A et B 1907\n- Décès B 1880"}},
        {"f": {"Ref. code": "SB 23/1254", "Title": "- Décès B 1880"}},
    ]

    # When
    applied = apply_corrections(records, [TITLE_TYPO])

    # Then
    assert applied == [TITLE_TYPO]
    assert records[0]["f"]["Title"] == "- Mariages A et B 1907\n- Décès B 1907"
    assert records[1]["f"]["Title"] == "- Décès B 1880"


def test_correction_finds_davel_vd_records_by_their_cote():
    # Given
    records = [{"f": {"Cote": "SB 267/59", "Unités de description associées": "SB 23/52-55\nSB 23/1229-1332"}}]
    correction = {"cote": "SB 267/59", "field": "Unités de description associées", "published": "SB 23/1229-1332", "corrected": "SB 23/1229-1232"}

    # When
    apply_corrections(records, [correction])

    # Then
    assert records[0]["f"]["Unités de description associées"] == "SB 23/52-55\nSB 23/1229-1232"


def test_correction_whose_text_is_gone_is_unused(tmp_path):
    # Given
    (tmp_path / "davel").mkdir()
    (tmp_path / "davel" / "sa-1.json").write_text(json.dumps([{"f": {"Ref. code": "SB 23/1253", "Title": "- Décès B 1907"}}]), encoding="utf-8")

    # When
    unused = unused_corrections(tmp_path, [TITLE_TYPO])

    # Then
    assert unused == [TITLE_TYPO]
