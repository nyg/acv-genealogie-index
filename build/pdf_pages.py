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
            if abs(last - first) != end - start:
                raise ValueError(f"{cote} : {part['content']} compte {abs(last - first) + 1} pages du registre pour {end - start + 1} pages du PDF")


def _check_anchors(cote, part):
    (first, last), (start, end) = part["pages"], part["pdf"]
    points = [(first, start), *part["anchors"], (last, end)]
    direction = 1 if last >= first else -1
    pages_per_pdf_page = 2 if part["spread"] else 1
    for (page, pdf), (next_page, next_pdf) in zip(points, points[1:]):
        if (next_page - page) * direction <= 0 or (next_pdf - pdf) * pages_per_pdf_page < abs(next_page - page):
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
            "note": part.get("note", ""),
        } for part in entry["parts"]]
        _check_parts(cote, entry["pdfPages"], parts)
        registers[cote] = {"pdfPages": entry["pdfPages"], "parts": parts}
    return registers


def load_pdf_pages(path):
    return parse_pdf_pages(json.loads(path.read_text(encoding="utf-8")))
