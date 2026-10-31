# immo-ops

**Agent IA de recherche immobilière, local et open source**, pour la France. C'est une adaptation de [career-ops](https://github.com/santifer/career-ops) (recherche d'emploi) à l'achat ou à la location d'un bien.

> Les agences utilisent des outils pour vendre au meilleur prix. immo-ops donne à l'acheteur les données pour acheter au juste prix.

Ce que fait immo-ops, depuis Claude Code (ou tout CLI d'agent compatible) :

- **Scanner** Leboncoin sur tes zones (commune + rayon), avec un préfiltre selon tes critères durs. Le scan ne consomme aucun token LLM, et il te notifie des nouvelles annonces et des **baisses de prix**.
- **Évaluer** une annonce (de Leboncoin, SeLoger, PAP, d'une agence…) dans un rapport A→G :
  - le prix demandé comparé aux **ventes réelles DVF** de la commune, avec médiane, quartiles, tendance et comparables ;
  - le coût réel (frais de notaire, travaux estimés, mensualité) ;
  - les risques **Géorisques** (inondation, arrêtés CatNat, cavités et marnières, radon) ;
  - les temps de trajet, les signaux d'alerte, un score sur 5 et les questions à poser.
- **Suivre** chaque bien dans un tableau markdown, de « Évalué » à « Acheté ».
- **Préparer** une visite (fiche sur mesure, débrief), une **offre** (fourchette de prix, arguments sourcés, lettre d'offre) ou une **comparaison** entre plusieurs biens.
- **Étudier un marché** : prix réels et risques de plusieurs communes, pour savoir où ton budget achète quoi.

Toutes les données publiques utilisées sont gratuites et sans clé API : [DVF géolocalisées](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres-geolocalisees/) (Etalab), [API Découpage administratif](https://geo.api.gouv.fr), [Géorisques](https://www.georisques.gouv.fr/doc-api) et [OSRM](https://project-osrm.org/) pour les trajets.

## Installation

Il faut Python 3.10 ou plus récent et [Claude Code](https://claude.com/claude-code).

```bash
git clone -b immo-ops https://github.com/Reb0rnDraco/career-ops.git immo-ops
cd immo-ops
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 immo.py doctor
claude          # puis : /immo-ops setup
```

Le mode `setup` te pose quelques questions (zones, type de bien, budget, travaux, trajets), puis écrit `config/criteres.yml` et `modes/_profil.md`.

## Utilisation

| Commande | Effet |
|---|---|
| `/immo-ops scan` | nouvelles annonces + tri rapide |
| coller une URL ou un texte d'annonce | rapport complet dans `reports/` + ligne dans `data/biens.md` |
| `/immo-ops pipeline` | évaluer les annonces en attente |
| `/immo-ops marche Fécamp` | prix réels et risques d'une commune ou d'un secteur |
| `/immo-ops visite` | fiche de visite, puis débrief |
| `/immo-ops offre` | prix d'ouverture / cible / plafond, arguments, lettre d'offre (brouillon) |
| `/immo-ops comparer` | départager plusieurs biens à coût réel égal |
| `/immo-ops suivi` | état de la recherche et prochaine action |

Les outils sont aussi utilisables sans agent :

```bash
python3 immo.py dvf --commune "Le Havre" --type appartement --surface 70 --prix-m2 2600
python3 immo.py risques --commune Rouen
python3 immo.py budget --prix 245000 --travaux 15000
python3 immo.py trajet --de "Fécamp" --vers "Le Havre"
```

### Scan automatique (cron, homelab)

```bash
# 2 scans par jour, décalage aléatoire inclus dans le script
17 8,19 * * * /chemin/immo-ops/scripts/scan-cron.sh >> /chemin/immo-ops/data/scan.log 2>&1
```

Avec `notifications.ntfy_url` dans ta config (ntfy.sh ou ton instance auto-hébergée), tu reçois les nouvelles annonces et les baisses de prix sur ton téléphone. L'évaluation, elle, reste manuelle (`/immo-ops pipeline`) parce qu'elle consomme des tokens.

## Architecture

Elle reprend les principes de career-ops :

- **les modes markdown sont le cerveau** : `modes/_shared.md` contient le barème, et chaque mode a son fichier. On personnalise sans toucher au code.
- **des scripts sans token** : `immo.py` + `immo/` font le scan, la DVF, Géorisques, le budget et le suivi.
- **les fichiers font foi** : `data/biens.md` (suivi), `data/annonces.json` (mémoire du scanner), `reports/`.
- **séparation système / utilisateur** : tes critères, ton profil, tes données et tes rapports sont ignorés par git, donc rien de personnel n'arrive sur GitHub. `IMMO_OPS_DATA_DIR` permet de les placer ailleurs (par exemple un volume de ton serveur).
- **l'humain décide** : l'agent rédige les messages et les offres, et c'est toi qui les envoies.

```
scan (Leboncoin) ─► préfiltre ─► data/annonces.json ─► data/pipeline.md
                                                 │
coller une annonce ──────────────────────────────┤
                                                 ▼
               immo.py contexte (DVF + Géorisques + trajets + budget)
                                                 ▼
                 modes/evaluer.md ─► reports/NNN-….md ─► data/biens.md
                                                 ▼
                        visite ─► offre ─► compromis
```

## Limites, et ce qu'immo-ops ne fait pas

- **Leboncoin uniquement en scan automatique.** Le scan passe par [`lbc`](https://github.com/etienne-hd/lbc), un client non officiel. Leboncoin est protégé par DataDome : en cas de blocage, le scan s'arrête au lieu d'insister. Reste modeste (2 pages par zone, 1 à 3 scans par jour) et respecte les CGU du site. Les annonces d'autres portails s'évaluent en les collant.
- **La DVF reflète le passé** : environ 6 mois de retard, l'état des biens n'y figure pas, et l'Alsace-Moselle et Mayotte ne sont pas couvertes. Dans une petite commune, il y a peu de ventes et la médiane est fragile (le rapport l'indique).
- **Ce n'est pas un conseil financier ou juridique.** Le financement se valide avec ta banque ou ton courtier, l'acte avec le notaire, et l'état du bien avec le dossier de diagnostics.

## Tests

```bash
python3 -m pytest -q     # réseau simulé, aucune requête réelle
```

## Licence

MIT. Basé sur [career-ops](https://github.com/santifer/career-ops) de santifer (MIT).
