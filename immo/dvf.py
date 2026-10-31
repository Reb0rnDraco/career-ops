"""Demandes de Valeurs Foncières (DVF) — ventes réelles, open data Etalab (geo-dvf).

Source : https://files.data.gouv.fr/geo-dvf/latest/csv/{annee}/communes/{dep}/{insee}.csv
Une ligne = un couple (mutation, local/parcelle) ; une vente apparaît donc sur plusieurs
lignes. On regroupe par id_mutation et on ne garde que les ventes « propres » d'un seul
logement (maison OU appartement), sinon le prix au m² n'a pas de sens.

Limites à rappeler dans les rapports : décalage de ~6 mois, pas d'Alsace-Moselle ni de
Mayotte, pas l'état du bien, et une vente « maison + grand terrain » gonfle le €/m² bâti.
"""
from __future__ import annotations

import csv
import io
import statistics
from collections import defaultdict
from datetime import date

from . import net

BASE = "https://files.data.gouv.fr/geo-dvf/latest/csv"
TYPES = {"maison": "Maison", "appartement": "Appartement"}
PM2_MIN, PM2_MAX = 200, 20000


def _f(v) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def url_commune(annee: int, insee: str) -> str:
    dep = insee[:3] if insee.startswith("97") else insee[:2]
    return f"{BASE}/{annee}/communes/{dep}/{insee}.csv"


def lignes_commune(insee: str, annees: list[int]) -> tuple[list[dict], list[int]]:
    rows, ok = [], []
    for an in annees:
        try:
            txt = net.get_text(url_commune(an, insee), ttl_hours=24 * 14)
        except net.NotFound:
            continue
        ok.append(an)
        rows.extend(csv.DictReader(io.StringIO(txt)))
    return rows, ok


def annees_disponibles(nb: int = 5, aujourdhui: date | None = None) -> list[int]:
    """Années à tenter (la plus récente peut ne pas exister encore : 404 ignoré)."""
    y = (aujourdhui or date.today()).year
    return list(range(y, y - nb - 1, -1))


def ventes(rows: list[dict], type_bien: str) -> list[dict]:
    """Regroupe les lignes par mutation et renvoie une vente propre par mutation."""
    cible = TYPES[type_bien]
    groupes: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groupes[r["id_mutation"]].append(r)

    out = []
    for mid, g in groupes.items():
        if g[0].get("nature_mutation") != "Vente":
            continue
        logements = {}
        for r in g:
            tl = r.get("type_local")
            if tl in ("Maison", "Appartement"):
                cle = (tl, r.get("surface_reelle_bati"), r.get("nombre_pieces_principales"),
                       r.get("adresse_numero"), r.get("adresse_nom_voie"), r.get("lot1_numero"))
                logements[cle] = r
        if len(logements) != 1:
            continue  # aucun logement, ou vente groupée de plusieurs logements
        (tl, *_), r = next(iter(logements.items()))
        if tl != cible:
            continue
        surface, valeur = _f(r.get("surface_reelle_bati")), _f(r.get("valeur_fonciere"))
        if not surface or not valeur or surface < 9 or valeur < 10_000:
            continue
        pm2 = valeur / surface
        if not PM2_MIN <= pm2 <= PM2_MAX:
            continue
        parcelles = {(x.get("id_parcelle"), x.get("code_nature_culture"), x.get("surface_terrain"))
                     for x in g if _f(x.get("surface_terrain"))}
        terrain = sum(_f(p[2]) for p in parcelles) or None
        adresse = " ".join(filter(None, [r.get("adresse_numero"), r.get("adresse_suffixe"),
                                         r.get("adresse_nom_voie")])).strip()
        out.append({
            "id_mutation": mid,
            "date": r.get("date_mutation"),
            "prix": round(valeur),
            "surface": surface,
            "pieces": _f(r.get("nombre_pieces_principales")),
            "terrain": terrain,
            "prix_m2": round(pm2),
            "adresse": adresse or None,
            "commune": r.get("nom_commune"),
            "lat": _f(r.get("latitude")),
            "lng": _f(r.get("longitude")),
        })
    return sorted(out, key=lambda v: v["date"] or "", reverse=True)


def _stats(vals: list[float]) -> dict:
    if not vals:
        return {"n": 0}
    d = {"n": len(vals), "mediane": round(statistics.median(vals))}
    if len(vals) >= 4:
        q = statistics.quantiles(vals, n=4)
        d.update(q1=round(q[0]), q3=round(q[2]))
    return d


def analyse(vts: list[dict], surface: float | None = None, terrain: float | None = None,
            nb_comparables: int = 10) -> dict:
    """Statistiques €/m² + comparables les plus proches en surface (et terrain si fourni)."""
    res = {"global": _stats([v["prix_m2"] for v in vts]), "par_annee": {}}
    par_an: dict[str, list[float]] = defaultdict(list)
    for v in vts:
        par_an[(v["date"] or "????")[:4]].append(v["prix_m2"])
    res["par_annee"] = {an: _stats(x) for an, x in sorted(par_an.items())}
    if surface:
        bande = [v for v in vts if 0.7 * surface <= v["surface"] <= 1.3 * surface]
        res["surface_similaire"] = {"bande_m2": [round(0.7 * surface), round(1.3 * surface)],
                                    **_stats([v["prix_m2"] for v in bande])}

        def dist(v):
            d = abs(v["surface"] - surface) / surface
            if terrain and v.get("terrain"):
                d += 0.3 * abs(v["terrain"] - terrain) / max(terrain, 1)
            return d
        res["comparables"] = sorted(vts, key=dist)[:nb_comparables]
    else:
        res["comparables"] = vts[:nb_comparables]
    return res


def positionner(prix_m2: float | None, stats: dict) -> str | None:
    """Situe un €/m² demandé par rapport à la distribution (texte court)."""
    if not prix_m2 or not stats.get("n"):
        return None
    med = stats["mediane"]
    ecart = (prix_m2 - med) / med * 100
    if "q1" in stats and prix_m2 < stats["q1"]:
        zone = "sous le 1er quartile"
    elif "q3" in stats and prix_m2 > stats["q3"]:
        zone = "au-dessus du 3e quartile"
    else:
        zone = "dans l'intervalle interquartile" if "q1" in stats else "proche de la médiane"
    return f"{ecart:+.0f} % vs médiane ({med} €/m², n={stats['n']}), {zone}"
