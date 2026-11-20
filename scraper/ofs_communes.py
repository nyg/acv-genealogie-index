"""Writes data/raw/ofs/communes-vd.json, the Vaud communes and their district, from the Swiss official commune register (OFS).

    python3 scraper/ofs_communes.py

The snapshot date is before the 2008 district reform: the 19 former districts are those of the registers' era (1803-2007).
"""

import csv
import io
import json
import urllib.request
from pathlib import Path

SNAPSHOT_DATE = "01-01-2000"
SNAPSHOT_URL = f"https://www.agvchapp.bfs.admin.ch/api/communes/snapshot?date={SNAPSHOT_DATE}"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "ofs" / "communes-vd.json"


def vaud_communes(rows):
    canton = next(row for row in rows if row["Level"] == "1" and row["ShortName"] == "VD")
    districts = {row["HistoricalCode"]: row["Name"] for row in rows if row["Level"] == "2" and row["Parent"] == canton["HistoricalCode"]}
    return dict(sorted((row["Name"], districts[row["Parent"]]) for row in rows if row["Level"] == "3" and row["Parent"] in districts))


def main():
    with urllib.request.urlopen(SNAPSHOT_URL, timeout=60) as response:
        rows = list(csv.DictReader(io.StringIO(response.read().decode("utf-8-sig"))))
    communes = vaud_communes(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"source": SNAPSHOT_URL, "communes": communes}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUTPUT.name} : {len(communes)} communes, {len(set(communes.values()))} districts")


if __name__ == "__main__":
    main()
