---
name: acv-pdf-pages
description: Map where each part of a davel-vd.ch register PDF sits (register pages, répertoires) into data/manual/pdf-pages.json, reading PDF pages in the in-app browser. Use when adding registers to the PDF page map, finding a répertoire or a register page in a PDF, or resuming that work.
---

# ACV PDF page map

`data/manual/pdf-pages.json` tells the site, per cote, which PDF pages hold each part of the register and which register page sits on which PDF page. Work register by register: **plan → profile → read pages → write the entry → check**. A register is done when its entry passes `scripts/check.sh` and every register part has its first and last page read on the image.

## Steps

1. **Plan.** `uv run --with numbers-parser scraper/pdf_plan.py --match "^E[bd] 92/" --hints index_paroisses.numbers` lists the registers without an entry. For each: the inventory parts and their `pp.`, the répertoire lines (séparé, incorporé, sans), the note, the saved profile, and the user's hand-made « Contenu PDF » ranges (PDF ranges only, often 1-2 pages off). Without `--hints` it runs with plain `python3`.
2. **Profile.** Open `https://davel-vd.ch/` with `preview_start`, inject the full text of `scraper/davel_pdf.js` with `javascript_tool`, run the `pdf.enqueue({...})` call printed by the plan, poll `pdf.status()` until `queue` is empty, then `pdf.exportProfiles()`: the tool saves the padded result to a file; `python3 scraper/save_export.py <file> pdf-profiles`. About 3-5 requests per Eb/Ed PDF; the whole PDF is never downloaded.
3. **Read the profile.** `strips` are the narrow colour-chart scans the operator put before each physical volume: a strip after page 1 starts a separate répertoire volume (or a second scanning batch). `segments` group pages by format: separate répertoires are another format than the register. `text` is false on every PDF seen so far: no OCR.
4. **Read pages.** `await pdf.view(path, [6, 285, 355], { band: 0.06, from: 0.02 })` draws a horizontal band of each page across the tab; screenshot it. `pdf.view(path, [58, 59, 60, 61])` shows whole pages side by side to recognise covers, title pages, blank leaves and répertoires. `left`/`right` (0-1) crop the band to one half to magnify a corner. One ~1 MB request per new page, cached afterwards. Screenshot again when a band shows blank: the pane can lag. `pdf.close()` removes the overlay.
   - Page numbers sit at `from` ≈ 0.01-0.03 on Eb pages and at ≈ 0.06-0.09 (printed « Page N ») on Ed forms; adjust `from` until the number shows.
   - For each register part, read its first and last page: the number written on the page and its PDF page. When the offset differs between the two ends, bisect with bands until you find where it changes.
   - Read one page of each répertoire: its references name the pagination the entry must use.
5. **Write the entry** in `data/manual/pdf-pages.json`, parts in PDF order:
   ```json
   "Eb 92/4": {"pdfPages": 441, "parts": [
     {"pdf": "6-140", "content": "Mariages 1760-1787", "pages": "312-178", "note": "Pagination ancienne, décroissante, celle du répertoire ; l'inventaire indique pp. 1-135."},
     {"pdf": "142-201", "content": "Répertoire des mariages 1760-1787"}
   ]},
   "Ed 92/6": {"pdfPages": 516, "parts": [
     {"pdf": "6-456", "content": "Décès 1821-1854", "pages": "1-375", "anchors": [[100, 130], [150, 190], [200, 250]], "note": "Feuillets blancs intercalés tout au long du registre."}
   ]}
   ```
   - `pages` is the pagination the répertoire cites, read on the page; a descending range is fine. When it differs from the inventory's `pp.`, say so in `note`.
   - Without `anchors`, a part has one PDF page per register page; `build/pdf_pages.py` rejects a mismatch. Split the part where the offset changes: a page number written twice (Eb 92/1 p. 166) goes in both parts, so the site offers both PDF pages.
   - `anchors` are `[page, pdf]` pairs read on the images, for registers whose offset drifts every few pages (blank leaves bound between gatherings, common in Ed). The site interpolates between them and shows « ≈ PDF p. N ». Read one every 50-100 pages and check one interpolated page; Ed 92/1 was 3 pages off with 100-page gaps.
   - Name events in `content` (« Répertoire des décès », « Baptêmes ») so the site highlights the parts matching the searched event.
   - `pdfPages` equals the profile's `pages`; a test checks it.
6. **Check.** `scripts/check.sh`. Add a case to `pdfCases` in `tests/site_smoke.mjs` for a register with a new kind of layout.

## What the PDFs look like

- **Eb/Ed** (ABBYY Recognition Server, 2014-2015): page 1 is a strip, then covers and a title; register page 1 is usually PDF 5-10. One image per page.
- **Separate répertoires** (1917-1920 for Eb) are bound apart but scanned into the same PDF, right after the part they index, each behind a strip. **Incorporated répertoires** sit at the end of the volume, usually after a marbled cover, or inside the tête-bêche part.
- **Tête-bêche**: the PDF follows the operator. Usually the main part first, then the flipped volume (a back cover shows) from the tête-bêche start; a tête-bêche répertoire may come right after the part it indexes.
- **Paginations**: Eb répertoires often cite an older, descending pagination written on the pages (Eb 92/1, 92/2, 92/4, 92/6, 92/7), not the inventory's `pp.`. Ed registers have one printed pagination.
- **Blank leaves**: Ed registers often have unnumbered blank leaves bound in every few pages. Their JPEGs are smaller (about 60 % of the median), a hint for where to look, not proof.
- **SB 267** (img2pdf, 2022): page objects are spread through the file, so the profile only counts pages; offset +3 (barcode sheet, title, verso); no répertoire in the PDF, which ends at the last act.
- `#page=N` links are untested: the in-app pane cannot display PDFs, and navigating it to a PDF URL opens a download dialog for the user. Read pages through `pdf.view`.
- Ollon's 17 Eb/Ed registers took about 370 requests in all, most of them page images.
