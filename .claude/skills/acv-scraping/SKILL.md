---
name: acv-scraping
description: Scrape ACV inventories (davel-vd.ch, davel.vd.ch) in the in-app browser and rebuild the index. Use when adding parishes, arrondissements or fonds to the index, resuming a scraping batch, or building the davel.vd.ch index.
---

# ACV scraping

Work in **batches**: plan → scrape → export → save → check → publish. A batch is done when `scripts/check.sh` passes and `python3 build/report.py` shows the new series as indexed.

## Steps

1. **Plan.** `python3 scraper/plan.py davel-vd --fonds eb --match "ollon|huemoz" --batch 20`, or `python3 scraper/plan.py davel --fonds "SB 268"`. It prints the batch, its duration and the two browser calls to run. For `davel`, when the fonds index is missing it prints an index batch instead: run that batch first through the same steps, exporting with `sa.exportIndex` and saving with `davel-index`.
2. **Open the site** with `preview_start`: `https://davel-vd.ch/` or `https://davel.vd.ch/detail.aspx?ID=623416`. davel-vd.ch shows "Verifying your browser" for about a second; wait until the title changes.
3. **Inject the scraper.** `cat` `scraper/davel_vd.js` (or `scraper/davel_scopearchiv.js`) and run its full text with `javascript_tool`, followed by the `enqueue` call from step 1. The scraper lives in the page: any reload or navigation drops `window.acv` / `window.sa` with every unexported record, so export before navigating and re-inject after.
4. **Keep the tab in front** with `tabs_select` until the batch ends, polling `acv.status()` / `sa.status()` about once a minute (`computer` wait between polls). The batch is over when `running` is false and `queue` is empty; read `errors` (a 404 means a wrong slug or ID).
5. **Export** with the export call from step 1. The result is padded past the browser tool's size limit, so the tool saves it to a file and prints the path; run `python3 scraper/save_export.py <path>` (add `davel` or `davel-index` for davel.vd.ch).
6. **Check** with `scripts/check.sh` and read every report section:
   - a new inventory wording under "contenu non analysé" → extend `build/scope_parser.py`, with a test in `tests/`;
   - an OCR-damaged locality → add it to `data/manual/communes-paroisses-corrections.json`;
   - a batch covering a place the user researches → add a case to `tests/site_smoke.mjs`.
7. **Look** at `site/preview.html` in the browser pane; `python3 build/preview.py <place-id>…` chooses its places (ids like `paroisse-92`, `arrondissement-73`).
8. **Publish**: republish `site/artifact.html` with the Artifact tool (same file path, keeps the URL); once the GitHub repo exists, commit and push `docs/` too.

## Browser pane

- A tab in the background is throttled to about one timer per minute after a few minutes, so a hidden scraping tab crawls. Run one scraping tab at a time and keep it in front.
- Editing an `.html` file with the Edit tool opens a preview tab in front of the others. During a batch, patch HTML with a script, or re-front the scraping tab afterwards.
- The pane blocks `localhost`, refuses `file://` previews around 1 MB (hence `site/preview.html`), and claude.ai artifact pages ask for a sign-in it does not have. Check the site through `site/preview.html` and `tests/site_smoke.mjs`.
- davel.vd.ch's CSP blocks blob workers, so timers cannot move off the page.

## davel-vd.ch (Eb, Ed, SB 267, with PDFs)

- AtoM site. Slugs follow the cotes (`eb-3-1-8`, `ed-68-bis-1-5`, `sb-267-73`); `data/raw/davel-vd/_series_index.json` lists all 410 series.
- The scraper reads children from `/<slug>/informationobject/fullWidthTreeView?firstLoad=false` and the fields from each record page. The site disables EAD export.
- PDF links are hashed upload paths, found only on record pages.

## davel.vd.ch (SB 268, SB 269, Ec, SB 23, SB 115, no PDFs)

- scopeArchiv. The default `nav` mode follows each record's "lower-level entry" and "next entry" links, one request per record, from any davel.vd.ch page. The archive-plan tree (`mode 'tree'`, on `archivplansuche.aspx` only) pages children by 100 and silently misses the rest.
- Field labels come in English (UI language), values in French.
- SB 268/N and SB 269/N reuse SB 267's arrondissement numbers; Ec N reuses the Eb/Ed parish numbers.
- SB 23 and SB 115 split into periods, then arrondissement groups (`SB 23/56-65 Ollon`). The build maps groups to arrondissements through the cote ranges in SB 267's "Unités de description associées", narrowest range first (SB 267/59 lists `SB 23/1229-1332`, a typo for 1232).
- Titles containing `FANTOME` are placeholders; `plan.py` skips them.
- SB 324 splits by district, which the build cannot map to arrondissements yet.
