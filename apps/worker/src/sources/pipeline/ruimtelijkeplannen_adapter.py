"""Bron 1: Ruimtelijkeplannen — bestemmingsplan- en omgevingsplanmutaties.

Signaalwaarde: 12-36 maanden vóór sloop. Horizon: 18-30 maanden.

Bron: KOOP SRU (repository.overheid.nl) — Gemeenteblad publicaties van
vastgestelde bestemmingsplannen en omgevingsplanwijzigingen met
herontwikkeling-gerelateerde trefwoorden.

Noot: de originele PDOK WFS (service.pdok.nl/kadaster/plannen) is offline
sinds begin 2026. KOOP SRU dekt hetzelfde corpus via officielebekendmakingen.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterator

import httpx
from lxml import etree

from .base import PipelineSourceAdapter, ParsedSignal, RawSignal

log = logging.getLogger(__name__)

_SRU_URL = "https://repository.overheid.nl/sru"
_DC = "http://purl.org/dc/terms/"
_SRU_NS = "http://docs.oasis-open.org/ns/search-ws/sruResponse"

_PLAN_KEYWORDS = [
    "sloop", "herontwikkeling", "transformatie", "woningbouw",
    "nieuwbouw", "gebiedsontwikkeling", "verdichting", "herstructurering",
    "sanering", "renovatie",
]

_PLAN_TYPES = [
    "bestemmingsplan", "omgevingsplan", "wijzigingsplan",
    "inpassingsplan", "omgevingsprogramma",
]


class RuimtelijkePlannenAdapter(PipelineSourceAdapter):
    source_name = "ruimtelijkeplannen"
    cron_schedule = "0 6 * * *"

    def fetch_signals(self, since: datetime) -> Iterator[RawSignal]:
        since_str = since.strftime("%Y-%m-%d")
        type_parts = " OR ".join(f'cql.textAndIndexes="{t}"' for t in _PLAN_TYPES)
        kw_parts = " OR ".join(f'cql.textAndIndexes="{k}"' for k in _PLAN_KEYWORDS)
        query = (
            f"w.publicatienaam=Gemeenteblad"
            f" AND dt.modified>={since_str}"
            f" AND ({type_parts})"
            f" AND ({kw_parts})"
        )

        start = 1
        page_size = 50
        max_records = 500
        fetched = 0

        while True:
            try:
                with httpx.Client(timeout=30) as client:
                    resp = client.get(_SRU_URL, params={
                        "operation": "searchRetrieve",
                        "version": "2.0",
                        "query": query,
                        "startRecord": start,
                        "maximumRecords": page_size,
                        "recordSchema": "gzd",
                    })
                    resp.raise_for_status()
            except Exception as exc:
                log.warning("[%s] Fetch mislukt (start=%d): %s", self.source_name, start, exc)
                break

            try:
                root = etree.fromstring(resp.content)
            except Exception:
                break

            records = root.findall(f".//{{{_SRU_NS}}}record")
            if not records:
                break

            for rec in records:
                raw = _parse_record(rec)
                if not raw:
                    continue
                yield RawSignal(
                    source_id=raw["id"],
                    raw_payload=raw,
                    source_url=raw.get("url"),
                )

            fetched += len(records)
            if len(records) < page_size or fetched >= max_records:
                break
            start += page_size

    def parse_signal(self, raw: RawSignal) -> ParsedSignal | None:
        item = raw.raw_payload
        titel = item.get("titel", "") or ""
        gemeente = item.get("gemeente", "") or ""
        datum_str = item.get("datum", "")

        try:
            signal_time = datetime.fromisoformat(datum_str[:10]).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            signal_time = datetime.now(timezone.utc)

        plan_type = _detect_plan_type(titel)
        signal_type = {
            "omgevingsplan": "omgevingsplan_mutatie",
            "wijzigingsplan": "bestemmingswijziging_herziening",
        }.get(plan_type, "bestemmingswijziging")

        strength = "high" if plan_type in ("bestemmingsplan", "omgevingsplan") else "medium"

        return ParsedSignal(
            source=self.source_name,
            source_id=raw.source_id,
            signal_type=signal_type,
            signal_strength=strength,
            signal_time=signal_time,
            title=titel[:200] or None,
            description=None,
            address_text=None,
            postcode=None,
            gemeente=gemeente or None,
            bag_pand_id=None,
            geometry_ewkt=None,
            source_url=raw.source_url,
            raw_payload=item,
            estimated_horizon_months_min=18,
            estimated_horizon_months_max=30,
            eigenaar_type="onbekend",
        )


def _parse_record(rec) -> dict | None:
    try:
        def dc(tag):
            el = rec.find(f".//{{{_DC}}}{tag}")
            return (el.text or "").strip() if el is not None and el.text else ""

        doc_id = dc("identifier")
        if not doc_id:
            return None
        return {
            "id": doc_id,
            "titel": dc("title") or dc("alternative"),
            "gemeente": dc("creator"),
            "datum": dc("modified") or dc("date") or dc("available"),
            "url": f"https://zoek.officielebekendmakingen.nl/{doc_id}.html",
        }
    except Exception:
        return None


def _detect_plan_type(titel: str) -> str:
    t = titel.lower()
    if "omgevingsplan" in t:
        return "omgevingsplan"
    if "wijzigingsplan" in t:
        return "wijzigingsplan"
    if "inpassingsplan" in t:
        return "inpassingsplan"
    return "bestemmingsplan"
