# Mode : suivi — où en est la recherche

1. `python3 immo.py tracker list --json` et `python3 immo.py pipeline list --json`.
2. Résumer :
   - annonces en attente d'évaluation ;
   - biens par statut (À visiter, Visite prévue, Offre faite…) ;
   - **actions dues** : visites à planifier pour les biens « À visiter » ; relance des offres dont la validité expire (date dans les notes) ; débrief manquant après une visite passée ;
   - baisses de prix récentes sur des biens suivis (historique dans `data/annonces.json`).
3. Proposer la prochaine action concrète, une seule.

Changer un statut : `python3 immo.py tracker statut <N|url> "<statut>" --note "<texte>"`.
