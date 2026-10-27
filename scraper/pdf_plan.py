"""Prepares PDF page maps: for registers missing from data/manual/pdf-pages.json, prints what the inventory and the
saved PDF profiles say, and the browser call that profiles the rest.

    python3 scraper/pdf_plan.py --match "^E[bd] 92/"
    uv run --with numbers-parser scraper/pdf_plan.py --match "^E[bd] 92/" --hints index_paroisses.numbers
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

from scope_parser import parse_scope_content  # noqa: E402

RAW_DIR = ROOT / "data" / "raw" / "davel-vd"
PDF_PROFILES = RAW_DIR / "_pdf_profiles.json"
PDF_PAGES = ROOT / "data" / "manual" / "pdf-pages.json"


def registers_with_pdf():
    for path in sorted(RAW_DIR.glob("[!_]*.json")):
        for record in json.loads(path.read_text(encoding="utf-8")):
            if record.get("pdf"):
                yield record


def table_hints(numbers_path):
    from numbers_parser import Document

    hints, cote = {}, None
    for sheet in Document(numbers_path).sheets:
        for table in sheet.tables:
            if "contenu pdf" not in table.name.lower():
                continue
            for row in table.rows(values_only=True):
                first, last, content = (list(row) + [None, None, None])[:3]
                if isinstance(first, str) and re.match(r"E[bd] \d", first):
                    cote = first.strip()
                elif cote and content:
                    pages = "-".join(str(int(v)) if isinstance(v, float) else str(v) for v in (first, last) if v is not None)
                    hints.setdefault(cote, []).append(f"PDF {pages or '?'} : {content}")
    return hints


def describe(record, profile, hints):
    fields = record["f"]
    print(f"\n## {fields['Cote']} ({fields.get('Taille du fichier', '?')}) {fields.get('Date(s)', '').replace(' (Création)', '')}")
    print(f"   PDF : {record['pdf']}")
    for segment in parse_scope_content(fields.get("Portée et contenu", "")):
        print(f"   Partie : {segment.label} {segment.dates_text} {segment.pages}{' (tête-bêche)' if segment.head_to_tail else ''}")
    for line in fields.get("Instruments de recherche", "").splitlines():
        print(f"   Répertoire : {re.sub(r'\s*\(microfilm:[^)]*\)', '', line).strip()}")
    for key in ("Note", "Étendue matérielle et support"):
        if fields.get(key):
            print(f"   {key} : {' / '.join(fields[key].splitlines())}")
    if profile:
        formats = " ".join(f"{first}-{last}:{w}x{h}" for first, last, w, h in profile["segments"]) if "segments" in profile else profile["layout"]
        print(f"   Profil : {profile['pages']} pages, bandes {profile.get('strips', '?')}, formats {formats}")
    for hint in hints.get(fields["Cote"], []):
        print(f"   Table « Contenu PDF » : {hint}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--match", default=".", help="regex on the cote, e.g. '^E[bd] 92/'")
    parser.add_argument("--all", action="store_true", help="include registers already in pdf-pages.json")
    parser.add_argument("--hints", help="index_paroisses.numbers, read with numbers-parser")
    args = parser.parse_args()

    done = json.loads(PDF_PAGES.read_text(encoding="utf-8"))
    profiles = json.loads(PDF_PROFILES.read_text(encoding="utf-8")) if PDF_PROFILES.exists() else {}
    hints = table_hints(args.hints) if args.hints else {}
    todo = [record for record in registers_with_pdf()
            if re.search(args.match, record["f"]["Cote"]) and (args.all or record["f"]["Cote"] not in done)]
    print(f"{len(todo)} registres à traiter ({sum(record['f']['Cote'] in profiles for record in todo)} avec profil PDF)")
    for record in todo:
        describe(record, profiles.get(record["f"]["Cote"]), hints)
    missing = {record["f"]["Cote"]: record["pdf"] for record in todo if record["f"]["Cote"] not in profiles}
    if missing:
        print(f"\nProfils manquants ({len(missing)}, environ 3 requêtes chacun) : coller scraper/davel_pdf.js dans un onglet davel-vd.ch, puis")
        print(f"  pdf.enqueue({json.dumps(missing, ensure_ascii=False)})")
        print("puis pdf.exportProfiles() et python3 scraper/save_export.py <fichier> pdf-profiles")


if __name__ == "__main__":
    main()
