import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

from parse_correspondence import reference_spellings, respell_locality  # noqa: E402


def test_letter_spaced_names_take_the_official_spelling():
    # Given
    spellings = reference_spellings([{"locality": "Essertines-sur-Yverdon"}, {"locality": "Ollon"}])

    # When
    respelled = [respell_locality(name, spellings) for name in ("E s s er tine s-s ur-Yverdon", "Salaz (Oll on)")]

    # Then
    assert respelled == ["Essertines-sur-Yverdon", "Salaz (Ollon)"]


def test_names_missing_a_hyphen_take_the_official_spelling():
    # Given
    spellings = reference_spellings([{"locality": "Belmont-sur-Lausanne"}])

    # When
    respelled = respell_locality("Belmont-sur Lausanne", spellings)

    # Then
    assert respelled == "Belmont-sur-Lausanne"


def test_a_hamlet_spelled_like_a_commune_keeps_its_name():
    # Given
    spellings = reference_spellings([{"locality": "Grandvaux"}])

    # When
    respelled = respell_locality("Grand Vaux (Vaux-sur-Morges)", spellings)

    # Then
    assert respelled == "Grand Vaux (Vaux-sur-Morges)"


def test_every_correction_matches_a_parish_table_entry():
    # Given
    localities = {entry["locality"] for entry in json.loads((ROOT / "data/raw/vd-ch/communes-paroisses.json").read_text(encoding="utf-8"))}

    # When
    corrections = json.loads((ROOT / "data/manual/communes-paroisses-corrections.json").read_text(encoding="utf-8"))

    # Then
    assert [key for key in corrections if key not in localities] == []
