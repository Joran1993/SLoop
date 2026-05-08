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

# Totaalgewicht per gebruiksdoel (kg/m²) — alle materialen samen
# Basis: constructiebeton + metselwerk + hout + metaal + glas
# Bouwjaar-correctie wordt apart toegepast
_GEWICHT_PER_M2: dict[str, float] = {
    "woonfunctie":            1400,  # mix baksteen/beton afhankelijk van periode
    "kantoorfunctie":         1700,  # zwaarder skelet, meer glas
    "industriefunctie":       900,   # lichtere constructie, staalskelet, grote overspanning
    "winkelfunctie":          1500,
    "gezondheidszorgfunctie": 1700,
    "onderwijsfunctie":       1400,
    "_default":               1300,
}

# Metaalgehalte (% van totaalgewicht) per gebruiksdoel
# Metaal is de enige significante residustroom met positieve waarde
_METAAL_PCT: dict[str, float] = {
    "industriefunctie":  0.08,   # staalskelet, dakbeplating
    "kantoorfunctie":    0.04,
    "woonfunctie":       0.015,  # wapeningsstaal in beton ~1.5%
    "_default":          0.03,
}

# Sloopkosten bandbreedte (€/m²) exclusief asbestsanering
_SLOOPKOSTEN_M2: dict[str, tuple[int, int]] = {
    "industriefunctie":       (12, 22),  # relatief eenvoudig, grote volumes
    "kantoorfunctie":         (22, 38),
    "woonfunctie":            (28, 45),
    "winkelfunctie":          (20, 35),
    "gezondheidszorgfunctie": (30, 50),
    "onderwijsfunctie":       (25, 42),
    "_default":               (20, 40),
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


# Bereikbaarheid per provincie: agrarisch/industrieel = hoog, urban = lager.
# Bron: mix van bevolkingsdichtheid en industriële activiteit per provincie.
_BEREIKBAARHEID_PER_PROVINCIE: dict[str, int] = {
    "Drenthe": 80,
    "Flevoland": 72,
    "Friesland": 78,
    "Gelderland": 65,
    "Groningen": 75,
    "Limburg": 62,
    "Noord-Brabant": 60,
    "Noord-Holland": 45,
    "Overijssel": 68,
    "Utrecht": 48,
    "Zeeland": 80,
    "Zuid-Holland": 42,
}


def score_bereikbaarheid(provincie: str | None = None, gemeente: str | None = None) -> int:
    """
    Bereikbaarheid gebaseerd op provincie (bevolkingsdichtheid/industrieligging).
    Hoge score = goed bereikbaar voor vrachtverkeer (agrarisch/industrieel).
    Lage score = moeilijk bereikbaar (dichte stedelijke omgeving).
    """
    if provincie and provincie in _BEREIKBAARHEID_PER_PROVINCIE:
        return _BEREIKBAARHEID_PER_PROVINCIE[provincie]
    return 55  # Onbekend: neutraal


def calculate_total_score(
    bouwjaar: int | None,
    oppervlakte_m2: int | None,
    energielabel: str | None,
    weights: dict[str, float] | None = None,
    provincie: str | None = None,
    gemeente: str | None = None,
) -> ScoreBreakdown:
    """Bereken totaalscore met optionele custom gewichten (Enterprise)."""
    w = weights if weights else _DEFAULT_WEIGHTS

    asbest = score_asbest_risico(bouwjaar)
    omvang = score_omvang(oppervlakte_m2)
    bereikbaarheid = score_bereikbaarheid(provincie, gemeente)
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


_METAALPRIJS_EUR_PER_KG = 0.18  # Gemengd schroot — conservatieve marktprijs

# Asbest fractie van vloeroppervlak per bouwperiode en gebruiksdoel
# Industriefunctie: dakplaten, wand-elementen → hogere fractie
def _asbest_fractie(bouwjaar: int, gebruiksdoelen: list[str]) -> float:
    is_industrie = any("industrie" in d.lower() for d in gebruiksdoelen)
    if bouwjaar < 1945:
        return 0.08 if is_industrie else 0.05
    if bouwjaar < 1976:
        return 0.35 if is_industrie else 0.22
    if bouwjaar < 1993:
        return 0.12 if is_industrie else 0.08
    return 0.0


def _resolve_gebruiksdoel(gebruiksdoelen: list[str], lookup: dict) -> object:
    for doel in gebruiksdoelen:
        doel_lower = doel.lower().replace(" ", "")
        for key in lookup:
            if key != "_default" and key in doel_lower:
                return lookup[key]
    return lookup["_default"]


def estimate_sloopindicatoren(
    gebruiksdoelen: list[str] | None,
    oppervlakte_m2: int | None,
    bouwjaar: int | None,
) -> dict:
    """
    Vier bruikbare indicatoren voor een sloopbedrijf:
      totaal_ton       — totale sloopafvalmassa (maatgevend voor planning/transport)
      residuwaarde_eur — schatting metaalwaarde (opbrengst)
      asbest_m2        — asbestverdacht oppervlak (saneringskosten)
      sloopkosten_min/max — indicatieve sloopkosten excl. asbestsanering
    """
    if not oppervlakte_m2 or oppervlakte_m2 <= 0:
        return {}

    doelen = gebruiksdoelen or []

    kg_per_m2 = _resolve_gebruiksdoel(doelen, _GEWICHT_PER_M2)
    totaal_kg = kg_per_m2 * oppervlakte_m2
    totaal_ton = round(totaal_kg / 1000, 1)

    metaal_pct = _resolve_gebruiksdoel(doelen, _METAAL_PCT)
    metaal_kg = totaal_kg * metaal_pct
    residuwaarde_eur = int(round(metaal_kg * _METAALPRIJS_EUR_PER_KG / 100) * 100)

    if bouwjaar is None:
        asbest_m2 = None
    elif bouwjaar >= 1993:
        asbest_m2 = 0
    else:
        fractie = _asbest_fractie(bouwjaar, doelen)
        asbest_m2 = int(round(oppervlakte_m2 * fractie))

    kosten_low, kosten_high = _resolve_gebruiksdoel(doelen, _SLOOPKOSTEN_M2)
    sloopkosten_min = int(round(kosten_low * oppervlakte_m2 / 1000) * 1000)
    sloopkosten_max = int(round(kosten_high * oppervlakte_m2 / 1000) * 1000)

    result: dict = {
        "totaal_ton": totaal_ton,
        "residuwaarde_eur": residuwaarde_eur,
        "sloopkosten_min": sloopkosten_min,
        "sloopkosten_max": sloopkosten_max,
    }
    if asbest_m2 is not None:
        result["asbest_m2"] = asbest_m2
    return result
