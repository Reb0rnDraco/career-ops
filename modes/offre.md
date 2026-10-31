# Mode : offre — prix, arguments, lettre d'offre

Rappel en une phrase au début : ceci est une aide à la décision, pas un conseil juridique ou financier ; le financement se valide avec la banque ou le courtier, l'acte avec le notaire.

## 1. Rassembler

- Le rapport du bien et, s'il existe, le débrief de visite.
- Un contexte à jour : `python3 immo.py contexte <id>` (historique de prix, jours en ligne, DVF).
- Auprès de l'utilisateur : son prix maximum réel, son financement (accord de principe ? apport ?), son calendrier, son degré d'attachement au bien.

## 2. Construire le prix

Présenter trois niveaux, chacun justifié :

| Niveau | Base |
|---|---|
| **Offre d'ouverture** | bas de la fourchette « prix juste » du bloc C, moins les travaux chiffrés non intégrés au prix |
| **Cible** | prix juste DVF ajusté (état, terrain, prestations) |
| **Plafond** | ce que l'utilisateur est prêt à payer sans regret, sous son budget total travaux compris |

**Arguments factuels de négociation** (seulement ceux qui s'appliquent et sont sourcés) : comparables DVF moins chers, DPE et coût de rénovation énergétique, travaux constatés à la visite, durée de mise en vente et baisses de prix passées, assainissement non conforme, risques (cavité, inondation) à lever.

Signaler ce qui affaiblit la position : bien très demandé, prix déjà sous le marché, plusieurs visites prévues.

## 3. Rédiger (brouillon, jamais envoyé par l'agent)

Une **lettre d'offre d'achat** à relire par l'utilisateur :

- identité de l'acquéreur et désignation du bien (adresse, référence de l'annonce) ;
- prix proposé, en précisant frais d'agence inclus ou non ;
- **conditions suspensives** : obtention du prêt (montant, durée, taux maximum) ; selon le cas, contrôle SPANC, levée de doute sur une cavité, absence de servitude, obtention d'un permis ;
- durée de validité de l'offre (souvent 7 à 10 jours) ;
- calendrier souhaité (compromis, acte) ;
- mention qu'il s'agit d'une offre sous réserve de la signature d'un avant-contrat.

Rappeler : une offre acceptée par écrit engage les deux parties sur le prix ; le délai de rétractation de 10 jours ne court qu'à partir du compromis.

Proposer aussi un court message d'accompagnement pour l'agence ou le vendeur. Une fois envoyée par l'utilisateur : `python3 immo.py tracker statut <N> "Offre faite" --note "<montant>, valable jusqu'au <date>"`.

## 4. Contre-offre

Si l'utilisateur rapporte une contre-offre : recalculer l'écart avec la cible et le plafond, rappeler les arguments non encore utilisés, proposer une réponse (accepter, couper la poire en deux, tenir), et mettre à jour le statut (`Contre-offre`, `Offre acceptée`).
