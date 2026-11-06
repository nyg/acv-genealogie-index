import json
import re

from scope_parser import classify, normalize


def parse_range(text):
    match = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*", text)
    if not match:
        raise ValueError(f"plage de pages illisible : {text!r}")
    first = int(match[1])
    return first, int(match[2] or first)


def part_kind(part):
    if part.get("pages"):
        return "registre"
    return "repertoire" if normalize(part["content"]).startswith("repertoire") else "autre"


def _check_parts(cote, pdf_pages, parts):
    previous_start, previous_end = 0, 0
    for part in parts:
        start, end = part["pdf"]
        nested = previous_start <= start and end <= previous_end
        if not (start <= end <= pdf_pages and (previous_end < start or nested)):
            raise ValueError(f"{cote} : PDF p. {start}-{end} hors du PDF ({pdf_pages} pages) ou chevauchant la partie précédente")
        if not nested:
            previous_start, previous_end = start, end
        if part["anchors"] or part["spread"]:
            _check_anchors(cote, part)
        elif part["pages"]:
            first, last = part["pages"]
            several_numbers_on_one_page = start == end
            if not several_numbers_on_one_page and abs(last - first) != end - start:
                raise ValueError(f"{cote} : {part['content']} compte {abs(last - first) + 1} pages du registre pour {end - start + 1} pages du PDF")


def _check_anchors(cote, part):
    (first, last), (start, end) = part["pages"], part["pdf"]
    ends = [[first, start], [last, end]]
    for anchor in part["anchors"]:
        if anchor in ends:
            raise ValueError(f"{cote} : le repère p. {anchor[0]} → PDF {anchor[1]} est le début ou la fin de la partie, déjà pris comme repère : le retirer")
    points = [(first, start), *part["anchors"], (last, end)]
    direction = 1 if last >= first else -1
    for (page, pdf), (next_page, next_pdf) in zip(points, points[1:]):
        most_pages = 2 * (next_pdf - pdf) + 1 if part["spread"] else next_pdf - pdf
        if (next_page - page) * direction <= 0 or most_pages < abs(next_page - page):
            raise ValueError(f"{cote} : repère p. {next_page} → PDF {next_pdf} incompatible avec p. {page} → PDF {pdf}")


def parse_pdf_pages(entries):
    registers = {}
    for cote, entry in entries.items():
        parts = [{
            "pdf": list(parse_range(part["pdf"])),
            "pages": list(parse_range(part["pages"])) if part.get("pages") else None,
            "content": part["content"],
            "kind": part_kind(part),
            "kinds": classify(part["content"]),
            "anchors": [list(anchor) for anchor in part.get("anchors", [])],
            "spread": part.get("spread", False),
            "roman": part.get("roman", False),
            "approx": False,
            "note": part.get("note", ""),
        } for part in entry["parts"]]
        _check_parts(cote, entry["pdfPages"], parts)
        registers[cote] = {"pdfPages": entry["pdfPages"], "parts": parts}
    return registers


def load_pdf_pages(path):
    return parse_pdf_pages(json.loads(path.read_text(encoding="utf-8")))


# Barcode sheet, title page and its verso come before register page 1 (sampled on 18 PDFs).
SB267_OFFSET = 3
# Acts after these years are left out of the PDFs, which then stop mid-volume.
SB267_LAST_PUBLISHED_YEAR = {"naissance": 1899, "mariage": 1929, "deces": 1959}
SB267_EVENTS = {"naissance": "naissances", "mariage": "mariages", "deces": "décès"}


def sb267_default_parts(unit):
    kinds = classify(unit["title"])
    pages = re.search(r"(\d+) pages utiles", unit["extent"])
    if len(kinds) != 1 or kinds[0] not in SB267_EVENTS or not pages:
        return None
    kind = kinds[0]
    if int(unit["end"][:4]) > SB267_LAST_PUBLISHED_YEAR[kind]:
        return None
    last_page = int(pages[1])
    events = SB267_EVENTS[kind]
    years = f"{unit['start'][:4]}-{unit['end'][:4]}"
    repertoire_start = last_page + SB267_OFFSET + 1
    return [
        _default_part([1 + SB267_OFFSET, last_page + SB267_OFFSET], [1, last_page], f"{events.capitalize()} {years}", kind,
                      "Position déduite de la règle PDF = page + 3, non vérifiée sur ce registre : vers la fin, la page cherchée peut être 1 à 4 pages plus loin (page numérotée deux fois, page bis, formulaires blancs)."),
        _default_part([repertoire_start, repertoire_start], None, f"Répertoire des {events} {years}", kind,
                      "Début approché : souvent 1 ou 2 pages plus loin, la dernière page du registre étant souvent photographiée deux fois."),
    ]


def _default_part(pdf, pages, content, kind, note):
    return {"pdf": pdf, "pages": pages, "content": content, "kind": "registre" if pages else "repertoire", "kinds": [kind],
            "anchors": [], "spread": False, "roman": False, "approx": True, "note": note}
