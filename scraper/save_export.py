"""Saves a scraper export, as written to disk by the browser tool, into data/raw/.

    python3 scraper/save_export.py <tool-result-file>               # acv.exportSeries → data/raw/davel-vd/<series>.json
    python3 scraper/save_export.py <tool-result-file> davel         # sa.exportSubtrees → data/raw/davel/sa-<id>.json
    python3 scraper/save_export.py <tool-result-file> davel-index   # sa.exportIndex → merged into data/raw/davel/_index.json
"""

import json
import re
import sys
from pathlib import Path

RAW_ROOT = Path(__file__).resolve().parent.parent / "data" / "raw"
DAVEL_INDEX = RAW_ROOT / "davel" / "_index.json"
SAFE_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def read_export(tool_result_path):
    items = json.loads(Path(tool_result_path).read_text(encoding="utf-8"))
    text = re.sub(r"\s*\(captured at origin [^)]*\)\s*$", "", items[0]["text"])
    payload = json.loads(text)
    if isinstance(payload, str):
        payload = json.loads(payload.split("\n/*PAD*/")[0])
    return payload


def save_series(series_records, source):
    raw_dir = RAW_ROOT / source
    raw_dir.mkdir(parents=True, exist_ok=True)
    for slug, records in series_records.items():
        if not SAFE_SLUG.match(slug):
            raise ValueError(f"unexpected slug {slug!r}")
        target = raw_dir / f"{slug}.json"
        target.write_text(json.dumps(records, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{target.relative_to(RAW_ROOT.parent.parent)}: {len(records)} records")


def save_index(index_entries):
    index = json.loads(DAVEL_INDEX.read_text(encoding="utf-8")) if DAVEL_INDEX.exists() else {}
    index.update(index_entries)
    DAVEL_INDEX.parent.mkdir(parents=True, exist_ok=True)
    DAVEL_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for parent_id, entry in index_entries.items():
        print(f"{parent_id} {entry['title']}: {len(entry['children'])} enfants")


if __name__ == "__main__":
    target = sys.argv[2] if len(sys.argv) > 2 else "davel-vd"
    export = read_export(sys.argv[1])
    if target == "davel-index":
        save_index(export)
    else:
        save_series(export, target)
