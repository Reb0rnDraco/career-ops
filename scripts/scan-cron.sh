#!/usr/bin/env bash
# Scan planifié (zéro token) : à lancer par cron, 1 à 3 fois par jour maximum.
#   crontab -e
#   17 8,19 * * * /chemin/vers/immo-ops/scripts/scan-cron.sh >> /chemin/vers/immo-ops/data/scan.log 2>&1
# Les nouvelles annonces et baisses de prix arrivent par ntfy si notifications.ntfy_url est défini.
# L'évaluation (qui consomme des tokens) reste manuelle : /immo-ops pipeline.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python

# Petit décalage aléatoire (0-10 min) pour ne pas taper Leboncoin à heure fixe.
sleep $(( RANDOM % 600 ))

echo "=== $(date -Iseconds) scan ==="
$PY immo.py scan || echo "scan terminé avec le code $? (voir message ci-dessus)"
