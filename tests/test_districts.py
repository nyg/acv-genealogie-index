import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from districts import place_districts, short_district_name  # noqa: E402

COMMUNES = {"Dompierre (VD)": "District de Moudon", "Forel (Lavaux)": "District de Lavaux", "Le Chenit": "District de la Vallée", "Ollon": "District d'Aigle"}


def place(place_id, name):
    return {"id": place_id, "name": name}


def test_a_place_named_after_its_commune_takes_the_commune_district():
    # Given
    places = [place("paroisse-47", "Dompierre"), place("arrondissement-40", "Forel/Lavaux"), place("paroisse-92", "Ollon")]

    # When
    districts = place_districts(places, COMMUNES, {})

    # Then
    assert districts == {"paroisse-47": "District de Moudon", "arrondissement-40": "District de Lavaux", "paroisse-92": "District d'Aigle"}


def test_a_place_named_after_a_village_takes_the_district_of_its_seat_commune():
    # Given
    places = [place("paroisse-126", "Le Sentier"), place("arrondissement-49", "Huémoz puis Villars-sur-Ollon")]
    seats = {"paroisse-126": "Le Chenit", "arrondissement-49": "Ollon"}

    # When
    districts = place_districts(places, COMMUNES, seats)

    # Then
    assert districts == {"paroisse-126": "District de la Vallée", "arrondissement-49": "District d'Aigle"}


def test_a_place_without_a_known_commune_stops_the_build():
    # Given
    places = [place("paroisse-54", "L'Etivaz")]

    # When / Then
    with pytest.raises(ValueError, match="paroisse-54"):
        place_districts(places, COMMUNES, {})


@pytest.mark.parametrize(("district", "name"), [
    ("District d'Aigle", "Aigle"), ("District de Morges", "Morges"), ("District du Pays-d'Enhaut", "Pays-d'Enhaut"), ("District de la Vallée", "La Vallée"),
])
def test_a_district_is_shown_without_its_prefix(district, name):
    # When
    short = short_district_name(district)

    # Then
    assert short == name
