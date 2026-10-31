"""Scan avec un faux client Leboncoin, et commandes CLI avec réseau simulé."""
import json
from types import SimpleNamespace

import pytest

import immo.leboncoin as L
from conftest import FIX


class FakeEnum:
    def __getattr__(self, name):
        return name


class FakeLbc:
    Category = FakeEnum()
    Sort = FakeEnum()
    OwnerType = FakeEnum()

    class City:
        def __init__(self, **kw):
            self.kw = kw


class FakeClient:
    def __init__(self, pages, exc=None):
        self.pages, self.exc, self.calls = pages, exc, []

    def search(self, **kw):
        self.calls.append(kw)
        if self.exc:
            raise self.exc
        return SimpleNamespace(ads=self.pages[kw["page"] - 1], max_pages=len(self.pages))


def test_parametres_recherche(cfg):
    p = L.parametres_recherche(cfg)
    assert p["real_estate_type"] == ["1"]
    assert p["price"] == [100000, 250000] and p["square"] == [80, 100000]


def test_scanner_pagine_et_normalise(cfg, make_ad):
    page1 = [make_ad(i) for i in range(35)]
    page2 = [make_ad(100)]
    client = FakeClient([page1, page2])
    zones = [{"nom": "Rouen", "lat": 49.44, "lng": 1.09, "rayon_km": 10}]
    res = L.scanner(cfg, zones, log=lambda m: None, client=client, sleep=lambda s: None, lbc_module=FakeLbc)
    assert len(res) == 36 and res[0]["id"] == "lbc:0"
    assert client.calls[0]["category"] == "IMMOBILIER_VENTES_IMMOBILIERES"
    assert client.calls[0]["locations"][0].kw["radius"] == 10000
    assert len(client.calls) == 2


def test_scanner_bloque(cfg):
    client = FakeClient([], exc=Exception("HTTP 403 Forbidden"))
    zones = [{"nom": "Rouen", "lat": 49.44, "lng": 1.09, "rayon_km": 10}]
    with pytest.raises(L.LbcBloque):
        L.scanner(cfg, zones, log=lambda m: None, client=client, sleep=lambda s: None, lbc_module=FakeLbc)


@pytest.fixture
def reseau_simule(monkeypatch):
    """geo.api, DVF, Géorisques et OSRM simulés : aucun appel réseau réel."""
    from immo import net
    commune = {"nom": "Rouen", "code": "76540", "codesPostaux": ["76000"], "codeDepartement": "76",
               "codeRegion": "28", "population": 110000, "centre": {"coordinates": [1.09, 49.44]}}
    dvf_txt = (FIX / "dvf_sample.csv").read_text(encoding="utf-8")

    def get_json(url, ttl_hours=24, params=None):
        if "geo.api.gouv.fr" in url:
            return [commune] if url.endswith("/communes") else commune
        if "gaspar/risques" in url:
            return {"data": [{"risques_detail": [{"libelle_risque_long": "Inondation"},
                                                  {"libelle_risque_long": "Mouvement de terrain"}]}]}
        if "gaspar/catnat" in url:
            return {"data": [{"date_debut_evt": "2021-06-01", "libelle_risque_jo": "Inondations et/ou Coulées de Boue"}]}
        if "cavites" in url:
            return {"data": [{"type": "marnière"}, {"type": "marnière"}]}
        if "radon" in url:
            raise RuntimeError("service indisponible")
        if "project-osrm" in url:
            return {"routes": [{"duration": 1500, "distance": 21000}]}
        raise AssertionError(url)

    def get_text(url, ttl_hours=24, params=None):
        if "/2024/" in url:
            return dvf_txt
        raise net.NotFound(url)

    monkeypatch.setattr(net, "get_json", get_json)
    monkeypatch.setattr(net, "get_text", get_text)


def run(capsys, *args):
    import immo as _  # noqa: F401
    import importlib.util
    from conftest import ROOT
    spec = importlib.util.spec_from_file_location("immo_cli", ROOT / "immo.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main(list(args))
    return capsys.readouterr().out


def _ecrire_config(data_tmp):
    (data_tmp / "config").mkdir(exist_ok=True)
    (data_tmp / "config" / "criteres.yml").write_text(
        "types: [maison]\nzones: [{commune: Rouen, rayon_km: 10}]\nprix: {max: 250000}\n"
        "trajets: [{nom: Travail, vers: '49.5,1.0', max_minutes: 30}]\nmots_bonus: [jardin]\n",
        encoding="utf-8")


def test_cli_dvf(reseau_simule, capsys):
    res = json.loads(run(capsys, "dvf", "--commune", "Rouen", "--type", "maison", "--surface", "100", "--prix-m2", "2500"))
    assert res["code_insee"] == "76540" and res["global"]["mediane"] == 2000
    assert res["annees_trouvees"] == [2024]
    assert res["positionnement"].startswith("+25 %")


def test_cli_risques(reseau_simule, capsys):
    res = json.loads(run(capsys, "risques", "--commune", "Rouen"))
    assert res["risques"] == ["Inondation", "Mouvement de terrain"]
    assert res["cavites"]["total"] == 2 and "radon" in res["erreurs"]


def test_cli_contexte_annonce(reseau_simule, capsys, data_tmp, make_ad):
    from immo import annonces as A
    _ecrire_config(data_tmp)
    store = {}
    A.integrer(store, A.depuis_leboncoin(make_ad(9, prix=200000)), [])
    A.sauver(store)
    ctx = json.loads(run(capsys, "contexte", "lbc:9"))
    assert ctx["commune"]["code"] == "76540"
    assert ctx["dvf"]["positionnement"].startswith("+0 %")
    assert ctx["trajets"][0]["minutes"] == 25 and ctx["trajets"][0]["ok"] is True
    assert ctx["budget"]["prix"] == 200000
    assert ctx["mots_bonus_trouves"] == ["jardin"]
    assert ctx["risques"]["cavites"]["total"] == 2


def test_cli_pipeline_ajouter_et_marquer(capsys, data_tmp, monkeypatch):
    import io
    _ecrire_config(data_tmp)
    ann = {"id": "seloger:123", "url": "https://www.seloger.com/annonces/123.htm", "titre": "Maison",
           "prix": 190000, "surface": 95, "type": "maison", "commune": "Rouen", "code_postal": "76000"}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(ann)))
    res = json.loads(run(capsys, "pipeline", "ajouter"))
    assert res == {"etat": "nouvelle", "rejet": [], "id": "seloger:123"}
    out = run(capsys, "pipeline", "list")
    assert "seloger:123" in out
    run(capsys, "pipeline", "marquer", "seloger:123", "evaluee", "--rapport", "001-rouen.md")
    assert "seloger:123" not in run(capsys, "pipeline", "list")
    assert "seloger:123" in run(capsys, "pipeline", "list", "--filtre", "evaluee")


def test_cli_tracker(capsys):
    assert run(capsys, "tracker", "numero").strip() == "001"
    run(capsys, "tracker", "ajouter", "--num", "1", "--commune", "Rouen", "--bien", "Maison 100 m²",
        "--prix", "200000", "--prix-m2", "2000", "--score", "4.2", "--rapport", "001-rouen-2026-10-31.md",
        "--url", "https://lbc/9")
    run(capsys, "tracker", "statut", "1", "À visiter", "--note", "appeler l'agence")
    rows = json.loads(run(capsys, "tracker", "list", "--json"))
    assert rows[0]["Statut"] == "À visiter"
    assert run(capsys, "tracker", "numero").strip() == "002"


def test_cli_scan_bout_en_bout(reseau_simule, capsys, data_tmp, make_ad, monkeypatch):
    """Scan complet : préfiltre, dédup inter-zones, store, vue pipeline, puis baisse de prix."""
    _ecrire_config(data_tmp)
    lot = [make_ad(1), make_ad(2, prix=400000), make_ad(1)]  # 1 en double (zones qui se chevauchent)
    monkeypatch.setattr(L, "scanner", lambda cfg, zones: list(map(A_norm, lot)))
    res = json.loads(run(capsys, "scan", "--sans-notif"))
    assert res["annonces_lues"] == 2 and res["nouvelles_retenues"] == 1
    assert res["nouvelles_rejetees_prefiltre"] == 1 and res["en_attente_evaluation"] == 1
    assert (data_tmp / "data" / "pipeline.md").exists()
    lot[:] = [make_ad(1, prix=170000)]
    res = json.loads(run(capsys, "scan", "--sans-notif"))
    assert res["baisses_de_prix"] == ["lbc:1"] and res["nouvelles_retenues"] == 0
    assert "📉" in (data_tmp / "data" / "pipeline.md").read_text(encoding="utf-8")


def test_cli_dvf_sans_fichier(reseau_simule, capsys, monkeypatch):
    from immo import net

    def rien(url, **k):
        raise net.NotFound(url)
    monkeypatch.setattr(net, "get_text", rien)
    res = json.loads(run(capsys, "dvf", "--commune", "Rouen"))
    assert res["global"] == {"n": 0} and "arrondissement" in res["avertissement"]


def A_norm(ad):
    from immo.annonces import depuis_leboncoin
    return depuis_leboncoin(ad)
