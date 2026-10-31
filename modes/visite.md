# Mode : visite — préparer, puis débriefer

Identifier le bien (numéro du tracker, id ou URL) et relire son rapport dans `reports/`.

## Avant la visite

Produire une **fiche de visite** imprimable (`reports/{NNN}-visite.md`), adaptée au bien et pas générique :

1. **Les 3 points qui décident** pour ce bien (tirés des blocs B à F du rapport).
2. **Questions à poser** — reprendre celles du bloc G, compléter selon le bien :
   - pourquoi vendez-vous ? depuis quand en vente ? offres déjà reçues ?
   - montant de la taxe foncière, des charges (copropriété), consommation réelle d'énergie (factures) ;
   - année de construction, travaux réalisés (factures, garanties décennales), toiture, chaudière (âge, entretien) ;
   - assainissement : collectif ou individuel ? date et conclusion du contrôle SPANC ;
   - diagnostics disponibles (DDT complet, ERP) — demander à les recevoir avant toute offre ;
   - copropriété : PV des 3 dernières AG, travaux votés, fonds de travaux, procédures ;
   - en zone à cavités : périmètre de marnière connu sur la parcelle ?
3. **À vérifier sur place** (check-list cochable) : humidité (traces, odeur, salpêtre), fissures (façade, linteaux), charpente et toiture (depuis le grenier), menuiseries, tableau électrique (âge, différentiel), plomberie, chauffage, orientation et luminosité aux heures utiles, bruit (route, voisinage), réseau mobile, voisinage immédiat, état des parties communes.
4. **Repérage autour** : trajet aux heures réelles, commerces, école, stationnement.

Proposer de rédiger le message de prise de rendez-vous ; l'utilisateur l'envoie lui-même. Une fois le rendez-vous fixé : `python3 immo.py tracker statut <N> "Visite prévue" --note "<date>"`.

## Après la visite (débrief)

1. Demander les impressions : ce qui a plu, ce qui inquiète, réponses obtenues, photos/notes.
2. Mettre à jour le rapport : ajouter une section `## Visite du <date>` (faits constatés, réponses du vendeur, défauts repérés) et **réviser le score** si des faits nouveaux le justifient (montrer avant → après et pourquoi).
3. Chiffrer les travaux repérés (*estimation*, fourchette) et relancer `python3 immo.py budget --prix <prix> --travaux <montant>`.
4. `python3 immo.py tracker statut <N> Visité --note "<résumé une ligne>"`.
5. Proposer la suite : contre-visite (avec un artisan si gros doute), mode `offre`, ou écarter.
