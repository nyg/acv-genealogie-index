# Registres vaudois

Index of the Archives cantonales vaudoises (ACV) civil-status registers for the user's genealogy research: for a place, an event and a date, `docs/index.html` names the register to open (cote, PDF, pages). The user writes in French; the site, README and data are in French. Layout and commands: `README.md`. Current coverage and data-quality issues: `python3 build/report.py`.

## Rules

- Scrape only through the in-app browser, at one request every 1.5 s. Both ACV sites reject plain HTTP clients; work inside the real browser session instead of replaying its cookies or challenge.
- Keep `*.numbers` out of git: `sources_pierre_henri_durand.numbers` holds the user's family data. `index_paroisses.numbers` is the user's older hand-made index (read it with `numbers-parser`), a reference to check scraped data against.
- Data is CC BY-SA 4.0 (ACV): keep the attribution in the site footer and README.
- Run `scripts/check.sh` after any change to `build/`, `site/template.html` or `data/`.
- Run `build/build.py` without `python3 -I`: it imports its sibling modules.

## Published copies

- Artifact (private): https://claude.ai/artifact/WTuMXSDGgVLo7yAFjvjTYF, published from `site/artifact.html`.
- Public repo https://github.com/nyg/acv-genealogie-index, GitHub Pages from `docs/` on `main`: https://nyg.github.io/acv-genealogie-index/. Pushing `docs/index.html` to `main` publishes the site.

## Next goal

Question 2, not started: from a register found by the site, reach the act's page in the PDF (répertoire → name → register page → PDF page). The "Contenu PDF" tables in `index_paroisses.numbers` map PDF page ranges by hand for a few registers.
