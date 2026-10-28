"""Coverage and quality report on data/acv.sqlite (run build/build.py first).

    python3 build/report.py [--limit N]
"""

import argparse
import json
import sqlite3
from pathlib import Path

from inventory_corrections import CORRECTIONS as INVENTORY_CORRECTIONS
from inventory_corrections import unused_corrections

ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "data" / "acv.sqlite"
DAVEL_INDEX = ROOT / "data" / "raw" / "davel" / "_index.json"
PARISH_TABLE = ROOT / "data" / "raw" / "vd-ch" / "communes-paroisses.json"
CORRECTIONS = ROOT / "data" / "manual" / "communes-paroisses-corrections.json"
DAVEL_PARENTS = {"SB 268": ["623416"], "SB 269": ["623415"], "Ec": ["10010"], "SB 23": ["557958", "589164"], "SB 115": ["613621", "615711", "626074"]}


def section(title, rows, limit, describe):
    print(f"\n{title} : {len(rows)}")
    for row in rows[:limit]:
        print(f"  {describe(row)}")
    if len(rows) > limit:
        print(f"  … et {len(rows) - limit} autres")


def coverage(connection):
    print("Couverture")
    for fonds, done, total in connection.execute(
        "SELECT fonds, SUM(scraped), COUNT(*) FROM series WHERE slug NOT LIKE 'sa-%' GROUP BY fonds ORDER BY fonds"
    ):
        print(f"  {fonds:7} {done:4}/{total} séries (davel-vd.ch)")
    index = json.loads(DAVEL_INDEX.read_text(encoding="utf-8")) if DAVEL_INDEX.exists() else {}
    scraped = {path.stem.removeprefix("sa-") for path in DAVEL_INDEX.parent.glob("sa-*.json")}
    for fonds, parents in DAVEL_PARENTS.items():
        units = connection.execute("SELECT COUNT(*) FROM units WHERE fonds = ?", (fonds,)).fetchone()[0]
        if all(parent in index for parent in parents):
            roots = [child for parent in parents for child, title in index[parent]["children"] if "FANTOME" not in title]
            print(f"  {fonds:7} {sum(root in scraped for root in roots):4}/{len(roots)} entrées (davel.vd.ch), {units} unités")
        else:
            print(f"  {fonds:7} index absent (scraper/plan.py davel --fonds \"{fonds}\"), {units} unités")


def quality(connection, limit):
    unparsed = connection.execute(
        "SELECT u.cote, u.scope_content FROM segments s JOIN units u ON u.slug = s.unit_slug WHERE s.kinds = 'inconnu' ORDER BY u.cote"
    ).fetchall()
    section("Registres au contenu non analysé (champ « Portée et contenu » à vérifier)", unparsed, limit,
            lambda row: f"{row[0]} : {(row[1] or '(vide)')[:110]!r}")

    undated = connection.execute(
        "SELECT u.cote, s.label, s.dates FROM segments s JOIN units u ON u.slug = s.unit_slug WHERE s.date_start IS NULL OR s.date_end IS NULL"
    ).fetchall()
    section("Segments sans dates", undated, limit, lambda row: f"{row[0]} : {row[1]} ({row[2]!r})")

    outside = connection.execute("""
        SELECT u.cote, s.label, s.date_start, s.date_end, u.date_start, u.date_end
        FROM segments s JOIN units u ON u.slug = s.unit_slug
        WHERE u.date_start IS NOT NULL AND s.date_start IS NOT NULL AND u.scope_content NOT LIKE 'Registre ouvert entre%'
          AND (CAST(substr(s.date_start, 1, 4) AS INTEGER) < CAST(substr(u.date_start, 1, 4) AS INTEGER) - 1
            OR CAST(substr(s.date_end, 1, 4) AS INTEGER) > CAST(substr(u.date_end, 1, 4) AS INTEGER) + 1)
        ORDER BY u.cote
    """).fetchall()
    section("Segments hors des dates du registre (souvent une coquille de l'inventaire)", outside, limit,
            lambda row: f"{row[0]} : {row[1]} {row[2]} → {row[3]}, registre {row[4]} → {row[5]}")

    section(f"Corrections sans effet, l'inventaire a peut-être été corrigé (retirer de {INVENTORY_CORRECTIONS.relative_to(ROOT)} et de data/manual/erreurs-acv.md)",
            unused_corrections(), limit, lambda correction: f"{correction['cote']} : {correction['field']} {correction['published']!r}")

    corrections = json.loads(CORRECTIONS.read_text(encoding="utf-8"))
    orphans = [entry for entry in json.loads(PARISH_TABLE.read_text(encoding="utf-8"))
               if not entry["parishes"] and not corrections.get(entry["locality"], {}).get("parishes")]
    section(f"Localités de la table des paroisses sans paroisse (corriger dans {CORRECTIONS.relative_to(ROOT)})", orphans, limit,
            lambda entry: f"{entry['locality']!r} : {entry['description'][:80]!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    with sqlite3.connect(DATABASE) as connection:
        coverage(connection)
        quality(connection, args.limit)


if __name__ == "__main__":
    main()
