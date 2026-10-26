"""Writes site/preview.html, docs/index.html reduced to a few places, small enough for the in-app browser preview.

    python3 build/preview.py [place-id ...]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLACES = ["paroisse-92", "paroisse-68-bis", "arrondissement-73", "arrondissement-49"]
DATA_START = "const DATA = "


def main(place_ids):
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    start = html.index(DATA_START) + len(DATA_START)
    end = html.index(";\n", start)
    data = json.loads(html[start:end].replace("<\\/", "</"))
    keep = set(place_ids)
    data["places"] = [place for place in data["places"] if place["id"] in keep]
    data["units"] = [unit for unit in data["units"] if unit["place"] in keep]
    slugs = {unit["slug"] for unit in data["units"]}
    data["segments"] = [segment for segment in data["segments"] if segment["unit"] in slugs]
    reduced = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    target = ROOT / "site" / "preview.html"
    target.write_text(html[:start] + reduced + html[end:], encoding="utf-8")
    print(f"{target.relative_to(ROOT)}: {len(data['places'])} lieux, {len(data['units'])} registres, {target.stat().st_size // 1024} Ko")


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT_PLACES)
