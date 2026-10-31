"""Risques naturels et technologiques via l'API Géorisques (gratuite).

Utilisé à l'échelle de la commune (GASPAR) et, si on a des coordonnées, de l'adresse.
L'API évolue : en cas d'échec, l'agent doit renvoyer vers https://www.georisques.gouv.fr
(rapport « Mes risques » par adresse) plutôt que d'inventer.
"""
from __future__ import annotations

import os

from . import net

API = os.environ.get("GEORISQUES_API", "https://georisques.gouv.fr/api/v1")


def _data(payload) -> list:
    if isinstance(payload, dict):
        return payload.get("data") or []
    return payload or []


def risques_commune(insee: str) -> list[str]:
    out = []
    for item in _data(net.get_json(f"{API}/gaspar/risques", ttl_hours=24 * 30, params={"code_insee": insee})):
        for r in item.get("risques_detail") or []:
            lib = r.get("libelle_risque_long") or r.get("libelle_risque")
            if lib and lib not in out:
                out.append(lib)
    return out


def catnat(insee: str, max_items: int = 15) -> list[dict]:
    items = _data(net.get_json(f"{API}/gaspar/catnat", ttl_hours=24 * 30,
                               params={"code_insee": insee, "page_size": 100}))
    out = [{"debut": i.get("date_debut_evt"), "fin": i.get("date_fin_evt"),
            "risque": i.get("libelle_risque_jo"), "arrete": i.get("date_publication_jo")} for i in items]
    out.sort(key=lambda x: x["debut"] or "", reverse=True)
    return out[:max_items]


def cavites(insee: str) -> dict:
    """Cavités souterraines recensées (marnières en Normandie, carrières...)."""
    items = _data(net.get_json(f"{API}/cavites", ttl_hours=24 * 30,
                               params={"code_insee": insee, "page_size": 100}))
    types: dict[str, int] = {}
    for c in items:
        t = c.get("type") or c.get("type_cavite") or "inconnu"
        types[t] = types.get(t, 0) + 1
    return {"total": len(items), "par_type": types}


def radon(insee: str) -> str | None:
    items = _data(net.get_json(f"{API}/radon", ttl_hours=24 * 30, params={"code_insee": insee}))
    return str(items[0].get("classe_potentiel")) if items else None


def rapport(insee: str) -> dict:
    """Agrège tout ce qui répond ; chaque bloc en échec est signalé, jamais inventé."""
    res: dict = {"code_insee": insee, "erreurs": {},
                 "lien": f"https://www.georisques.gouv.fr/mes-risques/connaitre-les-risques-pres-de-chez-moi"}
    for cle, fn in (("risques", risques_commune), ("catnat", catnat), ("cavites", cavites), ("radon", radon)):
        try:
            res[cle] = fn(insee)
        except Exception as e:  # noqa: BLE001
            res["erreurs"][cle] = str(e)[:200]
    return res
