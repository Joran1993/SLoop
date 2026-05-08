"""Pipeline runner — orkestreert adapter → DB → clusterer → predictor → DB.

Gebruik:
    from src.pipelines.pipeline_runner import run_pipeline
    run_pipeline(adapter, lookback_days=90)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Type

from supabase import create_client, Client

from ..sources.pipeline.base import PipelineSourceAdapter, ParsedSignal
from ..clusterer.clusterer import cluster_signals, SignalCluster
from ..predictor.rules import predict, load_config
from ..sources.kvk_lookup import lookup_eigenaar_by_address, eigenaar_type_from_naam

log = logging.getLogger(__name__)

_MIN_KANS_DEFAULT = 0.10


def _get_supabase() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def run_pipeline(
    adapter: PipelineSourceAdapter,
    lookback_days: int = 90,
) -> dict:
    """
    Voert één adapter-cyclus uit:
    1. Haal signalen op
    2. Parseer en valideer
    3. Sla op in pipeline_signals (upsert)
    4. Cluster + voorspel → pipeline_projects (upsert)
    5. Log voorspelling in pipeline_predictions_log
    """
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    supabase = _get_supabase()
    cfg = load_config()
    min_kans = cfg.get("thresholds", {}).get("min_kans_opslaan", _MIN_KANS_DEFAULT)

    log.info("[%s] Start — since %s", adapter.source_name, since.date())

    # ── 1. Fetch + parse ──────────────────────────────────────────────────────
    parsed_signals: list[ParsedSignal] = []
    raw_count = 0

    for raw in adapter.fetch_signals(since):
        raw_count += 1
        try:
            parsed = adapter.parse_signal(raw)
        except Exception as exc:
            log.warning("[%s] parse_signal fout voor %s: %s", adapter.source_name, raw.source_id, exc)
            continue
        if parsed is None:
            continue
        parsed = adapter.resolve_location(parsed)
        parsed = _enrich_eigenaar(parsed)
        parsed_signals.append(parsed)

    log.info("[%s] %d raw → %d parsed", adapter.source_name, raw_count, len(parsed_signals))

    # ── 2. Upsert pipeline_signals (in batches van 100) ──────────────────────
    inserted_ids: dict[str, str] = {}  # source_id → DB uuid
    if parsed_signals:
        # Dedupliceer op (source, source_id) — duplicaten in één batch geven DB-error
        seen: dict[str, ParsedSignal] = {}
        for s in parsed_signals:
            seen[f"{s.source}:{s.source_id}"] = s
        rows = [_signal_to_row(s) for s in seen.values()]
        for i in range(0, len(rows), 100):
            batch = rows[i:i + 100]
            try:
                result = (
                    supabase.table("pipeline_signals")
                    .upsert(batch, on_conflict="source,source_id", ignore_duplicates=False)
                    .execute()
                )
                for row in result.data or []:
                    key = f"{row['source']}:{row['source_id']}"
                    inserted_ids[key] = row["id"]
            except Exception as exc:
                log.warning("[%s] Upsert batch %d mislukt: %s", adapter.source_name, i, exc)

    # Haal ook reeds bestaande signalen op voor clustervorming
    all_signals = _load_existing_signals(supabase, adapter.source_name)
    if not all_signals:
        all_signals = parsed_signals

    # ── 3. Cluster ────────────────────────────────────────────────────────────
    clusters = cluster_signals(all_signals)
    log.info("[%s] %d signalen → %d clusters", adapter.source_name, len(all_signals), len(clusters))

    # ── 4. Voorspel + upsert pipeline_projects (alleen pand-gekoppelde clusters) ──
    project_count = 0
    for cluster in clusters:
        if not cluster.bag_pand_id:
            continue  # Sla solo/geo clusters over — te veel ruis zonder pand-koppeling
        pred = predict(cluster.signals)
        if pred.sloop_kans < min_kans:
            continue

        project_row = _cluster_to_project_row(cluster, pred)
        try:
            project_id = _upsert_project(supabase, project_row, cluster.bag_pand_id)
        except Exception as exc:
            log.warning("[%s] Upsert project mislukt: %s", adapter.source_name, exc)
            continue

        # Link signalen aan project
        if project_id:
            _link_signals(supabase, project_id, cluster, inserted_ids)

        project_count += 1

    log.info("[%s] %d projecten opgeslagen (kans ≥ %.0f%%)", adapter.source_name, project_count, min_kans * 100)

    return {
        "source": adapter.source_name,
        "raw_signals": raw_count,
        "parsed_signals": len(parsed_signals),
        "clusters": len(clusters),
        "projects_saved": project_count,
    }


def _enrich_eigenaar(parsed: ParsedSignal) -> ParsedSignal:
    """Verrijkt parsed signal met KVK eigenaar info als het adres bruikbaar is."""
    if parsed.eigenaar_naam:
        return parsed
    if not parsed.address_text or not parsed.gemeente:
        return parsed

    # Splits "Straatnaam 12A" uit het adres
    parts = _split_address(parsed.address_text)
    if not parts:
        return parsed

    straatnaam, huisnummer = parts
    kvk_result = lookup_eigenaar_by_address(straatnaam, huisnummer, parsed.gemeente)
    if kvk_result:
        parsed.eigenaar_naam = kvk_result.get("naam")
        if parsed.eigenaar_type == "onbekend":
            parsed.eigenaar_type = eigenaar_type_from_naam(parsed.eigenaar_naam)

    return parsed


def _split_address(address_text: str) -> tuple[str, str] | None:
    """Splits 'Straatnaam 12A, Plaats' → ('Straatnaam', '12A'). Geeft None bij mislukking."""
    import re
    # Verwijder alles na komma (plaatsnaam)
    parts = address_text.split(",")[0].strip()
    m = re.match(r"^(.+?)\s+(\d+\S*)$", parts)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None


def _signal_to_row(s: ParsedSignal) -> dict:
    return {
        "source": s.source,
        "source_id": s.source_id,
        "signal_type": s.signal_type,
        "signal_strength": s.signal_strength,
        "signal_time": s.signal_time.isoformat(),
        "geometry": s.geometry_ewkt,
        "address_text": s.address_text,
        "postcode": s.postcode,
        "gemeente": s.gemeente,
        "bag_pand_id": s.bag_pand_id,
        "title": s.title,
        "description": s.description,
        "raw_payload": s.raw_payload,
        "source_url": s.source_url,
        "estimated_horizon_months_min": s.estimated_horizon_months_min,
        "estimated_horizon_months_max": s.estimated_horizon_months_max,
        "eigenaar_type": s.eigenaar_type,
        "eigenaar_naam": s.eigenaar_naam,
    }


def _cluster_to_project_row(cluster: SignalCluster, pred) -> dict:
    row: dict = {
        "cluster_geometry": cluster.geometry_ewkt,
        "address_text": cluster.address_text,
        "postcode": cluster.postcode,
        "gemeente": cluster.gemeente,
        "sloop_kans": float(pred.sloop_kans),
        "horizon_months_min": pred.horizon_months_min,
        "horizon_months_max": pred.horizon_months_max,
        "signal_count": cluster.signal_count,
        "signal_diversity": cluster.signal_diversity,
        "prediction_explanation": pred.explanation,
        "prediction_version": pred.model_version,
        "status": "actief",
    }
    if cluster.bag_pand_id:
        row["bag_pand_id"] = cluster.bag_pand_id
    return row


def _upsert_project(supabase: Client, row: dict, bag_pand_id: str | None) -> str | None:
    """Insert of update een project. Geeft het DB-id terug."""
    if bag_pand_id:
        # Zoek bestaand project op bag_pand_id
        existing = (
            supabase.table("pipeline_projects")
            .select("id")
            .eq("bag_pand_id", bag_pand_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            project_id = existing.data[0]["id"]
            supabase.table("pipeline_projects").update(row).eq("id", project_id).execute()
            return project_id

    result = supabase.table("pipeline_projects").insert(row).execute()
    return (result.data or [{}])[0].get("id")


def _load_existing_signals(supabase: Client, source: str) -> list[ParsedSignal]:
    """Laad recente signalen van deze bron terug als ParsedSignal voor clustervorming."""
    try:
        result = (
            supabase.table("pipeline_signals")
            .select("*")
            .eq("source", source)
            .limit(2000)
            .execute()
        )
        signals = []
        for row in result.data or []:
            from ..sources.pipeline.base import ParsedSignal
            from datetime import datetime, timezone
            try:
                signals.append(ParsedSignal(
                    source=row["source"],
                    source_id=row["source_id"],
                    signal_type=row["signal_type"],
                    signal_strength=row["signal_strength"],
                    signal_time=datetime.fromisoformat(row["signal_time"]),
                    title=row.get("title"),
                    description=row.get("description"),
                    address_text=row.get("address_text"),
                    postcode=row.get("postcode"),
                    gemeente=row.get("gemeente"),
                    bag_pand_id=row.get("bag_pand_id"),
                    geometry_ewkt=row.get("geometry"),
                    source_url=row.get("source_url"),
                    raw_payload=row.get("raw_payload", {}),
                    estimated_horizon_months_min=row.get("estimated_horizon_months_min", 12),
                    estimated_horizon_months_max=row.get("estimated_horizon_months_max", 36),
                ))
            except Exception:
                pass
        return signals
    except Exception as exc:
        log.warning("Kon bestaande signalen niet laden: %s", exc)
        return []


def _link_signals(supabase: Client, project_id: str, cluster: SignalCluster, inserted_ids: dict):
    rows = []
    for sig in cluster.signals:
        key = f"{sig.source}:{sig.source_id}"
        signal_db_id = inserted_ids.get(key)
        if signal_db_id:
            rows.append({"project_id": project_id, "signal_id": signal_db_id, "weight": 1.0})

    if rows:
        try:
            supabase.table("pipeline_project_signals").upsert(rows, ignore_duplicates=True).execute()
        except Exception as exc:
            log.debug("Link signalen mislukt: %s", exc)
