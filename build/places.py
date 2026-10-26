import re

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
