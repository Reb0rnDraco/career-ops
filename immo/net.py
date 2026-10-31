"""Petit client HTTP avec cache disque (les données publiques changent peu)."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

from . import __version__
from .paths import cache_dir

USER_AGENT = f"immo-ops/{__version__} (+recherche immobiliere personnelle)"
TIMEOUT = 30


class NotFound(Exception):
    pass


def _cache_path(url: str, suffix: str) -> Path:
    h = hashlib.sha1(url.encode()).hexdigest()[:20]
    d = cache_dir() / "http"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{h}{suffix}"


def get_text(url: str, ttl_hours: float = 24, params: dict | None = None) -> str:
    full = requests.Request("GET", url, params=params).prepare().url
    cp = _cache_path(full, ".txt")
    miss = _cache_path(full, ".404")
    now = time.time()
    if ttl_hours > 0:
        if cp.exists() and now - cp.stat().st_mtime < ttl_hours * 3600:
            return cp.read_text(encoding="utf-8")
        if miss.exists() and now - miss.stat().st_mtime < ttl_hours * 3600:
            raise NotFound(full)
    r = requests.get(full, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    if r.status_code == 404:
        miss.write_text("", encoding="utf-8")
        raise NotFound(full)
    r.raise_for_status()
    r.encoding = r.encoding or "utf-8"
    text = r.text
    if ttl_hours > 0:
        cp.write_text(text, encoding="utf-8")
    return text


def get_json(url: str, ttl_hours: float = 24, params: dict | None = None):
    return json.loads(get_text(url, ttl_hours=ttl_hours, params=params))
