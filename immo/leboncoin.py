"""Scan Leboncoin via la librairie non officielle `lbc` (zéro token LLM).

Leboncoin protège son API (DataDome). Le scan reste volontairement lent et modeste :
quelques pages, des pauses aléatoires, aucune parallélisation. En cas de 403,
on s'arrête proprement au lieu d'insister.
"""
from __future__ import annotations

import random
import sys
import time
from typing import Callable, Iterable

from .annonces import TYPE_LBC_INV, depuis_leboncoin


class LbcIndisponible(Exception):
    pass


class LbcBloque(Exception):
    pass


def _import_lbc():
    try:
        import lbc  # noqa: F401
        return lbc
    except ImportError as e:  # pragma: no cover - dépend de l'environnement
        raise LbcIndisponible(
            "La librairie `lbc` n'est pas installée. Lance : pip install -r requirements.txt"
        ) from e


def _range(rng: dict | None, defaut_max: int) -> list[int] | None:
    rng = rng or {}
    if rng.get("min") is None and rng.get("max") is None:
        return None
    return [int(rng.get("min") or 0), int(rng.get("max") or defaut_max)]


def parametres_recherche(cfg: dict) -> dict:
    """Traduit les critères en filtres Leboncoin (les filtres serveur réduisent le volume)."""
    kw: dict = {}
    types = [TYPE_LBC_INV[t] for t in cfg["types"] if t in TYPE_LBC_INV]
    if types:
        kw["real_estate_type"] = types
    for cle, lbc_key, dmax in (("prix", "price", 100_000_000), ("surface", "square", 100_000),
                               ("pieces", "rooms", 99), ("terrain", "land_plot_surface", 10_000_000)):
        r = _range(cfg.get(cle), dmax)
        if r:
            kw[lbc_key] = r
    return kw


def _is_blocked(exc: Exception) -> bool:
    txt = f"{type(exc).__name__} {exc}".lower()
    return "403" in txt or "datadome" in txt or "forbidden" in txt


def scanner(cfg: dict, zones: Iterable[dict], log: Callable[[str], None] = lambda m: print(m, file=sys.stderr),
            client=None, sleep=time.sleep, lbc_module=None) -> list[dict]:
    """Retourne la liste brute d'annonces normalisées (avant préfiltre et dédup)."""
    lbc = lbc_module or _import_lbc()
    if client is None:
        client = lbc.Client()
    sc = cfg["scan"]
    pages = int(sc.get("pages_max", 2))
    categorie = "IMMOBILIER_VENTES_IMMOBILIERES" if cfg["projet"] == "achat" else "IMMOBILIER_LOCATIONS"
    proprio = {"particuliers": "PRIVATE", "pros": "PRO"}.get(sc.get("proprietaire", "tous"))

    def pause():
        sleep(random.uniform(float(sc.get("delai_min_s", 3)), float(sc.get("delai_max_s", 7))))

    def run(label: str, **kwargs):
        out = []
        for page in range(1, pages + 1):
            try:
                res = client.search(page=page, limit=35, **kwargs)
            except Exception as e:  # noqa: BLE001 - la lib lève des exceptions variées
                if _is_blocked(e):
                    raise LbcBloque(
                        "Leboncoin a bloqué la requête (403/DataDome). Réessaie plus tard, "
                        "réduis pages_max, ou colle les URL d'annonces à la main."
                    ) from e
                log(f"  ⚠ {label} page {page} : {e}")
                break
            ads = list(getattr(res, "ads", []) or [])
            out.extend(depuis_leboncoin(ad) for ad in ads)
            log(f"  {label} p{page} : {len(ads)} annonces")
            if len(ads) < 35 or page >= (getattr(res, "max_pages", None) or pages):
                break
            pause()
        return out

    resultats: list[dict] = []
    first = True
    for url in cfg.get("recherches_url") or []:
        if not first:
            pause()
        first = False
        resultats += run("recherche enregistrée", url=url)

    if zones:
        filtres = parametres_recherche(cfg)
        lbc_mod = lbc
        for z in zones:
            if not first:
                pause()
            first = False
            kwargs = dict(
                category=getattr(lbc_mod.Category, categorie),
                sort=lbc_mod.Sort.NEWEST,
                locations=[lbc_mod.City(lat=z["lat"], lng=z["lng"], radius=int(z["rayon_km"] * 1000), city=z["nom"])],
                **filtres,
            )
            if proprio:
                kwargs["owner_type"] = getattr(lbc_mod.OwnerType, proprio)
            resultats += run(f"{z['nom']} +{z['rayon_km']:g} km", **kwargs)
    return resultats
