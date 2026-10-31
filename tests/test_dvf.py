import csv
from datetime import date

from conftest import FIX

from immo import dvf as D


def rows():
    with open(FIX / "dvf_sample.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_ventes_maison_regroupe_et_filtre():
    v = D.ventes(rows(), "maison")
    ids = sorted(x["id_mutation"] for x in v)
    # 2024-3 (2 maisons), 2024-5 (échange), 2024-6 (prix aberrant), 2024-8 (terrain nu) exclus
    assert ids == ["2024-1", "2024-2", "2024-7"]
    m1 = next(x for x in v if x["id_mutation"] == "2024-1")
    assert m1["prix_m2"] == 2000
    assert m1["terrain"] == 600  # deux natures de culture sur la même parcelle
    assert m1["adresse"] == "12 RUE DES LILAS"
    assert v[0]["date"] >= v[-1]["date"]  # tri récent d'abord


def test_ventes_appartement():
    v = D.ventes(rows(), "appartement")
    assert [x["prix_m2"] for x in v] == [3000]


def test_analyse_et_comparables():
    v = D.ventes(rows(), "maison")
    res = D.analyse(v, surface=105, terrain=500)
    assert res["global"] == {"n": 3, "mediane": 2000}
    assert set(res["par_annee"]) == {"2024"}
    assert res["surface_similaire"]["n"] == 3
    assert res["comparables"][0]["surface"] in (100, 110)


def test_quartiles_et_positionnement():
    stats = D._stats([1800, 2000, 2100, 2200, 2400, 2600])
    assert stats["n"] == 6 and "q1" in stats and "q3" in stats
    assert "au-dessus du 3e quartile" in D.positionner(3000, stats)
    assert "sous le 1er quartile" in D.positionner(1500, stats)
    assert D.positionner(None, stats) is None
    assert D.positionner(2000, {"n": 0}) is None


def test_url_et_annees():
    assert D.url_commune(2024, "76540").endswith("/2024/communes/76/76540.csv")
    assert D.url_commune(2024, "97411").endswith("/2024/communes/974/97411.csv")
    assert D.annees_disponibles(5, date(2026, 10, 31)) == [2026, 2025, 2024, 2023, 2022, 2021]


def test_lignes_commune_ignore_404(monkeypatch):
    from immo import net
    txt = (FIX / "dvf_sample.csv").read_text(encoding="utf-8")

    def fake(url, **k):
        if "/2024/" in url:
            return txt
        raise net.NotFound(url)
    monkeypatch.setattr(net, "get_text", fake)
    r, ok = D.lignes_commune("76540", [2025, 2024, 2023])
    assert ok == [2024] and len(r) == 11
