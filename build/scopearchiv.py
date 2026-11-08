"""Units and segments from the davel.vd.ch (scopeArchiv) records in data/raw/davel."""

import re
from pathlib import Path

from inventory_corrections import read_raw
from scope_parser import classify, parse_date_range

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "davel"
PAGE_BASE = "https://davel.vd.ch/detail.aspx?ID="
JUSTIFICATIVE_FONDS = {"Ec", "SB 23", "SB 115", "SB 324"}
CIVIL_REGISTER_KINDS = [
    ("reconnaissance", "reconnaissance"), ("légitimation", "legitimation"),
    ("naissance", "naissance"), ("mariage", "mariage"), ("décès", "deces"),
]
RELATED_RANGE = re.compile(r"(SB \d+)/(\d+)(?:-(\d+))?")
ARRONDISSEMENT_SERIES = re.compile(r"^(?P<name>.+?)\s*\(arrondissement (?:de l'|d')état civil\)")


def fonds_of(cote):
    match = re.match(r"(SB \d+|Ec|Eb|Ed)\b", cote)
    return match.group(1) if match else ""


def related_ranges(places):
    """Maps SB 23 / SB 115 / SB 324 cote numbers to arrondissements, from SB 267 'Unités de description associées'."""
    ranges = []
    for place in places.values():
        for related in place.get("related", []):
            for fonds, start, end in RELATED_RANGE.findall(related):
                if fonds in JUSTIFICATIVE_FONDS:
                    ranges.append((fonds, int(start), int(end or start), place["id"]))
    return ranges


def place_for(cote, ranges):
    fonds = fonds_of(cote)
    number = re.match(r"(?:SB \d+/|Ec )(\d+(?: (?:bis|ter))?)", cote)
    if fonds in ("SB 268", "SB 269") and number:
        return f"arrondissement-{number.group(1)}"
    if fonds == "Ec" and number:
        return f"paroisse-{number.group(1).replace(' ', '-')}"
    first = RELATED_RANGE.search(cote)
    if not first:
        return None
    value = int(first.group(2))
    containing = [(end - start, place_id) for range_fonds, start, end, place_id in ranges if range_fonds == fonds and start <= value <= end]
    return min(containing)[1] if containing else None


US_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")


def creation_dates(fields):
    return US_DATE.sub(lambda match: f"{int(match[2]):02}.{int(match[1]):02}.{match[3]}", fields.get("Creation date(s)", ""))


def _dates(fields):
    content = fields.get("Content", "")
    if "entre le" in content:
        start, end = parse_date_range(content)
        if start:
            return start, end
    return parse_date_range(re.sub(r"Concernant.*", "", fields.get("Dates", "")))


LISTED_CONTENT = re.compile(r"^[-–]?\s*(?P<label>[^\d()]+?)\s+(?P<dates>\d{4}[^()]*?)\.?$")
DESCRIBED_CONTENT = re.compile(r"^[-–]?\s*(?P<label>[^\d():]+?)\s*(?P<dates>\d{4}[^():]*?)?\s*:\s*[-–]?\s*(?P<content>[^:]+?)\.?$")
YEAR_SPANS = re.compile(r"\s*\b\d{4}(?:\s*-\s*\d{4})?\b")
REMARK = re.compile(r"\s*\(([^()]*)\)")
ACT_NUMBERS = re.compile(r"\bNos?\.?\s*\d+(?:\s*-\s*\d+)?")
ARRONDISSEMENT_PREFIX = re.compile(r"^[^:()]*\(arrondissement[^()]*\)\s*:\s*")
LISTED_LINE_BREAK = re.compile(r"\n|(?<=\.)\s*(?=[-–]\s)|\s+\\?\s*(?=[-–]\s+[A-ZÉ])")


def _segment_row(unit, kinds, label, start, end, dates):
    return {"unit": unit["slug"], "kinds": kinds, "label": label, "start": start, "end": end,
            "dates": dates, "pages": "", "tb": False, "foreign": False, "section": ""}


def _described_line(line):
    described = DESCRIBED_CONTENT.match(line)
    if not described:
        return None
    content = YEAR_SPANS.sub("", described["content"]).strip(" ,")
    dates = (described["dates"] or ", ".join(span.strip() for span in YEAR_SPANS.findall(described["content"]))).strip(" ,")
    years = re.findall(r"\b\d{4}\b", dates)
    if not years or not content:
        return None
    return f"{described['label']} ({content})", classify(content) or ["divers"], dates, years


def _listed_line(line):
    line = ARRONDISSEMENT_PREFIX.sub("", line)
    unremarked = REMARK.sub("", line).strip()
    listed = LISTED_CONTENT.match(unremarked)
    if not listed or not classify(listed["label"]):
        return _described_line(unremarked)
    years = re.findall(r"\b\d{4}\b", ACT_NUMBERS.sub("", listed["dates"]))
    if not years:
        return None
    missing = "".join(f" ({remark})" for remark in REMARK.findall(line) if "manque" in remark)
    return f"{listed['label']}{missing}", classify(listed["label"]), listed["dates"], years


def justificative_segments(unit):
    segments = []
    for line in LISTED_LINE_BREAK.split(f"{unit['title']}\n{unit['scope']}"):
        listed = _listed_line(line.strip())
        if listed:
            label, kinds, dates, years = listed
            segments.append(_segment_row(unit, ["pj", *kinds], f"Pièces justificatives : {label}",
                                         f"{min(years)}-01-01", f"{max(years)}-12-31", dates))
    return segments or [_segment_row(unit, ["pj", *classify(unit["title"])], f"Pièces justificatives : {unit['title']}", unit["start"], unit["end"], unit["dates"])]


def _segments(unit, fonds, series_title):
    if unit.get("missing"):
        return [_segment_row(unit, ["annonce"] if fonds == "SB 268" else ["inconnu"], unit["title"], unit["start"], unit["end"], unit["dates"])]
    if fonds == "SB 268":
        return [_segment_row(unit, ["annonce"], "Promesses de mariage", unit["start"], unit["end"], unit["dates"])]
    if fonds == "SB 269":
        lowered = series_title.lower()
        kinds = next(([kind] for keyword, kind in CIVIL_REGISTER_KINDS if keyword in lowered), ["inconnu"])
        return [_segment_row(unit, kinds, f"{series_title} (bourgeois, événements hors arrondissement)", unit["start"], unit["end"], unit["dates"])]
    return justificative_segments(unit)


FIRST_INCLUDED_LOCALITY = re.compile(r"Comprend\s*:\s*-\s*([^-]+?)\s+-")


def series_arrondissement_names(record, by_slug):
    names = []
    current = record
    while current:
        if match := ARRONDISSEMENT_SERIES.match(current["f"].get("Title", "")):
            included = FIRST_INCLUDED_LOCALITY.search(current["f"].get("Notes", ""))
            names += [name for name in (match["name"], included and included[1]) if name and name not in names]
        current = by_slug.get(current["parent"])
    return names


def load_scopearchiv(places, find_arrondissement=lambda name: None):
    ranges = related_ranges(places)
    units, segments = [], []
    for path in sorted(RAW_DIR.glob("sa-*.json")):
        records = read_raw(path)
        by_slug = {record["slug"]: record for record in records}
        for record in records:
            fields = record["f"]
            if record.get("children"):
                continue
            cote = fields.get("Ref. code", "")
            placeholder = "FANTOME" in cote
            if placeholder and not fields.get("Dates", "").startswith("Lacune"):
                continue
            fonds = fonds_of(cote)
            place_id = place_for(cote, ranges)
            if place_id is None and fonds == "SB 324":
                found = next(filter(None, map(find_arrondissement, series_arrondissement_names(record, by_slug))), None)
                place_id = found and found["id"]
            if place_id not in places:
                print(f"lieu introuvable pour {cote}")
                continue
            start, end = _dates(fields)
            unit = {
                "slug": record["slug"], "place": place_id, "fonds": fonds, "cote": cote, "level": fields.get("Level", ""),
                "title": fields.get("Title", ""), "start": start, "end": end,
                "dates": re.sub(r"Concernant.*", "", fields.get("Dates", "")).strip(),
                "extent": fields.get("Importance matérielle", ""), "scope": fields.get("Content", ""),
                "aids": fields.get("Instruments de recherche", ""), "note": fields.get("Notes", ""),
                "pdf": "", "pdfSize": "", "mgmt": "", "url": PAGE_BASE + record["slug"].removeprefix("sa-"),
            }
            if placeholder:
                unit["missing"] = True
            units.append(unit)
            parent = by_slug.get(record["parent"]) or {}
            segments.extend(_segments(unit, fonds, parent.get("f", {}).get("Title", "")))
    return units, segments
