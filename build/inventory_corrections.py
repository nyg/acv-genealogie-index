"""Known errors of the ACV inventories, fixed when reading the raw records (data/manual/corrections-inventaire.json)."""

import json
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORRECTIONS = ROOT / "data" / "manual" / "corrections-inventaire.json"
RAW_FILES = ("davel-vd/[!_]*.json", "davel/sa-*.json")


@cache
def load_corrections(path=CORRECTIONS):
    return json.loads(path.read_text(encoding="utf-8"))


def apply_corrections(records, corrections):
    applied = []
    for record in records:
        fields = record["f"]
        cote = fields.get("Cote") or fields.get("Ref. code", "")
        for correction in corrections:
            field = correction["field"]
            if correction["cote"] == cote and correction["published"] in fields.get(field, ""):
                fields[field] = fields[field].replace(correction["published"], correction["corrected"])
                applied.append(correction)
    return applied


def read_raw(path):
    records = json.loads(path.read_text(encoding="utf-8"))
    apply_corrections(records, load_corrections())
    return records


def unused_corrections(raw_root=ROOT / "data" / "raw", corrections=None):
    corrections = load_corrections() if corrections is None else corrections
    applied = []
    for pattern in RAW_FILES:
        for path in sorted(raw_root.glob(pattern)):
            applied += apply_corrections(json.loads(path.read_text(encoding="utf-8")), corrections)
    return [correction for correction in corrections if correction not in applied]
