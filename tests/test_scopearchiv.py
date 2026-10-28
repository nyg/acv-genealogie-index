import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from scopearchiv import creation_dates  # noqa: E402


def test_creation_dates_in_us_order_become_day_month_year():
    # When
    dates = creation_dates({"Creation date(s)": "1/6/1876 - 12/30/1928"})

    # Then
    assert dates == "06.01.1876 - 30.12.1928"


def test_creation_dates_with_years_only_stay_as_they_are():
    # When
    dates = creation_dates({"Creation date(s)": "1882 - 1996"})

    # Then
    assert dates == "1882 - 1996"
