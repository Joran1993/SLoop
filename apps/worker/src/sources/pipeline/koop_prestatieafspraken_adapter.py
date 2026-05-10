"""Woningcorporatie sloopplannen via prestatieafspraken in het Gemeenteblad.

Woningcorporaties publiceren jaarlijks prestatieafspraken met gemeenten.
Die bevatten soms specifieke slooplocaties (adressen) 12-36 maanden vóór sloop.

Aanpak:
  1. KOOP SRU: vind Gemeenteblad-publicaties met 'prestatieafspraken' + slooptermen
  2. Haal de HTML-pagina op (zoek.officielebekendmakingen.nl/{id}.html)
  3. Extraheer Nederlandse adressen (postcode-regex)
  4. Elk adres → één RawSignal → resolve_location() → bag_pand_id

Levert gemiddeld ~20-80 adres-signalen per maand.
Horizon: 12-36 maanden.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Iterator

import httpx
from lxml import etree, html

from .base import PipelineSourceAdapter, ParsedSignal, RawSignal

log = logging.getLogger(__name__)

_SRU_URL = "https://repository.overheid.nl/sru"
_NS_SRU = "http://docs.oasis-open.org/ns/search-ws/sruResponse"
_OBK_BASE = "https://zoek.officielebekendmakingen.nl"

# Prestatieafspraken die sloopplannen noemen
_SLOOP_RE = re.compile(
    r"\b(slopen|sloopplan|sloopwoningen|slooplocaties|te\s+slopen|worden\s+gesloopt|sloopjaar|renovatie\s+of\s+sloop)\b",
    re.IGNORECASE,
)

# Publicaties overslaan die duidelijk geen woningcorporatie-sloop zijn
_SKIP_RE = re.compile(
    r"\b(legesverordening|APV|grondbeleid|omgevingsvisie|welstandsnota|erfgoedverordening"
    r"|parkeerbeleid|subsidieregeling|verkeersplan|milieubeleidsplan)\b",
    re.IGNORECASE,
)

# Postcode-patroon als kern van adresextractie
_POSTCODE_RE = re.compile(r"\b(\d{4})\s*([A-Z]{2})\b")

# Straatwoorden voor adres-extractie (zelfde logica als koop_sloopvergunning_adapter)
_STREET_WORD_RE = re.compile(
    r"\b\w+(?:straat|weg|laan|plein|dijk|kade|hof|gracht|dreef|allee|baan|pad|steeg"
    r"|drift|dam|singel|markt|boulevard|ring|oord|park|laantje|gaarde|veld|tuin|stroom)\b",
    re.IGNORECASE,
)

_PAGE_SIZE = 50
_MAX_RECORDS = 300           # Max publicaties per run
_MAX_HTML_PER_RUN = 80       # Max HTML-fetches per run (rate-limiting)
_HTML_DELAY_S = 0.4          # Rust tussen HTML-requests


def _iter_sru_records(root: etree._Element) -> Iterator[dict]:
    """Extraheer basisvelden uit GZD SRU-records."""
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
        elif current:
            if tag == "title":
                current.setdefault("title", text)
            elif tag == "abstract":
                current.setdefault("abstract", text)
            elif tag == "modified":
                current.setdefault("modified", text)
            elif tag in ("ligtInGemeente", "gemeentenaam", "creator"):
                current.setdefault("gemeente", text)
            elif tag in ("preferredUrl", "url") and "zoek.officielebekendmakingen" in text:
                current.setdefault("source_url", text)
    if current.get("id"):
        yield current


def _extract_addresses_from_text(text: str, gemeente: str | None) -> list[str]:
    """
    Extraheer adres-strings uit vrije tekst via postcode-patroon.
    Retourneert lijst van 'Straatnaam HNR, PPCPLA'-strings.
    """
    results: set[str] = set()
    for m in _POSTCODE_RE.finditer(text):
        postcode = m.group(1) + m.group(2)
        before = text[: m.start()].strip()

        # Zoek straatwoord vóór de postcode
        street_matches = list(_STREET_WORD_RE.finditer(before))
        if not street_matches:
            continue

        last = street_matches[-1]
        fragment_start = before.rfind(" ", 0, last.start())
        adres_fragment = before[fragment_start + 1 if fragment_start >= 0 else 0:].strip()

        # Neem maximaal 5 woorden vóór de postcode
        words = adres_fragment.split()
        if len(words) > 5:
            adres_fragment = " ".join(words[-5:])

        if adres_fragment and len(adres_fragment) > 3:
            full = f"{adres_fragment}, {postcode}"
            if gemeente:
                full += f" {gemeente}"
            results.add(full)

    return list(results)


def _fetch_html_text(pub_id: str, client: httpx.Client) -> str | None:
    """Haal de HTML-tekst op van een officielebekendmakingen.nl-pagina."""
    url = f"{_OBK_BASE}/{pub_id}.html"
    try:
        resp = client.get(url, timeout=15)
        resp.raise_for_status()
        doc = html.fromstring(resp.content)
        # Gooi navigatie/header weg, pak alleen de documentinhoud
        for bad in doc.cssselect("nav, header, footer, script, style"):
            bad.getparent().remove(bad) if bad.getparent() is not None else None
        return doc.text_content()
    except Exception as exc:
        log.debug("[prestatieafspraken] HTML fetch mislukt voor %s: %s", pub_id, exc)
        return None


class KoopPrestatieafsprakenAdapter(PipelineSourceAdapter):
    """Woningcorporatie sloopplannen via prestatieafspraken in het Gemeenteblad."""

    source_name = "woningcorporatie_prestatieafspraken"
    cron_schedule = "0 6 * * 1"  # Elke maandag 06:00

    def fetch_signals(self, since: datetime) -> Iterator[RawSignal]:
        since_str = since.strftime("%Y-%m-%d")
        query = (
            f"w.publicatienaam=Gemeenteblad"
            f" AND cql.textAndIndexes=\"prestatieafspraken\""
            f" AND (cql.textAndIndexes=\"slopen\" OR cql.textAndIndexes=\"sloopplan\""
            f" OR cql.textAndIndexes=\"sloopwoningen\")"
            f" AND dt.modified>={since_str}"
        )

        start = 1
        fetched = 0
        html_fetched = 0

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            while fetched < _MAX_RECORDS:
                try:
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
                    log.warning("[%s] SRU fetch mislukt (start=%d): %s", self.source_name, start, exc)
                    break

                try:
                    root = etree.fromstring(resp.content)
                except Exception as exc:
                    log.warning("[%s] XML parse fout: %s", self.source_name, exc)
                    break

                records = root.findall(f".//{{{_NS_SRU}}}record")
                if not records:
                    break

                for rec in _iter_sru_records(root):
                    pub_id = rec.get("id", "")
                    if not pub_id:
                        continue

                    title = rec.get("title", "") or ""
                    abstract = rec.get("abstract", "") or ""
                    gemeente = rec.get("gemeente") or None

                    # Sla evidente ruis over (beleid/verordeningen)
                    if _SKIP_RE.search(title):
                        continue
                    # SRU-query filtert al op "prestatieafspraken" + "slopen" in volledige tekst;
                    # hier geen extra titelfilter — dat gooit te veel weg.

                    # Probeer adressen te extraheren uit abstract
                    addresses = _extract_addresses_from_text(abstract, gemeente)

                    # Als abstract geen adressen geeft: haal HTML op (met rate-limit)
                    if not addresses and html_fetched < _MAX_HTML_PER_RUN:
                        time.sleep(_HTML_DELAY_S)
                        page_text = _fetch_html_text(pub_id, client)
                        html_fetched += 1
                        if page_text and _SLOOP_RE.search(page_text):
                            addresses = _extract_addresses_from_text(page_text, gemeente)

                    if addresses:
                        # Eén signaal per gevonden adres
                        for i, adres in enumerate(addresses):
                            yield RawSignal(
                                source_id=f"{pub_id}_{i}",
                                raw_payload={
                                    "pub_id": pub_id,
                                    "title": title,
                                    "abstract": abstract,
                                    "gemeente": gemeente,
                                    "modified": rec.get("modified", ""),
                                    "address_text": adres,
                                },
                                source_url=rec.get("source_url") or f"{_OBK_BASE}/{pub_id}.html",
                            )
                    else:
                        # Geen adressen gevonden: gemeente-niveau marker (wordt niet
                        # omgezet naar lead vanwege ontbrekend bag_pand_id, maar
                        # blijft beschikbaar in pipeline_signals als referentie)
                        yield RawSignal(
                            source_id=pub_id,
                            raw_payload={
                                "pub_id": pub_id,
                                "title": title,
                                "abstract": abstract,
                                "gemeente": gemeente,
                                "modified": rec.get("modified", ""),
                                "address_text": None,
                            },
                            source_url=rec.get("source_url") or f"{_OBK_BASE}/{pub_id}.html",
                        )

                fetched += len(records)
                if len(records) < _PAGE_SIZE:
                    break
                start += _PAGE_SIZE

        log.info("[%s] %d publicaties verwerkt, %d HTML-fetches, %d signalen",
                 self.source_name, fetched, html_fetched,
                 sum(1 for _ in []))  # count wordt bijgehouden door caller

    def parse_signal(self, raw: RawSignal) -> ParsedSignal | None:
        rec = raw.raw_payload
        title = rec.get("title", "") or ""
        gemeente = rec.get("gemeente") or None
        address_text = rec.get("address_text") or None

        datum_str = rec.get("modified", "")
        try:
            signal_time = datetime.fromisoformat(datum_str[:10]).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError, AttributeError):
            signal_time = datetime.now(timezone.utc)

        return ParsedSignal(
            source=self.source_name,
            source_id=raw.source_id,
            signal_type="woningcorporatie_sloopplan",
            signal_strength="medium",
            signal_time=signal_time,
            title=title[:200] or None,
            description=rec.get("abstract", "")[:300] or None,
            address_text=address_text,
            postcode=None,
            gemeente=gemeente,
            bag_pand_id=None,
            geometry_ewkt=None,
            source_url=raw.source_url,
            raw_payload=rec,
            estimated_horizon_months_min=12,
            estimated_horizon_months_max=36,
            eigenaar_type="corporatie_waarschijnlijk",
        )
