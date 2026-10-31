from immo import annonces as A


def test_normalisation_leboncoin(make_ad):
    a = A.depuis_leboncoin(make_ad(42))
    assert a["id"] == "lbc:42" and a["type"] == "maison"
    assert a["surface"] == 100 and a["terrain"] == 450 and a["pieces"] == 5
    assert a["dpe"] == "D" and a["ges"] == "C"
    assert a["prix_m2"] == 1800
    assert a["publie_le"] == "2026-10-30"
    assert "Maison" in A.resume(a) and "1 800 €/m²" in A.resume(a)


def test_prefiltre(cfg, make_ad):
    ok = A.depuis_leboncoin(make_ad(1))
    assert A.raisons_rejet(ok, cfg) == []
    cher = A.depuis_leboncoin(make_ad(2, prix=300000))
    assert any("prix" in r for r in A.raisons_rejet(cher, cfg))
    g = A.depuis_leboncoin(make_ad(3, dpe="g"))
    assert A.raisons_rejet(g, cfg) == ["DPE G > E"]
    appart = A.depuis_leboncoin(make_ad(4, type_="2"))
    assert A.raisons_rejet(appart, cfg) == ["type appartement"]
    viager = A.depuis_leboncoin(make_ad(5, body="Vente en VIAGER occupé"))
    assert A.raisons_rejet(viager, cfg) == ["mot exclu « viager »"]


def test_donnee_absente_ne_rejette_pas(cfg, make_ad):
    a = A.depuis_leboncoin(make_ad(6, surface="", dpe="n"))
    assert a["surface"] is None and a["dpe"] is None
    assert A.raisons_rejet(a, cfg) == []


def test_integration_dedup_et_baisse(cfg, make_ad):
    store = {}
    a = A.depuis_leboncoin(make_ad(7, prix=260000))
    assert A.integrer(store, a, A.raisons_rejet(a, cfg), "2026-10-01") == "nouvelle"
    assert store["lbc:7"]["statut_pipeline"] == "rejetee"  # trop cher
    assert A.integrer(store, a, A.raisons_rejet(a, cfg), "2026-10-02") == "connue"
    b = A.depuis_leboncoin(make_ad(7, prix=240000))
    assert A.integrer(store, b, A.raisons_rejet(b, cfg), "2026-10-10") == "baisse"
    s = store["lbc:7"]
    assert s["historique_prix"] == [["2026-10-01", 260000], ["2026-10-10", 240000]]
    assert s["statut_pipeline"] == "a_evaluer"  # repasse sous le plafond
    assert s["vu_le"] == "2026-10-01" and s["derniere_vue"] == "2026-10-10"


def test_sauver_charger(make_ad):
    store = {}
    A.integrer(store, A.depuis_leboncoin(make_ad(8)), [])
    A.sauver(store)
    assert A.charger()["lbc:8"]["prix"] == 180000
