"""Fails when data/acv.sqlite is older than docs/index.html, so that scripts reading the database do not use stale data.

    python3 build/freshness.py
"""

import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "data" / "acv.sqlite"
SITE = ROOT / "docs" / "index.html"
SITE_GENERATED_AT = re.compile(r'const DATA = \{"generatedAt":"([^"]+)"')


def database_generated_at(database):
    if not database.exists():
        return None
    try:
        with closing(sqlite3.connect(f"file:{database}?mode=ro", uri=True)) as connection:
            row = connection.execute("SELECT value FROM meta WHERE key = 'generatedAt'").fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row else None


def site_generated_at(site):
    match = SITE_GENERATED_AT.search(site.read_text(encoding="utf-8"))
    return match[1] if match else None


def stale_reason(database=DATABASE, site=SITE):
    built = database_generated_at(database)
    published = site_generated_at(site)
    if built is None:
        return f"{database.name} n'indique pas sa date de génération (table meta) : relancer build/build.py"
    if published and built < published:
        return f"{database.name} ({built}) est plus ancien que {site.name} ({published}) : relancer build/build.py"
    return None


def main():
    reason = stale_reason()
    if reason:
        print(reason, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
