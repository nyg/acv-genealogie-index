"""Turns the official ACV correspondence tables (PDF) into JSON. Run with: uv run --with pdfplumber scraper/parse_correspondence.py"""

import json
import re
import subprocess
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

from places import parish_name, parish_number  # noqa: E402
from scope_parser import normalize  # noqa: E402

RAW_DIR = ROOT / "data" / "raw" / "vd-ch"
ARRONDISSEMENT_COLUMNS = [(240, "locality"), (440, "1876"), (635, "1912"), (840, "1928"), (10_000, "1960")]
PAGE_FURNITURE = re.compile(r"^(Pierre-Yves Favez\b.*|\d{1,3}|[|I]|(\d{1,3}\s+)?[|I]?\s*La paroisse, une\b.*)$")
BRACKET = re.compile(r"[\[|Ï1Il]\s?[0-9ÏIlO]{1,3}(?:\s?(?:bis|ter))?\s?[\]|Ï1Il]")
STRICT_BRACKET = re.compile(r"\[(\d{1,3}(?: ?(?:bis|ter))?)\]")
OCR_DIGITS = str.maketrans({"Ï": "1", "I": "1", "l": "1", "O": "0", "|": "", "[": "", "]": ""})
SMALL_WORDS = {"la", "le", "les", "de", "du", "des", "sur", "sous", "en", "près", "et", "soit", "puis", "dit", "ou"}
SPURIOUS_DIACRITICS = re.compile(r"[ÄÖÜÔÀÂäöü]")


def _rows(page, tolerance=3):
    rows = []
    for word in sorted(page.extract_words(), key=lambda w: (round(w["top"]), w["x0"])):
        if rows and abs(rows[-1][0] - word["top"]) <= tolerance:
            rows[-1][1].append(word)
        else:
            rows.append((word["top"], [word]))
    return [words for _, words in rows]


def _column(x, columns):
    return next(name for limit, name in columns if x < limit)


def official_spelling(locality):
    expanded = re.sub(r"-s\.-", "-sur-", locality)
    return re.sub(r"-(ville|dessous|dessus)\b", lambda match: f"-{match[1].capitalize()}", expanded)


def parse_arrondissements():
    import pdfplumber

    entries = []
    with pdfplumber.open(RAW_DIR / "doc-etat-civil_correspondance_communes-arrondissements.pdf") as pdf:
        for page in pdf.pages:
            for words in _rows(page):
                cells = {}
                for word in words:
                    cells.setdefault(_column(word["x0"], ARRONDISSEMENT_COLUMNS), []).append(word["text"])
                cells = {name: " ".join(texts) for name, texts in cells.items()}
                if cells.get("1876") in (None, "1876") or cells.get("locality", "").startswith(("Communes", "Arrondissements", "Page")):
                    continue
                if "locality" not in cells and entries:
                    for period, text in cells.items():
                        entries[-1]["periods"][period] = f"{entries[-1]['periods'].get(period, '')} {text}".strip()
                    continue
                locality, note = re.match(r"^(.*?)\s*(\(voir [^)]*\))?$", cells.get("locality", "")).groups()
                entries.append({
                    "locality": official_spelling(locality),
                    "note": (note or "").strip("()"),
                    "periods": {period: cells[period] for period in ("1876", "1912", "1928", "1960") if period in cells},
                })
    return entries


def parish_names_by_number():
    index = json.loads((ROOT / "data" / "raw" / "davel-vd" / "_series_index.json").read_text(encoding="utf-8"))
    names = {}
    for fonds in ("eb", "ed"):
        for _, label in index[fonds]:
            cote, rest = label.split(" - ", 1)
            number = parish_number(cote)
            if number:
                names.setdefault(number, set()).add(normalize(parish_name(rest.rsplit(", ", 1)[0])).split(" (")[0])
    return names


def parish_display_names():
    index = json.loads((ROOT / "data" / "raw" / "davel-vd" / "_series_index.json").read_text(encoding="utf-8"))
    return {parish_name(label.split(" - ", 1)[1].rsplit(", ", 1)[0]).split(" (")[0]
            for fonds in ("eb", "ed") for _, label in index[fonds] if " - " in label}


def _name_key(text):
    # The OCR mixes up l and i, and spaces out letters or drops hyphens inside names.
    return re.sub(r"[^a-z]", "", normalize(text)).replace("l", "i")


def _spelling_variants(name):
    base = name.split(" (")[0]
    for part in base.split(" - "):
        yield part
        yield re.sub(r"^(?:La|Le|Les) |^L'", "", part)
    alternative = re.search(r"\((-?)([^)]{4,})\)", name)
    if alternative:
        yield f"{base}-{alternative[2]}" if alternative[1] else alternative[2]


def reference_spellings(arrondissement_entries):
    spellings = {}
    for name in sorted(parish_display_names()) + [entry["locality"] for entry in arrondissement_entries]:
        for variant in _spelling_variants(name):
            if len(_name_key(variant)) >= 4:
                spellings.setdefault(_name_key(variant), variant)
    return spellings


def _has_fragments(text):
    tokens = [re.sub(r"^[dlDL]['’]", "", token) for token in re.split(r"[\s-]+", text)]
    return any(len(token) == 1 or token[:1].islower() and token not in SMALL_WORDS for token in tokens if token)


def _is_damaged(piece, reference):
    if normalize(piece) == normalize(reference):
        return bool(SPURIOUS_DIACRITICS.search(piece))
    if normalize(piece).replace("-", " ") == normalize(reference).replace("-", " "):
        return True
    if re.sub(r"[^a-z]", "", normalize(piece)) != re.sub(r"[^a-z]", "", normalize(reference)):
        return True
    return _has_fragments(piece)


def respell_locality(text, spellings):
    def respell(piece):
        piece = " ".join(piece.split())
        reference = spellings.get(_name_key(piece))
        if not reference or not _is_damaged(piece, reference):
            return piece
        # Both reference tables drop the accent on capitals.
        return f"É{reference[1:]}" if piece.startswith("É") and reference.startswith("E") else reference

    main, _, rest = text.partition("(")
    rest = f"({rest}" if rest else ""
    respelled_main = respell(main)
    respelled_rest = re.sub(r"\(([^()]*)\)", lambda match: f"({respell(match[1])})", rest)
    if respelled_main == main.strip() and respelled_rest == rest:
        return text
    return f"{respelled_main} {respelled_rest}".strip()


def fix_ocr_letters(text):
    return text.replace("ïï", "ll").replace("ÏÏ", "ll").replace("ï", "l").replace("Ï", "l").replace("Ë", "É")


def _number_candidates(token):
    inner, whole = token[1:-1], token
    suffix = re.search(r"(bis|ter)", token)
    bases = {re.sub(r"\D", "", part.translate(OCR_DIGITS)) for part in (inner, whole, token[1:], token[:-1])}
    return [f"{base.lstrip('0')}{' ' + suffix.group(1) if suffix else ''}" for base in bases if base and base.lstrip("0")]


def _similar(a, b):
    return SequenceMatcher(None, a, b).ratio() >= 0.7


def _validated(number, before, names):
    preceding = normalize(fix_ocr_letters(before[-45:])).replace(" ", "")
    for name in names.get(number, ()):
        compact = name.replace(" ", "")
        if compact[:6] in preceding or _similar(compact, preceding[-len(compact):]):
            return True
    return False


def _parish_by_fuzzy_name(description, names):
    leading = re.match(r"[^\W\d_]+", normalize(fix_ocr_letters(description)).replace(" ", ""))
    if not leading or len(leading.group(0)) < 4:
        return []
    word = leading.group(0)
    scored = [(SequenceMatcher(None, name.replace(" ", ""), word[:len(name.replace(" ", ""))]).ratio(), number)
              for number, variants in names.items() for name in variants if len(name) >= 4]
    best = max(scored, default=(0, None))
    return [best[1]] if best[0] >= 0.75 else []


def decode_parishes(description, names):
    numbers, cleaned, cursor = [], [], 0
    for match in BRACKET.finditer(description):
        token = match.group(0)
        strict = STRICT_BRACKET.fullmatch(token.replace(" ]", "]"))
        candidates = [strict.group(1)] if strict else _number_candidates(token)
        chosen = next((n for n in candidates if n in names and _validated(n, description[:match.start()], names)), None)
        if chosen is None and strict and candidates[0] in names:
            chosen = candidates[0]
        if chosen is None:
            continue
        numbers.append(chosen)
        cleaned.append(description[cursor:match.start()])
        cleaned.append(f"[{chosen}]")
        cursor = match.end()
    cleaned.append(description[cursor:])
    return list(dict.fromkeys(numbers)), fix_ocr_letters("".join(cleaned))


def _split_line(line, column):
    gap = re.match(r"^(\S.*?\S|\S)\s{2,}(\S.*)$", line)
    if gap and abs(len(line) - len(gap.group(2)) - column) <= 6:
        return gap.group(1), gap.group(2)
    if len(line) <= column:
        return line.strip(), ""
    for offset in range(0, 8):
        for position in (column - offset, column + offset):
            if 0 < position < len(line) and line[position - 1] == " " and line[position] != " ":
                return line[:position].strip(), line[position:].strip()
    return line.strip(), ""


def _table_a_lines():
    text = subprocess.run(
        ["pdftotext", "-layout", "-f", "1", "-l", "15", str(RAW_DIR / "doc-etat-civil_correspondance_communes-paroisses.pdf"), "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    started = False
    for page in text.split("\f"):
        lines = [line.rstrip() for line in page.splitlines()]
        gaps = Counter(m.end(1) + len(m.group(2)) for m in (re.match(r"^(\S.*?\S)(\s{2,})\S", line) for line in lines) if m)
        column = gaps.most_common(1)[0][0] if gaps else 30
        for line in lines:
            if not started:
                started = line.startswith("Entre crochets")
                continue
            if re.match(r"^B\.\s+Tableau", line):
                return
            if not line.strip() or PAGE_FURNITURE.match(line.strip()):
                continue
            yield line, column


def _continues_previous(locality, previous):
    closes_open_paren = previous.count("(") > previous.count(")") and locality.count(")") > locality.count("(")
    return locality[:1] == "(" or locality[:1].islower() or closes_open_paren


def _parishes_named_in(description, names):
    text = f" {normalize(fix_ocr_letters(description))} "
    found = []
    for number, variants in names.items():
        for name in variants:
            position = text.find(f" {name} ") if len(name) >= 4 else -1
            if position >= 0:
                found.append((position, number))
    return [number for _, number in sorted(found)]


def _resolve_references(results):
    by_key = {normalize(entry["locality"]): entry for entry in results}
    for entry in results:
        reference = re.match(r"^Voir (.+)$", entry["description"])
        if entry["parishes"] or not reference:
            continue
        target = next((other for key, other in by_key.items() if key.startswith(normalize(reference.group(1)).split(",")[0])), None)
        if target:
            entry["parishes"] = target["parishes"]


def parse_parishes(spellings):
    names = parish_names_by_number()
    entries = []
    for line, column in _table_a_lines():
        if line.startswith(" "):
            if entries and len(line) - len(line.lstrip()) >= column - 8:
                entries[-1]["raw"] += " " + line.strip()
            continue
        locality, description = _split_line(line, column)
        if entries and (_continues_previous(locality, entries[-1]["locality"]) or not description and not entries[-1]["raw"]):
            entries[-1]["locality"] += f" {locality}"
            entries[-1]["raw"] += f" {description}" if description else ""
            continue
        entries.append({"locality": locality, "raw": description})
    results = []
    for entry in entries:
        raw = re.sub(r"\s+", " ", entry["raw"]).strip()
        numbers, description = decode_parishes(raw, names)
        results.append({
            "locality": respell_locality(fix_ocr_letters(re.sub(r"\s+|(?<=\w)(?=\()", " ", entry["locality"])).strip(), spellings),
            "description": description,
            "parishes": numbers or _parishes_named_in(raw, names) or _parish_by_fuzzy_name(raw, names),
        })
    _resolve_references(results)
    return results


def _write(name, entries, label):
    target = RAW_DIR / name
    target.write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{target.name}: {len(entries)} {label}")


if __name__ == "__main__":
    arrondissements = parse_arrondissements()
    _write("communes-arrondissements.json", arrondissements, "localités")
    _write("communes-paroisses.json", parse_parishes(reference_spellings(arrondissements)), "localités")
