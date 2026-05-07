"""Scoring-functies voor sloop-leads.

Elke functie retourneert een int 0-100.
Default scoring-gewichten (overschrijfbaar per Enterprise org):
  asbest_risico × 0.25 + omvang × 0.35 + bereikbaarheid × 0.15 + circulair × 0.25
"""
from __future__ import annotations

import math
from dataclasses import dataclass

_DEFAULT_WEIGHTS = {
    "asbest_risico": 0.25,
    "omvang": 0.35,
    "bereikbaarheid": 0.15,
    "circulair": 0.25,
}

# Materiaal-kentallen per gebruiksdoel (kg/m²)
_MATERIAAL_KENTALLEN: dict[str, dict[str, float]] = {
    "woonfunctie":       {"beton_kg": 1500, "hout_kg": 150, "glas_kg": 25, "metaal_kg": 20},
    "kantoorfunctie":    {"beton_kg": 1800, "hout_kg": 80,  "glas_kg": 50, "metaal_kg": 40},
    "industriefunctie":  {"beton_kg": 1200, "hout_kg": 200, "glas_kg": 15, "metaal_kg": 80},
    "winkelfunctie":     {"beton_kg": 1600, "hout_kg": 100, "glas_kg": 60, "metaal_kg": 30},
    "gezondheidsfunctie":{"beton_kg": 1700, "hout_kg": 90,  "glas_kg": 40, "metaal_kg": 35},
    "onderwijsfunctie":  {"beton_kg": 1400, "hout_kg": 120, "glas_kg": 35, "metaal_kg": 25},
    # Default voor onbekende/overige functies
    "_default":          {"beton_kg": 1400, "hout_kg": 120, "glas_kg": 30, "metaal_kg": 30},
}


@dataclass
class ScoreBreakdown:
    asbest_risico: int
    omvang: int
    bereikbaarheid: int
    circulair: int
    total: int
    weights_used: dict[str, float]


def score_asbest_risico(bouwjaar: int | None) -> int:
    """
    Asbestrisico gebaseerd op bouwjaar.
    Asbest verwerking verboden per 1 juli 1993 in NL.
    """
    if bouwjaar is None:
        return 40  # Onbekend: conservatief gemiddeld
    if bouwjaar < 1945:
        return 95  # Vooroorlogse panden: bijna zeker asbest
    if bouwjaar < 1980:
        return 90
    if bouwjaar < 1994:
        return 70  # Mogelijk asbest tot en met 1993
    if bouwjaar < 2001:
        return 25  # Transitieperiode — incidenteel
    return 5



# Ankerpunten per spec (oppervlakte m², score)
_OMVANG_ANCHORS = [(50, 20), (500, 60), (5000, 90), (50_000, 100)]


def score_omvang(oppervlakte_m2: int | None) -> int:
    """
    Stuksgewijze log-interpolatie over ankerpunten:
    50m² → 20, 500m² → 60, 5000m² → 90, 50000m² → 100
    """
    if not oppervlakte_m2 or oppervlakte_m2 <= 0:
        return 20

    if oppervlakte_m2 <= _OMVANG_ANCHORS[0][0]:
        return _OMVANG_ANCHORS[0][1]
    if oppervlakte_m2 >= _OMVANG_ANCHORS[-1][0]:
        return _OMVANG_ANCHORS[-1][1]

    log_val = math.log(oppervlakte_m2)
    for (a_m2, a_score), (b_m2, b_score) in zip(_OMVANG_ANCHORS, _OMVANG_ANCHORS[1:]):
        if a_m2 <= oppervlakte_m2 <= b_m2:
            t = (log_val - math.log(a_m2)) / (math.log(b_m2) - math.log(a_m2))
            return int(round(a_score + t * (b_score - a_score)))

    return 100


def score_circulair_potentieel(
    bouwjaar: int | None,
    energielabel: str | None,
) -> int:
    """
    Circulair potentieel: combinatie van bouwjaar (ouder = meer herbruikbaar)
    en energielabel (slechter label = meer materiaal te vervangen).
    """
    # Bouwjaar-component (0-60)
    if bouwjaar is None:
        bouwjaar_score = 30
    elif bouwjaar < 1940:
        bouwjaar_score = 60  # Oudste panden: hout, steen, herstelbare materialen
    elif bouwjaar < 1960:
        bouwjaar_score = 55
    elif bouwjaar < 1980:
        bouwjaar_score = 45
    elif bouwjaar < 2000:
        bouwjaar_score = 30
    elif bouwjaar < 2015:
        bouwjaar_score = 15
    else:
        bouwjaar_score = 5

    # Energielabel-component (0-40)
    label_scores = {
        "G": 40, "F": 35, "E": 30, "D": 22,
        "C": 15, "B": 8, "A": 3, "A+": 1, "A++": 0,
    }
    label_score = label_scores.get((energielabel or "").upper(), 20)

    return int(min(bouwjaar_score + label_score, 100))


def score_bereikbaarheid() -> int:
    """Placeholder v1: vaste waarde 50. Vervangen door PostGIS-afstand in v2."""
    return 50


def calculate_total_score(
    bouwjaar: int | None,
    oppervlakte_m2: int | None,
    energielabel: str | None,
    weights: dict[str, float] | None = None,
) -> ScoreBreakdown:
    """Bereken totaalscore met optionele custom gewichten (Enterprise)."""
    w = weights if weights else _DEFAULT_WEIGHTS

    asbest = score_asbest_risico(bouwjaar)
    omvang = score_omvang(oppervlakte_m2)
    bereikbaarheid = score_bereikbaarheid()
    circulair = score_circulair_potentieel(bouwjaar, energielabel)

    total = (
        asbest * w.get("asbest_risico", 0.25)
        + omvang * w.get("omvang", 0.35)
        + bereikbaarheid * w.get("bereikbaarheid", 0.15)
        + circulair * w.get("circulair", 0.25)
    )

    return ScoreBreakdown(
        asbest_risico=asbest,
        omvang=omvang,
        bereikbaarheid=bereikbaarheid,
        circulair=circulair,
        total=int(round(total)),
        weights_used=w,
    )


def estimate_materiaalvolumes(
    gebruiksdoelen: list[str] | None,
    oppervlakte_m2: int | None,
) -> dict[str, float]:
    """Ruwe materiaalvolume-inschatting op basis van gebruiksdoel × m²."""
    if not oppervlakte_m2 or oppervlakte_m2 <= 0:
        return {}

    # Kies de dominante gebruiksfunctie (eerste match in kentallen-tabel)
    kentallen = _MATERIAAL_KENTALLEN["_default"]
    for doel in (gebruiksdoelen or []):
        doel_lower = doel.lower().replace(" ", "")
        for key in _MATERIAAL_KENTALLEN:
            if key != "_default" and key in doel_lower:
                kentallen = _MATERIAAL_KENTALLEN[key]
                break

    return {
        material: round(kg_per_m2 * oppervlakte_m2)
        for material, kg_per_m2 in kentallen.items()
    }
