"""Plans the next scraping batch: lists what is not yet in data/raw/ and prints the browser calls to run.

    python3 scraper/plan.py davel-vd [--fonds eb|ed|sb-267] [--match REGEX] [--batch N]
    python3 scraper/plan.py davel --fonds "SB 268" [--match REGEX] [--batch N]
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

RAW_ROOT = Path(__file__).resolve().parent.parent / "data" / "raw"
SECONDS_PER_REQUEST = 1.6
SB267_RECORDS_PER_ARRONDISSEMENT = 60
DAVEL_RECORDS_PER_ROOT = 15
DAVEL_PARENTS = {
    "SB 268": ["623416"],
    "SB 269": ["623415"],
    "Ec": ["10010"],
    "SB 23": ["557958", "589164"],
    "SB 115": ["613621", "615711", "626074"],
}


def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


def estimated_records(label):
    pieces = re.match(r"\S+ [\d a-z]+?/(\d+)(?:-(\d+))? - ", label)
    if label.startswith("SB 267") or not pieces:
        return SB267_RECORDS_PER_ARRONDISSEMENT
    first, last = int(pieces.group(1)), int(pieces.group(2) or pieces.group(1))
    return last - first + 2


def duration(records):
    minutes = round(records * SECONDS_PER_REQUEST / 60)
    return f"~{minutes} min" if minutes < 90 else f"~{minutes / 60:.1f} h"


def quoted(ids):
    return ", ".join(f"'{identifier}'" for identifier in ids)


def plan_davel_vd(args):
    index = json.loads((RAW_ROOT / "davel-vd" / "_series_index.json").read_text(encoding="utf-8"))
    done = {path.stem for path in (RAW_ROOT / "davel-vd").glob("[!_]*.json")}
    fonds_list = [args.fonds] if args.fonds else list(index)
    for fonds in fonds_list:
        series = [(slug, label) for slug, label in index[fonds] if " - (vide)" not in label]
        print(f"{fonds}: {sum(slug in done for slug, _ in series)}/{len(series)} séries indexées")
    remaining = [(slug, label) for fonds in fonds_list for slug, label in index[fonds]
                 if slug not in done and " - (vide)" not in label and re.search(args.match, normalize(label))]
    batch = remaining[:args.batch]
    if not batch:
        print("Rien à faire pour ce filtre.")
        return
    records = sum(estimated_records(label) for _, label in batch)
    print(f"\nLot de {len(batch)} séries sur {len(remaining)} restantes, {duration(records)} :")
    for _, label in batch:
        print(f"  {label}")
    slugs = [slug for slug, _ in batch]
    print(f"\nDans l'onglet https://davel-vd.ch/, après avoir collé scraper/davel_vd.js :\n\nacv.enqueue({quoted(slugs)}); acv.status()")
    print(f"\nQuand acv.status().running est false :\n\nacv.exportSeries({quoted(slugs)})")


def plan_davel(args):
    if args.fonds not in DAVEL_PARENTS:
        sys.exit(f"--fonds doit être l'un de : {', '.join(DAVEL_PARENTS)}")
    index_path = RAW_ROOT / "davel" / "_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    parents = DAVEL_PARENTS[args.fonds]
    missing = [parent for parent in parents if parent not in index]
    if missing:
        print(f"L'index de {args.fonds} manque. Dans un onglet davel.vd.ch, après avoir collé scraper/davel_scopearchiv.js :")
        print(f"\nsa.enqueueIndex({quoted(missing)}); sa.status()")
        print(f"\nQuand sa.status().running est false :\n\nsa.exportIndex({quoted(missing)})")
        print("\npuis : python3 scraper/save_export.py <fichier> davel-index")
        return
    done = {path.stem.removeprefix("sa-") for path in (RAW_ROOT / "davel").glob("sa-*.json")}
    roots = [(identifier, title) for parent in parents for identifier, title in index[parent]["children"] if "FANTOME" not in title]
    print(f"{args.fonds}: {sum(identifier in done for identifier, _ in roots)}/{len(roots)} entrées indexées")
    remaining = [(identifier, title) for identifier, title in roots if identifier not in done and re.search(args.match, normalize(title))]
    batch = remaining[:args.batch]
    if not batch:
        print("Rien à faire pour ce filtre.")
        return
    print(f"\nLot de {len(batch)} entrées sur {len(remaining)} restantes, {duration(len(batch) * DAVEL_RECORDS_PER_ROOT)} :")
    for _, title in batch:
        print(f"  {title}")
    ids = [identifier for identifier, _ in batch]
    print(f"\nDans un onglet davel.vd.ch, après avoir collé scraper/davel_scopearchiv.js :\n\n{'; '.join(f'sa.enqueue({identifier})' for identifier in ids)}; sa.status()")
    print(f"\nQuand sa.status().running est false :\n\nsa.exportSubtrees({quoted(ids)})")
    print("\npuis : python3 scraper/save_export.py <fichier> davel")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", choices=["davel-vd", "davel"])
    parser.add_argument("--fonds", help="davel-vd : eb, ed ou sb-267 ; davel : " + ", ".join(DAVEL_PARENTS))
    parser.add_argument("--match", default="", help="expression régulière sur le titre, sans accents ni majuscules (ex. ollon|huemoz)")
    parser.add_argument("--batch", type=int, default=20)
    args = parser.parse_args()
    args.match = normalize(args.match)
    plan_davel_vd(args) if args.source == "davel-vd" else plan_davel(args)


if __name__ == "__main__":
    main()
