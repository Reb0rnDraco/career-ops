# Mode : comparer — départager 2 à 5 biens

1. Identifier les biens (numéros du tracker ou ids). Tous doivent avoir un rapport ; sinon proposer de les évaluer d'abord.
2. Relire les rapports (et débriefs de visite), puis `python3 immo.py budget --prix <prix> --travaux <estimation>` pour chacun afin de comparer à coût réel égal.
3. Restituer :
   - **un tableau** : prix, coût total travaux compris, mensualité, €/m² vs médiane, surface, terrain, DPE, trajet, risques, score, statut ;
   - **par dimension**, qui gagne et de combien ;
   - **ce qui les distingue vraiment** (souvent 2 ou 3 critères seulement) ;
   - une recommandation argumentée, en tenant compte des priorités de `modes/_profil.md`, et la condition qui renverserait le classement.
4. Si l'utilisateur tranche, mettre à jour les statuts (`Écarté` pour les autres, avec la raison).
