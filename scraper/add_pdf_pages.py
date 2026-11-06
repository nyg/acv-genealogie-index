"""Merges register entries from scratch JSON files into data/manual/pdf-pages.json, in the file's own layout.

    python3 scraper/add_pdf_pages.py scratch.json [more.json …]
    python3 scraper/add_pdf_pages.py --replace scratch.json

Each scratch file maps cotes to entries ({"pdfPages": …, "parts": […]}). New cotes are appended in the order given,
--replace rewrites existing ones in place. Nothing is written unless every entry passes build/pdf_pages.py's checks and
its pdfPages matches the saved PDF profile.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

from pdf_pages import parse_pdf_pages  # noqa: E402

PDF_PAGES = ROOT / "data" / "manual" / "pdf-pages.json"
PDF_PROFILES = ROOT / "data" / "raw" / "davel-vd" / "_pdf_profiles.json"


def render(entries):
    blocks = []
    for cote, entry in entries.items():
        parts = ",\n".join(f"      {json.dumps(part, ensure_ascii=False)}" for part in entry["parts"])
        blocks.append(f'  {json.dumps(cote, ensure_ascii=False)}: {{\n    "pdfPages": {entry["pdfPages"]},\n    "parts": [\n{parts}\n    ]\n  }}')
    return "{\n" + ",\n".join(blocks) + "\n}\n"


def merge(entries, additions, replace):
    clashes = sorted(set(entries) & set(additions))
    if clashes and not replace:
        raise ValueError(f"déjà dans pdf-pages.json (--replace pour les remplacer) : {', '.join(clashes)}")
    return {**entries, **additions}


def check(additions, profiles):
    parse_pdf_pages(additions)
    for cote, entry in additions.items():
        profile = profiles.get(cote)
        if profile is None:
            raise ValueError(f"{cote} : pas de profil PDF enregistré")
        if entry["pdfPages"] != profile["pages"]:
            raise ValueError(f"{cote} : pdfPages {entry['pdfPages']}, le profil compte {profile['pages']} pages")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scratch", nargs="+", type=Path)
    parser.add_argument("--replace", action="store_true", help="remplace les cotes déjà présentes")
    args = parser.parse_args()

    additions = {}
    for path in args.scratch:
        additions.update(json.loads(path.read_text(encoding="utf-8")))
    entries = json.loads(PDF_PAGES.read_text(encoding="utf-8"))
    try:
        check(additions, json.loads(PDF_PROFILES.read_text(encoding="utf-8")))
        merged = merge(entries, additions, args.replace)
    except ValueError as error:
        sys.exit(str(error))
    PDF_PAGES.write_text(render(merged), encoding="utf-8")
    print(f"{len(additions)} registres ajoutés ou remplacés, {len(merged)} au total")


if __name__ == "__main__":
    main()
