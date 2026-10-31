# Mode : marche — étude de marché d'une commune ou d'un secteur

Fonctionne sans configuration (utile avant même de définir ses critères).

## Étapes

1. Identifier la commune (demander le code postal si homonymes). Pour un secteur : `python3 immo.py communes --autour <commune> --rayon <km>` et retenir 3 à 8 communes représentatives (taille, distance).
2. Pour chaque commune et chaque type pertinent (maison et/ou appartement) :
   ```bash
   python3 immo.py dvf --commune "<commune>" --cp <cp> --type maison [--surface <surface visée>] --elargir-km 5
   python3 immo.py risques --commune "<commune>" --cp <cp>
   ```
3. Si l'utilisateur a des trajets dans sa config : `python3 immo.py trajet --de "<commune>" --vers "<destination>"`.
4. Si utile et autorisé par l'utilisateur, une ou deux recherches web pour le contexte (projets d'aménagement, fermeture d'usine, ligne de train) ; citer les sources.

## Restitution (dans la conversation ; proposer d'en faire un document si c'est long)

- **Tableau comparatif** : commune, ventes (n), médiane €/m², Q1–Q3, tendance sur les dernières années, prix médian d'une vente, trajet, risques principaux.
- **Lecture** : où le budget de l'utilisateur achète quoi (ex. « 250 k€ = ~110 m² à X, ~85 m² à Y ») ; communes sous-cotées ou surcotées ; tendance (hausse, plateau, baisse).
- **Limites** : DVF = ventes passées (~6 mois de retard), pas l'état des biens ; petites communes = peu de ventes, médianes fragiles.
- **Suggestions** : zones à ajouter/retirer de `config/criteres.yml` ; proposer de faire la modification.
