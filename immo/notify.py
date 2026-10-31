"""Notification push optionnelle via ntfy (auto-hébergeable, ou ntfy.sh)."""
from __future__ import annotations

import requests


def envoyer(url: str | None, titre: str, message: str, priorite: str = "default") -> bool:
    if not url:
        return False
    try:
        # Titre en paramètre de requête : évite les soucis d'encodage des en-têtes HTTP.
        r = requests.post(url, data=message.encode("utf-8"), timeout=15,
                          params={"title": titre, "priority": priorite, "tags": "house"})
        return r.ok
    except requests.RequestException:
        return False
