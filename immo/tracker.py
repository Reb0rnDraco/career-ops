"""Tracker des biens (data/biens.md) et vue pipeline (data/pipeline.md).

- `data/biens.md` est la source de vérité des biens évalués : un tableau markdown,
  lisible et versionnable. Toute écriture passe par ce module (écriture atomique).
- `data/pipeline.md` est une VUE régénérée depuis data/annonces.json : ne pas l'éditer
  à la main, utiliser `python3 immo.py pipeline marquer ...`.
"""
from __future__ import annotations

import os
import re
import tempfile
from datetime import date
from pathlib import Path

from . import annonces as A
from .paths import pipeline_file, reports_dir, tracker_file

STATUTS = [
    "Évalué", "À visiter", "Visite prévue", "Visité", "Offre faite",
    "Contre-offre", "Offre acceptée", "Compromis signé", "Acheté",
    "Écarté", "Retiré du marché",
]
COLONNES = ["#", "Date", "Commune", "Bien", "Prix", "€/m²", "Score", "Statut", "Rapport", "Notes", "URL"]
ENTETE = "# Suivi des biens\n\n" \
         "<!-- Généré et mis à jour par `python3 immo.py tracker ...` — évite les éditions manuelles. -->\n\n"


def _norm_statut(s: str) -> str:
    low = s.strip().lower()
    for st in STATUTS:
        if st.lower() == low:
            return st
    alias = {"evalue": "Évalué", "a visiter": "À visiter", "visite": "Visité", "ecarte": "Écarté",
             "offre": "Offre faite", "compromis": "Compromis signé", "retire": "Retiré du marché",
             "achete": "Acheté"}
    import unicodedata
    plain = unicodedata.normalize("NFKD", low).encode("ascii", "ignore").decode()
    if plain in alias:
        return alias[plain]
    raise ValueError(f"Statut inconnu : {s!r}. Valides : {', '.join(STATUTS)}")


def _cell(v) -> str:
    return str(v if v is not None else "—").replace("|", "/").replace("\n", " ").strip() or "—"


def lire(path: Path | None = None) -> list[dict]:
    p = path or tracker_file()
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| #"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(COLONNES):
            continue
        rows.append(dict(zip(COLONNES, cells)))
    return rows


def ecrire(rows: list[dict], path: Path | None = None) -> None:
    p = path or tracker_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: int(r["#"]) if r["#"].isdigit() else 10**9)
    lines = [ENTETE, "| " + " | ".join(COLONNES) + " |", "|" + "|".join("---" for _ in COLONNES) + "|"]
    lines += ["| " + " | ".join(_cell(r.get(c)) for c in COLONNES) + " |" for r in rows]
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".biens-", suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, p)


def prochain_numero() -> int:
    nums = [int(m.group(1)) for f in reports_dir().glob("*.md") if (m := re.match(r"(\d{3,})-", f.name))]
    nums += [int(r["#"]) for r in lire() if r["#"].isdigit()]
    return max(nums, default=0) + 1


def trouver(rows: list[dict], cle: str) -> dict | None:
    """Par numéro (#), par URL, ou par id d'annonce présent dans les notes/URL (lbc:123)."""
    for r in rows:
        if r["#"] == cle.lstrip("0") or r["#"] == cle:
            return r
    for r in rows:
        if cle in (r.get("URL") or "") or cle in (r.get("Notes") or ""):
            return r
    if cle.startswith("lbc:"):
        num = cle.split(":", 1)[1]
        for r in rows:
            if num in (r.get("URL") or ""):
                return r
    return None


def ajouter(num: int, commune: str, bien: str, prix, pm2, score, rapport: str, url: str,
            notes: str = "", statut: str = "Évalué", jour: str | None = None) -> dict:
    """Ajoute OU met à jour (même URL) — jamais de doublon."""
    rows = lire()
    statut = _norm_statut(statut)
    ex = next((r for r in rows if url and url != "—" and r.get("URL") == url), None)
    prix_txt = f"{float(prix):,.0f} €".replace(",", " ") if prix not in (None, "", "—") else "—"
    pm2_txt = f"{int(float(pm2)):,}".replace(",", " ") if pm2 not in (None, "", "—") else "—"
    score_txt = f"{float(score):.1f}/5" if score not in (None, "", "—") else "N/A"
    rapport_txt = f"[{num:03d}](../reports/{rapport})" if rapport else "—"
    row = {"#": str(num), "Date": jour or date.today().isoformat(), "Commune": commune, "Bien": bien,
           "Prix": prix_txt, "€/m²": pm2_txt, "Score": score_txt, "Statut": statut,
           "Rapport": rapport_txt, "Notes": notes or "—", "URL": url or "—"}
    if ex:
        row["#"] = ex["#"]
        rows[rows.index(ex)] = row
    else:
        rows.append(row)
    ecrire(rows)
    return row


def changer_statut(cle: str, statut: str, note: str | None = None) -> dict:
    rows = lire()
    r = trouver(rows, cle)
    if not r:
        raise LookupError(f"Aucun bien ne correspond à {cle!r} dans {tracker_file()}")
    r["Statut"] = _norm_statut(statut)
    if note:
        base = "" if r["Notes"] in ("—", "") else r["Notes"] + " ; "
        r["Notes"] = f"{base}{date.today().isoformat()} {note}"
    ecrire(rows)
    return r


# --------------------------------------------------------------------------- pipeline (vue)

STATUTS_PIPELINE = {"a_evaluer", "evaluee", "ecartee", "rejetee"}


def marquer(store: dict, aid: str, statut: str, rapport: str | None = None) -> dict:
    if statut not in STATUTS_PIPELINE:
        raise ValueError(f"statut pipeline invalide : {statut} ({sorted(STATUTS_PIPELINE)})")
    if aid not in store:
        raise LookupError(f"Annonce inconnue : {aid}")
    store[aid]["statut_pipeline"] = statut
    if rapport:
        store[aid]["rapport"] = rapport
    return store[aid]


def rendre_pipeline(store: dict, path: Path | None = None) -> Path:
    p = path or pipeline_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    groupes = {k: [] for k in ("a_evaluer", "evaluee", "ecartee", "rejetee")}
    for a in store.values():
        groupes.setdefault(a.get("statut_pipeline", "a_evaluer"), []).append(a)
    for g in groupes.values():
        g.sort(key=lambda a: a.get("vu_le") or "", reverse=True)

    def ligne(a, coche=" "):
        baisse = ""
        h = a.get("historique_prix") or []
        if len(h) > 1 and h[0][1] and h[-1][1] and h[-1][1] < h[0][1]:
            baisse = f" — 📉 {h[0][1]:,.0f} → {h[-1][1]:,.0f} €".replace(",", " ")
        rap = f" — rapport {a['rapport']}" if a.get("rapport") else ""
        return f"- [{coche}] `{a['id']}` {A.resume(a)}{baisse}{rap} — {a.get('url')}"

    out = ["# Pipeline des annonces", "",
           "<!-- VUE GÉNÉRÉE depuis data/annonces.json — ne pas éditer. "
           "Utiliser `python3 immo.py pipeline marquer <id> <statut>`. -->", "",
           f"## À évaluer ({len(groupes['a_evaluer'])})", ""]
    out += [ligne(a) for a in groupes["a_evaluer"]] or ["_Rien en attente._"]
    out += ["", f"## Évaluées ({len(groupes['evaluee'])})", ""]
    out += [ligne(a, "x") for a in groupes["evaluee"]] or ["_Aucune._"]
    out += ["", f"## Écartées après lecture ({len(groupes['ecartee'])})", ""]
    out += [ligne(a, "x") for a in groupes["ecartee"]] or ["_Aucune._"]
    out += ["", f"## Rejetées par le préfiltre ({len(groupes['rejetee'])})", "",
            "<details><summary>Voir</summary>", ""]
    out += [f"- `{a['id']}` {A.resume(a)} — ❌ {', '.join(a.get('rejet') or [])}" for a in groupes["rejetee"]]
    out += ["", "</details>", ""]
    p.write_text("\n".join(out), encoding="utf-8")
    return p
