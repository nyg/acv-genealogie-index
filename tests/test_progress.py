import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from progress import progress_entries, render_progress  # noqa: E402

EXACT = [{"approx": False}]
APPROX = [{"approx": True}]


def series(fonds, scraped):
    return {"fonds": fonds, "cote": f"{fonds} 1", "scraped": scraped}


def unit(place_id, fonds, pdf="x.pdf", parts=None, start="1800-01-01", end="1810-12-31"):
    return {"place": place_id, "fonds": fonds, "pdf": pdf, "start": start, "end": end, **({"pdfParts": parts} if parts else {})}


def test_a_place_is_mapped_once_every_register_with_a_pdf_has_read_pages():
    # Given
    places = [{"id": "paroisse-15", "kind": "paroisse", "name": "Bex", "series": [series("Eb", True), series("Ed", True)]}]
    units = [unit("paroisse-15", "Eb", parts=EXACT), unit("paroisse-15", "Ed", parts=EXACT), unit("paroisse-15", "Ed", pdf="")]

    # When
    [entry] = progress_entries(places, units, {"paroisse-15": "District d'Aigle"})

    # Then
    assert entry["status"] == "releve"
    assert entry["pages"] == {"total": 2, "exact": 2, "approx": 0}


def test_deduced_pages_leave_a_place_indexed_but_not_mapped():
    # Given
    places = [{"id": "arrondissement-12", "kind": "arrondissement", "name": "Bex", "series": [series("SB 267", True)]}]
    units = [unit("arrondissement-12", "SB 267", parts=EXACT), unit("arrondissement-12", "SB 267", parts=APPROX), unit("arrondissement-12", "SB 267")]

    # When
    [entry] = progress_entries(places, units, {"arrondissement-12": "District d'Aigle"})

    # Then
    assert entry["status"] == "indexe"
    assert entry["pages"] == {"total": 3, "exact": 1, "approx": 1}


def test_a_place_with_only_unscraped_digitized_series_is_not_indexed():
    # Given
    places = [{"id": "paroisse-9", "kind": "paroisse", "name": "Avenches", "series": [series("Eb", False), series("SB 268", True)]}]

    # When
    [entry] = progress_entries(places, [], {"paroisse-9": "District d'Avenches"})

    # Then
    assert entry["status"] == "attente"


def test_the_page_groups_places_by_district_and_links_them_to_the_search():
    # Given
    places = [
        {"id": "paroisse-15", "kind": "paroisse", "name": "Bex", "series": [series("Eb", True)]},
        {"id": "paroisse-9", "kind": "paroisse", "name": "Avenches", "series": [series("Eb", False)]},
    ]
    units = [unit("paroisse-15", "Eb", parts=EXACT)]
    districts = {"paroisse-15": "District d'Aigle", "paroisse-9": "District d'Avenches"}

    # When
    page = render_progress(places, units, districts, "2026-11-20T10:00:00+00:00")

    # Then
    aigle = page[page.index('id="district-aigle"'):page.index('id="district-avenches"')]
    assert 'class="pill releve" href="./#lieu=Bex"' in aigle
    assert "Avenches" not in aigle.split("</header>", 1)[1]
    assert 'class="pill attente" href="./#lieu=Avenches"' in page
    assert "extraits le 20.11.2026" in page
