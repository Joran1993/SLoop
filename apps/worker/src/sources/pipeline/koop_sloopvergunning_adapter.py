"""Bron: KOOP Gemeenteblad — aangevraagde en verleende sloopvergunningen (landelijk).

Signaalwaarde: 3-12 maanden vóór sloop (aanvraag) of 1-6 maanden (verlening).
Dekt alle Nederlandse gemeenten via w.activiteit=slopen filter op het Gemeenteblad.

Levert gemiddeld ~3.600 nieuwe records per jaar (~300/maand) met adres en geometrie.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Iterator

import httpx
from lxml import etree

from .base import PipelineSourceAdapter, ParsedSignal, RawSignal

log = logging.getLogger(__name__)

_SRU_URL = "https://repository.overheid.nl/sru"
_NS_SRU = "http://docs.oasis-open.org/ns/search-ws/sruResponse"

_SKIP_PATTERNS = re.compile(
    r"(mobiel breken|puinbreken|ingetrokken|intrekk|buiten behandeling|niet ontvankelijk)",
    re.IGNORECASE,
)
_SLOOPMELDING_PATTERN = re.compile(r"\bsloopmelding\b", re.IGNORECASE)
_AANVRAAG_PATTERN = re.compile(r"\b(aanvraag|aangevraagd|ingediend|ontvangen)\b", re.IGNORECASE)
_VERLENING_PATTERN = re.compile(
    r"\b(verleend|besluit|beschikking|vergund|toegestaan)\b", re.IGNORECASE
)

# Matches RD New POINT geometry: "POINT(x y)" or "POINT (x y)"
_POINT_RE = re.compile(r"POINT\s*\(\s*([\d.]+)\s+([\d.]+)\s*\)", re.IGNORECASE)
# Matches first coordinate pair from POLYGON for centroid approximation
_POLYGON_FIRST_RE = re.compile(r"POLYGON\s*\(\s*\(\s*([\d.]+)\s+([\d.]+)", re.IGNORECASE)

_PAGE_SIZE = 100
_MAX_RECORDS = 2000

_PDOK_LOCATIE_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"

# Direct adrespatroon na "omgevingsvergunning" of "sloopvergunning"
_OMGEV_ADRES_RE = re.compile(
    r"(?:omgevingsvergunning|sloopvergunning)\s+(.+?),\s*(\d{4}\s?[A-Z]{2})",
    re.IGNORECASE,
)


def _geocode_pdok(address_text: str, gemeente: str | None) -> str | None:
    """Geocodeer adres via PDOK Locatieserver (gratis) → bag_pand_id."""
    if not address_text:
        return None
    q = address_text.split(",")[0].strip()
    if gemeente:
        q = f"{q} {gemeente}"
    try:
        with httpx.Client(timeout=6) as client:
            resp = client.get(_PDOK_LOCATIE_URL, params={
                "q": q,
                "fq": "type:adres",
                "rows": 1,
                "fl": "pandidentificatie,weergavenaam",
            })
            if resp.status_code != 200:
                return None
            docs = resp.json().get("response", {}).get("docs", [])
            if docs:
                return docs[0].get("pandidentificatie") or None
    except Exception:
        pass
    return None


def _parse_rd_geometry(geom_str: str | None) -> str | None:
    """Haal EWKT POINT uit een KOOP geometrie-string (RD New / EPSG:28992)."""
    if not geom_str:
        return None
    m = _POINT_RE.search(geom_str)
    if m:
        return f"SRID=28992;POINT({m.group(1)} {m.group(2)})"
    m = _POLYGON_FIRST_RE.search(geom_str)
    if m:
        return f"SRID=28992;POINT({m.group(1)} {m.group(2)})"
    return None


_STREET_WORD_RE = re.compile(
    r"\b\w+(?:straat|weg|laan|plein|dijk|kade|hof|gracht|dreef|allee|baan|pad|steeg|drift|dam|singel|markt|boulevard|ring|oord|park)\b",
    re.IGNORECASE,
)


def _extract_address(title: str, gemeente: str | None) -> str | None:
    """Probeer adres te extraheren uit publicatietitel."""
    # Primair: direct patroon "omgevingsvergunning/sloopvergunning <adres>, <postcode>"
    m = _OMGEV_ADRES_RE.search(title)
    if m:
        adres = m.group(1).strip().rstrip(",")
        postcode = m.group(2).replace(" ", "")
        return f"{adres}, {postcode}{(' ' + gemeente) if gemeente else ''}"

    postcode_m = re.search(r"(\d{4}\s?[A-Z]{2})", title)
    if not postcode_m:
        return None

    postcode = postcode_m.group(1).replace(" ", "")
    before = title[: postcode_m.start()].strip().rstrip(",").rstrip()

    # Zoek het laatste straatwoord en neem alles daarvandaan
    street_matches = list(_STREET_WORD_RE.finditer(before))
    if street_matches:
        last_street = street_matches[-1]
        fragment_start = before.rfind(" ", 0, last_street.start())
        adres = before[fragment_start + 1 if fragment_start >= 0 else 0:].strip()
    else:
        # Fallback: neem laatste segment na scheidingstekens
        for sep in (", ", ": ", " voor ", " aan de ", " ten behoeve van ", " te "):
            idx = before.rfind(sep)
            if idx != -1:
                before = before[idx + len(sep):]
        adres = before.strip()

    if adres and len(adres) > 3:
        return f"{adres}, {postcode}{(' ' + gemeente) if gemeente else ''}"
    return None


def _iter_records(root: etree._Element) -> Iterator[dict]:
    """Itereer over GZD records en extraheer relevante velden."""
    current: dict = {}
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        text = (elem.text or "").strip()
        if not text:
            continue
        if tag == "identifier" and text.startswith("gmb-"):
            if current.get("id"):
                yield current
            current = {"id": text}
        elif current and tag == "title":
            current.setdefault("title", text)
        elif current and tag == "abstract":
            current.setdefault("abstract", text)
        elif current and tag == "modified":
            current.setdefault("modified", text)
        elif current and tag == "ligtInGemeente":
            current.setdefault("gemeente", text)
        elif current and tag == "geometrie":
            current.setdefault("geometrie", text)
        elif current and tag == "locatiepunt":
            current.setdefault("locatiepunt", text)
        elif current and tag in ("preferredUrl", "url") and "zoek.officielebekendmakingen" in text:
            current.setdefault("source_url", text)
    if current.get("id"):
        yield current


class KoopSloopVergunningAdapter(PipelineSourceAdapter):
    """Landelijke sloopvergunning-adapter via KOOP Gemeenteblad (activiteit=slopen)."""

    source_name = "koop_sloopvergunning"
    cron_schedule = "0 7 * * *"

    def fetch_signals(self, since: datetime) -> Iterator[RawSignal]:
        since_str = since.strftime("%Y-%m-%d")
        query = (
            f"w.publicatienaam=Gemeenteblad"
            f" AND w.activiteit=slopen"
            f" AND dt.modified>={since_str}"
        )

        start = 1
        fetched = 0
        while fetched < _MAX_RECORDS:
            try:
                with httpx.Client(timeout=30) as client:
                    resp = client.get(_SRU_URL, params={
                        "operation": "searchRetrieve",
                        "version": "2.0",
                        "query": query,
                        "startRecord": start,
                        "maximumRecords": _PAGE_SIZE,
                        "recordSchema": "gzd",
                    })
                    resp.raise_for_status()
            except Exception as exc:
                log.warning("[%s] Fetch mislukt (start=%d): %s", self.source_name, start, exc)
                break

            try:
                root = etree.fromstring(resp.content)
            except Exception as exc:
                log.warning("[%s] XML parse fout: %s", self.source_name, exc)
                break

            records = root.findall(f".//{{{_NS_SRU}}}record")
            if not records:
                break

            for rec_data in _iter_records(root):
                if not rec_data.get("id"):
                    continue
                fetched += 1
                yield RawSignal(
                    source_id=rec_data["id"],
                    raw_payload=rec_data,
                    source_url=rec_data.get("source_url"),
                )

            if len(records) < _PAGE_SIZE:
                break
            start += _PAGE_SIZE

        log.info("[%s] %d publicaties opgehaald", self.source_name, fetched)

    def parse_signal(self, raw: RawSignal) -> ParsedSignal | None:
        rec = raw.raw_payload
        title = rec.get("title", "") or ""
        abstract = rec.get("abstract", "") or ""
        combined = f"{title} {abstract}"

        # Sloopmelding: al gedekt door koop_sloopmelding_adapter — overslaan
        if _SLOOPMELDING_PATTERN.search(title):
            return None

        # Niet-relevante publicaties overslaan
        if _SKIP_PATTERNS.search(combined):
            return None

        gemeente = rec.get("gemeente") or None

        # Bepaal signaaltype op basis van titelinhoud
        is_verleend = bool(_VERLENING_PATTERN.search(combined))
        is_aanvraag = bool(_AANVRAAG_PATTERN.search(combined))

        if not is_verleend and not is_aanvraag:
            return None

        signal_type = "verleende_sloopvergunning" if is_verleend else "aangevraagde_sloopvergunning"
        signal_strength = "high" if is_verleend else "medium"
        horizon_min = 1 if is_verleend else 3
        horizon_max = 6 if is_verleend else 12

        # Datum
        datum_str = rec.get("modified", "")
        try:
            signal_time = datetime.fromisoformat(datum_str).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            signal_time = datetime.now(timezone.utc)

        # Geometrie (EPSG:28992)
        geometry_ewkt = _parse_rd_geometry(rec.get("geometrie"))

        # Adres + geocodeer naar bag_pand_id
        address_text = _extract_address(title, gemeente)
        bag_pand_id = _geocode_pdok(address_text, gemeente) if address_text else None

        return ParsedSignal(
            source=self.source_name,
            source_id=raw.source_id,
            signal_type=signal_type,
            signal_strength=signal_strength,
            signal_time=signal_time,
            title=title[:200] if title else None,
            description=abstract[:300] if abstract else None,
            address_text=address_text,
            postcode=None,
            gemeente=gemeente,
            bag_pand_id=bag_pand_id,
            geometry_ewkt=geometry_ewkt,
            source_url=raw.source_url or f"https://zoek.officielebekendmakingen.nl/{raw.source_id}.html",
            raw_payload=rec,
            estimated_horizon_months_min=horizon_min,
            estimated_horizon_months_max=horizon_max,
            eigenaar_type="onbekend",
        )
