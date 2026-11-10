# Registres vaudois

Index of the Archives cantonales vaudoises (ACV) civil-status registers for the user's genealogy research: for a place, an event and a date, `docs/index.html` names the register to open (cote, PDF, pages). The user writes in French; the site, README and data are in French. Commands: `README.md`. To find the register, PDF and PDF page for a place, event and date, run `node cli/acv.mjs chercher <lieu> <acte> [date] [--page N] --json` instead of reading the data. Current coverage and data-quality issues: `python3 build/report.py`.

## Rules

- Scrape only through the in-app browser, at one request every 1.5 s. Both ACV sites reject plain HTTP clients; work inside the real browser session instead of replaying its cookies or challenge.
- Keep `*.numbers` out of git: `sources_pierre_henri_durand.numbers` holds the user's family data. `index_paroisses.numbers` is the user's older hand-made index (read it with `numbers-parser`), a reference to check scraped data against.
- Data is CC BY-SA 4.0 (ACV): keep the attribution in the site footer and README.
- Run `scripts/check.sh` after any change to `build/`, `site/`, `cli/`, `scraper/davel_pdf.js` or `data/`.
- `docs/apercu.user.js` is built from `site/apercu.user.js` with `scraper/davel_pdf.js`, `site/pdfjs_reader.js` and `site/page_map.js` inlined. Bump its `@version` whenever one of them changes: Tampermonkey only updates installed copies to a higher version. Its table of contents comes from `docs/pdf-pages.json`, fetched at run time, so new page maps need no bump.
- `cli/acv.mjs` runs the site's own script from `docs/index.html` (via `cli/site.mjs`): put lookup logic in `site/template.html` as functions that take their inputs, not in the CLI, so both always answer the same.
- Run `build/build.py` without `python3 -I`: it imports its sibling modules.
- Before indexing a place or changing how places link to parishes and arrondissements, read `data/manual/points-ouverts.md`: known index gaps, such as a link the ACV tables miss.

## Published site

- Public repo https://github.com/nyg/acv-genealogie-index, GitHub Pages from `docs/` on `master`: https://nyg.github.io/acv-genealogie-index/. Pushing `docs/index.html` to `master` publishes the site.

## Next goal

Question 2, started: from a register found by the site, reach the act's page in the PDF (répertoire → name → register page → PDF page). `data/manual/pdf-pages.json` maps all Ollon (17), Bex (24), Aigle (21), Ballaigues (8), Château-d'Oex (26), L'Étivaz (8), Gryon (8), Huémoz (5), Leysin (8), Lignerolle (8), Lutry (21), Ormont-Dessous (18), Ormont-Dessus (16), Rougemont (21), Cheseaux (19), La Sarraz (16), Noville (12), Villeneuve (18), Roche (4), Yvorne (4), Pully (17), Belmont-sur-Lausanne (9), Vevey (46: Eb 132/1-17, French and German parishes, and Ed 132/1-29; Eb 132/18 and Ed 132/30 have no PDF), Bullet (12), Sainte-Croix (24), La Tour-de-Peilz (15) and Oron (18) Eb/Ed registers, 13 of the 21 of Arzier, Genolier and Begnins, and 18 SB 267 registers read on the images; other SB 267 registers get the « PDF = page + 3 » default from `build/pdf_pages.py`, shown « ≈ », except those cut off by the publication limit. The skill `acv-pdf-pages` adds more. Not done: other parishes, the drifting Ed volumes Ed 5/1, 5/3, 12/1, 12/3, 12/4, 58/1, 58/3 and 58/4, and a letter → PDF page index for répertoires.
