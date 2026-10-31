# Mode : setup — premier lancement ou changement de critères

But : produire `config/criteres.yml` (valide) et `modes/_profil.md`, par la conversation, sans faire remplir un formulaire.

## 1. État des lieux

```bash
python3 immo.py doctor
```

- `config/criteres.yml` existe déjà → demander ce qu'il faut changer, modifier seulement ces champs, revalider.
- module `lbc` manquant → proposer `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`. Demander avant d'installer.

## 2. Questions (en une ou deux fois, pas un interrogatoire)

1. **Projet** : acheter ou louer ? Résidence principale, secondaire, ou investissement locatif ?
2. **Où** : communes pivots et rayon acceptable. Proposer `python3 immo.py communes --autour <commune> --rayon <km>` pour montrer ce que couvre le rayon.
3. **Quoi** : maison / appartement, surface mini, chambres, terrain, extérieur, garage…
4. **Budget** : prix maxi FAI (frais d'agence inclus), apport, durée de prêt envisagée, taux obtenu s'il est connu. Les revenus sont optionnels (ils servent seulement au taux d'endettement) : ne pas insister.
5. **Travaux** : prêt à rénover ? Jusqu'à quel montant ? DPE maximum toléré ?
6. **Trajets** : lieux à rejoindre souvent (travail, école, famille) et temps maximum en voiture.
7. **Éliminatoires et coups de cœur** : ce qui fait fuir, ce qui fait craquer (→ `mots_exclus`, `mots_bonus`).
8. **Ce qui compte le plus** : pour régler les `ponderations` (ex. « le prix avant tout » → `prix_marche: 35`).

Si l'utilisateur a déjà une recherche enregistrée sur Leboncoin, lui proposer d'en coller l'URL dans `recherches_url` : c'est le moyen le plus fiable de reproduire exactement ses filtres.

## 3. Écriture

1. Partir de `config/criteres.example.yml`, écrire `config/criteres.yml` avec ses réponses (garder les commentaires utiles, supprimer les exemples qui ne le concernent pas).
2. Écrire `modes/_profil.md` depuis `templates/_profil.template.md` : situation, projet, priorités, tolérance travaux, calendrier — **uniquement ce qu'il a dit**.
3. Valider : `python3 immo.py doctor`. Corriger jusqu'à ce que la config soit valide.

Rappeler en une phrase que `config/criteres.yml`, `modes/_profil.md`, `data/` et `reports/` sont ignorés par git : rien de personnel ne part sur GitHub.

## 4. Suite

> C'est prêt. Tu peux lancer `/immo-ops scan`, coller une annonce, ou demander `/immo-ops marche <commune>` pour voir les prix réels du secteur.

Proposer ensuite l'automatisation : un scan planifié (`scripts/scan-cron.sh`, cron sur le homelab, ou une tâche planifiée Claude) avec notification ntfy, en rappelant de rester à 1–3 scans par jour.
