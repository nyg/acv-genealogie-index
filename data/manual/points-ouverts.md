# Points ouverts

Lacunes connues de l'index lui-même, pas de l'inventaire des ACV (celles-là vont dans `erreurs-acv.md`). Retirer la ligne une fois le point réglé et couvert par un cas de `tests/site_smoke.mjs`.

| Lieu | Point ouvert | Indice | Piste |
|---|---|---|---|
| La Tour-de-Peilz | Le site ne propose pas Vevey (`paroisse-132`) avant 1615, ni l'arrondissement de Vevey (`arrondissement-101`) dès juin 2004 : les deux tables ne lient La Tour-de-Peilz qu'à la paroisse 129 et à l'arrondissement 51. | Note d'Eb 129/1-6 et d'Ed 129/1-9 : « Dépendance de Vevey avec diacre dès 1584, érigée en paroisse en 1599. Registres dès 1615. » Note de SB 267/51 : « Supprimé par l'arrêté du 5 mai 2004 et rattaché à l'arrondissement de Vevey dès le 1er juin 2004. » | Paroisse : une entrée « La Tour-de-Peilz » dans `communes-paroisses-corrections.json`, comme pour Lavey, si `parish_period` de `build/places.py` lit la période. Arrondissement : la table s'arrête en 1960 ; une entrée « La Tour-de-Peilz » dans `communes-arrondissements-corrections.json` qui ajoute une période Vevey dès 2004, si l'arrondissement 51 cesse alors d'être proposé. |
