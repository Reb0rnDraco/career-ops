# Mode : scan — nouvelles annonces

## Étapes

1. `python3 immo.py scan` (zéro token). Sortie JSON : `nouvelles_retenues`, `nouvelles_rejetees_prefiltre`, `baisses_de_prix`, `en_attente_evaluation`, liste `nouvelles`.
2. Codes de sortie :
   - `2` : config absente/invalide → mode `setup`.
   - `3` : `lbc` non installé → proposer l'installation (demander avant).
   - `4` : blocage Leboncoin (403/DataDome) → **ne pas réessayer en boucle**. Expliquer : réessayer dans quelques heures, baisser `scan.pages_max`, ou coller les URL d'annonces repérées à la main (elles passeront par `evaluer`). Ne jamais proposer de contourner l'anti-bot.
3. Résumer en quelques lignes : combien de nouvelles, combien écartées par le préfiltre (et la raison dominante), les baisses de prix (ancien → nouveau prix).
4. **Tri rapide** (sans rapport complet) des nouvelles retenues : pour chacune, une ligne `id — résumé — premier avis` à partir du titre, du prix au m² et des mots de la description. Classer en *prometteuse* / *à voir* / *peu probable*.
5. Proposer d'évaluer les prometteuses (`/immo-ops pipeline`, ou une par une).

## Préfiltre (rappel)

Le préfiltre applique seulement les critères **durs** de `config/criteres.yml` (type, prix, surface, pièces, chambres, terrain, DPE max, mots exclus). Une donnée absente de l'annonce ne rejette jamais. Une annonce rejetée qui repasse sous le plafond de prix revient automatiquement « à évaluer ».

Si l'utilisateur trouve trop de bruit ou trop peu d'annonces, ajuster `config/criteres.yml` avec lui (pas le code).

## Recherches hors Leboncoin

SeLoger, Bien'ici, PAP, Logic-Immo et les sites d'agences ne sont pas scannés automatiquement (pas d'API ouverte, CGU restrictives). Pour une annonce repérée là-bas : la coller, et le mode `evaluer` l'enregistre avec `python3 immo.py pipeline ajouter`.
