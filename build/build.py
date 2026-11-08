"""Builds data/acv.sqlite, docs/index.html and docs/data.json from the raw DAVEL records in data/raw."""

import difflib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from inventory_corrections import read_raw
from pdf_pages import load_pdf_pages, sb267_default_parts
from places import arrondissement_history, arrondissement_name, corrected_entries, localities_from_note, parish_name, parish_number, parish_period, repair_parish_names, spelling_key, split_official_locality
from scope_parser import classify, normalize, parse_date_range, parse_scope_content
from scopearchiv import creation_dates, fonds_of, load_scopearchiv, place_for, related_ranges
from scopearchiv import PAGE_BASE as SCOPEARCHIV_PAGE_BASE
from scopearchiv import RAW_DIR as SCOPEARCHIV_RAW_DIR

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "davel-vd"
CORRESPONDENCE_DIR = ROOT / "data" / "raw" / "vd-ch"
CORRECTIONS = ROOT / "data" / "manual" / "communes-paroisses-corrections.json"
PDF_PAGES = ROOT / "data" / "manual" / "pdf-pages.json"
DATABASE = ROOT / "data" / "acv.sqlite"
SITE_TEMPLATE = ROOT / "site" / "template.html"
SITE_OUTPUT = ROOT / "docs" / "index.html"
DATA_OUTPUT = ROOT / "docs" / "data.json"
PAGE_MAP = ROOT / "site" / "page_map.js"
PAGE_MAP_OUTPUT = ROOT / "docs" / "pdf-pages.json"
VIEWER_SOURCE = ROOT / "site" / "apercu.user.js"
VIEWER_OUTPUT = ROOT / "docs" / "apercu.user.js"
PDF_READER = ROOT / "scraper" / "davel_pdf.js"
PDFJS_READER = ROOT / "site" / "pdfjs_reader.js"
STANDALONE_HEAD = '<!doctype html>\n<html lang="fr">\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'

FONDS_LABEL = {"eb": "Eb", "ed": "Ed", "sb-267": "SB 267"}
CONTAINER_LEVELS = {"Fonds", "Sous-fonds", "Série", "Sous-série"}
INDEX_HEADINGS = ("repertoire", "liste")
SB267_KINDS = [
    ("reconnaissance", "reconnaissance"), ("légitimation", "legitimation"),
    ("naissance", "naissance"), ("mariage", "mariage"), ("décès", "deces"),
]


def fonds_key(slug):
    return "sb-267" if slug.startswith("sb-267") else slug.split("-")[0]


def split_index_label(label):
    cote, rest = label.split(" - ", 1)
    title, dates = rest.rsplit(", ", 1)
    return cote, title, dates


def build_places(series_index):
    places = {}
    for fonds in ("eb", "ed"):
        for slug, label in series_index[fonds]:
            cote, title, dates = split_index_label(label)
            if title.startswith("(vide)"):
                continue
            number = parish_number(cote)
            place_id = f"paroisse-{number.replace(' ', '-')}"
            name = parish_name(title)
            if re.search(r"paroisse catholique", title, re.IGNORECASE) and not re.search(r"paroisse réformée", title, re.IGNORECASE):
                name = f"{name} (catholique)"
            place = places.setdefault(place_id, {"id": place_id, "kind": "paroisse", "name": name, "aliases": [], "series": [], "localities": []})
            if name != place["name"] and name not in place["aliases"]:
                place["aliases"].append(name)
            place["series"].append({"slug": slug, "fonds": FONDS_LABEL[fonds], "cote": cote, "title": title, "dates": dates, "scraped": False, "note": "", "url": PAGE_BASE + slug})
    for slug, label in series_index["sb-267"]:
        cote, title, dates = split_index_label(label)
        place_id = f"arrondissement-{cote.split('/')[1]}"
        name = arrondissement_name(title)
        successive_names = [part.strip() for part in re.split(r",?\s+puis\s+", name)]
        places[place_id] = {
            "id": place_id, "kind": "arrondissement", "name": name, "aliases": successive_names if len(successive_names) > 1 else [],
            "series": [{"slug": slug, "fonds": "SB 267", "cote": cote, "title": title, "dates": dates, "scraped": False, "note": "", "url": PAGE_BASE + slug}],
            "localities": [],
        }
    return places


def _add_locality(place, name, qualifier, source, since=None, until=None):
    key = normalize(name)
    existing = next((locality for locality in place["localities"] if normalize(locality["name"]) == key), None)
    if existing is None:
        place["localities"].append({"name": name, "qualifier": qualifier, "source": source, "since": since, "until": until})
        return
    existing["since"] = min(existing["since"], since) if existing["since"] and since else None
    existing["until"] = max(existing["until"], until) if existing["until"] and until else None
    if qualifier and qualifier not in existing["qualifier"]:
        existing["qualifier"] = " · ".join(filter(None, [existing["qualifier"], qualifier]))
    if source not in existing["source"]:
        existing["source"] = f"{existing['source']}, {source}"


def _compact(name):
    return re.sub(r"[^a-z0-9]", "", normalize(name))


NOTE_SOURCE = "note de l'inventaire"


def merge_spelling_variants(places):
    for place in places.values():
        official = {spelling_key(locality["name"]): locality for locality in place["localities"] if locality["source"] != NOTE_SOURCE}
        for variant in [locality for locality in place["localities"] if locality["source"] == NOTE_SOURCE]:
            match = official.get(spelling_key(variant["name"]))
            if match is None:
                continue
            place["localities"].remove(variant)
            _add_locality(place, match["name"], variant["qualifier"], variant["source"], variant["since"], variant["until"])
            for other in places.values():
                for locality in other["localities"]:
                    if _compact(locality["name"]) == _compact(match["name"]) and variant["name"] not in locality.setdefault("aliases", []):
                        locality["aliases"].append(variant["name"])


def _arrondissement_finder(places):
    by_key = {}
    for place in places.values():
        if place["kind"] == "arrondissement":
            for name in [place["name"], *place["aliases"]]:
                by_key[_compact(name)] = place

    def find(name):
        inside = re.search(r"\(([^)]+)\)", name)
        keys = [_compact(name)] + ([_compact(inside.group(1))] if inside else []) + ([_compact(name.split("/")[0])] if "/" in name else [])
        for key in keys:
            if key in by_key:
                return by_key[key]
        prefixed = [place for known, place in by_key.items() if known.startswith(keys[0])]
        if len(prefixed) == 1:
            return prefixed[0]
        close = difflib.get_close_matches(keys[0], by_key, n=1, cutoff=0.85)
        return by_key[close[0]] if close else None

    return find


def add_official_localities(places):
    parish_places = {place_id.removeprefix("paroisse-").replace("-", " "): place for place_id, place in places.items() if place["kind"] == "paroisse"}
    parish_names = {number: [place["name"], *place["aliases"]] for number, place in parish_places.items()}
    corrections = json.loads(CORRECTIONS.read_text(encoding="utf-8"))
    for entry in corrected_entries(json.loads((CORRESPONDENCE_DIR / "communes-paroisses.json").read_text(encoding="utf-8")), corrections):
        name, context = split_official_locality(entry["locality"])
        description = repair_parish_names(entry["description"], parish_names)
        for number in entry["parishes"]:
            if number in parish_places:
                _add_locality(parish_places[number], name, " ".join(filter(None, [context, description])), "table des paroisses", *parish_period(description, number))

    find_arrondissement = _arrondissement_finder(places)
    for entry in json.loads((CORRESPONDENCE_DIR / "communes-arrondissements.json").read_text(encoding="utf-8")):
        history = arrondissement_history(entry["periods"])
        qualifier = ", ".join(f"{name} dès {since}" if since else name for name, since in history)
        if entry["note"]:
            qualifier = f"{qualifier} ({entry['note']})"
        for index, (name, since) in enumerate(history):
            place = find_arrondissement(name)
            if place:
                _add_locality(place, entry["locality"], qualifier, "table des arrondissements", int(since[-4:]) if index and since else None)
            else:
                print(f"arrondissement inconnu : {name!r} ({entry['locality']})")


def add_scopearchiv_series(places):
    ranges = related_ranges(places)
    for path in sorted(SCOPEARCHIV_RAW_DIR.glob("sa-*.json")):
        root = next(record for record in read_raw(path) if record["parent"] is None)
        cote = root["f"].get("Ref. code", "")
        place_id = place_for(cote, ranges) if fonds_of(cote) in ("SB 268", "SB 269", "Ec") else None
        if place_id in places:
            places[place_id]["series"].append({
                "slug": root["slug"], "fonds": fonds_of(cote), "cote": cote, "title": root["f"].get("Title", ""),
                "dates": creation_dates(root["f"]), "scraped": True, "note": root["f"].get("Notes", ""),
                "url": SCOPEARCHIV_PAGE_BASE + root["slug"].removeprefix("sa-"),
            })


def piece_dates(fields):
    return parse_date_range(re.sub(r"\(Création\)", "", fields.get("Date(s)", "")))


def make_unit(record, place_id, fonds):
    fields = record["f"]
    start, end = piece_dates(fields)
    return {
        "slug": record["slug"],
        "url": PAGE_BASE + record["slug"],
        "place": place_id,
        "fonds": FONDS_LABEL[fonds],
        "cote": fields.get("Cote", ""),
        "level": fields.get("Niveau de description", ""),
        "title": fields.get("Titre", ""),
        "start": start,
        "end": end,
        "dates": re.sub(r"\s*\(Création\)", "", fields.get("Date(s)", "")),
        "extent": fields.get("Étendue matérielle et support", ""),
        "scope": fields.get("Portée et contenu", ""),
        "aids": fields.get("Instruments de recherche", ""),
        "note": fields.get("Note", ""),
        "pdf": record.get("pdf") or "",
        "pdfSize": fields.get("Taille du fichier", ""),
        "mgmt": fields.get("Cote de gestion", ""),
    }


def segment_row(unit_slug, segment):
    return {
        "unit": unit_slug,
        "kinds": segment.kinds,
        "label": segment.label,
        "start": segment.start,
        "end": segment.end,
        "dates": segment.dates_text,
        "pages": segment.pages,
        "tb": segment.head_to_tail,
        "foreign": segment.foreign,
        "section": segment.section,
    }


def parish_segments(unit):
    segments = [segment_row(unit["slug"], segment) for segment in parse_scope_content(unit["scope"])]
    if segments:
        return segments
    heading = unit["scope"].splitlines()[0].strip(" \"«».") if unit["scope"] else ""
    kinds = classify(heading) if normalize(heading).startswith(INDEX_HEADINGS) else []
    return [{"unit": unit["slug"], "kinds": kinds or ["inconnu"], "label": heading if kinds else "Contenu non détaillé", "start": unit["start"], "end": unit["end"],
             "dates": unit["dates"], "pages": "", "tb": False, "foreign": False, "section": ""}]


def civil_register_segment(unit, series_title):
    lowered = series_title.lower()
    kinds = next(([kind] for keyword, kind in SB267_KINDS if keyword in lowered), ["inconnu"])
    start, end = parse_date_range(unit["scope"]) if "entre le" in unit["scope"] else (None, None)
    return {"unit": unit["slug"], "kinds": kinds, "label": series_title, "start": start or unit["start"], "end": end or unit["end"],
            "dates": unit["scope"] if start else unit["dates"], "pages": "", "tb": False, "foreign": False, "section": ""}


def is_register(record):
    fields = record["f"]
    return fields.get("Niveau de description") not in CONTAINER_LEVELS and "FANTOME" not in fields.get("Cote", "")


def load_scraped(places):
    series_by_slug = {series["slug"]: (place, series) for place in places.values() for series in place["series"]}
    units, segments = [], []
    for path in sorted(RAW_DIR.glob("[!_]*.json")):
        records = read_raw(path)
        by_slug = {record["slug"]: record for record in records}
        root = next(record for record in records if record["parent"] is None)
        place, series = series_by_slug[root["slug"]]
        series["scraped"] = True
        series["note"] = root["f"].get("Note", "")
        place["related"] = root["f"].get("Unités de description associées", "").splitlines()
        for locality in localities_from_note(series["note"]):
            merged = re.match(r"adjonction en (\d{4})", locality["qualifier"])
            _add_locality(place, locality["name"], locality["qualifier"], NOTE_SOURCE, int(merged.group(1)) if merged else None)
        fonds = fonds_key(root["slug"])
        for record in records:
            if record is root or not is_register(record):
                continue
            unit = make_unit(record, place["id"], fonds)
            units.append(unit)
            if fonds == "sb-267":
                parent = by_slug[record["parent"]]
                series = record if parent is root else parent
                segments.append(civil_register_segment(unit, series["f"].get("Titre", "")))
            else:
                segments.extend(parish_segments(unit))
    return units, segments


def attach_pdf_pages(units):
    units_by_cote = {unit["cote"]: unit for unit in units if unit["pdf"]}
    for cote, register in load_pdf_pages(PDF_PAGES).items():
        if cote not in units_by_cote:
            raise ValueError(f"{PDF_PAGES.name} : {cote} n'est pas un registre indexé avec PDF")
        units_by_cote[cote]["pdfParts"] = register["parts"]
    for unit in units_by_cote.values():
        if unit["fonds"] == "SB 267" and "pdfParts" not in unit and (parts := sb267_default_parts(unit)):
            unit["pdfParts"] = parts


SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE places (id TEXT PRIMARY KEY, kind TEXT, name TEXT, aliases TEXT);
CREATE TABLE localities (place_id TEXT REFERENCES places(id), name TEXT, qualifier TEXT, source TEXT, since INTEGER, until INTEGER, aliases TEXT);
CREATE TABLE series (slug TEXT PRIMARY KEY, place_id TEXT REFERENCES places(id), fonds TEXT, cote TEXT, title TEXT, dates TEXT, scraped INTEGER, note TEXT, url TEXT);
CREATE TABLE units (slug TEXT PRIMARY KEY, place_id TEXT REFERENCES places(id), fonds TEXT, cote TEXT, level TEXT, title TEXT,
    date_start TEXT, date_end TEXT, dates TEXT, extent TEXT, scope_content TEXT, finding_aids TEXT, note TEXT,
    pdf_url TEXT, pdf_size TEXT, management_code TEXT, page_url TEXT, missing INTEGER);
CREATE TABLE segments (unit_slug TEXT REFERENCES units(slug), kinds TEXT, label TEXT, date_start TEXT, date_end TEXT, dates TEXT,
    pages TEXT, head_to_tail INTEGER, foreign_events INTEGER, section TEXT);
CREATE INDEX segments_dates ON segments(date_start, date_end);
CREATE TABLE pdf_parts (unit_slug TEXT REFERENCES units(slug), pdf_start INTEGER, pdf_end INTEGER, kind TEXT, content TEXT,
    page_first INTEGER, page_last INTEGER, note TEXT);
"""

PDF_BASE = "https://davel-vd.ch/uploads/r/null/"
PAGE_BASE = "https://davel-vd.ch/"


def write_database(payload):
    places, units, segments = payload["places"], payload["units"], payload["segments"]
    DATABASE.unlink(missing_ok=True)
    with sqlite3.connect(DATABASE) as connection:
        connection.executescript(SCHEMA)
        connection.execute("INSERT INTO meta VALUES ('generatedAt', ?)", (payload["generatedAt"],))
        for place in places:
            connection.execute("INSERT INTO places VALUES (?, ?, ?, ?)", (place["id"], place["kind"], place["name"], " | ".join(place["aliases"])))
            connection.executemany("INSERT INTO localities VALUES (?, ?, ?, ?, ?, ?, ?)", [
                (place["id"], loc["name"], loc["qualifier"], loc["source"], loc["since"], loc["until"], " | ".join(loc.get("aliases", []))) for loc in place["localities"]
            ])
            connection.executemany("INSERT INTO series VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
                (s["slug"], place["id"], s["fonds"], s["cote"], s["title"], s["dates"], int(s["scraped"]), s["note"], s["url"]) for s in place["series"]
            ])
        connection.executemany("INSERT INTO units VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            (u["slug"], u["place"], u["fonds"], u["cote"], u["level"], u["title"], u["start"], u["end"], u["dates"], u["extent"],
             u["scope"], u["aids"], u["note"], PDF_BASE + u["pdf"] if u["pdf"] else None, u["pdfSize"], u["mgmt"], u["url"], int(u.get("missing", False)))
            for u in units
        ])
        connection.executemany("INSERT INTO segments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            (s["unit"], ",".join(s["kinds"]), s["label"], s["start"], s["end"], s["dates"], s["pages"], int(s["tb"]), int(s["foreign"]), s["section"])
            for s in segments
        ])
        connection.executemany("INSERT INTO pdf_parts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
            (u["slug"], *part["pdf"], part["kind"], part["content"], *(part["pages"] or (None, None)), part["note"])
            for u in units for part in u.get("pdfParts", [])
        ])


def site_payload(places, units, segments):
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pdfBase": PDF_BASE,
        "pageBase": PAGE_BASE,
        "places": list(places.values()),
        "units": units,
        "segments": segments,
    }


def data_json(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def keep_date_if_unchanged(payload, previous=DATA_OUTPUT):
    try:
        text = previous.read_text(encoding="utf-8")
        kept = {**payload, "generatedAt": json.loads(text)["generatedAt"]}
    except (OSError, ValueError, KeyError):
        return payload
    return kept if data_json(kept) == text else payload


def write_data(payload):
    DATA_OUTPUT.write_text(data_json(payload), encoding="utf-8")


def write_site(payload):
    data = data_json(payload).replace("</", "<\\/")
    page = SITE_TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", data).replace("/*__PAGE_MAP__*/", PAGE_MAP.read_text(encoding="utf-8"))
    SITE_OUTPUT.parent.mkdir(exist_ok=True)
    SITE_OUTPUT.write_text(STANDALONE_HEAD + page, encoding="utf-8")


def write_viewer(units):
    viewer = (VIEWER_SOURCE.read_text(encoding="utf-8")
              .replace("/*__PDF_READER__*/", PDF_READER.read_text(encoding="utf-8").strip())
              .replace("/*__PDFJS_READER__*/", PDFJS_READER.read_text(encoding="utf-8").strip())
              .replace("/*__PAGE_MAP__*/", PAGE_MAP.read_text(encoding="utf-8").strip()))
    VIEWER_OUTPUT.write_text(viewer, encoding="utf-8")
    page_map = {
        unit["pdf"]: {"cote": unit["cote"], "pdfParts": [
            {key: part[key] for key in ("pdf", "pages", "content", "anchors", "spread", "roman", "approx", "note")} for part in unit["pdfParts"]
        ]}
        for unit in units if unit.get("pdfParts")
    }
    PAGE_MAP_OUTPUT.write_text(json.dumps(page_map, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    places = build_places(json.loads((RAW_DIR / "_series_index.json").read_text(encoding="utf-8")))
    add_official_localities(places)
    units, segments = load_scraped(places)
    merge_spelling_variants(places)
    attach_pdf_pages(units)
    add_scopearchiv_series(places)
    other_units, other_segments = load_scopearchiv(places, _arrondissement_finder(places))
    units += other_units
    segments += other_segments
    payload = keep_date_if_unchanged(site_payload(places, units, segments))
    write_database(payload)
    write_site(payload)
    write_data(payload)
    write_viewer(units)
    scraped = sum(series["scraped"] for place in places.values() for series in place["series"])
    print(f"{len(places)} lieux, {scraped} séries indexées, {len(units)} registres, {len(segments)} segments")


if __name__ == "__main__":
    main()
