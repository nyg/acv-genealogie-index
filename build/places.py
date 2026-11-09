import re
import unicodedata
from difflib import SequenceMatcher
from typing import NamedTuple

from scope_parser import normalize

ARTICLE_FOR = {"des": "Les ", "du": "Le ", "de la": "La ", "de l'": "L'", "de l’": "L'"}
CONNECTORS = {"de", "du", "des", "sur", "sous", "près", "la", "le", "les", "l'", "d'", "en"}
LEADING_ARTICLES = {"les", "la", "le"}

PARISH_TITLES = [
    re.compile(
        rf"{prefix}\s*(?P<prep>de la |de l'|de l’|d'\s?|d’\s?|de |du |des )?(?P<name>[^,.;]+?)"
        r"(?=\s+(?:et|annexe|avec|puis)\b|[,.;]|$)",
        re.IGNORECASE,
    )
    for prefix in (r"Registres paroissiaux", r"paroisse (?:réformée|catholique)(?: de langue allemande)?", r"Registres")
]


def parish_number(cote):
    match = re.match(r"E[bd] (?P<number>\d+(?: (?:bis|ter))?)", cote)
    return match["number"] if match else None


def parish_name(title):
    simplified = re.sub(r"réformée et de la commune", "réformée", title)
    simplified = re.sub(r"\s+et de la commune\s+(?:de |d'|d’)\s*[^,.;]+", "", simplified)
    candidates = [
        (match.start(), priority, ARTICLE_FOR.get((match["prep"] or "").strip().lower(), "") + match["name"].strip())
        for priority, pattern in enumerate(PARISH_TITLES)
        for match in pattern.finditer(simplified)
        if match["name"].strip() and not normalize(match["name"]).startswith(("paroiss", "registres"))
    ]
    return min(candidates)[2] if candidates else title.rstrip(".")


LEADING_ARTICLE = re.compile(r"^(?:(?:les?|la)\s+|l')")


def spelling_key(name):
    compact = re.sub(r"[^a-z0-9]", "", LEADING_ARTICLE.sub("", normalize(name).replace("’", "'")))
    return re.sub(r"(.)\1+", r"\1", compact).removesuffix("s")


def arrondissement_name(title):
    return re.sub(r"\s*\(arrondissement de l'état civil\)\s*", "", title).strip()


def _leading_name(text):
    words = text.split()
    taken = []
    for index, word in enumerate(words):
        bare = word.strip("(),;.")
        if not bare:
            break
        if bare[0].isupper():
            taken.append(bare)
        elif bare.lower() in LEADING_ARTICLES and index == 0:
            taken.append(bare)
        elif bare.lower() in CONNECTORS and taken:
            taken.append(bare)
        else:
            break
        if word != bare and word.endswith((",", ";", ".", "(")):
            break
    while taken and not taken[-1][0].isupper():
        taken.pop()
    name = " ".join(taken)
    return name, text[len(" ".join(words[:len(name.split())])):].strip(" ,;.") if name else text


def _split_items(listing):
    items = []
    for chunk in re.split(r"[;,]|\n", listing):
        chunk = chunk.strip(" .")
        if chunk:
            items.extend(part.strip() for part in re.split(r"\s+et\s+(?=[A-ZÉ])", chunk))
    return items


def _localities_from_listing(listing, context):
    localities = []
    for item in _split_items(listing):
        name, qualifier = _leading_name(item)
        if name:
            localities.append({"name": name, "qualifier": " ".join(filter(None, [context, qualifier]))})
        elif localities:
            localities[-1]["qualifier"] = " ".join(filter(None, [localities[-1]["qualifier"], item]))
    return localities


TRAILING_ARTICLE = re.compile(r"^(?P<base>[^(]+?)\s*\((?P<article>L'|L’|La|Le|Les|la|le|les|l')\)\s*(?P<rest>.*)$")


def split_official_locality(text):
    match = TRAILING_ARTICLE.match(text)
    if match:
        article = match["article"].capitalize()
        name = f"{article}{match['base']}" if article.endswith(("'", "’")) else f"{article} {match['base']}"
        rest = match["rest"]
    else:
        name, _, rest = text.partition(" (")
        rest = f"({rest}" if rest else ""
    return name.strip(), rest.strip()


def corrected_entries(table, corrections):
    for entry in table:
        correction = dict(corrections.get(entry["locality"], {}))
        hidden = correction.pop("followedBy", None)
        yield {**entry, **correction}
        if hidden:
            yield hidden


CHANGE_DATE = re.compile(r"\s*\((?:dès\s*)?(?:(\d{2})[. ]{0,2}(\d{2})[. ]{0,2})?(\d{4})\)")


def arrondissement_history(periods):
    history = []
    for year in ("1876", "1912", "1928", "1960"):
        for index, part in enumerate((periods.get(year) or "").split(">")):
            date = CHANGE_DATE.search(part)
            since = ".".join(group for group in date.groups() if group) if date else None
            name = CHANGE_DATE.sub("", part).strip()
            if name and (not history or history[-1][0] != name):
                history.append((name, since or (year if index == 0 else "")))
    return history


LOW, HIGH = float("-inf"), float("inf")
PERIOD_RANGE = (
    r"(?:(?:en|de)\s+)?(?P<first>\d{4})(?:/\d{4})?\s*-\s*(?P<last>\d{4})(?!\d)"
    r"|de\s+(?P<start>\d{4})\s+à\s+(?P<end>\d{4})(?!\d)"
    r"|(?:dès|en)\s*(?P<since>\d{4})(?:/\d{4})?(?!\d)"
    r"|jusqu['’]en\s*(?P<until>\d{4})(?!\d)"
)
FIRST_RANGE = re.compile(rf"\s*(?:{PERIOD_RANGE})")
NEXT_RANGE = re.compile(rf"\s*,?\s*(?:et\s+)?(?:{PERIOD_RANGE})")
OPENING = re.compile(r"\s*\(\s*")
CLOSING = re.compile(r"\s*\)")
LINK_END = re.compile(r"\s*(?:$|[;,.)])|\s+(?:puis|sauf)\b|\s+et\s*(?=[^\W\d])(?!\S*\d)")
LINK_REFERENCE = re.compile(r"\[\s*(?P<number>\d+(?: bis| ter)?)\s*\]")
EXCEPTION_BEFORE = re.compile(r"\bsauf\s+(?P<rest>[^\[\];,]*)$")
DETACHED_BEFORE = re.compile(r"détach\w*\s+(?:de|d['’]|du)\b[^\[\];,(]*$")
THEN_BETWEEN = re.compile(r"\s*,?\s*puis\b[^\d;\[\]]*")
WRITTEN_NAME = re.compile(r"(?P<name>[A-ZÀ-Ý][\w'’-]*)\s*(?:\([^()]*\)\s*)?$")
NOTE_CONTEXT = re.compile(r"^(?:annexe|adjonction)\s*")
OWN_REGISTERS = re.compile(r"(?:chacun\s+)?avec\s+(?:ses\s+)?registres?\s+(?:propres|distincts|séparés|autonomes)\s*")
SENTENCE_END = re.compile(r"\.\s+(?=[A-ZÀ-Ý])")


def _bounds(period):
    since, until = period
    return (LOW if since is None else since, HIGH if until is None else until)


def _period(low, high):
    return (None if low == LOW else low, None if high == HIGH else high)


def merged_periods(periods):
    spans = []
    for low, high in sorted(_bounds(period) for period in periods):
        if spans and low <= spans[-1][1] + 1:
            spans[-1] = (spans[-1][0], max(spans[-1][1], high))
        else:
            spans.append((low, high))
    return [_period(*span) for span in spans]


def bounded(periods):
    merged = merged_periods(periods or [])
    return merged if merged and merged != [(None, None)] else None


def union_periods(first, second):
    return None if first is None or second is None else bounded(first + second)


def _without_interior(periods, removed):
    # Boundary years stay: an act of the year a link changed can be in either parish's register.
    low_cut, high_cut = _bounds(removed)
    if high_cut <= low_cut:
        return periods
    kept = []
    for low, high in map(_bounds, periods):
        if low <= min(high, low_cut) and low_cut != LOW:
            kept.append((low, min(high, low_cut)))
        if max(low, high_cut) <= high and high_cut != HIGH:
            kept.append((max(low, high_cut), high))
    return [_period(*span) for span in kept]


def _gaps(periods):
    merged = merged_periods(periods)
    return [(merged[index][1], merged[index + 1][0]) for index in range(len(merged) - 1)]


def _range_of(match):
    if match["first"]:
        return int(match["first"]), int(match["last"])
    if match["start"]:
        return int(match["start"]), int(match["end"])
    if match["since"]:
        return int(match["since"]), None
    return None, int(match["until"])


def _ranges_at(text, position):
    ranges, end = [], position
    while match := (NEXT_RANGE if ranges else FIRST_RANGE).match(text, end):
        ranges.append(_range_of(match))
        end = match.end()
    return ranges, end


def _period_after(text, position):
    opening = OPENING.match(text, position)
    if opening:
        ranges, end = _ranges_at(text, opening.end())
        closing = CLOSING.match(text, end)
        return (ranges, closing.end()) if ranges and closing else ([], position)
    return _ranges_at(text, position)


def _dated_link(description, references, index):
    reference = references[index]
    ranges, end = _period_after(description, reference.end())
    if ranges and LINK_END.match(description, end):
        item_start = references[index - 1].end() if index else 0
        if DETACHED_BEFORE.search(description, item_start, reference.start()):
            return ([(None, ranges[0][0])] if ranges == [(ranges[0][0], None)] else []), end
        return ranges, end
    if ranges:
        return [], reference.end()
    exception = EXCEPTION_BEFORE.search(description, references[index - 1].end() if index else 0, reference.start())
    if exception:
        ranges, stop = _period_after(exception["rest"], 0)
        if ranges and not re.search(r"\d", exception["rest"][stop:]):
            return ranges, reference.end()
    return [], reference.end()


def _same_clause(description, references, index):
    following = index + 1
    if following < len(references) and ";" not in description[references[index].end():references[following].start()]:
        return following
    return None


def _until_next_link(description, references, links, index):
    following = _same_clause(description, references, index)
    if following is None or not THEN_BETWEEN.fullmatch(description, references[index].end(), references[following].start()):
        return []
    later = links[following][0]
    if not later or later[0][0] is None:
        return []
    resumed = [(later[-1][1], None)] if later[-1][1] is not None and following == len(references) - 1 else []
    return [(None, later[0][0])] + _gaps(later) + resumed


def _folded(text):
    chars, origins = [], []
    for position, char in enumerate(text):
        for folded in normalize(char.replace("’", "'")):
            chars.append(folded)
            origins.append(position)
    return "".join(chars), origins


def _mentions(text, start, names):
    folded, origins = _folded(text)
    ends = set()
    for name in names:
        key = normalize(ARTICLE_PREFIX.sub("", name).replace("’", "'"))
        for match in re.finditer(rf"(?<![^\W\d_]){re.escape(key)}(?![^\W\d_])", folded):
            if key and origins[match.start()] >= start:
                ends.add(origins[match.end() - 1] + 1)
    return sorted(ends)


def _with_returns(description, references, index, ranges, end, parish_names):
    written = WRITTEN_NAME.search(description, references[index - 1].end() if index else 0, references[index].start())
    names = [*_spellings(parish_names.get(references[index]["number"], [])), *([written["name"]] if written else [])]
    for mention in _mentions(description, end, names):
        periods, stop = _period_after(description, mention)
        if periods and LINK_END.match(description, stop):
            ranges = ranges + periods
        elif merged_periods(ranges)[-1][1] is not None:
            return None
    return bounded(ranges)


def parish_period(description, number, parish_names=None):
    references = list(LINK_REFERENCE.finditer(description))
    cited = [index for index, reference in enumerate(references) if reference["number"] == number]
    if len(cited) != 1:
        return None
    index = cited[0]
    links = [_dated_link(description, references, position) for position in range(len(references))]
    ranges, end = links[index]
    following = _same_clause(description, references, index)
    if ranges and ranges[-1][1] is None and following is not None:
        for later in links[following][0]:
            ranges = _without_interior(ranges, later)
    if not ranges:
        ranges = _until_next_link(description, references, links, index)
    return _with_returns(description, references, index, ranges, end, parish_names or {}) if ranges else None


def note_periods(qualifier):
    rest = NOTE_CONTEXT.sub("", qualifier, count=1)
    ranges, end = _period_after(rest, 0)
    if not ranges:
        return None
    trailing = SENTENCE_END.split(rest[end:])[0].strip(" ,;.")
    registers = OWN_REGISTERS.match(trailing)
    if registers:
        kept, stop = _period_after(trailing, registers.end())
        ranges += kept
        trailing = trailing[stop if kept else registers.end():]
    return None if re.search(r"\d", trailing) else bounded(ranges)


def localities_from_note(note):
    localities = []
    lines = [line.strip() for line in (note or "").splitlines() if line.strip()]
    index = 0
    while index < len(lines):
        line = lines[index]
        header = re.match(r"(?P<head>(?:Comprend|Annexe|Adjonction)[^:]*):\s*(?P<rest>.*)$", line)
        index += 1
        if not header:
            continue
        context = "annexe" if header["head"].startswith("Annexe") else ""
        if header["head"].startswith("Adjonction"):
            context = "adjonction"
        if header["rest"]:
            localities.extend(_localities_from_listing(header["rest"], context))
            continue
        while index < len(lines) and not lines[index].endswith(":"):
            localities.extend(_localities_from_listing(lines[index], context))
            index += 1
    return localities


PARISH_REFERENCE = re.compile(r"\[(?P<number>\d+(?: bis| ter)?)\]")
NAME_BOUNDARY = re.compile(r"[\[\]();:,|]|\.(?=\s)")
ARTICLE_PREFIX = re.compile(r"^(?:(?:les?|la)\s+|l')", re.IGNORECASE)
CONTRACTED_ARTICLE = re.compile(r"(?<!\S)(?:du|des|au|aux)\s+$", re.IGNORECASE)
ARTICLE_PARENTHESIS = re.compile(r"^\s*\((?:l'|l’|la|le|les)\)$", re.IGNORECASE)
ELISION = re.compile(r"[dl]['’]", re.IGNORECASE)
CATHOLIC_SUFFIX = " (catholique)"
CAPITAL_ACCENTS = {"\u0300", "\u0301", "\u0302"}
# Lowest similarity between a damaged name and the parish name, e.g. « Vieh » for « Vich ».
DAMAGE_RATIO = 0.75
UNRELATED, DAMAGED, SHORT_FORM, SAME = range(4)


class NameMatch(NamedTuple):
    level: int
    head: str
    written: str
    spelling: str
    tail: str


def _typographic(name):
    # The ACV titles drop the accent on capitals and write « Oe » for « Œ ».
    decomposed = unicodedata.normalize("NFD", name.replace("Œ", "Oe").replace("œ", "oe").replace("’", "'"))
    kept = "".join(char for index, char in enumerate(decomposed) if not (char in CAPITAL_ACCENTS and decomposed[index - 1].isupper()))
    return ARTICLE_PREFIX.sub(lambda article: article[0].lower(), unicodedata.normalize("NFC", kept))


def _letters(name):
    return re.sub(r"[^a-z0-9]", "", normalize(name.replace("Œ", "Oe").replace("œ", "oe")))


def _resemblance(written, spelling):
    written_form, spelling_form = _typographic(written), _typographic(spelling)
    if written_form == spelling_form:
        return SAME, 1.0
    if spelling_form.startswith((f"{written_form} ", f"{written_form}-")):
        return SHORT_FORM, 1.0
    ratio = SequenceMatcher(None, _letters(written), _letters(spelling)).ratio()
    return DAMAGED if ratio >= DAMAGE_RATIO else UNRELATED, ratio


def _boundary(region):
    return max((match.end() for match in NAME_BOUNDARY.finditer(region)), default=0)


def _name_starts(region):
    after = _boundary(region)
    for index in range(after, len(region)):
        glued_to = re.search(r"\S*$", region[after:index])[0]
        gluable = glued_to.isalpha() and glued_to.islower() or ELISION.fullmatch(glued_to)
        if not region[index].isspace() and (not glued_to or region[index].isupper() and gluable):
            yield index


def _variants(spelling, head, tail):
    if CONTRACTED_ARTICLE.search(head) or ARTICLE_PARENTHESIS.match(tail):
        return [spelling, ARTICLE_PREFIX.sub("", spelling)]
    return [spelling]


def _closest_name(region, spellings, tail=""):
    scored = [(*_resemblance(region[start:], variant), -start, variant)
              for start in _name_starts(region) for spelling in spellings for variant in _variants(spelling, region[:start], tail)]
    level, _, negative_start, spelling = max(scored, default=(UNRELATED, 0.0, -len(region), ""))
    return NameMatch(level, region[:-negative_start], region[-negative_start:], spelling, tail)


def _match_name(segment, spellings):
    region = segment.rstrip()
    if region.endswith(")") and "(" in region:
        inside = _closest_name(region[:-1], spellings, ")")
        if inside.level >= SHORT_FORM:
            return inside
        name_region = region[:region.rindex("(")].rstrip()
        return _closest_name(name_region, spellings, region[len(name_region):])
    return _closest_name(region, spellings)


def _repaired(match):
    head, written = match.head, match.written
    if head[-1:].isalpha():
        head += "'" if re.search(r"(?<!\S)[dl]$", head, re.IGNORECASE) else " "
    if match.level == DAMAGED:
        first = written[0] if _typographic(written[0]) == match.spelling[0] else match.spelling[0]
        written = first + match.spelling[1:]
    return f"{head}{written}{match.tail} "


def _references(description):
    position = 0
    for reference in PARISH_REFERENCE.finditer(description):
        yield description[position:reference.start()], reference
        position = reference.end()


def _spellings(names):
    return [name.removesuffix(CATHOLIC_SUFFIX) for name in names]


def repair_parish_names(description, parish_names):
    pieces, rest = [], description
    for segment, reference in _references(description):
        match = _match_name(segment, _spellings(parish_names.get(reference["number"], [])))
        pieces += [segment if match.level == UNRELATED else _repaired(match), reference[0]]
        rest = description[reference.end():]
    return "".join(pieces) + rest


def parish_name_mismatches(description, parish_names, village_names):
    mismatches = []
    for segment, reference in _references(description):
        number = reference["number"]
        if _match_name(segment, _spellings(parish_names.get(number, []))).level >= DAMAGED:
            continue
        if _match_name(segment, village_names.get(number, [])).level >= SHORT_FORM:
            continue
        region = segment.rstrip()
        mismatches.append((number, region[_boundary(region):].strip()))
    return mismatches
