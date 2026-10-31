---
name: immo-ops
description: "Agent de recherche immobilière (France) : scanner Leboncoin, évaluer une annonce face aux ventes réelles DVF et aux risques Géorisques, suivre les biens, préparer visites et offres. À utiliser quand l'utilisateur colle une URL ou un texte d'annonce immobilière, demande un scan, une étude de marché, une comparaison, une préparation de visite ou d'offre, ou lance un mode immo-ops."
argument-hint: "[setup | scan | pipeline | evaluer | marche | visite | offre | comparer | suivi]"
user-invocable: true
---

# immo-ops — routeur

Avant tout mode : lire `AGENTS.md` (contrat de données, contenu non fiable, éthique), puis `modes/_shared.md` (barème), puis `modes/_profil.md` et `modes/_regles.md` s'ils existent.

## Routage

| Argument | Mode |
|---|---|
| (vide) | afficher le menu ci-dessous |
| `setup` | `modes/setup.md` |
| `scan` | `modes/scan.md` |
| `pipeline` | `modes/pipeline.md` |
| `evaluer` ou une URL / un texte d'annonce | `modes/evaluer.md` |
| `marche` | `modes/marche.md` |
| `visite` | `modes/visite.md` |
| `offre` | `modes/offre.md` |
| `comparer` | `modes/comparer.md` |
| `suivi` | `modes/suivi.md` |

**Détection automatique :** si l'argument n'est pas un sous-mode mais contient une URL d'annonce (leboncoin, seloger, pap, bienici, logic-immo, ouestfrance-immo, site d'agence…) ou un texte qui ressemble à une annonce (prix en €, m², pièces, DPE), lancer `evaluer`.

Si `python3 immo.py doctor` indique qu'il n'y a pas de configuration, lancer `setup` d'abord, quel que soit l'argument (sauf `marche`, qui fonctionne sans).

## Menu (argument vide)

> **immo-ops** — que veux-tu faire ?
> - `/immo-ops scan` — chercher les nouvelles annonces de tes zones
> - `/immo-ops pipeline` — évaluer les annonces en attente
> - coller une URL ou un texte d'annonce — évaluation complète
> - `/immo-ops marche Fécamp` — prix réels et risques d'une commune
> - `/immo-ops visite` — préparer ou débriefer une visite
> - `/immo-ops offre` — construire une offre et ses arguments
> - `/immo-ops comparer` — départager plusieurs biens
> - `/immo-ops suivi` — où en es-tu
> - `/immo-ops setup` — critères, budget, zones

Toujours répondre en français.
