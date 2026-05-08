"""Signaalclusterer — groepeert ParsedSignals per pand of geo-cluster.

Strategie:
1. Als signalen een bag_pand_id hebben → groepeer op pand_id.
2. Signalen zonder pand_id → groepeer op ruimtelijke nabijheid (≤ clustering_radius_m).
3. Signalen zonder geometrie en zonder pand_id → elk op zichzelf.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import yaml

from ..sources.pipeline.base import ParsedSignal

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "predictor_rules.yaml"


@dataclass
class SignalCluster:
    cluster_id: str                          # bag_pand_id of "geo:<lat>:<lon>"
    bag_pand_id: str | None
    geometry_ewkt: str | None                # representatief punt
    gemeente: str | None
    postcode: str | None
    address_text: str | None
    signals: list[ParsedSignal] = field(default_factory=list)

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def signal_diversity(self) -> int:
        return len({s.signal_type for s in self.signals})


def cluster_signals(signals: Sequence[ParsedSignal]) -> list[SignalCluster]:
    """Groepeert signalen in clusters op basis van pand_id of locatie."""
    cfg = _load_config()
    radius_m = cfg.get("thresholds", {}).get("clustering_radius_m", 200)

    clusters: dict[str, SignalCluster] = {}

    # Stap 1: groepeer op pand_id
    with_pand = [s for s in signals if s.bag_pand_id]
    without_pand = [s for s in signals if not s.bag_pand_id]

    for sig in with_pand:
        cid = f"pand:{sig.bag_pand_id}"
        if cid not in clusters:
            clusters[cid] = SignalCluster(
                cluster_id=cid,
                bag_pand_id=sig.bag_pand_id,
                geometry_ewkt=sig.geometry_ewkt,
                gemeente=sig.gemeente,
                postcode=sig.postcode,
                address_text=sig.address_text,
            )
        clusters[cid].signals.append(sig)

    # Stap 2: geo-clustering voor signalen zonder pand_id
    with_geom = [s for s in without_pand if s.geometry_ewkt]
    without_geom = [s for s in without_pand if not s.geometry_ewkt]

    geo_clusters: list[SignalCluster] = []
    for sig in with_geom:
        pt = _parse_ewkt_point(sig.geometry_ewkt)
        if pt is None:
            without_geom.append(sig)
            continue

        merged = False
        for gc in geo_clusters:
            rep = _parse_ewkt_point(gc.geometry_ewkt)
            if rep and _distance_m(pt, rep) <= radius_m:
                gc.signals.append(sig)
                merged = True
                break

        if not merged:
            cid = f"geo:{pt[0]:.1f}:{pt[1]:.1f}"
            gc = SignalCluster(
                cluster_id=cid,
                bag_pand_id=None,
                geometry_ewkt=sig.geometry_ewkt,
                gemeente=sig.gemeente,
                postcode=sig.postcode,
                address_text=sig.address_text,
            )
            gc.signals.append(sig)
            geo_clusters.append(gc)

    for gc in geo_clusters:
        clusters[gc.cluster_id] = gc

    # Stap 3: signalen zonder geometrie en zonder pand → eigen cluster
    for i, sig in enumerate(without_geom):
        cid = f"solo:{sig.source_id}"
        clusters[cid] = SignalCluster(
            cluster_id=cid,
            bag_pand_id=None,
            geometry_ewkt=None,
            gemeente=sig.gemeente,
            postcode=sig.postcode,
            address_text=sig.address_text,
            signals=[sig],
        )

    return list(clusters.values())


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


def _parse_ewkt_point(ewkt) -> tuple[float, float] | None:
    """Parseer EWKT string of GeoJSON dict → (x, y). Geeft None bij fout."""
    if not ewkt:
        return None
    try:
        # PostgREST geeft geometrie soms terug als GeoJSON dict
        if isinstance(ewkt, dict):
            coords = ewkt.get("coordinates", [])
            return float(coords[0]), float(coords[1])
        point_part = ewkt.split(";", 1)[-1].strip()
        coords = point_part.replace("POINT(", "").replace(")", "").split()
        return float(coords[0]), float(coords[1])
    except (IndexError, ValueError, TypeError):
        return None


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Euclidische afstand in meters (RD New is in meters)."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
