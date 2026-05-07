"""EP-Online client — energielabels per adres.

Open API, geen key vereist.
Documentatie: https://public.ep-online.nl/swagger/index.html
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

_BASE = "https://public.ep-online.nl/api/v5"


@dataclass
class EpLabel:
    postcode: str
    huisnummer: str
    huisnummertoevoeging: str | None
    energielabel: str | None      # "A", "B", ... "G", "A+", "A++"
    energieklasse: str | None
    registratiedatum: str | None  # ISO-8601
    geldig_tot: str | None
    pand_id: str | None
    raw: dict


def get_label_for_address(
    postcode: str,
    huisnummer: str | int,
    huisnummertoevoeging: str | None = None,
) -> EpLabel | None:
    """Haal energielabel op voor een adres (postcode + huisnummer)."""
    params: dict = {
        "postcode": postcode.replace(" ", ""),
        "huisnummer": str(huisnummer),
    }
    if huisnummertoevoeging:
        params["huisnummertoevoeging"] = huisnummertoevoeging

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{_BASE}/PandEnergielabel/Adres", params=params)
    except httpx.HTTPError as exc:
        log.warning("EP-Online request mislukt: %s", exc)
        return None

    if resp.status_code == 404:
        log.debug("EP-Online: geen label voor %s %s", postcode, huisnummer)
        return None

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        log.warning("EP-Online HTTP-fout: %s", exc)
        return None

    data = resp.json()
    if not data:
        return None

    # API retourneert een lijst; neem het meest recente label
    if isinstance(data, list):
        data = sorted(data, key=lambda x: x.get("registratiedatum", ""), reverse=True)[0]

    return EpLabel(
        postcode=postcode,
        huisnummer=str(huisnummer),
        huisnummertoevoeging=huisnummertoevoeging,
        energielabel=data.get("energieklasse") or data.get("energielabel"),
        energieklasse=data.get("energieklasse"),
        registratiedatum=data.get("registratiedatum"),
        geldig_tot=data.get("geldigTot"),
        pand_id=data.get("pandId") or data.get("bagPandId"),
        raw=data,
    )
