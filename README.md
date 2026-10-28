# Registres vaudois

Index des registres d'état civil des Archives cantonales vaudoises (ACV) : pour un lieu, un type d'acte et une date, il indique dans quel registre (cote, PDF, pages) chercher.

Site : https://nyg.github.io/acv-genealogie-index/

## Aperçu des PDF

Les PDF de davel-vd.ch pèsent souvent plusieurs centaines de Mo, et le navigateur en télécharge l'essentiel avant d'afficher la page demandée. Le script d'aperçu ne lit que la page affichée (environ 1 Mo). Il tourne sur davel-vd.ch, car davel-vd.ch n'autorise pas les autres sites, dont celui de l'index, à lire ses PDF.

Installation dans Chrome :

1. Installer l'extension [Tampermonkey](https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo).
2. Dans `chrome://extensions`, ouvrir les détails de Tampermonkey et activer « Autoriser les scripts utilisateur » (« Allow User Scripts »).
3. Ouvrir https://nyg.github.io/acv-genealogie-index/apercu.user.js et cliquer sur « Installer ».
4. Recharger le site de l'index.

Les liens « PDF p. » ouvrent alors la fiche du registre sur davel-vd.ch avec la page demandée par-dessus, et « Feuilleter le PDF » s'ajoute aux liens de chaque registre. Sur davel-vd.ch, chaque fiche qui a un PDF reçoit aussi un bouton « Feuilleter le PDF page par page ».

Dans l'aperçu, ← et → changent de page (les pages voisines sont chargées à l'avance), un clic sur la page l'agrandit à la largeur de l'écran, + et − règlent le zoom, R fait pivoter la page et Échap ferme l'aperçu. « PDF entier » ouvre le fichier complet à la même page. Pour les registres dont les pages sont reliées au PDF, le sommaire (☰ ou S) liste les parties du registre, « Registre p. » mène à la page citée par le répertoire, et la barre indique la partie et la page du registre affichées. Tampermonkey met le script à jour depuis la même adresse.

## Sources

- [davel-vd.ch](https://davel-vd.ch) : registres numérisés, avec PDF. Registres paroissiaux (Eb, 1562-1821), état civil cantonal (Ed, 1821-1875), état civil fédéral par arrondissement (SB 267, dès 1876).
- [davel.vd.ch](https://davel.vd.ch) : inventaire général, sans PDF. Promesses de mariage (SB 268), événements hors arrondissement (SB 269), pièces justificatives (Ec, SB 23, SB 115, SB 324).
- Tables de correspondance des ACV, communes et localités vers paroisses (jusqu'en 1875) et vers arrondissements d'état civil (1876-1960).

Les données sont publiées par les ACV sous licence [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.fr) ; les données dérivées de ce dépôt (`data/`, `docs/index.html`) le sont aussi.

## Structure

- `scraper/davel_vd.js` : scraper pour davel-vd.ch, exécuté dans un vrai navigateur (le site bloque les clients HTTP sans navigateur). Il parcourt l'arbre d'une série et lit chaque fiche, une requête toutes les 1,5 s.
- `scraper/davel_scopearchiv.js` : même rôle pour davel.vd.ch, en suivant les liens « entrée inférieure / entrée suivante » de chaque fiche.
- `scraper/davel_pdf.js` : lit les PDF de davel-vd.ch par requêtes partielles, dans le navigateur : nombre de pages, bandes de numérisation, formats de page, et affichage d'une page sans télécharger le PDF entier. Le script d'aperçu l'inclut.
- `scraper/pdf_plan.py` : pour les registres sans correspondance PDF, résume l'inventaire, le profil du PDF et les tables « Contenu PDF » de `index_paroisses.numbers`.
- `scraper/plan.py` : calcule le prochain lot (séries pas encore dans `data/raw/`) et affiche les appels à lancer dans le navigateur.
- `scraper/save_export.py` : enregistre un export d'un des scrapers dans `data/raw/`.
- `scraper/parse_correspondence.py` : extrait les deux tables de correspondance (PDF) en JSON.
- `data/raw/davel-vd/_series_index.json` : liste des 410 séries de davel-vd.ch (paroisses Eb/Ed, arrondissements SB 267).
- `data/raw/davel-vd/_pdf_profiles.json` : profil de chaque PDF relevé (pages, bandes, formats).
- `data/raw/davel/_index.json` : identifiants des entrées de davel.vd.ch par fonds, construit par lots.
- `data/manual/` : corrections manuelles de l'OCR de la table des paroisses, et `pdf-pages.json`, saisi à la main : par registre, les pages du PDF de chaque partie (registre, répertoire) et la pagination du registre correspondante, avec des repères quand des feuillets blancs décalent la pagination. Ollon (Eb 92, Ed 92), Bex (Eb 15, Ed 15) et Aigle (Eb 3, Ed 3) sont saisis.
- `data/manual/erreurs-acv.md` : erreurs des inventaires relevées en construisant l'index, à signaler aux ACV. Celles dont la correction est sûre sont dans `data/manual/corrections-inventaire.json`, que `build/inventory_corrections.py` applique aux fiches brutes ; le rapport signale une correction devenue sans effet.
- `build/scope_parser.py` : analyse le champ « Portée et contenu » (type d'acte, dates, pages, tête-bêche, partie du registre).
- `build/places.py` : noms de paroisses et localités rattachées.
- `build/pdf_pages.py` : lit et vérifie `data/manual/pdf-pages.json` (une page du PDF par page du registre dans chaque partie, deux pour les doubles pages, parties imbriquées quand des pages portent deux numéros).
- `build/scopearchiv.py` : registres et pièces de davel.vd.ch.
- `site/apercu.user.js` : script d'aperçu des PDF pour Tampermonkey (voir « Aperçu des PDF »).
- `site/page_map.js` : passage entre page du registre et page du PDF, commun au site et au script d'aperçu.
- `build/build.py` : construit `data/acv.sqlite`, le site `docs/index.html` (un seul fichier, données incluses), `docs/apercu.user.js`, le script d'aperçu avec `scraper/davel_pdf.js` et `site/page_map.js` inclus, et `docs/pdf-pages.json`, les pages du PDF par registre que le script lit pour son sommaire.
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

`scripts/check.sh` lance `uvx pytest -q tests`, `node tests/site_smoke.mjs`, `node tests/pdf_probe.mjs` et `node tests/apercu.mjs`. Le test de fumée exécute le script du site sur des recherches réelles (lieu, acte, date) et vérifie que la bonne cote ressort, et que les pages du registre tombent sur la bonne page du PDF.
