"""Places each parish and civil-status arrondissement in a former Vaud district (1803-2007), through the commune of its seat."""

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMUNES = ROOT / "data" / "raw" / "ofs" / "communes-vd.json"
SEATS = ROOT / "data" / "manual" / "lieux-communes.json"


def commune_key(name):
    name = re.sub(r"\s*\((?:VD|catholique)\)$", "", name)
    ascii_name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", ascii_name.lower())


def short_district_name(district):
    name = re.sub(r"^District (?:d'|de |du )", "", district)
    return name[:1].upper() + name[1:]


def place_districts(places, communes, seats):
    by_key = {commune_key(name): district for name, district in communes.items()}
    districts = {place["id"]: by_key.get(commune_key(seats.get(place["id"], place["name"]))) for place in places}
    unknown = [place["id"] for place in places if districts[place["id"]] is None]
    if unknown:
        raise ValueError(f"{SEATS.name} : commune du siège à indiquer pour {', '.join(unknown)}")
    return districts


def load_districts(places):
    communes = json.loads(COMMUNES.read_text(encoding="utf-8"))["communes"]
    seats = json.loads(SEATS.read_text(encoding="utf-8"))
    return place_districts(places, communes, seats)
