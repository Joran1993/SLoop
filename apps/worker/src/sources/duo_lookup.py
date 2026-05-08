"""DUO open onderwijsdata — schoolnaam + contact op basis van postcode.

Datasets worden bij eerste gebruik gedownload en in-memory gecachet.
Updatefrequentie DUO: maandelijks.

Gebruik:
    from src.sources.duo_lookup import lookup_school_by_postcode
    result = lookup_school_by_postcode("1234AB", "12")
    # → {"contact_naam": "CBS De Regenboog", "contact_website": "www.cbsregenboog.nl",
    #    "contact_telefoon": "020-1234567", "eigenaar_naam": "CBS De Regenboog"}
"""
from __future__ import annotations

import csv
import io
import logging
from functools import lru_cache

import httpx

log = logging.getLogger(__name__)

_PO_URL = "https://duo.nl/open_onderwijsdata/images/02.-alle-schoolvestigingen-basisonderwijs.csv"
_VO_URL = "https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv"

# postcode_normalized -> list of records
_Index = dict[str, list[dict]]


def _normalize_postcode(pc: str | None) -> str:
    return (pc or "").replace(" ", "").upper()


def _download_csv(url: str) -> list[dict]:
    try:
        resp = httpx.get(url, timeout=30, follow_redirects=True,
                         headers={"User-Agent": "SloopradarWorker/1.0"})
        resp.raise_for_status()
        content = resp.content.decode("latin-1")
        reader = csv.DictReader(io.StringIO(content), delimiter=";")
        return list(reader)
    except Exception as exc:
        log.warning("DUO download mislukt (%s): %s", url, exc)
        return []


@lru_cache(maxsize=1)
def _build_index() -> _Index:
    log.info("DUO index opbouwen (eenmalig)...")
    idx: _Index = {}
    for url in (_PO_URL, _VO_URL):
        for row in _download_csv(url):
            pc = _normalize_postcode(row.get("POSTCODE"))
            if pc:
                idx.setdefault(pc, []).append(row)
    log.info("DUO index klaar: %d postcodes", len(idx))
    return idx


def lookup_school_by_postcode(
    postcode: str | None,
    huisnummer: str | None = None,
) -> dict:
    """
    Zoek schoolnaam + contact op postcode (+ optioneel huisnummer).
    Geeft leeg dict terug als niets gevonden.
    """
    if not postcode:
        return {}

    idx = _build_index()
    pc_norm = _normalize_postcode(postcode)
    candidates = idx.get(pc_norm, [])

    if not candidates:
        return {}

    # Verfijn op huisnummer als gegeven
    if huisnummer:
        hn = str(huisnummer).strip()
        matches = [
            r for r in candidates
            if str(r.get("HUISNUMMER-TOEVOEGING", "")).strip().startswith(hn)
        ]
        if matches:
            candidates = matches

    best = candidates[0]
    naam = best.get("VESTIGINGSNAAM", "").strip()
    telefoon = best.get("TELEFOONNUMMER", "").strip() or None
    website = best.get("INTERNETADRES", "").strip() or None

    if not naam:
        return {}

    result: dict = {"eigenaar_naam": naam, "contact_naam": naam}
    if telefoon:
        result["contact_telefoon"] = telefoon
    if website:
        # Zorg voor volledig URL
        if not website.startswith("http"):
            website = f"https://{website}"
        result["contact_website"] = website
    return result
