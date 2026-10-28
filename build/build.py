"""Builds data/acv.sqlite and site/index.html from the raw DAVEL records in data/raw/davel-vd."""

import difflib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pdf_pages import load_pdf_pages
from places import arrondissement_history, arrondissement_name, localities_from_note, parish_name, parish_number, split_official_locality
from scope_parser import normalize, parse_date_range, parse_scope_content
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
PAGE_MAP = ROOT / "site" / "page_map.js"
PAGE_MAP_OUTPUT = ROOT / "docs" / "pdf-pages.json"
VIEWER_SOURCE = ROOT / "site" / "apercu.user.js"
VIEWER_OUTPUT = ROOT / "docs" / "apercu.user.js"
PDF_READER = ROOT / "scraper" / "davel_pdf.js"
STANDALONE_HEAD = '<!doctype html>\n<html lang="fr">\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'

FONDS_LABEL = {"eb": "Eb", "ed": "Ed", "sb-267": "SB 267"}
CONTAINER_LEVELS = {"Fonds", "Sous-fonds", "Série", "Sous-série"}
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


def _add_locality(place, name, qualifier, source, since=None):
    key = normalize(name)
    existing = next((locality for locality in place["localities"] if normalize(locality["name"]) == key), None)
    if existing is None:
        place["localities"].append({"name": name, "qualifier": qualifier, "source": source, "since": since})
        return
    existing["since"] = min(existing["since"], since) if existing["since"] and since else None
    if qualifier and qualifier not in existing["qualifier"]:
        existing["qualifier"] = " · ".join(filter(None, [existing["qualifier"], qualifier]))
    if source not in existing["source"]:
        existing["source"] = f"{existing['source']}, {source}"


def _compact(name):
    return re.sub(r"[^a-z0-9]", "", normalize(name))


def _arrondissement_finder(places):
    by_key = {}
    for place in places.values():
        if place["kind"] == "arrondissement":
            for name in [place["name"], *place["aliases"]]:
                by_key[_compact(name)] = place

    def find(name):
        inside = re.search(r"\(([^)]+)\)", name)
        keys = [_compact(name)] + ([_compact(inside.group(1))] if inside else [])
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
    corrections = json.loads(CORRECTIONS.read_text(encoding="utf-8"))
    for entry in json.loads((CORRESPONDENCE_DIR / "communes-paroisses.json").read_text(encoding="utf-8")):
        entry = {**entry, **corrections.get(entry["locality"], {})}
        name, context = split_official_locality(entry["locality"])
        for number in entry["parishes"]:
            if number in parish_places:
                _add_locality(parish_places[number], name, " ".join(filter(None, [context, entry["description"]])), "table des paroisses")

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
        root = next(record for record in json.loads(path.read_text(encoding="utf-8")) if record["parent"] is None)
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
    return [{"unit": unit["slug"], "kinds": ["inconnu"], "label": "Contenu non détaillé", "start": unit["start"], "end": unit["end"],
             "dates": unit["dates"], "pages": "", "tb": False, "foreign": False, "section": ""}]


def civil_register_segment(unit, series_title):
    lowered = series_title.lower()
    kinds = next(([kind] for keyword, kind in SB267_KINDS if keyword in lowered), ["inconnu"])
    start, end = parse_date_range(unit["scope"]) if "entre le" in unit["scope"] else (None, None)
    return {"unit": unit["slug"], "kinds": kinds, "label": series_title, "start": start or unit["start"], "end": end or unit["end"],
            "dates": unit["scope"] if start else unit["dates"], "pages": "", "tb": False, "foreign": False, "section": ""}


def load_scraped(places):
    series_by_slug = {series["slug"]: (place, series) for place in places.values() for series in place["series"]}
    units, segments = [], []
    for path in sorted(RAW_DIR.glob("[!_]*.json")):
        records = json.loads(path.read_text(encoding="utf-8"))
        by_slug = {record["slug"]: record for record in records}
        root = next(record for record in records if record["parent"] is None)
        place, series = series_by_slug[root["slug"]]
        series["scraped"] = True
        series["note"] = root["f"].get("Note", "")
        place["related"] = root["f"].get("Unités de description associées", "").splitlines()
        for locality in localities_from_note(series["note"]):
            merged = re.match(r"adjonction en (\d{4})", locality["qualifier"])
            _add_locality(place, locality["name"], locality["qualifier"], "note de l'inventaire", int(merged.group(1)) if merged else None)
        fonds = fonds_key(root["slug"])
        for record in records:
            if record is root or record["f"].get("Niveau de description") in CONTAINER_LEVELS:
                continue
            unit = make_unit(record, place["id"], fonds)
            units.append(unit)
            if fonds == "sb-267":
                segments.append(civil_register_segment(unit, by_slug[record["parent"]]["f"].get("Titre", "")))
            else:
                segments.extend(parish_segments(unit))
    return units, segments


def attach_pdf_pages(units):
    units_by_cote = {unit["cote"]: unit for unit in units if unit["pdf"]}
    for cote, register in load_pdf_pages(PDF_PAGES).items():
        if cote not in units_by_cote:
            raise ValueError(f"{PDF_PAGES.name} : {cote} n'est pas un registre indexé avec PDF")
        units_by_cote[cote]["pdfParts"] = register["parts"]


SCHEMA = """
CREATE TABLE places (id TEXT PRIMARY KEY, kind TEXT, name TEXT, aliases TEXT);
CREATE TABLE localities (place_id TEXT REFERENCES places(id), name TEXT, qualifier TEXT, source TEXT, since INTEGER);
CREATE TABLE series (slug TEXT PRIMARY KEY, place_id TEXT REFERENCES places(id), fonds TEXT, cote TEXT, title TEXT, dates TEXT, scraped INTEGER, note TEXT, url TEXT);
CREATE TABLE units (slug TEXT PRIMARY KEY, place_id TEXT REFERENCES places(id), fonds TEXT, cote TEXT, level TEXT, title TEXT,
    date_start TEXT, date_end TEXT, dates TEXT, extent TEXT, scope_content TEXT, finding_aids TEXT, note TEXT,
    pdf_url TEXT, pdf_size TEXT, management_code TEXT, page_url TEXT);
CREATE TABLE segments (unit_slug TEXT REFERENCES units(slug), kinds TEXT, label TEXT, date_start TEXT, date_end TEXT, dates TEXT,
    pages TEXT, head_to_tail INTEGER, foreign_events INTEGER, section TEXT);
CREATE INDEX segments_dates ON segments(date_start, date_end);
CREATE TABLE pdf_parts (unit_slug TEXT REFERENCES units(slug), pdf_start INTEGER, pdf_end INTEGER, kind TEXT, content TEXT,
    page_first INTEGER, page_last INTEGER, note TEXT);
"""

PDF_BASE = "https://davel-vd.ch/uploads/r/null/"
PAGE_BASE = "https://davel-vd.ch/"


def write_database(places, units, segments):
    DATABASE.unlink(missing_ok=True)
    with sqlite3.connect(DATABASE) as connection:
        connection.executescript(SCHEMA)
        for place in places.values():
            connection.execute("INSERT INTO places VALUES (?, ?, ?, ?)", (place["id"], place["kind"], place["name"], " | ".join(place["aliases"])))
            connection.executemany("INSERT INTO localities VALUES (?, ?, ?, ?, ?)", [(place["id"], loc["name"], loc["qualifier"], loc["source"], loc["since"]) for loc in place["localities"]])
            connection.executemany("INSERT INTO series VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
                (s["slug"], place["id"], s["fonds"], s["cote"], s["title"], s["dates"], int(s["scraped"]), s["note"], s["url"]) for s in place["series"]
            ])
        connection.executemany("INSERT INTO units VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            (u["slug"], u["place"], u["fonds"], u["cote"], u["level"], u["title"], u["start"], u["end"], u["dates"], u["extent"],
             u["scope"], u["aids"], u["note"], PDF_BASE + u["pdf"] if u["pdf"] else None, u["pdfSize"], u["mgmt"], u["url"])
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


def write_site(places, units, segments):
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pdfBase": PDF_BASE,
        "pageBase": PAGE_BASE,
        "places": list(places.values()),
        "units": units,
        "segments": segments,
    }
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = SITE_TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", data).replace("/*__PAGE_MAP__*/", PAGE_MAP.read_text(encoding="utf-8"))
    SITE_OUTPUT.parent.mkdir(exist_ok=True)
    SITE_OUTPUT.write_text(STANDALONE_HEAD + page, encoding="utf-8")


def write_viewer(units):
    viewer = (VIEWER_SOURCE.read_text(encoding="utf-8")
              .replace("/*__PDF_READER__*/", PDF_READER.read_text(encoding="utf-8").strip())
              .replace("/*__PAGE_MAP__*/", PAGE_MAP.read_text(encoding="utf-8").strip()))
    VIEWER_OUTPUT.write_text(viewer, encoding="utf-8")
    page_map = {
        unit["pdf"]: {"cote": unit["cote"], "pdfParts": [
            {key: part[key] for key in ("pdf", "pages", "content", "anchors", "spread", "roman", "note")} for part in unit["pdfParts"]
        ]}
        for unit in units if unit.get("pdfParts")
    }
    PAGE_MAP_OUTPUT.write_text(json.dumps(page_map, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    places = build_places(json.loads((RAW_DIR / "_series_index.json").read_text(encoding="utf-8")))
    add_official_localities(places)
    units, segments = load_scraped(places)
    attach_pdf_pages(units)
    add_scopearchiv_series(places)
    other_units, other_segments = load_scopearchiv(places)
    units += other_units
    segments += other_segments
    write_database(places, units, segments)
    write_site(places, units, segments)
    write_viewer(units)
    scraped = sum(series["scraped"] for place in places.values() for series in place["series"])
    print(f"{len(places)} lieux, {scraped} séries indexées, {len(units)} registres, {len(segments)} segments")


if __name__ == "__main__":
    main()
