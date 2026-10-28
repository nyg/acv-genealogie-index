---
name: acv-pdf-pages
description: Map where each part of a davel-vd.ch register PDF sits (register pages, répertoires) into data/manual/pdf-pages.json, reading PDF pages in the in-app browser. Use when adding registers to the PDF page map, finding a répertoire or a register page in a PDF, or resuming that work.
---

# ACV PDF page map

`data/manual/pdf-pages.json` tells the site, per cote, which PDF pages hold each part of the register and which register page sits on which PDF page. Work register by register: **plan → profile → read pages → write the entry → check**. A register is done when its entry passes `scripts/check.sh` and every register part has its first and last page read on the image.

## Steps

1. **Plan.** `uv run --with numbers-parser scraper/pdf_plan.py --match "^E[bd] 92/" --hints index_paroisses.numbers` lists the registers without an entry. For each: the inventory parts and their `pp.`, the répertoire lines (séparé, incorporé, sans), the note, the saved profile, and the user's hand-made « Contenu PDF » ranges (PDF ranges only, often 1-2 pages off). Without `--hints` it runs with plain `python3`. In a worktree the `.numbers` file stays in the main checkout: `--hints ../../../index_paroisses.numbers`.
2. **Profile.** Open `https://davel-vd.ch/` with `preview_start`, inject the full text of `scraper/davel_pdf.js` with `javascript_tool` (when the local file has no unpushed changes, `(0, eval)(await (await fetch('https://raw.githubusercontent.com/nyg/acv-genealogie-index/<commit>/scraper/davel_pdf.js')).text())` injects it without pasting it), run the `pdf.enqueue({...})` call printed by the plan, poll `pdf.status()` until `queue` is empty, then `pdf.exportProfiles()`: the tool saves the padded result to a file; `python3 scraper/save_export.py <file> pdf-profiles`. About 3-5 requests per Eb/Ed PDF; the whole PDF is never downloaded.
3. **Read the profile.** `strips` are the narrow colour-chart scans the operator put before each physical volume: a strip after page 1 starts a separate répertoire volume (or a second scanning batch). `segments` group pages by format: separate répertoires are another format than the register. `text` is false on every PDF seen so far: no OCR.
4. **Read pages.** `await pdf.view(path, [6, 285, 355], { band: 0.06, from: 0.02 })` draws a horizontal band of each page across the tab; screenshot it. `pdf.view(path, [58, 59, 60, 61])` shows whole pages side by side to recognise covers, title pages, blank leaves and répertoires. `left`/`right` (0-1) crop the band to one half to magnify a corner. One ~1 MB request per new page, cached afterwards. Screenshot again when a band shows blank: the pane can lag. `pdf.close()` removes the overlay.
   - Page numbers sit at `from` ≈ 0.01-0.05 on Eb pages and at ≈ 0.03-0.09 (printed « Page N ») on Ed forms; adjust `from` until the number shows, and crop with `left`/`right` to magnify a faint one. Several pages per call (one band each) save screenshots.
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
   - `pages` is the pagination the répertoire cites, read on the page; a descending range is fine. When it differs from the inventory's `pp.`, say so in `note`. When the PDF shows the inventory is wrong (swapped parts, wrong pages or dates), also add it to `data/manual/erreurs-acv.md`.
   - Without `anchors`, a part has one PDF page per register page; `build/pdf_pages.py` rejects a mismatch. Split the part where the offset changes: a page number written twice (Eb 92/1 p. 166) goes in both parts, so the site offers both PDF pages.
   - `anchors` are `[page, pdf]` pairs read on the images, for registers whose offset drifts every few pages (blank leaves bound between gatherings, common in Ed). The site interpolates between them and shows « ≈ PDF p. N ». Read one every 50 PDF pages and check one interpolated page; Ed 15/3 was 5 pages off with a 100-page gap. When the check calls an anchor « incompatible », the page was misread: read it again.
   - A part may sit inside the previous part's PDF range when pages carry two numbers (Eb 15/1: mariages pp. 72-89 are also baptêmes pp. 339-356). Put the outer part first.
   - `"spread": true` for parts photographed as double pages (Ed 15/2, Ed 3/2): two register pages per PDF page, positions always approximate between anchors. Read anchors on the right-hand page: the site rounds a half page up, so a left-hand anchor sends the right-hand page beside it to the next PDF page. The part may start or end on a right-hand page; one starting on a left-hand page needs an anchor on the right-hand page of the same image (Eb 23/8: `[[2, 5], …]`).
   - A page bound with its transcription before it (Eb 3/1 pp. 1-23, « Traduction de la page ci-contre ») takes two PDF pages: anchors two PDF pages apart on the originals give exact positions.
   - A page carrying several numbers (Eb 10/1 PDF 229: « 218. 219. … 224. » written side by side) is a part of that one PDF page with the whole range: `{"pdf": "229", "pages": "218-224"}`. Every number in it leads to that page.
   - `"roman": true` for a pagination in roman numerals: write `pages` in arabic numbers; the site shows and accepts roman numerals.
   - A part without `pages` (Eb 15/3 décès I-III) still shows its PDF range and highlights for its events.
   - Name events in `content` (« Répertoire des décès », « Baptêmes ») so the site highlights the parts matching the searched event.
   - `pdfPages` equals the profile's `pages`; a test checks it.
6. **Check.** `scripts/check.sh`. Add a case to `pdfCases` in `tests/site_smoke.mjs` for a register with a new kind of layout.

## What the PDFs look like

- **Eb/Ed** (ABBYY Recognition Server, 2014-2015): page 1 is a strip, then covers and a title; register page 1 is usually PDF 5-10. One image per page.
- **Separate répertoires** (1917-1920 for Eb) are bound apart but scanned into the same PDF, right after the part they index, each behind a strip. One PDF may hold the separate répertoires of several registers (Eb 54/1 holds three, covering Eb 54/1-4); their covers list where each section starts (« Mariages … dès page 20 »), so split them into one part per section. **Incorporated répertoires** sit at the end of the volume, usually after a marbled cover, or inside the tête-bêche part.
- **Tête-bêche**: the PDF follows the operator. Usually the main part first, then the flipped volume (a back cover shows) from the tête-bêche start; a tête-bêche répertoire may come right after the part it indexes. Eb 23/8's tête-bêche part was photographed upside down, from the last page back: `pages` descending, `rotate: true` in `pdf.view` reads it, and the middle image holds the last page of both parts, so one of them gets a nested one-page part.
- **Paginations**: Eb répertoires often cite an older, descending pagination written on the pages (Eb 92/1, 92/2, 92/4, 92/6, 92/7), not the inventory's `pp.`. Many Eb pages carry two numbers, the older one crossed out; when they diverge, read one répertoire line to see which one it cites (Eb 15/9's répertoire cites the newer one, with « anc. pag. » in brackets). The older pagination may run on from the tête-bêche end: Eb 54/1's tête-bêche part holds pp. 2-36 and its baptêmes run from 115 down to 41. Ed registers have one printed pagination.
- **Irregular Eb pages** (Bex, Aigle): bis, A/B and duplicate numbers, loose slips photographed recto and verso, the same page photographed twice. Each one shifts the offset: split the part there and say what sits in between in `note`.
- **Skipped or corrected numbers** (Aigle): a pagination can skip numbers (Eb 3/3 pp. 284 and 305, Ed 3/10 p. 203, Ed 3/13 pp. 434-443) or be corrected in ink over a stretch (Ed 3/8: 195-202 written over as 198-205). The offset then decreases: an anchor check failing with « incompatible » on a correctly read page means a skip, so bisect and split the part. Use the corrected numbers.
- **Inventory labels**: the inventory can attach a part's page range to the wrong content (Eb 3/6 swaps its two parts): read the title page of each part.
- **Blank leaves**: Ed registers often have unnumbered blank leaves bound in every few pages. Their JPEGs are smaller (about 60 % of the median), a hint for where to look, not proof (no use on L'Étivaz's grayscale Ed scans).
- **Unused printed forms** (Ballaigues Ed 10/1, 10/3, 10/4): Ed volumes bound with spare blank or crossed-out forms, their « Page ___ » left empty or written « 0 », the offset growing by 20-30 over the first 150 pages. Anchor the stretch, then split exact parts where the offset settles. Ed 10/4 also skips numbers (pp. 139-140, 152-153).
- **JPEG 2000 pages** (Ed 10/1, whose profile is skipped too): `pdf.view` fails with « The source image cannot be decoded ». Return the bytes of `await pdf.imageOf(path, n)` as base64, padded like `exportProfiles` so the tool writes them to a file, about 6 pages per call; then decode, crop and stack the bands with Pillow (`uv run --with pillow`) and read the PNG. Each page costs about 2 requests.
- **Pencil pagination at the foot** (Eb 23/13-15): no number at the top; read the bottom with `from: 0.92`.
- **16th-century fragments** (Eb 23/1-3): leaves torn or of uneven size, often mounted on paper, so the number of the next leaf shows above the page's own (Eb 23/2: « 73 » above « 71 »). Trust a number only when the neighbouring pages agree with it.
- **SB 267** (img2pdf, 2022): page objects are spread through the file, so the profile only counts pages; offset +3 (barcode sheet, title, verso); no répertoire in the PDF, which ends at the last act.
- `#page=N` links work in the user's browser (checked on Eb 92/7). The in-app pane cannot display PDFs, and navigating it to a PDF URL opens a download dialog for the user: read pages through `pdf.view`.
- Ollon's 17 Eb/Ed registers took about 370 requests in all, most of them page images. Bex's 24 took about 830: 130 for the profiles, about 45 per Eb register (bisecting the offset shifts) and 15 per Ed register. Aigle's 21 took about 880 in all. Ballaigues's 8 took about 560: the Eb 10/1 baptêmes alone about 120 (slips, skipped numbers, multi-number pages). Château-d'Oex's 26 took about 690, 95 of them for the profiles. L'Étivaz's 8 took about 425, 21 of them for the profiles.
