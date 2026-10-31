#!/usr/bin/env python3
"""immo-ops — outils zéro-token appelés par l'agent (et utilisables à la main).

  python3 immo.py doctor                       Vérifie installation, config et sources
  python3 immo.py scan [--dry-run]             Scanne Leboncoin selon config/criteres.yml
  python3 immo.py pipeline [list|show|marquer] Annonces en attente d'évaluation
  python3 immo.py contexte <id|--commune ...>  Tout le contexte d'évaluation en un JSON
  python3 immo.py dvf --commune X --type maison [--surface 110]
  python3 immo.py risques --commune X
  python3 immo.py trajet --de X --vers Y
  python3 immo.py budget --prix 250000 [--travaux 20000] [--neuf]
  python3 immo.py tracker [list|ajouter|statut|numero]
  python3 immo.py communes --autour X --rayon 15
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from immo import annonces as A
from immo import budget as B
from immo import config as C
from immo import dvf as D
from immo import geo as G
from immo import notify as N
from immo import risques as R
from immo import tracker as T
from immo import trajet as TR
from immo.paths import config_file, data_root


def out(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def err(msg: str, code: int = 1) -> None:
    print(f"✖ {msg}", file=sys.stderr)
    sys.exit(code)


def _cfg(allow_example=False):
    try:
        return C.load(allow_example=allow_example)
    except C.ConfigError as e:
        err(str(e), 2)


def _lieu(texte: str) -> dict:
    """'lat,lng' ou 'Commune' ou 'Commune 76400'."""
    parts = texte.replace(";", ",").split(",")
    if len(parts) == 2:
        try:
            return {"nom": texte, "lat": float(parts[0]), "lng": float(parts[1])}
        except ValueError:
            pass
    toks = texte.split()
    cp = toks[-1] if toks and toks[-1].isdigit() and len(toks[-1]) == 5 else None
    nom = " ".join(toks[:-1]) if cp else texte
    return G.chercher_commune(nom, cp)


# --------------------------------------------------------------------------- doctor


def cmd_doctor(a):
    ok = True

    def ligne(etat, msg):
        nonlocal ok
        ok &= etat != "✖"
        print(f"{etat} {msg}")

    ligne("✔" if sys.version_info >= (3, 10) else "✖", f"Python {sys.version.split()[0]} (≥ 3.10 requis)")
    for mod, why in (("yaml", "pyyaml"), ("requests", "requests"), ("lbc", "lbc — scan Leboncoin")):
        try:
            __import__(mod)
            ligne("✔", f"module {why}")
        except ImportError:
            ligne("✖" if mod != "lbc" else "⚠", f"module {why} manquant → pip install -r requirements.txt")
    print(f"• Données : {data_root()}")
    if not config_file().exists():
        ligne("✖", f"{config_file()} absent → lancer le mode `setup`")
        onboarding = True
    else:
        onboarding = False
        try:
            cfg = C.load()
            ligne("✔", f"config valide ({len(cfg['zones'])} zone(s), types {cfg['types']}, projet {cfg['projet']})")
        except C.ConfigError as e:
            ligne("✖", str(e))
    profil = data_root() / "modes" / "_profil.md"
    ligne("✔" if profil.exists() else "⚠", "modes/_profil.md (contexte personnel)" if profil.exists()
          else "modes/_profil.md absent → le mode `setup` le crée (recommandé)")
    if not a.hors_ligne:
        import requests
        for nom, url in (("geo.api.gouv.fr", f"{G.API}/communes?nom=Rouen&limit=1"),
                         ("DVF (data.gouv.fr)", D.url_commune(date.today().year - 2, "76540")),
                         ("Géorisques", f"{R.API}/gaspar/risques?code_insee=76540"),
                         ("Leboncoin", "https://www.leboncoin.fr/")):
            try:
                code = requests.get(url, timeout=10, headers={"User-Agent": "immo-ops doctor"}).status_code
                etat = "✔" if code < 400 else ("⚠" if nom == "Leboncoin" else "✖")
                ligne(etat, f"{nom} : HTTP {code}" + (" (403 = DataDome, normal depuis un serveur ; le scan via lbc peut quand même passer)" if nom == "Leboncoin" and code == 403 else ""))
            except requests.RequestException as e:
                ligne("✖" if nom != "Leboncoin" else "⚠", f"{nom} injoignable : {type(e).__name__}")
    if a.json:
        out({"ok": ok, "onboarding_requis": onboarding})
    sys.exit(0 if ok else 1)


# --------------------------------------------------------------------------- scan


def cmd_scan(a):
    from immo import leboncoin as L

    cfg = _cfg()
    zones = []
    for z in cfg["zones"]:
        try:
            zones.append(G.resoudre_zone(z))
        except Exception as e:  # noqa: BLE001
            err(f"Zone {z} introuvable : {e}")
    print(f"Scan Leboncoin — {len(zones)} zone(s), {len(cfg['recherches_url'])} recherche(s) enregistrée(s)", file=sys.stderr)
    try:
        brutes = L.scanner(cfg, zones)
    except L.LbcIndisponible as e:
        err(str(e), 3)
    except L.LbcBloque as e:
        err(str(e), 4)

    # Dédup intra-scan (zones qui se chevauchent)
    vues = {}
    for ann in brutes:
        vues[ann["id"]] = ann
    store = A.charger()
    bilan = {"nouvelle": [], "baisse": [], "hausse": [], "connue": []}
    nouvelles_ok = []
    for ann in vues.values():
        rejet = A.raisons_rejet(ann, cfg)
        etat = A.integrer(store, ann, rejet)
        bilan[etat].append(ann["id"])
        if etat == "nouvelle" and not rejet:
            nouvelles_ok.append(ann)
    if a.dry_run:
        print("(dry-run : rien n'est écrit)", file=sys.stderr)
    else:
        A.sauver(store)
        T.rendre_pipeline(store)
    rejetees = sum(1 for i in bilan["nouvelle"] if store[i].get("rejet"))
    resume = {
        "annonces_lues": len(vues),
        "nouvelles_retenues": len(nouvelles_ok),
        "nouvelles_rejetees_prefiltre": rejetees,
        "baisses_de_prix": bilan["baisse"],
        "hausses_de_prix": bilan["hausse"],
        "deja_connues": len(bilan["connue"]),
        "en_attente_evaluation": sum(1 for x in store.values() if x.get("statut_pipeline") == "a_evaluer"),
        "nouvelles": [{"id": x["id"], "resume": A.resume(x), "url": x["url"]} for x in nouvelles_ok],
    }
    out(resume)
    if not a.dry_run and not a.sans_notif and (nouvelles_ok or bilan["baisse"]):
        lignes = [f"• {A.resume(x)}\n  {x['url']}" for x in nouvelles_ok[:10]]
        lignes += [f"📉 {A.resume(store[i])}\n  {store[i]['url']}" for i in bilan["baisse"][:5]]
        N.envoyer(cfg["notifications"].get("ntfy_url"),
                  f"immo-ops : {len(nouvelles_ok)} nouvelle(s), {len(bilan['baisse'])} baisse(s)",
                  "\n".join(lignes))


# --------------------------------------------------------------------------- pipeline


def cmd_pipeline(a):
    store = A.charger()
    if a.action == "list":
        items = [x for x in store.values() if x.get("statut_pipeline") == a.filtre]
        items.sort(key=lambda x: x.get("vu_le") or "", reverse=True)
        if a.json:
            out([{k: x.get(k) for k in ("id", "url", "prix", "prix_m2", "commune", "vu_le")} | {"resume": A.resume(x)} for x in items])
        else:
            for x in items:
                print(f"{x['id']}\t{A.resume(x)}\t{x['url']}")
            print(f"— {len(items)} annonce(s)", file=sys.stderr)
    elif a.action == "show":
        if a.id not in store:
            err(f"Annonce inconnue : {a.id}")
        out(store[a.id])
    elif a.action == "marquer":
        try:
            T.marquer(store, a.id, a.statut, a.rapport)
        except (ValueError, LookupError) as e:
            err(str(e))
        A.sauver(store)
        T.rendre_pipeline(store)
        print(f"✔ {a.id} → {a.statut}")
    elif a.action == "ajouter":
        # Annonce collée à la main (SeLoger, PAP, agence...) : l'agent fournit un JSON normalisé
        ann = json.loads(sys.stdin.read())
        for champ in ("id", "url"):
            if not ann.get(champ):
                err(f"champ '{champ}' requis dans le JSON")
        ann.setdefault("source", "manuel")
        ann["prix_m2"] = A.prix_m2(ann)
        cfg = _cfg(allow_example=True)
        rejet = A.raisons_rejet(ann, cfg)
        etat = A.integrer(store, ann, rejet)
        A.sauver(store)
        T.rendre_pipeline(store)
        out({"etat": etat, "rejet": rejet, "id": ann["id"]})
    elif a.action == "rendre":
        print(T.rendre_pipeline(store))


# --------------------------------------------------------------------------- dvf / risques / trajet / budget


def _commune_args(a) -> dict:
    if a.insee:
        return G.chercher_commune("", code_insee=a.insee)
    if not a.commune:
        err("--commune ou --insee requis")
    return G.chercher_commune(a.commune, a.cp)


def _dvf(commune: dict, type_bien: str, surface, terrain, annees: int, elargir_km: float, min_ventes: int = 8):
    ans = D.annees_disponibles(annees)
    rows, ok = D.lignes_commune(commune["code"], ans)
    vts = D.ventes(rows, type_bien)
    perimetre = [commune["nom"]]
    if elargir_km and len(vts) < min_ventes and commune.get("lat"):
        for c in G.communes_autour(commune["lat"], commune["lng"], elargir_km, commune["codeRegion"]):
            if c["code"] == commune["code"]:
                continue
            r2, _ = D.lignes_commune(c["code"], ans)
            v2 = D.ventes(r2, type_bien)
            if v2:
                vts += v2
                perimetre.append(f"{c['nom']} ({c['distance_km']} km)")
    res = D.analyse(vts, surface=surface, terrain=terrain)
    if not ok:
        res["avertissement"] = ("Aucun fichier DVF pour ce code INSEE : Alsace-Moselle et Mayotte ne sont pas "
                                "couvertes ; pour Paris, Lyon et Marseille, utiliser le code d'arrondissement "
                                "(--insee 75111, 69383, 13206...).")
    res.update(commune=commune["nom"], code_insee=commune["code"], type=type_bien,
               annees_trouvees=sorted(ok), perimetre=perimetre,
               limites="DVF : ventes réelles, ~6 mois de décalage, état du bien inconnu ; "
                       "un grand terrain gonfle le €/m² bâti des maisons.")
    return res


def cmd_dvf(a):
    c = _commune_args(a)
    res = _dvf(c, a.type, a.surface, a.terrain, a.annees, a.elargir_km)
    if a.prix_m2:
        cible = res.get("surface_similaire") if res.get("surface_similaire", {}).get("n", 0) >= 5 else res["global"]
        res["positionnement"] = D.positionner(a.prix_m2, cible)
    out(res)


def cmd_risques(a):
    out(R.rapport(_commune_args(a)["code"]))


def cmd_trajet(a):
    d, v = _lieu(a.de), _lieu(a.vers)
    out({"de": d.get("nom"), "vers": v.get("nom"), **TR.trajet(d["lat"], d["lng"], v["lat"], v["lng"])})


def cmd_budget(a):
    cfg = _cfg(allow_example=True)
    fin = dict(cfg["financement"])
    if a.apport is not None:
        fin["apport"] = a.apport
    if a.taux is not None:
        fin["taux_annuel_pct"] = a.taux
    if a.duree is not None:
        fin["duree_ans"] = a.duree
    out(B.calcul(a.prix, fin, neuf=a.neuf, travaux=a.travaux))


def cmd_communes(a):
    c = _lieu(a.autour)
    region = c.get("codeRegion") or G.chercher_commune(c["nom"])["codeRegion"]
    out(G.communes_autour(c["lat"], c["lng"], a.rayon, region))


# --------------------------------------------------------------------------- contexte (pour le mode évaluer)


def cmd_contexte(a):
    """Agrège en un appel tout ce que le mode `evaluer` doit lire. Chaque bloc en échec est
    signalé dans `erreurs` : l'agent le mentionne au lieu d'inventer."""
    cfg = _cfg(allow_example=True)
    store = A.charger()
    ctx: dict = {"erreurs": {}}
    if a.id:
        if a.id not in store:
            err(f"Annonce {a.id} absente de data/annonces.json (scan, ou `pipeline ajouter`)")
        ann = store[a.id]
    else:
        ann = {"commune": a.commune, "code_postal": a.cp, "type": a.type, "surface": a.surface,
               "terrain": a.terrain, "prix": a.prix}
        ann["prix_m2"] = A.prix_m2(ann)
    ctx["annonce"] = {k: v for k, v in ann.items() if k != "images"}
    ctx["prefiltre"] = A.raisons_rejet(ann, cfg)

    try:
        commune = G.chercher_commune(ann["commune"], ann.get("code_postal"))
        ctx["commune"] = commune
    except Exception as e:  # noqa: BLE001
        ctx["erreurs"]["commune"] = str(e)
        out(ctx)
        return

    type_bien = ann.get("type") if ann.get("type") in D.TYPES else "maison"
    try:
        d = _dvf(commune, type_bien, ann.get("surface"), ann.get("terrain"), 5, a.elargir_km)
        cible = d.get("surface_similaire") if d.get("surface_similaire", {}).get("n", 0) >= 5 else d["global"]
        d["positionnement"] = D.positionner(ann.get("prix_m2"), cible)
        d["comparables"] = d["comparables"][:8]
        ctx["dvf"] = d
    except Exception as e:  # noqa: BLE001
        ctx["erreurs"]["dvf"] = str(e)[:300]

    ctx["risques"] = R.rapport(commune["code"])

    lat, lng = ann.get("lat") or commune["lat"], ann.get("lng") or commune["lng"]
    ctx["trajets"] = []
    for t in cfg.get("trajets") or []:
        try:
            dest = _lieu(t["vers"]) if isinstance(t.get("vers"), str) else t["vers"]
            r = TR.trajet(lat, lng, dest["lat"], dest["lng"])
            r.update(nom=t.get("nom", t.get("vers")), max_minutes=t.get("max_minutes"),
                     ok=(r["minutes"] <= t["max_minutes"]) if t.get("max_minutes") else None)
            ctx["trajets"].append(r)
        except Exception as e:  # noqa: BLE001
            ctx["erreurs"][f"trajet {t.get('nom')}"] = str(e)[:200]

    if ann.get("prix") and cfg["projet"] == "achat":
        ctx["budget"] = B.calcul(ann["prix"], cfg["financement"], neuf=False)
    txt = f"{ann.get('titre') or ''} {ann.get('description') or ''}".lower()
    ctx["mots_bonus_trouves"] = [m for m in cfg.get("mots_bonus") or [] if m.lower() in txt]
    h = ann.get("historique_prix") or []
    if len(h) > 1:
        ctx["historique_prix"] = h
    if ann.get("vu_le"):
        ctx["jours_depuis_premiere_vue"] = (date.today() - date.fromisoformat(ann["vu_le"])).days
    ctx["criteres"] = {k: cfg[k] for k in ("projet", "usage", "types", "prix", "surface", "pieces",
                                           "chambres", "terrain", "dpe_max", "ponderations")}
    out(ctx)


# --------------------------------------------------------------------------- tracker


def cmd_tracker(a):
    if a.action == "list":
        rows = T.lire()
        if a.statut:
            rows = [r for r in rows if r["Statut"].lower() == a.statut.lower()]
        if a.json:
            out(rows)
        else:
            for r in rows:
                print(" | ".join(r[c] for c in T.COLONNES[:9]))
    elif a.action == "numero":
        print(f"{T.prochain_numero():03d}")
    elif a.action == "ajouter":
        row = T.ajouter(a.num, a.commune, a.bien, a.prix, a.prix_m2, a.score, a.rapport, a.url,
                        notes=a.notes or "", statut=a.statut or "Évalué")
        out(row)
    elif a.action == "statut":
        try:
            out(T.changer_statut(a.cle, a.nouveau, a.note))
        except (ValueError, LookupError) as e:
            err(str(e))


# --------------------------------------------------------------------------- argparse


def main(argv=None):
    p = argparse.ArgumentParser(prog="immo.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("doctor"); s.add_argument("--json", action="store_true"); s.add_argument("--hors-ligne", action="store_true")
    s.set_defaults(fn=cmd_doctor)

    s = sub.add_parser("scan"); s.add_argument("--dry-run", action="store_true"); s.add_argument("--sans-notif", action="store_true")
    s.set_defaults(fn=cmd_scan)

    s = sub.add_parser("pipeline")
    s.add_argument("action", choices=["list", "show", "marquer", "ajouter", "rendre"], nargs="?", default="list")
    s.add_argument("id", nargs="?"); s.add_argument("statut", nargs="?")
    s.add_argument("--rapport"); s.add_argument("--json", action="store_true")
    s.add_argument("--filtre", default="a_evaluer", choices=sorted(T.STATUTS_PIPELINE))
    s.set_defaults(fn=cmd_pipeline)

    def commune_opts(s):
        s.add_argument("--commune"); s.add_argument("--cp"); s.add_argument("--insee")

    s = sub.add_parser("dvf"); commune_opts(s)
    s.add_argument("--type", choices=list(D.TYPES), default="maison")
    s.add_argument("--surface", type=float); s.add_argument("--terrain", type=float)
    s.add_argument("--prix-m2", type=float); s.add_argument("--annees", type=int, default=5)
    s.add_argument("--elargir-km", type=float, default=0, help="ajoute les communes voisines si < 8 ventes")
    s.set_defaults(fn=cmd_dvf)

    s = sub.add_parser("risques"); commune_opts(s); s.set_defaults(fn=cmd_risques)

    s = sub.add_parser("trajet"); s.add_argument("--de", required=True); s.add_argument("--vers", required=True)
    s.set_defaults(fn=cmd_trajet)

    s = sub.add_parser("budget"); s.add_argument("--prix", type=float, required=True)
    s.add_argument("--travaux", type=float, default=0); s.add_argument("--neuf", action="store_true")
    s.add_argument("--apport", type=float); s.add_argument("--taux", type=float); s.add_argument("--duree", type=int)
    s.set_defaults(fn=cmd_budget)

    s = sub.add_parser("communes"); s.add_argument("--autour", required=True); s.add_argument("--rayon", type=float, default=15)
    s.set_defaults(fn=cmd_communes)

    s = sub.add_parser("contexte"); s.add_argument("id", nargs="?")
    s.add_argument("--commune"); s.add_argument("--cp"); s.add_argument("--type", default="maison")
    s.add_argument("--surface", type=float); s.add_argument("--terrain", type=float); s.add_argument("--prix", type=float)
    s.add_argument("--elargir-km", type=float, default=8)
    s.set_defaults(fn=cmd_contexte)

    s = sub.add_parser("tracker")
    s.add_argument("action", choices=["list", "numero", "ajouter", "statut"], nargs="?", default="list")
    s.add_argument("cle", nargs="?"); s.add_argument("nouveau", nargs="?")
    s.add_argument("--statut"); s.add_argument("--note"); s.add_argument("--json", action="store_true")
    s.add_argument("--num", type=int); s.add_argument("--commune"); s.add_argument("--bien")
    s.add_argument("--prix"); s.add_argument("--prix-m2"); s.add_argument("--score")
    s.add_argument("--rapport"); s.add_argument("--url"); s.add_argument("--notes")
    s.set_defaults(fn=cmd_tracker)

    a = p.parse_args(argv)
    if a.cmd == "pipeline" and a.action in ("show", "marquer") and not a.id:
        p.error("id requis")
    if a.cmd == "pipeline" and a.action == "marquer" and not a.statut:
        p.error("statut requis (a_evaluer | evaluee | ecartee | rejetee)")
    if a.cmd == "tracker" and a.action == "ajouter" and not all([a.num, a.commune, a.bien]):
        p.error("tracker ajouter : --num, --commune et --bien sont requis")
    if a.cmd == "tracker" and a.action == "statut" and not (a.cle and a.nouveau):
        p.error("tracker statut <cle> <nouveau statut>")
    if a.cmd == "contexte" and not (a.id or a.commune):
        p.error("contexte : un id d'annonce, ou --commune")
    a.fn(a)


if __name__ == "__main__":
    main()
