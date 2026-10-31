import pytest

from immo import annonces as A
from immo import budget as B
from immo import config as C
from immo import tracker as T
from immo.paths import pipeline_file, reports_dir, tracker_file


def test_tracker_ajout_maj_statut():
    r = T.ajouter(1, "Rouen", "Maison 5p 100 m²", 180000, 1800, 3.84, "001-rouen-2026-10-31.md",
                  "https://lbc/1", jour="2026-10-31")
    assert r["Prix"] == "180 000 €" and r["Score"] == "3.8/5" and r["Rapport"].startswith("[001]")
    # même URL -> mise à jour, pas de doublon
    T.ajouter(5, "Rouen", "Maison 5p 100 m²", 175000, 1750, 4.1, "001-rouen-2026-10-31.md", "https://lbc/1")
    rows = T.lire()
    assert len(rows) == 1 and rows[0]["#"] == "1" and rows[0]["Score"] == "4.1/5"
    T.changer_statut("1", "a visiter", "RDV samedi")
    T.changer_statut("https://lbc/1", "Visité")
    row = T.lire()[0]
    assert row["Statut"] == "Visité" and "RDV samedi" in row["Notes"]
    with pytest.raises(ValueError):
        T.changer_statut("1", "Applied")
    with pytest.raises(LookupError):
        T.changer_statut("99", "Visité")
    assert tracker_file().read_text(encoding="utf-8").count("| 1 |") == 1


def test_numerotation():
    assert T.prochain_numero() == 1
    (reports_dir() / "007-fecamp-2026-10-31.md").write_text("x")
    assert T.prochain_numero() == 8


def test_pipeline_vue(cfg, make_ad):
    store = {}
    for i, prix in ((1, 180000), (2, 400000)):
        a = A.depuis_leboncoin(make_ad(i, prix=prix))
        A.integrer(store, a, A.raisons_rejet(a, cfg))
    T.marquer(store, "lbc:1", "evaluee", "001-rouen.md")
    T.rendre_pipeline(store)
    md = pipeline_file().read_text(encoding="utf-8")
    assert "## À évaluer (0)" in md and "## Évaluées (1)" in md and "rapport 001-rouen.md" in md
    assert "Rejetées par le préfiltre (1)" in md and "prix 400000 > 250000" in md
    with pytest.raises(ValueError):
        T.marquer(store, "lbc:1", "fini")


def test_budget():
    fin = dict(C.DEFAUTS["financement"], apport=20000, taux_annuel_pct=3.0, duree_ans=20,
               revenus_mensuels_nets=3000)
    r = B.calcul(200000, fin, travaux=10000)
    assert r["frais_notaire_estimes"] == 16000
    assert r["montant_emprunte"] == 206000
    assert 1130 <= r["mensualite_credit"] <= 1150  # ~1142 €
    assert r["taux_endettement_pct"] > 35 and r["endettement_ok"] is False
    assert B.calcul(200000, fin, neuf=True)["frais_notaire_estimes"] == 5000
    assert B.mensualite(12000, 0, 1) == 1000


def test_config_validation(tmp_path):
    p = tmp_path / "c.yml"
    p.write_text("types: [chateau]\nprix: {min: 5, max: 1}\n", encoding="utf-8")
    with pytest.raises(C.ConfigError) as e:
        C.load(p)
    msg = str(e.value)
    assert "types inconnus" in msg and "zone" in msg and "prix.min > prix.max" in msg


def test_config_exemple_valide():
    from immo.paths import example_config_file
    cfg = C.load(example_config_file())
    assert cfg["zones"][0]["commune"] == "Rouen"
