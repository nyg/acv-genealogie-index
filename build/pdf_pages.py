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
    previous_end = 0
    for part in parts:
        start, end = part["pdf"]
        if not previous_end < start <= end <= pdf_pages:
            raise ValueError(f"{cote} : PDF p. {start}-{end} hors du PDF ({pdf_pages} pages) ou chevauchant la partie précédente")
        previous_end = end
        if part["anchors"]:
            _check_anchors(cote, part)
        elif part["pages"]:
            first, last = part["pages"]
            if abs(last - first) != end - start:
                raise ValueError(f"{cote} : {part['content']} compte {abs(last - first) + 1} pages du registre pour {end - start + 1} pages du PDF")


def _check_anchors(cote, part):
    (first, last), (start, end) = part["pages"], part["pdf"]
    points = [(first, start), *part["anchors"], (last, end)]
    direction = 1 if last >= first else -1
    for (page, pdf), (next_page, next_pdf) in zip(points, points[1:]):
        if (next_page - page) * direction <= 0 or next_pdf - pdf < abs(next_page - page):
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
            "note": part.get("note", ""),
        } for part in entry["parts"]]
        _check_parts(cote, entry["pdfPages"], parts)
        registers[cote] = {"pdfPages": entry["pdfPages"], "parts": parts}
    return registers


def load_pdf_pages(path):
    return parse_pdf_pages(json.loads(path.read_text(encoding="utf-8")))
