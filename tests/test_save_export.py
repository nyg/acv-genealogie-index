import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scraper"))

from save_export import read_export  # noqa: E402


def test_padded_export_is_read_back(tmp_path):
    # Given
    payload = json.dumps({"eb-3-1-8": [{"slug": "eb-3-1-8"}]}) + "\n/*PAD*/" + " x" * 10
    tool_result = tmp_path / "result.txt"
    tool_result.write_text(json.dumps([{"type": "text", "text": json.dumps(payload) + "\n\n(captured at origin https://davel-vd.ch)"}]))

    # When
    export = read_export(tool_result)

    # Then
    assert export == {"eb-3-1-8": [{"slug": "eb-3-1-8"}]}
