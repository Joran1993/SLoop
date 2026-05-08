"""KVK Handelsregister lookup — zoekt bedrijven op adres.

Vereist: KVK_API_KEY in omgeving (gratis aanvragen via developer.kvk.nl).
Als de key ontbreekt wordt de lookup overgeslagen.

Gebruik:
    from src.sources.kvk_lookup import lookup_eigenaar_by_address
    result = lookup_eigenaar_by_address("Keizersgracht", "1", "Amsterdam")
    # → {"naam": "Bedrijfsnaam BV", "kvk_nummer": "12345678", "rechtsvorm": "BV"}
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

import httpx

log = logging.getLogger(__name__)

_KVK_BASE = "https://api.kvk.nl/api/v2"
_CACHE: dict[str, dict | None] = {}  # (straat, nummer, plaats) → resultaat


def lookup_eigenaar_by_address(
    straatnaam: str,
    huisnummer: str,
    plaats: str,
) -> dict | None:
    """
    Zoekt het eerste bedrijf op het opgegeven adres in het KVK.

    Returns dict met keys: naam, kvk_nummer, rechtsvorm, sbi_code, sbi_omschrijving
    of None als niets gevonden of API niet beschikbaar.
    """
    api_key = os.environ.get("KVK_API_KEY")
    if not api_key:
        return None

    cache_key = f"{straatnaam}|{huisnummer}|{plaats}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{_KVK_BASE}/zoeken",
                params={
                    "straatnaam": straatnaam,
                    "huisnummer": huisnummer,
                    "plaats": plaats,
                    "resultatenPerPagina": 5,
                },
                headers={"apikey": api_key},
            )
            if resp.status_code == 404:
                _CACHE[cache_key] = None
                return None
            resp.raise_for_status()
    except Exception as exc:
        log.debug("KVK lookup mislukt voor %s %s %s: %s", straatnaam, huisnummer, plaats, exc)
        return None

    data = resp.json()
    resultaten = data.get("resultaten", [])

    # Prefer hoofdvestiging over rechtspersoon-only entries
    for res in resultaten:
        if res.get("type") in ("hoofdvestiging", "nevenvestiging"):
            result = _extract_result(res)
            _CACHE[cache_key] = result
            return result

    # Fall back to first result
    if resultaten:
        result = _extract_result(resultaten[0])
        _CACHE[cache_key] = result
        return result

    _CACHE[cache_key] = None
    return None


def lookup_eigenaar_by_kvk(kvk_nummer: str) -> dict | None:
    """Haalt bedrijfsdetails op via KVK-nummer."""
    api_key = os.environ.get("KVK_API_KEY")
    if not api_key:
        return None

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"https://api.kvk.nl/api/v1/basisprofielen/{kvk_nummer}",
                headers={"apikey": api_key},
            )
            resp.raise_for_status()
    except Exception as exc:
        log.debug("KVK basisprofiel mislukt voor %s: %s", kvk_nummer, exc)
        return None

    data = resp.json()
    sbi = (data.get("sbiActiviteiten") or [{}])[0]
    return {
        "naam": data.get("naam"),
        "kvk_nummer": kvk_nummer,
        "rechtsvorm": data.get("_embedded", {}).get("eigenaar", {}).get("rechtsvorm"),
        "sbi_code": sbi.get("sbiCode"),
        "sbi_omschrijving": sbi.get("sbiOmschrijving"),
    }


def _extract_result(res: dict) -> dict:
    adres = res.get("adres", {}).get("binnenlandsAdres", {})
    return {
        "naam": res.get("naam"),
        "kvk_nummer": res.get("kvkNummer"),
        "vestigingsnummer": res.get("vestigingsnummer"),
        "rechtsvorm": None,  # Komt via basisprofiel; weglaten voor snelheid
        "straatnaam": adres.get("straatnaam"),
        "huisnummer": adres.get("huisnummer"),
        "plaats": adres.get("plaats"),
    }


def eigenaar_type_from_naam(naam: str | None) -> str:
    """
    Detecteert eigenaar_type op basis van bedrijfsnaam.
    Heuristisch, geen garantie.
    """
    if not naam:
        return "onbekend"
    n = naam.lower()

    CORPORATIE_HINTS = [
        "woningstichting", "woonstichting", "woningcorporatie", "woonzorg",
        "woningbouw", "volkshuisvesting", "patrimonium", "woongroep",
        "vestia", "portaal", "ymere", "alliantie", "mitros", "rochdale",
        "havensteder", "woonbron", "bo-ex", "eigen haard", "de key",
        "haag wonen", "quawonen", "mozaiek", "mozaïek", "wooninc",
        "woonplus", "tablis", "l'escaut", "trivire", "waterweg wonen",
        "stedelink", "wooncompagnie", "woondrecht", "prewonen",
    ]
    if any(h in n for h in CORPORATIE_HINTS):
        return "corporatie"

    if any(w in n for w in ["gemeente", "provincie", "rijksvastgoed", "rijksgebouw", " ministerie"]):
        return "overheid"

    if any(w in n for w in ["b.v.", " bv", " nv", " n.v.", "holding", "vastgoed", "projectontwikkel",
                             "ontwikkeling", " groep", "real estate", "properties"]):
        return "bedrijf"

    return "onbekend"


def infer_eigenaar_type_from_title(titel: str | None) -> str:
    """
    Detecteert eigenaar_type uit de sloopmelding-publicatietitel.
    Gebruikt als aanvullend signaal naast BAG-gegevens.
    """
    if not titel:
        return "onbekend"
    t = titel.lower()

    CORPORATIE_HINTS = [
        "woningcorporatie", "woningstichting", "woonstichting", "sociale huur",
        "corporatiewoning", "vestia", "portaal", "ymere", "alliantie",
        "mitros", "rochdale", "havensteder", "woonbron", "eigen haard",
    ]
    if any(h in t for h in CORPORATIE_HINTS):
        return "corporatie"

    BEDRIJF_HINTS = [
        "bedrijfshal", "bedrijfspand", "loods", "fabriek", "kantoorgebouw",
        "kantoorpand", "fabrieksgebouw", "opslaghal", "industrieel",
        "industriepand", "werkplaats", "garagehal", "showroom", "supermarkt",
        "winkelcentrum", "winkelgebouw", "tankstation", "benzinestation",
        "hotelpand", "kantoorhal", "productiehal",
    ]
    if any(h in t for h in BEDRIJF_HINTS):
        return "bedrijf"

    OVERHEID_HINTS = [
        "schoolgebouw", "basisschool", "middelbare school", "gymnasium",
        "gemeentehuis", "stadhuis", "bibliotheek", "ziekenhuis",
        "verpleeghuis", "brandweerkazerne", "politiebureau", "gemeentelijk",
        "gemeentepand", "sporthal", "zwembad", "wijkgebouw", "buurtcentrum",
        "kerkgebouw", "kapelgebouw",
    ]
    if any(h in t for h in OVERHEID_HINTS):
        return "overheid_instelling"

    return "onbekend"


def infer_eigenaar_type_from_bag(gebruiksdoel: list[str] | None, bouwjaar: int | None) -> str:
    """
    Schat eigenaar_type op basis van BAG gebruiksdoel en bouwjaar.
    Gebruikt als fallback als KVK niet beschikbaar is.

    Logica:
    - woonfunctie + bouwjaar 1945-1995 → waarschijnlijk corporatie (massale naoorlogse bouw)
    - industrie/bedrijf/kantoor → bedrijf
    - overige (sport, onderwijs, gezondheidszorg) → overheid/instelling
    """
    if not gebruiksdoel:
        return "onbekend"

    functies = {g.lower() for g in gebruiksdoel}

    BEDRIJFS_FUNCTIES = {"industriefunctie", "kantoorfunctie", "winkelfunctie", "logiesfunctie"}
    OVERHEID_FUNCTIES = {
        "onderwijsfunctie", "gezondheidszorgfunctie", "sportfunctie",
        "bijeenkomstfunctie", "overige gebruiksfunctie",
    }

    if functies & BEDRIJFS_FUNCTIES:
        return "bedrijf"

    if functies & OVERHEID_FUNCTIES:
        return "overheid_instelling"

    if "woonfunctie" in functies:
        # Sloopmeldingen voor woonfunctie zijn vrijwel nooit van particulieren;
        # corporaties en projectontwikkelaars dienen deze in.
        return "corporatie_waarschijnlijk"

    return "onbekend"
