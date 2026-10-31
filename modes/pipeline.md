# Mode : pipeline — traiter les annonces en attente

1. `python3 immo.py pipeline list --json` → annonces `a_evaluer`, les plus récentes d'abord.
2. S'il y en a plus de 5 : faire d'abord un **tri rapide** (une ligne par annonce : résumé + avis en quelques mots, à partir de `python3 immo.py pipeline show <id>` : titre, €/m², DPE, description). Demander lesquelles évaluer complètement ; marquer les autres :
   ```bash
   python3 immo.py pipeline marquer <id> ecartee
   ```
   En exécution sans surveillance (tâche planifiée), évaluer seulement celles jugées prometteuses et écarter celles qui ont un défaut rédhibitoire évident, en le notant dans le résumé final.
3. Évaluer chaque annonce retenue avec le mode `evaluer` (rapport + tracker + `pipeline marquer … evaluee`).
4. Finir par un tableau récapitulatif : id, commune, prix, score, recommandation, chemin du rapport ; trié par score décroissant.

`data/pipeline.md` est une vue régénérée à chaque commande : ne pas l'éditer.
