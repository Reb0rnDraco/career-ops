"""Géographie via l'API Découpage administratif (geo.api.gouv.fr, gratuite, sans clé)."""
from __future__ import annotations

import math
import re
import unicodedata

from . import net

API = "https://geo.api.gouv.fr"
FIELDS = "nom,code,codesPostaux,centre,codeDepartement,codeRegion,population"


def norm(s: str) -> str:
    """Normalise un nom de commune pour comparaison (accents, tirets, 'St', casse)."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    s = re.sub(r"\bste\b", "sainte", s)
    s = re.sub(r"\bst\b", "saint", s)
    return s


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _centre(c: dict) -> tuple[float, float] | None:
    coords = (c.get("centre") or {}).get("coordinates")
    return (coords[1], coords[0]) if coords else None


def chercher_commune(nom: str, code_postal: str | None = None, code_insee: str | None = None) -> dict:
    """Retourne la commune la plus probable : {nom, code, lat, lng, codesPostaux, ...}."""
    if code_insee:
        c = net.get_json(f"{API}/communes/{code_insee}", ttl_hours=24 * 30, params={"fields": FIELDS})
        return _format(c)
    params = {"fields": FIELDS, "boost": "population", "limit": 10}
    if code_postal:
        params["codePostal"] = code_postal
        res = net.get_json(f"{API}/communes", ttl_hours=24 * 30, params=params)
        target = norm(nom)
        exact = [c for c in res if norm(c["nom"]) == target]
        if exact or len(res) == 1:
            return _format((exact or res)[0])
        loose = [c for c in res if target and (target in norm(c["nom"]) or norm(c["nom"]) in target)]
        if loose:
            return _format(loose[0])
        params.pop("codePostal")
    params["nom"] = nom
    res = net.get_json(f"{API}/communes", ttl_hours=24 * 30, params=params)
    if not res:
        raise LookupError(f"Commune introuvable : {nom!r} {code_postal or ''}")
    target = norm(nom)
    exact = [c for c in res if norm(c["nom"]) == target]
    return _format((exact or res)[0])


def _format(c: dict) -> dict:
    ll = _centre(c)
    return {
        "nom": c["nom"],
        "code": c["code"],
        "codesPostaux": c.get("codesPostaux", []),
        "codeDepartement": c.get("codeDepartement"),
        "codeRegion": c.get("codeRegion"),
        "population": c.get("population"),
        "lat": ll[0] if ll else None,
        "lng": ll[1] if ll else None,
    }


def communes_autour(lat: float, lng: float, rayon_km: float, code_region: str) -> list[dict]:
    """Communes dont le centre est à moins de rayon_km, triées par distance."""
    res = net.get_json(
        f"{API}/communes", ttl_hours=24 * 30, params={"codeRegion": code_region, "fields": FIELDS}
    )
    out = []
    for c in res:
        ll = _centre(c)
        if not ll:
            continue
        d = haversine_km(lat, lng, *ll)
        if d <= rayon_km:
            f = _format(c)
            f["distance_km"] = round(d, 1)
            out.append(f)
    return sorted(out, key=lambda x: x["distance_km"])


def resoudre_zone(zone: dict) -> dict:
    """Une zone de config -> {nom, lat, lng, rayon_km, code}."""
    rayon = float(zone.get("rayon_km", 10))
    if "lat" in zone and "lng" in zone:
        return {"nom": zone.get("commune") or zone.get("nom") or "zone", "lat": float(zone["lat"]),
                "lng": float(zone["lng"]), "rayon_km": rayon, "code": zone.get("code_insee")}
    c = chercher_commune(zone["commune"], zone.get("code_postal"), zone.get("code_insee"))
    return {"nom": c["nom"], "lat": c["lat"], "lng": c["lng"], "rayon_km": rayon, "code": c["code"],
            "codeRegion": c["codeRegion"]}
