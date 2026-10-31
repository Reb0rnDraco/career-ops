"""Chargement et validation de config/criteres.yml."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .paths import config_file, example_config_file

TYPES_VALIDES = {"maison", "appartement", "terrain", "parking", "autre"}
DPE_ORDRE = "ABCDEFG"

DEFAUTS: dict[str, Any] = {
    "projet": "achat",
    "usage": "residence_principale",
    "types": ["maison"],
    "zones": [],
    "prix": {},
    "surface": {},
    "pieces": {},
    "chambres": {},
    "terrain": {},
    "dpe_max": None,
    "mots_exclus": ["viager", "nue-propriété", "nue propriété", "fonds de commerce"],
    "mots_bonus": [],
    "trajets": [],
    "recherches_url": [],
    "financement": {
        "apport": 0,
        "taux_annuel_pct": 3.5,
        "duree_ans": 25,
        "assurance_annuelle_pct": 0.3,
        "frais_notaire_ancien_pct": 8.0,
        "frais_notaire_neuf_pct": 2.5,
        "endettement_max_pct": 35,
    },
    "ponderations": {
        "prix_marche": 25,
        "adequation": 25,
        "etat_travaux": 20,
        "localisation": 15,
        "risques": 15,
    },
    "scan": {"pages_max": 2, "delai_min_s": 3, "delai_max_s": 7, "proprietaire": "tous"},
    "notifications": {"ntfy_url": None},
    "langue": "fr",
}


class ConfigError(Exception):
    pass


def _merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path: Path | None = None, allow_example: bool = False) -> dict:
    p = path or config_file()
    if not p.exists():
        if allow_example and example_config_file().exists():
            p = example_config_file()
        else:
            raise ConfigError(
                f"{p} introuvable. Lance le mode `setup` (ou copie config/criteres.example.yml)."
            )
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    cfg = _merge(DEFAUTS, raw)
    problems = validate(cfg)
    if problems:
        raise ConfigError("Configuration invalide :\n  - " + "\n  - ".join(problems))
    cfg["_source"] = str(p)
    return cfg


def validate(cfg: dict) -> list[str]:
    pb: list[str] = []
    if cfg["projet"] not in ("achat", "location"):
        pb.append("projet doit valoir 'achat' ou 'location'")
    bad = [t for t in cfg["types"] if t not in TYPES_VALIDES]
    if bad:
        pb.append(f"types inconnus : {bad} (valides : {sorted(TYPES_VALIDES)})")
    if not cfg["zones"] and not cfg["recherches_url"]:
        pb.append("au moins une zone (ou une recherche_url Leboncoin) est requise")
    for i, z in enumerate(cfg["zones"]):
        if not isinstance(z, dict) or not (z.get("commune") or ("lat" in z and "lng" in z)):
            pb.append(f"zones[{i}] : il faut 'commune' (ou 'lat' + 'lng')")
        elif float(z.get("rayon_km", 10)) <= 0:
            pb.append(f"zones[{i}] : rayon_km doit être > 0")
    if cfg["dpe_max"] and str(cfg["dpe_max"]).upper() not in DPE_ORDRE:
        pb.append("dpe_max doit être une lettre de A à G")
    for key in ("prix", "surface", "pieces", "chambres", "terrain"):
        rng = cfg.get(key) or {}
        lo, hi = rng.get("min"), rng.get("max")
        if lo is not None and hi is not None and lo > hi:
            pb.append(f"{key}.min > {key}.max")
    if sum(cfg["ponderations"].values()) <= 0:
        pb.append("ponderations : la somme doit être > 0")
    return pb
