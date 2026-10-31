"""Résolution des chemins : couche système (le dépôt) vs couche utilisateur (tes données).

DATA_ROOT = $IMMO_OPS_DATA_DIR si défini, sinon la racine du projet.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def data_root() -> Path:
    env = os.environ.get("IMMO_OPS_DATA_DIR")
    if env:
        p = Path(env)
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()
    return PROJECT_ROOT


def config_file() -> Path:
    return data_root() / "config" / "criteres.yml"


def example_config_file() -> Path:
    return PROJECT_ROOT / "config" / "criteres.example.yml"


def data_dir() -> Path:
    d = data_root() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def reports_dir() -> Path:
    d = data_root() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_dir() -> Path:
    d = data_root() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def annonces_file() -> Path:
    return data_dir() / "annonces.json"


def pipeline_file() -> Path:
    return data_dir() / "pipeline.md"


def tracker_file() -> Path:
    return data_dir() / "biens.md"
