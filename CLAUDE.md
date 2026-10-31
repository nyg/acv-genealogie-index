# Registres vaudois

Index of the Archives cantonales vaudoises (ACV) civil-status registers for the user's genealogy research: for a place, an event and a date, `docs/index.html` names the register to open (cote, PDF, pages). The user writes in French; the site, README and data are in French. Commands: `README.md`. Current coverage and data-quality issues: `python3 build/report.py`.

## Rules

- Scrape only through the in-app browser, at one request every 1.5 s. Both ACV sites reject plain HTTP clients; work inside the real browser session instead of replaying its cookies or challenge.
- Keep `*.numbers` out of git: `sources_pierre_henri_durand.numbers` holds the user's family data. `index_paroisses.numbers` is the user's older hand-made index (read it with `numbers-parser`), a reference to check scraped data against.
- Data is CC BY-SA 4.0 (ACV): keep the attribution in the site footer and README.
- Run `scripts/check.sh` after any change to `build/`, `site/`, `scraper/davel_pdf.js` or `data/`.
- `docs/apercu.user.js` is built from `site/apercu.user.js` with `scraper/davel_pdf.js` and `site/page_map.js` inlined. Bump its `@version` whenever one of them changes: Tampermonkey only updates installed copies to a higher version. Its table of contents comes from `docs/pdf-pages.json`, fetched at run time, so new page maps need no bump.
- Run `build/build.py` without `python3 -I`: it imports its sibling modules.

## Published site

- Public repo https://github.com/nyg/acv-genealogie-index, GitHub Pages from `docs/` on `master`: https://nyg.github.io/acv-genealogie-index/. Pushing `docs/index.html` to `master` publishes the site.

## Next goal

Question 2, started: from a register found by the site, reach the act's page in the PDF (répertoire → name → register page → PDF page). `data/manual/pdf-pages.json` maps all Ollon (17), Bex (24), Aigle (21), Ballaigues (8), Château-d'Oex (26) and L'Étivaz (8) Eb/Ed registers; the skill `acv-pdf-pages` adds more. Not done: other parishes (the « Contenu PDF » tables in `index_paroisses.numbers` cover Cheseaux, Lignerolle, Ormont-Dessus, Rougemont), SB 267, and a letter → PDF page index for répertoires.
