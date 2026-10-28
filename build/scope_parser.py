import calendar
import re
import unicodedata
from dataclasses import dataclass, field

MONTHS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
}

DATE_ATOM = re.compile(
    r"(?P<iso>(?P<iy>\d{4})-(?P<im>\d{2})-(?P<id>\d{2}))"
    r"|(?P<fday>\d{1,2})(?:er)?\s+(?P<fmonth>[a-zA-Zéû]+)\s+(?P<fyear>\d{4})"
    r"|(?P<year>\d{4})(?:\s+(?P<month>[a-zA-Zéû]+))?(?:\s+(?P<day>\d{1,2})(?:er)?\b)?"
)

SEGMENT = re.compile(
    r"(?P<label>[A-Za-zÀ-ÿ'’][A-Za-zÀ-ÿ'’ ]*?)\s*"
    r"(?P<qualifiers>(?:\([^()\d]*\)\s*)*)"
    r"\((?P<dates>[^()]*\d{4}[^()]*)\)"
)

PAGES_BEFORE_DATES = re.compile(r"^(?P<label>[^:()]+):\s*(?P<pages>pages?\s[^()]*?)\s*(?P<dates>\([^()]*\d{4}[^()]*\))", re.IGNORECASE)

ANNOUNCEMENT_PHRASE = re.compile(r"(annonces?|promesses?|publications?) de mariages?( celebres ailleurs)?")

KIND_PATTERNS = [
    ("naissance", re.compile(r"\bbapt|\bnaiss")),
    ("annonce", ANNOUNCEMENT_PHRASE),
    ("deces", re.compile(r"deces|mortuaire|sepulture|enterrement")),
    ("catechumenes", re.compile(r"catechum")),
    ("reconnaissance", re.compile(r"reconnaissance")),
    ("legitimation", re.compile(r"legitimation")),
]


@dataclass
class Segment:
    label: str
    kinds: list
    start: str | None
    end: str | None
    dates_text: str
    pages: str = ""
    head_to_tail: bool = False
    foreign: bool = False
    section: str = ""
    qualifiers: list = field(default_factory=list)


def normalize(text):
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def classify(label):
    normalized = normalize(label)
    kinds = [kind for kind, pattern in KIND_PATTERNS if pattern.search(normalized)]
    if "mariage" in ANNOUNCEMENT_PHRASE.sub("", normalized):
        kinds.append("mariage")
    return kinds


def _atom_bounds(atom):
    if atom["iso"]:
        iso = atom["iso"]
        return iso, iso
    year = int(atom["year"] or atom["fyear"])
    month = MONTHS.get(normalize(atom["month"] or atom["fmonth"] or ""))
    raw_day = atom["day"] or atom["fday"]
    day = int(raw_day) if raw_day and month else None
    if not month:
        return f"{year:04d}-01-01", f"{year:04d}-12-31"
    last_day = calendar.monthrange(year, month)[1]
    if not day or day > last_day:
        return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"
    return (f"{year:04d}-{month:02d}-{day:02d}",) * 2


def parse_date_range(text):
    principal = text.split(",")[0]
    atoms = list(DATE_ATOM.finditer(principal))
    if not atoms:
        return None, None
    start, _ = _atom_bounds(atoms[0])
    _, end = _atom_bounds(atoms[-1])
    return start, end


def _clean_pages(text):
    text = text.split(";")[0].strip(" ,.")
    return text if re.search(r"\d|\b[IVXLC]+\b", text) else ""


def _clean_label(raw_label):
    return re.sub(r"^(et|-)\s+", "", raw_label.strip())


def _segments_in_line(line, section):
    line = PAGES_BEFORE_DATES.sub(r"\g<label> \g<dates>, \g<pages>", line)
    matches =[match for match in SEGMENT.finditer(line) if classify(_clean_label(match["label"]))]
    segments = []
    for index, match in enumerate(matches):
        label = _clean_label(match["label"])
        qualifiers = re.findall(r"\(([^()]*)\)", match["qualifiers"])
        following = line[match.end(): matches[index + 1].start() if index + 1 < len(matches) else len(line)]
        pages = _clean_pages(following)
        start, end = parse_date_range(match["dates"])
        described = normalize(f"{label} {' '.join(qualifiers)}")
        segments.append(Segment(
            label=label,
            kinds=classify(label),
            start=start,
            end=end,
            dates_text=match["dates"].strip(),
            pages=pages,
            head_to_tail="tete-beche" in described or "tete-beche" in normalize(pages),
            foreign="forain" in described or "ailleurs" in described,
            section=section,
            qualifiers=qualifiers,
        ))
    trailing_pages = next((segment.pages for segment in reversed(segments) if segment.pages), "")
    for segment in segments:
        segment.pages = segment.pages or trailing_pages
    return segments


def parse_scope_content(text):
    segments = []
    section = ""
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.endswith(":") and not SEGMENT.search(line):
            section = line.rstrip(" :")
            continue
        segments.extend(_segments_in_line(line, section))
    return segments
