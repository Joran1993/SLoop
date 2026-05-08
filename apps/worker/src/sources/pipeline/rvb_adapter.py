"""Bron 5: Rijksvastgoedbedrijf (RVB) — afstoting en herontwikkeling overheidsgebouwen.

Signaalwaarde: 12-36 maanden vóór sloop. Horizon: 18-36 maanden.

Gebruikt KOOP SRU (repository.overheid.nl) met filter op creator=Rijksvastgoedbedrijf
en/of publicaties in het Staatsblad over rijksvastgoed.
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

_FILTER_KEYWORDS = [
    "sloop", "afstoot", "herontwikkeling", "transformatie",
    "renovatie", "nieuwbouw", "verkoop rijksvastgoed",
]

_NS = "http://standaarden.overheid.nl/sru/"


class RvbAdapter(PipelineSourceAdapter):
    source_name = "rvb"
    cron_schedule = "0 9 * * 2"

    def fetch_signals(self, since: datetime) -> Iterator[RawSignal]:
        since_str = since.strftime("%Y-%m-%d")
        kw_parts = " OR ".join(f'cql.textAndIndexes="{kw}"' for kw in _FILTER_KEYWORDS)
        query = (
            f"dt.modified>={since_str}"
            f" AND cql.textAndIndexes=\"rijksvastgoedbedrijf\""
            f" AND ({kw_parts})"
        )

        start = 1
        page_size = 50
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

            sru_ns = "http://docs.oasis-open.org/ns/search-ws/sruResponse"
            records = root.findall(f".//{{{sru_ns}}}record")
            if not records:
                break

            for rec in records:
                raw = _parse_gzd_record(rec)
                if not raw:
                    continue
                yield RawSignal(
                    source_id=raw["id"],
                    raw_payload=raw,
                    source_url=raw.get("url"),
                )

            if len(records) < page_size:
                break
            start += page_size

    def parse_signal(self, raw: RawSignal) -> ParsedSignal | None:
        item = raw.raw_payload
        titel = item.get("titel", "") or ""
        datum_str = item.get("datum", "")

        try:
            signal_time = datetime.fromisoformat(datum_str[:10]).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            signal_time = datetime.now(timezone.utc)

        return ParsedSignal(
            source=self.source_name,
            source_id=raw.source_id,
            signal_type="eigendomsoverdracht",
            signal_strength="medium",
            signal_time=signal_time,
            title=titel[:200] or None,
            description=item.get("beschrijving"),
            address_text=None,
            postcode=None,
            gemeente=item.get("gemeente") or None,
            bag_pand_id=None,
            geometry_ewkt=None,
            source_url=raw.source_url,
            raw_payload=item,
            estimated_horizon_months_min=12,
            estimated_horizon_months_max=36,
            eigenaar_type="overheid",
        )


def _parse_gzd_record(rec) -> dict | None:
    try:
        DC = "http://purl.org/dc/terms/"

        def dc(tag):
            el = rec.find(f".//{{{DC}}}{tag}")
            return (el.text or "").strip() if el is not None and el.text else ""

        doc_id = dc("identifier")
        if not doc_id:
            return None
        return {
            "id": doc_id,
            "titel": dc("title") or dc("alternative"),
            "gemeente": dc("creator"),
            "datum": dc("modified") or dc("date") or dc("available"),
            "beschrijving": dc("description"),
            "url": f"https://zoek.officielebekendmakingen.nl/{doc_id}.html",
        }
    except Exception:
        return None
