import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FIX = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def data_tmp(tmp_path, monkeypatch):
    """Chaque test écrit dans un DATA_ROOT jetable, jamais dans le dépôt."""
    monkeypatch.setenv("IMMO_OPS_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def cfg():
    from immo import config as C
    return C._merge(C.DEFAUTS, {
        "types": ["maison"],
        "zones": [{"commune": "Rouen", "rayon_km": 10}],
        "prix": {"min": 100000, "max": 250000},
        "surface": {"min": 80},
        "dpe_max": "E",
        "mots_bonus": ["garage", "jardin"],
    })


def attr(value, label=None):
    return SimpleNamespace(value=value, value_label=label or value)


def fake_ad(i, prix=180000, surface="100", type_="1", dpe="d", ville="Rouen", cp="76000", body="Belle maison avec jardin"):
    attrs = {"real_estate_type": attr(type_, "Maison"), "square": attr(surface), "rooms": attr("5"),
             "bedrooms": attr("3"), "land_plot_surface": attr("450"), "energy_rate": attr(dpe, dpe.upper()),
             "ges": attr("c", "C")}
    return SimpleNamespace(
        id=i, url=f"https://www.leboncoin.fr/ad/ventes_immobilieres/{i}", subject=f"Maison {i}",
        price=prix, attributes=attrs, body=body, images=["a.jpg"], first_publication_date="2026-10-30 10:00:00",
        location=SimpleNamespace(city=ville, zipcode=cp, lat=49.44, lng=1.09),
    )


@pytest.fixture
def make_ad():
    return fake_ad
