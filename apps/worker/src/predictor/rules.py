"""Predictor v1 — regelgebaseerd model voor sloopkans.

Leest gewichten uit config/predictor_rules.yaml.
Geeft sloop_kans (0.0–1.0) en horizon (min/max maanden) terug.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import yaml

from ..sources.pipeline.base import ParsedSignal

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "predictor_rules.yaml"
_MODEL_VERSION = "rules-v1"


@dataclass
class Prediction:
    sloop_kans: float           # 0.0–1.0
    horizon_months_min: int
    horizon_months_max: int
    explanation: dict
    model_version: str = _MODEL_VERSION


def load_config() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def predict(signals: Sequence[ParsedSignal]) -> Prediction:
    """Bereken sloopkans voor een groep signalen die bij hetzelfde pand/cluster horen."""
    cfg = load_config()

    signal_weights = cfg["signal_weights"]
    strength_mult = cfg["signal_strength_multiplier"]
    diversity_bonus_map = {int(k): v for k, v in cfg["diversity_bonus"].items()}
    bouwjaar_cfg = cfg["bouwjaar_score"]
    horizon_cfg = cfg["horizon"]
    thresholds = cfg["thresholds"]

    if not signals:
        return Prediction(
            sloop_kans=0.0,
            horizon_months_min=0,
            horizon_months_max=0,
            explanation={"reason": "geen signalen"},
        )

    # Gewogen som van signaalbijdragen
    raw_score = 0.0
    signal_contributions = []
    seen_types: set[str] = set()

    for sig in signals:
        base_weight = signal_weights.get(sig.signal_type, 0.3)
        mult = strength_mult.get(sig.signal_strength, 0.75)
        contrib = base_weight * mult
        raw_score += contrib
        seen_types.add(sig.signal_type)
        signal_contributions.append({
            "type": sig.signal_type,
            "strength": sig.signal_strength,
            "weight": base_weight,
            "contrib": round(contrib, 3),
        })

    # Diversiteitsbonus
    n_types = len(seen_types)
    bonus_keys = sorted(k for k in diversity_bonus_map if k <= n_types)
    diversity_bonus = diversity_bonus_map[bonus_keys[-1]] if bonus_keys else 0.0

    # Bouwjaarbonus (gebruik eerste signaal met bouwjaar-context)
    bouwjaar_bonus = 0.0

    # Squash naar 0–1 via tanh
    kans = math.tanh(raw_score * 0.6) + diversity_bonus
    kans = max(0.0, min(1.0, kans))

    # Horizon: neem de kortste horizon van alle signalen (meest urgent)
    horizon_mins = []
    horizon_maxs = []
    for sig in signals:
        h = horizon_cfg.get(sig.signal_type)
        if h:
            horizon_mins.append(h["min"])
            horizon_maxs.append(h["max"])
        else:
            horizon_mins.append(sig.estimated_horizon_months_min)
            horizon_maxs.append(sig.estimated_horizon_months_max)

    h_min = min(horizon_mins) if horizon_mins else 12
    h_max = max(horizon_maxs) if horizon_maxs else 36

    return Prediction(
        sloop_kans=round(kans, 4),
        horizon_months_min=h_min,
        horizon_months_max=h_max,
        explanation={
            "raw_score": round(raw_score, 3),
            "diversity_bonus": diversity_bonus,
            "signal_count": len(signals),
            "unique_types": n_types,
            "contributions": signal_contributions,
        },
    )
