"""EP-Online client — energielabels per adres.

Situatie (mei 2026): de public EP-Online REST API (v5) vereist nu OAuth-authenticatie.
RVO biedt een open bulk-download via PDOK:
  https://www.pdok.nl/introductie/-/article/ep-online

Werkende strategie voor v1:
  - Probeer de PDOK-gehoste EP-Online WFS (als die beschikbaar is)
  - Val terug op bouwjaar-gebaseerde schatting (zie scores.py)

In een volgende iteratie: laad de bulk-CSV in Supabase voor offline lookup.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

# PDOK host EP-Online als WFS — probeer dit endpoint
_PDOK_EP_WFS = "https://service.pdok.nl/rvo/ep-online/wfs/v1_0"


@dataclass
class EpLabel:
    postcode: str
    huisnummer: str
    huisnummertoevoeging: str | None
    energielabel: str | None
    energieklasse: str | None
    registratiedatum: str | None
    geldig_tot: str | None
    pand_id: str | None
    raw: dict


def get_label_for_address(
    postcode: str,
    huisnummer: str | int,
    huisnummertoevoeging: str | None = None,
) -> EpLabel | None:
    """
    Haal energielabel op via PDOK EP-Online WFS.
    Retourneert None als geen label gevonden of de service onbereikbaar is.
    """
    postcode_clean = postcode.replace(" ", "")
    hnr = str(huisnummer)

    # CQL filter voor WFS
    cql = f"postcode='{postcode_clean}' AND huisnummer={hnr}"
    if huisnummertoevoeging:
        cql += f" AND huisnummertoevoeging='{huisnummertoevoeging}'"

    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": "ep-online:ep-online",
        "CQL_FILTER": cql,
        "COUNT": 1,
        "OUTPUTFORMAT": "application/json",
    }

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(_PDOK_EP_WFS, params=params)
    except httpx.HTTPError as exc:
        log.debug("EP-Online WFS niet bereikbaar: %s", exc)
        return None

    if resp.status_code in (401, 403, 404):
        log.debug("EP-Online WFS: %d voor %s %s", resp.status_code, postcode_clean, hnr)
        return None

    try:
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.debug("EP-Online WFS parse-fout: %s", exc)
        return None

    features = data.get("features", [])
    if not features:
        return None

    props = features[0].get("properties", {})
    label = props.get("energieklasse") or props.get("energielabel")

    return EpLabel(
        postcode=postcode_clean,
        huisnummer=hnr,
        huisnummertoevoeging=huisnummertoevoeging,
        energielabel=label,
        energieklasse=props.get("energieklasse"),
        registratiedatum=props.get("pand_registratiedatum") or props.get("registratiedatum"),
        geldig_tot=props.get("geldig_tot"),
        pand_id=props.get("pand_id") or props.get("identificatie"),
        raw=props,
    )
