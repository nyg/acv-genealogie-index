# Registres vaudois

Index des registres d'état civil des Archives cantonales vaudoises (ACV) : pour un lieu, un type d'acte et une date, il indique dans quel registre (cote, PDF, pages) chercher.

Site : https://nyg.github.io/acv-genealogie-index/

## Sources

- [davel-vd.ch](https://davel-vd.ch) : registres numérisés, avec PDF. Registres paroissiaux (Eb, 1562-1821), état civil cantonal (Ed, 1821-1875), état civil fédéral par arrondissement (SB 267, dès 1876).
- [davel.vd.ch](https://davel.vd.ch) : inventaire général, sans PDF. Promesses de mariage (SB 268), événements hors arrondissement (SB 269), pièces justificatives (Ec, SB 23, SB 115, SB 324).
- Tables de correspondance des ACV, communes et localités vers paroisses (jusqu'en 1875) et vers arrondissements d'état civil (1876-1960).

Les données sont publiées par les ACV sous licence [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.fr) ; les données dérivées de ce dépôt (`data/`, `docs/index.html`) le sont aussi.

## Structure

- `scraper/davel_vd.js` : scraper pour davel-vd.ch, exécuté dans un vrai navigateur (le site bloque les clients HTTP sans navigateur). Il parcourt l'arbre d'une série et lit chaque fiche, une requête toutes les 1,5 s.
- `scraper/davel_scopearchiv.js` : même rôle pour davel.vd.ch, en suivant les liens « entrée inférieure / entrée suivante » de chaque fiche.
- `scraper/davel_pdf.js` : lit les PDF de davel-vd.ch par requêtes partielles, dans le navigateur : nombre de pages, bandes de numérisation, formats de page, et affichage d'une page sans télécharger le PDF entier.
- `scraper/pdf_plan.py` : pour les registres sans correspondance PDF, résume l'inventaire, le profil du PDF et les tables « Contenu PDF » de `index_paroisses.numbers`.
- `scraper/plan.py` : calcule le prochain lot (séries pas encore dans `data/raw/`) et affiche les appels à lancer dans le navigateur.
- `scraper/save_export.py` : enregistre un export d'un des scrapers dans `data/raw/`.
- `scraper/parse_correspondence.py` : extrait les deux tables de correspondance (PDF) en JSON.
- `data/raw/davel-vd/_series_index.json` : liste des 410 séries de davel-vd.ch (paroisses Eb/Ed, arrondissements SB 267).
- `data/raw/davel-vd/_pdf_profiles.json` : profil de chaque PDF relevé (pages, bandes, formats).
- `data/raw/davel/_index.json` : identifiants des entrées de davel.vd.ch par fonds, construit par lots.
- `data/manual/` : corrections manuelles de l'OCR de la table des paroisses, et `pdf-pages.json`, saisi à la main : par registre, les pages du PDF de chaque partie (registre, répertoire) et la pagination du registre correspondante, avec des repères quand des feuillets blancs décalent la pagination.
- `build/scope_parser.py` : analyse le champ « Portée et contenu » (type d'acte, dates, pages, tête-bêche, partie du registre).
- `build/places.py` : noms de paroisses et localités rattachées.
- `build/pdf_pages.py` : lit et vérifie `data/manual/pdf-pages.json` (une page du PDF par page du registre dans chaque partie).
- `build/scopearchiv.py` : registres et pièces de davel.vd.ch.
- `build/build.py` : construit `data/acv.sqlite` et le site `docs/index.html` (un seul fichier, données incluses).
- `build/report.py` : couverture par fonds et problèmes de données (contenus non analysés, dates incohérentes, localités sans paroisse).
- `build/preview.py` : version réduite du site (`site/preview.html`) pour l'aperçu du navigateur intégré.
- `scripts/check.sh` : reconstruit, lance les tests, génère l'aperçu et affiche le rapport.

## Ajouter des séries

La marche à suivre complète, pour un agent, est dans `.claude/skills/acv-scraping/SKILL.md`. En résumé :

```bash
python3 scraper/plan.py davel-vd --fonds eb --match "ollon|huemoz"
```

Coller dans la console de davel-vd.ch le contenu de `scraper/davel_vd.js`, puis les appels affichés par `plan.py` (`acv.enqueue(...)`, puis `acv.exportSeries(...)` une fois le lot terminé). Pour davel.vd.ch, même chose avec `plan.py davel --fonds "SB 268"` et `scraper/davel_scopearchiv.js`.

Enregistrer l'export avec `python3 scraper/save_export.py <fichier> [davel|davel-index]`, puis :

```bash
scripts/check.sh
```

## Pages des PDF

La marche à suivre pour ajouter des registres à `data/manual/pdf-pages.json` est dans `.claude/skills/acv-pdf-pages/SKILL.md`. Les PDF n'ont pas de texte : les numéros de page se lisent sur les images.

## Tables de correspondance

```bash
curl -O https://www.vd.ch/fileadmin/user_upload/themes/etat_droit/archives_cantonales/Fichiers-PDF/doc-etat-civil_correspondance_communes-paroisses.pdf
curl -O https://www.vd.ch/fileadmin/user_upload/themes/etat_droit/archives_cantonales/Fichiers-PDF/doc-etat-civil_correspondance_communes-arrondissements.pdf
uv run --with pdfplumber scraper/parse_correspondence.py
```

Les deux PDF vont dans `data/raw/vd-ch/`.

## Tests

`scripts/check.sh` lance `uvx pytest -q tests`, `node tests/site_smoke.mjs` et `node tests/pdf_probe.mjs`. Le test de fumée exécute le script du site sur des recherches réelles (lieu, acte, date) et vérifie que la bonne cote ressort, et que les pages du registre tombent sur la bonne page du PDF.
