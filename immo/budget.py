"""Coût total d'acquisition et mensualité de crédit (estimations, pas un conseil financier)."""
from __future__ import annotations


def mensualite(capital: float, taux_annuel_pct: float, duree_ans: int) -> float:
    n = duree_ans * 12
    t = taux_annuel_pct / 100 / 12
    if capital <= 0:
        return 0.0
    if t == 0:
        return capital / n
    return capital * t / (1 - (1 + t) ** -n)


def calcul(prix: float, fin: dict, neuf: bool = False, travaux: float = 0,
           frais_agence_inclus: bool = True, frais_agence: float = 0) -> dict:
    pct = fin["frais_notaire_neuf_pct"] if neuf else fin["frais_notaire_ancien_pct"]
    notaire = prix * pct / 100
    total = prix + notaire + travaux + (0 if frais_agence_inclus else frais_agence)
    emprunt = max(total - float(fin.get("apport") or 0), 0)
    m_credit = mensualite(emprunt, fin["taux_annuel_pct"], fin["duree_ans"])
    m_assurance = emprunt * fin.get("assurance_annuelle_pct", 0) / 100 / 12
    m = m_credit + m_assurance
    out = {
        "prix": round(prix),
        "frais_notaire_estimes": round(notaire),
        "frais_notaire_pct": pct,
        "travaux": round(travaux),
        "cout_total": round(total),
        "apport": round(float(fin.get("apport") or 0)),
        "montant_emprunte": round(emprunt),
        "taux_annuel_pct": fin["taux_annuel_pct"],
        "duree_ans": fin["duree_ans"],
        "mensualite_credit": round(m_credit),
        "mensualite_assurance": round(m_assurance),
        "mensualite_totale": round(m),
        "cout_interets": round(m_credit * fin["duree_ans"] * 12 - emprunt),
    }
    rev = fin.get("revenus_mensuels_nets")
    if rev:
        charges = float(fin.get("autres_credits_mensuels") or 0)
        taux = (m + charges) / rev * 100
        out["taux_endettement_pct"] = round(taux, 1)
        out["endettement_ok"] = taux <= fin.get("endettement_max_pct", 35)
    return out
