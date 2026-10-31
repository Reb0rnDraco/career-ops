"""Temps de trajet voiture : OSRM public si joignable, sinon estimation à vol d'oiseau.

Le serveur de démo OSRM est limité ; ne jamais boucler dessus. Le résultat indique
toujours sa méthode pour que le rapport puisse la citer.
"""
from __future__ import annotations

from . import net
from .geo import haversine_km

OSRM = "https://router.project-osrm.org/route/v1/driving"


def trajet(lat1: float, lng1: float, lat2: float, lng2: float) -> dict:
    try:
        data = net.get_json(f"{OSRM}/{lng1},{lat1};{lng2},{lat2}", ttl_hours=24 * 30,
                            params={"overview": "false"})
        r = data["routes"][0]
        return {"minutes": round(r["duration"] / 60), "km": round(r["distance"] / 1000, 1), "methode": "osrm"}
    except Exception:  # noqa: BLE001
        d = haversine_km(lat1, lng1, lat2, lng2)
        km = d * 1.3  # détour routier moyen
        return {"minutes": round(km / 55 * 60), "km": round(km, 1), "methode": "estimation vol d'oiseau ×1,3 à 55 km/h"}
