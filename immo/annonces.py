"""Modèle d'annonce normalisée, préfiltre (critères durs) et stockage local.

Le stockage `data/annonces.json` est la mémoire du scanner : il sert à
dédupliquer, à garder la description complète (pour évaluer sans re-télécharger)
et à suivre l'historique des prix (les baisses sont des arguments de négociation).
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path

from .config import DPE_ORDRE
from .paths import annonces_file

TYPE_LBC = {"1": "maison", "2": "appartement", "3": "terrain", "4": "parking", "5": "autre"}
TYPE_LBC_INV = {v: k for k, v in TYPE_LBC.items()}


def _num(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(" ", "").replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def prix_m2(a: dict) -> int | None:
    if a.get("prix") and a.get("surface"):
        return round(a["prix"] / a["surface"])
    return None


def depuis_leboncoin(ad) -> dict:
    """Convertit un objet `lbc.Ad` (ou équivalent) en annonce normalisée."""
    attrs = getattr(ad, "attributes", None) or {}

    def val(key):
        a = attrs.get(key)
        return getattr(a, "value", None) if a is not None else None

    def label(key):
        a = attrs.get(key)
        return getattr(a, "value_label", None) if a is not None else None

    loc = getattr(ad, "location", None)
    dpe = (val("energy_rate") or "").upper() or None
    ges = (val("ges") or "").upper() or None
    a = {
        "id": f"lbc:{ad.id}",
        "source": "leboncoin",
        "url": ad.url,
        "titre": ad.subject,
        "prix": _num(ad.price),
        "type": TYPE_LBC.get(str(val("real_estate_type") or ""), (label("real_estate_type") or "").lower() or None),
        "surface": _num(val("square")),
        "pieces": _num(val("rooms")),
        "chambres": _num(val("bedrooms")),
        "terrain": _num(val("land_plot_surface")),
        "dpe": dpe if dpe in DPE_ORDRE else None,
        "ges": ges if ges in DPE_ORDRE else None,
        "commune": getattr(loc, "city", None),
        "code_postal": getattr(loc, "zipcode", None),
        "lat": getattr(loc, "lat", None),
        "lng": getattr(loc, "lng", None),
        "publie_le": (getattr(ad, "first_publication_date", None) or "")[:10] or None,
        "description": getattr(ad, "body", None) or "",
        "images": list(getattr(ad, "images", None) or [])[:8],
        "attributs": {k: getattr(v, "value_label", None) for k, v in attrs.items()},
    }
    a["prix_m2"] = prix_m2(a)
    return a


# --------------------------------------------------------------------------- préfiltre


def _texte(a: dict) -> str:
    return f"{a.get('titre') or ''} {a.get('description') or ''}".lower()


def raisons_rejet(a: dict, cfg: dict) -> list[str]:
    """Critères durs uniquement. Une donnée absente ne rejette jamais (on laisse l'évaluation trancher)."""
    r: list[str] = []
    if a.get("type") and cfg["types"] and a["type"] not in cfg["types"]:
        r.append(f"type {a['type']}")
    for cle, champ in (("prix", "prix"), ("surface", "surface"), ("pieces", "pieces"),
                       ("chambres", "chambres"), ("terrain", "terrain")):
        rng = cfg.get(cle) or {}
        v = a.get(champ)
        if v is None:
            continue
        if rng.get("min") is not None and v < rng["min"]:
            r.append(f"{cle} {v:g} < {rng['min']}")
        if rng.get("max") is not None and v > rng["max"]:
            r.append(f"{cle} {v:g} > {rng['max']}")
    dmax = (cfg.get("dpe_max") or "").upper()
    if dmax and a.get("dpe") and DPE_ORDRE.index(a["dpe"]) > DPE_ORDRE.index(dmax):
        r.append(f"DPE {a['dpe']} > {dmax}")
    txt = _texte(a)
    for mot in cfg.get("mots_exclus") or []:
        if mot.lower() in txt:
            r.append(f"mot exclu « {mot} »")
    return r


# --------------------------------------------------------------------------- stockage


def charger(path: Path | None = None) -> dict:
    p = path or annonces_file()
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def sauver(store: dict, path: Path | None = None) -> None:
    p = path or annonces_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".annonces-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, p)


def integrer(store: dict, a: dict, rejet: list[str], aujourdhui: str | None = None) -> str:
    """Ajoute / met à jour une annonce. Retourne 'nouvelle', 'baisse', 'hausse' ou 'connue'."""
    jour = aujourdhui or date.today().isoformat()
    ex = store.get(a["id"])
    if ex is None:
        a = dict(a)
        a.update(vu_le=jour, derniere_vue=jour, historique_prix=[[jour, a.get("prix")]],
                 rejet=rejet, statut_pipeline="rejetee" if rejet else "a_evaluer")
        store[a["id"]] = a
        return "nouvelle"
    ancien = ex.get("prix")
    hist = ex.get("historique_prix") or []
    ex.update({k: v for k, v in a.items() if v not in (None, "", [], {})})
    ex["derniere_vue"] = jour
    ex["rejet"] = rejet
    statut = ex.get("statut_pipeline", "a_evaluer")
    if statut == "rejetee" and not rejet:
        ex["statut_pipeline"] = "a_evaluer"  # ex. baisse de prix sous le plafond
    elif statut == "a_evaluer" and rejet:
        ex["statut_pipeline"] = "rejetee"
    if a.get("prix") is not None and ancien is not None and a["prix"] != ancien:
        hist.append([jour, a["prix"]])
        ex["historique_prix"] = hist
        return "baisse" if a["prix"] < ancien else "hausse"
    return "connue"


def resume(a: dict) -> str:
    """Ligne compacte lisible (pipeline, notifications)."""
    bits = [(a.get("type") or "bien").capitalize()]
    if a.get("pieces"):
        bits.append(f"{a['pieces']:g}p")
    if a.get("surface"):
        bits.append(f"{a['surface']:g} m²")
    if a.get("terrain"):
        bits.append(f"terrain {a['terrain']:g} m²")
    s = " ".join(bits)
    prix = f"{a['prix']:,.0f} €".replace(",", " ") if a.get("prix") else "prix ?"
    pm2 = f" ({a['prix_m2']:,} €/m²)".replace(",", " ") if a.get("prix_m2") else ""
    lieu = f"{a.get('commune') or '?'} ({a.get('code_postal') or '?'})"
    dpe = f" — DPE {a['dpe']}" if a.get("dpe") else " — DPE ?"
    return f"{s} — {prix}{pm2} — {lieu}{dpe}"
