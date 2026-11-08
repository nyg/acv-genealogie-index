import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from freshness import stale_reason  # noqa: E402


def site_built_at(tmp_path, generated_at):
    site = tmp_path / "index.html"
    site.write_text(f'<script>\nconst DATA = {{"generatedAt":"{generated_at}","places":[]}};\n</script>', encoding="utf-8")
    return site


def database_built_at(tmp_path, generated_at=None):
    database = tmp_path / "acv.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        if generated_at:
            connection.execute("INSERT INTO meta VALUES ('generatedAt', ?)", (generated_at,))
        connection.commit()
    return database


def test_database_built_with_the_site_is_fresh(tmp_path):
    # Given
    database = database_built_at(tmp_path, "2026-11-06T10:00:00+00:00")
    site = site_built_at(tmp_path, "2026-11-06T10:00:00+00:00")

    # When
    reason = stale_reason(database, site)

    # Then
    assert reason is None


def test_database_older_than_the_site_is_stale(tmp_path):
    # Given
    database = database_built_at(tmp_path, "2026-10-27T21:08:00+00:00")
    site = site_built_at(tmp_path, "2026-11-06T10:00:00+00:00")

    # When
    reason = stale_reason(database, site)

    # Then
    assert "plus ancien" in reason


def test_database_without_a_generation_date_is_stale(tmp_path):
    # Given
    database = database_built_at(tmp_path)
    site = site_built_at(tmp_path, "2026-11-06T10:00:00+00:00")

    # When
    reason = stale_reason(database, site)

    # Then
    assert "table meta" in reason


def test_missing_database_is_stale(tmp_path):
    # Given
    site = site_built_at(tmp_path, "2026-11-06T10:00:00+00:00")

    # When
    reason = stale_reason(tmp_path / "acv.sqlite", site)

    # Then
    assert "table meta" in reason
