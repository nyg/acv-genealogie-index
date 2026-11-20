"""Builds the indexing progress page, docs/avancement.html: parishes and arrondissements by district, registers by fonds, PDF pages."""

import unicodedata
from datetime import datetime
from html import escape
from urllib.parse import quote

from districts import short_district_name

DIGITIZED_FONDS = ("Eb", "Ed", "SB 267")
FONDS_ORDER = ["Eb", "Ed", "SB 267", "SB 269", "SB 268", "Ec", "SB 23", "SB 115", "SB 324"]
FONDS_ERA = {
    "Eb": "Registres paroissiaux", "Ed": "État civil cantonal", "SB 267": "État civil fédéral",
    "SB 269": "Bourgeois, hors arrondissement", "SB 268": "Promesses de mariage",
    "Ec": "Pièces justificatives", "SB 23": "Pièces justificatives", "SB 115": "Pièces justificatives", "SB 324": "Pièces justificatives",
}
FONDS_CLASS = {"Eb": "Eb", "Ed": "Ed", "SB 267": "SB", "SB 268": "SB268", "SB 269": "SB269"}
STATUS_LABELS = {"releve": "pages du PDF relevées", "indexe": "registres indexés", "attente": "pas encore indexé"}
KIND_NAMES = {"paroisse": ("paroisse", "paroisses"), "arrondissement": ("arrondissement", "arrondissements")}


def sort_key(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().lower()


def plural(count, singular, plural_form=None):
    return f"{count} {singular if count == 1 else plural_form or singular + 's'}"


def pdf_pages(units):
    with_pdf = [unit for unit in units if unit["pdf"] and unit["fonds"] in DIGITIZED_FONDS]
    exact = sum(any(not part.get("approx") for part in unit.get("pdfParts", [])) for unit in with_pdf)
    approx = sum(bool(unit.get("pdfParts")) and all(part.get("approx") for part in unit["pdfParts"]) for unit in with_pdf)
    return {"total": len(with_pdf), "exact": exact, "approx": approx}


def place_status(indexed, pages):
    if indexed and pages["total"] and pages["exact"] == pages["total"]:
        return "releve"
    return "indexe" if indexed else "attente"


def place_progress(place, units, district):
    pages = pdf_pages(units)
    indexed = any(series["scraped"] and series["fonds"] in DIGITIZED_FONDS for series in place["series"])
    return {
        "id": place["id"], "kind": place["kind"], "name": place["name"], "district": district,
        "series": [(series["fonds"], series["cote"], series["scraped"]) for series in place["series"]],
        "units": len(units), "pages": pages, "status": place_status(indexed, pages),
    }


def progress_entries(places, units, districts):
    units_by_place = {}
    for unit in units:
        units_by_place.setdefault(unit["place"], []).append(unit)
    return [place_progress(place, units_by_place.get(place["id"], []), districts[place["id"]]) for place in places]


def percent(count, total):
    return f"{100 * count / total:.2f}%" if total else "0%"


def whole_percent(count, total):
    return f"{round(100 * count / total) if total else 0} %"


def stacked_bar(segments, total, label, size=""):
    spans = "".join(f'<span class="{css}" style="width:{percent(count, total)}"></span>' for css, count in segments if count)
    return f'<div class="bar{f" {size}" if size else ""}" role="img" aria-label="{escape(label)}">{spans}</div>'


def status_bar(entries, label, size=""):
    counts = {status: sum(entry["status"] == status for entry in entries) for status in STATUS_LABELS}
    return stacked_bar([("releve", counts["releve"]), ("indexe", counts["indexe"])], len(entries), label, size)


def pages_bar(pages, size="thin"):
    label = f"Pages du PDF : {pages['exact']} registres relevés, {pages['approx']} déduits, sur {pages['total']}"
    return stacked_bar([("releve", pages["exact"]), ("approx", pages["approx"])], pages["total"], label, size)


def indexed_count(entries):
    return sum(entry["status"] != "attente" for entry in entries)


def place_link(entry, css=""):
    title = f"{entry['name']} : {STATUS_LABELS[entry['status']]}"
    return (f'<a class="{css}" href="./#lieu={quote(entry["name"])}" title="{escape(title)}">{escape(entry["name"])}'
            f'<span class="sr-only"> ({STATUS_LABELS[entry["status"]]})</span></a>')


def pills(entries):
    items = "".join(f'<li>{place_link(entry, f"pill {entry["status"]}")}</li>' for entry in sorted(entries, key=lambda entry: sort_key(entry["name"])))
    return f'<ul class="pills">{items}</ul>'


def series_chips(entry):
    return "".join(
        f'<span class="chip {FONDS_CLASS.get(fonds, "PJ")}{"" if scraped else " off"}" title="{escape(cote)}{"" if scraped else " : non indexé"}">{escape(fonds)}</span>'
        for fonds, cote, scraped in sorted(entry["series"], key=lambda series: FONDS_ORDER.index(series[0]))
    )


def pages_cell(pages):
    if not pages["total"]:
        return '<span class="muted">sans PDF</span>'
    approx = f' · <span title="pages déduites">≈ {pages["approx"]}</span>' if pages["approx"] else ""
    return f'{pages_bar(pages)}<span class="figure">{pages["exact"]} / {pages["total"]}{approx}</span>'


def detail_rows(entries, kind):
    indexed = sorted((entry for entry in entries if entry["kind"] == kind and entry["status"] != "attente"), key=lambda entry: sort_key(entry["name"]))
    if not indexed:
        return ""
    rows = "".join(
        f'<tr><th scope="row">{place_link(entry)}</th><td><span class="chips">{series_chips(entry)}</span></td>'
        f'<td class="number">{entry["units"]}</td><td class="pages-cell">{pages_cell(entry["pages"])}</td></tr>'
        for entry in indexed
    )
    return f'<tbody><tr class="group"><th colspan="4" scope="rowgroup">{KIND_NAMES[kind][1].capitalize()}</th></tr>{rows}</tbody>'


def district_id(district):
    return "district-" + "-".join(filter(None, "".join(char if char.isalnum() else " " for char in sort_key(short_district_name(district))).split()))


def kind_summary(entries, kind):
    of_kind = [entry for entry in entries if entry["kind"] == kind]
    singular, plural_form = KIND_NAMES[kind]
    return f"{indexed_count(of_kind)} {singular if indexed_count(of_kind) <= 1 else plural_form} sur {len(of_kind)}"


def district_card(district, entries):
    name = short_district_name(district)
    parishes = [entry for entry in entries if entry["kind"] == "paroisse"]
    arrondissements = [entry for entry in entries if entry["kind"] == "arrondissement"]
    tables = detail_rows(entries, "paroisse") + detail_rows(entries, "arrondissement")
    details = (f'<details><summary>Détail des lieux indexés</summary><div class="table-scroll"><table>'
               f'<thead><tr><th scope="col">Lieu</th><th scope="col">Séries</th><th scope="col" class="number">Registres</th><th scope="col">Pages du PDF relevées</th></tr></thead>'
               f'{tables}</table></div></details>') if tables else '<p class="muted">Aucun lieu indexé pour l\'instant.</p>'
    label = f"{name} : {indexed_count(entries)} lieux indexés sur {len(entries)}"
    return f'''<section class="district" id="{district_id(district)}" aria-labelledby="{district_id(district)}-title">
      <header><h3 id="{district_id(district)}-title">{escape(district)}</h3><p class="district-count"><strong>{indexed_count(entries)}</strong> / {len(entries)} lieux</p></header>
      {status_bar(entries, label)}
      <div class="kind"><h4>Paroisses <span>{kind_summary(entries, "paroisse")}</span></h4>{pills(parishes)}</div>
      <div class="kind"><h4>Arrondissements d'état civil <span>{kind_summary(entries, "arrondissement")}</span></h4>{pills(arrondissements)}</div>
      {details}
    </section>'''


def by_district(entries):
    districts = {}
    for entry in entries:
        districts.setdefault(entry["district"], []).append(entry)
    return sorted(districts.items(), key=lambda item: sort_key(short_district_name(item[0])))


def overview_row(district, entries):
    name = short_district_name(district)
    return (f'<li><a href="#{district_id(district)}">{escape(name)}</a>'
            f'{status_bar(entries, f"{name} : {indexed_count(entries)} lieux indexés sur {len(entries)}")}'
            f'<span class="figure">{indexed_count(entries)} / {len(entries)}</span></li>')


def stat_card(title, entries, noun, feminine):
    ending = "e" if feminine else ""
    releve = sum(entry["status"] == "releve" for entry in entries)
    partial = sum(entry["status"] == "indexe" and entry["pages"]["exact"] > 0 for entry in entries)
    indexed = indexed_count(entries)
    complete = str(releve) if releve else "aucun" + ending
    detail = f"dont {complete} avec toutes les pages du PDF relevées" + (f" et {partial} en partie" if partial else "")
    label = f"{indexed} {noun}s indexé{ending}s sur {len(entries)}, {detail}"
    return f'''<article class="stat">
      <h3>{title}</h3>
      <p class="big"><strong>{indexed}</strong> sur {len(entries)} <span>{whole_percent(indexed, len(entries))}</span></p>
      {status_bar(entries, label, "thick")}
      <p class="small">{plural(indexed, f"{noun} indexé{ending}", f"{noun}s indexé{ending}s")}, {detail}</p>
    </article>'''


def pages_card(pages):
    none = pages["total"] - pages["exact"] - pages["approx"]
    return f'''<article class="stat">
      <h3>Pages du PDF</h3>
      <p class="big"><strong>{pages["exact"]}</strong> sur {pages["total"]} <span>{whole_percent(pages["exact"], pages["total"])}</span></p>
      {pages_bar(pages, "thick")}
      <p class="small">registres indexés avec PDF : {pages["exact"]} relevés, {pages["approx"]} déduits (≈), {none} ouverts à la première page</p>
    </article>'''


def fonds_row(fonds, places, units):
    fonds_units = [unit for unit in units if unit["fonds"] == fonds]
    years = sorted(date[:4] for unit in fonds_units for date in (unit["start"], unit["end"]) if date)
    fonds_series = [series for place in places for series in place["series"] if series["fonds"] == fonds]
    digitized = fonds in DIGITIZED_FONDS
    indexed = sum(series["scraped"] for series in fonds_series)
    series_cell = (f'<progress max="{len(fonds_series)}" value="{indexed}" aria-label="{fonds} : {indexed} séries indexées sur {len(fonds_series)}"></progress>'
                   f'<span class="figure">{indexed} / {len(fonds_series)}</span>') if digitized else f'<span class="figure">{len(fonds_series) or "—"}</span>'
    return f'''<tr>
      <th scope="row"><span class="chip {FONDS_CLASS.get(fonds, "PJ")}">{escape(fonds)}</span></th>
      <td>{escape(FONDS_ERA[fonds])}<small>{years[0]}-{years[-1]} · {"davel-vd.ch, avec PDF" if digitized else "davel.vd.ch, sans PDF"}</small></td>
      <td class="series-cell">{series_cell}</td>
      <td class="number">{len(fonds_units)}</td>
      <td class="pages-cell">{pages_cell(pdf_pages(fonds_units)) if digitized else '<span class="muted">sans PDF</span>'}</td>
    </tr>'''


def legend():
    return ('<ul class="legend" aria-label="Légende">'
            '<li><span class="swatch releve"></span>Pages du PDF relevées : la page citée par le répertoire mène à la page du PDF</li>'
            '<li><span class="swatch approx"></span>Pages du PDF déduites (≈), état civil fédéral</li>'
            '<li><span class="swatch indexe"></span>Registres indexés : actes, dates et pages, PDF ouvert à sa première page</li>'
            '<li><span class="swatch attente"></span>Pas encore indexé : liste des séries et lien vers l\'inventaire</li></ul>')


def render_progress(places, units, districts, generated_at):
    entries = progress_entries(places, units, districts)
    groups = by_district(entries)
    parishes = [entry for entry in entries if entry["kind"] == "paroisse"]
    arrondissements = [entry for entry in entries if entry["kind"] == "arrondissement"]
    fonds = sorted({unit["fonds"] for unit in units}, key=FONDS_ORDER.index)
    date = datetime.fromisoformat(generated_at).strftime("%d.%m.%Y")
    return f'''<section class="intro">
    <h2 class="title">Avancement de l'index</h2>
    <p class="lede">Les registres des lieux indexés sont détaillés : actes, dates, pages. Les autres lieux apparaissent dans la recherche avec la liste de leurs séries et un lien vers l'inventaire. Les pages du PDF se relèvent ensuite registre par registre.</p>
    <p class="muted">Inventaires extraits le {date}.</p>
  </section>

  <section class="stats" aria-label="En bref">
    {stat_card("Paroisses", parishes, "paroisse", feminine=True)}
    {stat_card("Arrondissements d'état civil", arrondissements, "arrondissement", feminine=False)}
    {pages_card(pdf_pages(units))}
  </section>

  <section class="block" aria-labelledby="districts-title">
    <h2 id="districts-title">Par district</h2>
    <p class="muted">Districts de 1803 à 2007, ceux de l'époque des registres. Une paroisse ou un arrondissement compte dans le district de la commune où il a son siège.</p>
    {legend()}
    <ol class="overview">{"".join(overview_row(district, district_entries) for district, district_entries in groups)}</ol>
  </section>

  <div class="districts">
    {"".join(district_card(district, district_entries) for district, district_entries in groups)}
  </div>

  <section class="block" aria-labelledby="fonds-title">
    <h2 id="fonds-title">Par fonds</h2>
    <div class="table-scroll"><table class="fonds">
      <thead><tr><th scope="col">Fonds</th><th scope="col">Contenu</th><th scope="col">Séries indexées</th><th scope="col" class="number">Registres</th><th scope="col">Pages du PDF relevées</th></tr></thead>
      <tbody>{"".join(fonds_row(name, places, units) for name in fonds)}</tbody>
    </table></div>
  </section>

  <section class="block notes" aria-labelledby="pages-title">
    <h2 id="pages-title">Pages du PDF</h2>
    <p>Pour un registre relevé, la page du registre citée par le répertoire donne la page du PDF à ouvrir. Ailleurs, le PDF s'ouvre à sa première page.</p>
    <p><strong>État civil fédéral (SB 267)</strong> : sans relevé, la page du PDF est déduite de la page du registre (« ≈ », page + 3), sans avoir été vérifiée ; vers la fin du registre, elle peut être 1 à 4 pages plus loin. Les registres qui dépassent 1899 (naissances), 1929 (mariages) ou 1959 (décès) ne sont publiés que jusqu'à cette année-là, sans répertoire : pas de page déduite.</p>
    <p class="viewer-missing"><strong>Aperçu</strong> : les PDF pèsent souvent plusieurs centaines de Mo. Avec le <a href="https://github.com/nyg/acv-genealogie-index#installer-le-script" target="_blank" rel="noopener">script d'aperçu</a> (Tampermonkey, dans Chrome ou Firefox), les liens « PDF p. » n'en chargent que la page demandée.</p>
    <p class="viewer-installed"><strong>Aperçu</strong> : le script d'aperçu est installé : les liens « PDF p. » n'affichent que la page demandée, sans télécharger le PDF entier.</p>
  </section>'''
