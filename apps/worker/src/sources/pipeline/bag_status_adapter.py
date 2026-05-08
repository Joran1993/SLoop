"""BAG pandstatus — signalen op basis van 'Sloopvergunning verleend' status in BAG.

Signaalwaarde: 0-3 maanden vóór sloop. Horizon: 0-3 maanden.
Meest directe signaal: gemeente heeft bouwrechtelijk toestemming gegeven tot slopen.

Werkt via onze eigen bag_panden tabel (reeds gevuld door koop_pipeline enrichment).
Refresht ook BAG status van bestaande leads.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Iterator

import httpx
from supabase import create_client

from .base import PipelineSourceAdapter, ParsedSignal, RawSignal

log = logging.getLogger(__name__)

_HIGH_VALUE_STATUSES = {
    "Sloopvergunning verleend",
    "Pand buiten gebruik",
}

_BAG_OGC_BASE = "https://api.pdok.nl/kadaster/bag/ogc/v2/collections"


class BagStatusAdapter(PipelineSourceAdapter):
    source_name = "bag_status"
    cron_schedule = "0 6 * * *"  # dagelijks 06:00

    def fetch_signals(self, since: datetime) -> Iterator[RawSignal]:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        sb = create_client(url, key)

        # 1. Haal alle bag_panden op met relevante status
        offset = 0
        while True:
            result = (
                sb.table("bag_panden")
                .select("pand_id,status,bouwjaar,last_synced_at")
                .in_("status", list(_HIGH_VALUE_STATUSES))
                .range(offset, offset + 499)
                .execute()
            )
            rows = result.data or []
            for row in rows:
                yield RawSignal(
                    source_id=f"bag_status_{row['pand_id']}",
                    raw_payload=row,
                    source_url=f"https://bagviewer.kadaster.nl/lvbag/bag-viewer/index.html#?objecttype=pand&objectid={row['pand_id']}",
                )
            offset += len(rows)
            if len(rows) < 500:
                break

        # 2. Refresh BAG status voor leads waarvan pand_id bekend is
        # (steekproef: eerste 200 leads met pand_id, gesorteerd op score)
        leads = (
            sb.table("sloop_leads")
            .select("pand_id,gemeente,provincie,address_full")
            .not_.is_("pand_id", "null")
            .order("score_total", desc=True)
            .limit(200)
            .execute()
        ).data or []

        checked = 0
        for lead in leads:
            pand_id = lead.get("pand_id")
            if not pand_id:
                continue
            try:
                fresh_status = _fetch_bag_status(pand_id)
            except Exception as exc:
                log.debug("BAG status refresh mislukt voor %s: %s", pand_id, exc)
                continue

            if fresh_status and fresh_status in _HIGH_VALUE_STATUSES:
                # Update bag_panden tabel
                sb.table("bag_panden").upsert({
                    "pand_id": pand_id,
                    "status": fresh_status,
                    "last_synced_at": datetime.now(timezone.utc).isoformat(),
                }, on_conflict="pand_id").execute()

                yield RawSignal(
                    source_id=f"bag_status_{pand_id}",
                    raw_payload={
                        "pand_id": pand_id,
                        "status": fresh_status,
                        "gemeente": lead.get("gemeente"),
                        "address_full": lead.get("address_full"),
                    },
                    source_url=f"https://bagviewer.kadaster.nl/lvbag/bag-viewer/index.html#?objecttype=pand&objectid={pand_id}",
                )

            checked += 1
            if checked % 20 == 0:
                time.sleep(1)

    def parse_signal(self, raw: RawSignal) -> ParsedSignal | None:
        item = raw.raw_payload
        pand_id = item.get("pand_id")
        status = item.get("status", "")

        if not pand_id or status not in _HIGH_VALUE_STATUSES:
            return None

        if status == "Sloopvergunning verleend":
            signal_type = "sloopvergunning_verleend"
            signal_strength = "high"
            horizon_min, horizon_max = 0, 3
            title = f"Sloopvergunning verleend — pand {pand_id}"
        else:
            signal_type = "pand_buiten_gebruik"
            signal_strength = "medium"
            horizon_min, horizon_max = 3, 18
            title = f"Pand buiten gebruik — {pand_id}"

        address = item.get("address_full") or item.get("address_text")
        gemeente = item.get("gemeente")

        return ParsedSignal(
            source=self.source_name,
            source_id=raw.source_id,
            signal_type=signal_type,
            signal_strength=signal_strength,
            signal_time=datetime.now(timezone.utc),
            title=title,
            description=f"BAG pandstatus: {status}",
            address_text=address,
            postcode=None,
            gemeente=gemeente,
            bag_pand_id=pand_id,
            geometry_ewkt=None,
            source_url=raw.source_url,
            raw_payload=item,
            estimated_horizon_months_min=horizon_min,
            estimated_horizon_months_max=horizon_max,
            eigenaar_type="onbekend",
        )


def _fetch_bag_status(pand_id: str) -> str | None:
    """Haal actuele BAG pandstatus op via OGC API."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{_BAG_OGC_BASE}/pand/items",
                params={"identificatie": pand_id, "f": "json"},
            )
            if resp.status_code == 200:
                features = resp.json().get("features", [])
                if features:
                    return features[0].get("properties", {}).get("status")
    except Exception:
        pass
    return None
