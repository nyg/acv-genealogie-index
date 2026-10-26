#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 build/build.py
uvx --quiet pytest -q tests
node tests/site_smoke.mjs
python3 build/preview.py
python3 build/report.py --limit 5
