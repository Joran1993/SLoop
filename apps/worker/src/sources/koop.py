#!/usr/bin/env python3
"""
sru_pull.py — Haalt sloop- en asbest-gerelateerde bekendmakingen op via de
KOOP SRU 2.0 API (https://repository.overheid.nl/sru).

De API geeft publicaties terug in het GZD-schema (Gemeenschappelijke Zoek
Dienst). Gefilterd op Gemeenteblad, want daar verschijnen sloopmelding-
beschikkingen van gemeenten.

Gebruik:
    python sru_pull.py --days 7 --out results.json
    python sru_pull.py --days 30 --out results.json --max-records 50

Documentatie:
    Dataset:     https://data.overheid.nl/dataset/officiele-bekendmakingen
    SRU 2.0:     https://www.loc.gov/standards/sru/sru-2-0.html
    GZD-schema:  http://standaarden.overheid.nl/sru/gzd.xsd
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta

import requests
from lxml import etree


SRU_ENDPOINT = "https://repository.overheid.nl/sru"

KEYWORDS = [
    "sloopmelding",
    "sloopactiviteit",
    "asbest",
    "kennisgeving sloop",
    "omgevingsvergunning sloop",
]

# Heuristiek voor adres-detectie.
# Dutch street types appear as standalone words ("Kerkweg") OR as suffixes in compounds
# ("Eikenlaan", "Dorpsstraat"). Use only trailing \b so "laan" matches in "Eikenlaan".
_RE_POSTCODE = re.compile(r"\b\d{4}\s?[A-Z]{2}\b")
_RE_STRAAT   = re.compile(
    r"(?i)(straat|laan|weg|plein|kade|singel|gracht|dijk|ring|hof|dreef|steeg|pad)\b"
)


# ── CQL-query ─────────────────────────────────────────────────────────────────

def build_query(since_date: str) -> str:
    """Bouw CQL-query: Gemeenteblad + datumfilter + trefwoorden (OR)."""
    kw_parts = " OR ".join(f'cql.textAndIndexes="{kw}"' for kw in KEYWORDS)
    return (
        f"w.publicatienaam=Gemeenteblad"
        f" AND dt.modified>={since_date}"
        f" AND ({kw_parts})"
    )


# ── HTTP + exponential backoff ────────────────────────────────────────────────

def fetch_page(
    query: str,
    start: int,
    max_records: int,
    session: requests.Session,
) -> bytes:
    params = {
        "operation":      "searchRetrieve",
        "version":        "2.0",
        "query":          query,
        "startRecord":    start,
        "maximumRecords": max_records,
        "recordSchema":   "gzd",
    }

    for attempt in range(6):
        try:
            resp = session.get(SRU_ENDPOINT, params=params, timeout=30)
        except requests.RequestException as exc:
            _backoff(attempt, f"verbindingsfout: {exc}")
            continue

        if resp.status_code == 429:
            _backoff(attempt, "rate-limit (429)")
            continue

        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            _backoff(attempt, str(exc))
            continue

        return resp.content

    raise RuntimeError("Maximaal aantal pogingen bereikt voor SRU-aanvraag")


def _backoff(attempt: int, reason: str) -> None:
    wait = 2 ** attempt
    print(f"  [{reason}] — opnieuw proberen over {wait}s...", file=sys.stderr)
    time.sleep(wait)


# ── XML-parsing (GZD-schema) ──────────────────────────────────────────────────

def _local(el: etree._Element) -> str:
    return etree.QName(el.tag).localname


def _text(el: etree._Element | None) -> str | None:
    if el is None or not el.text:
        return None
    return el.text.strip() or None


def _find_local(root: etree._Element, *names: str) -> etree._Element | None:
    """Eerste element met een van de opgegeven lokale namen, namespace-agnostisch."""
    target = set(names)
    for el in root.iter():
        if _local(el) in target:
            return el
    return None


def _findall_local(root: etree._Element, name: str) -> list[etree._Element]:
    return [el for el in root.iter() if _local(el) == name]


def parse_response(xml_bytes: bytes) -> tuple[int, int | None, list[dict]]:
    """
    Geeft terug: (total_hits, next_record_position_or_None, records).
    next_record_position is None als er geen volgende pagina is.
    """
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        print(f"  XML-parseerfout: {exc}", file=sys.stderr)
        return 0, None, []

    # SRU-diagnostics (serverfoutmeldingen)
    for diag in _findall_local(root, "diagnostic"):
        msg  = _text(_find_local(diag, "message")) or "onbekend"
        dets = _text(_find_local(diag, "details")) or ""
        print(f"  SRU-melding: {msg} {dets}".strip(), file=sys.stderr)

    total_el = _find_local(root, "numberOfRecords")
    total = int(_text(total_el) or "0")

    next_el  = _find_local(root, "nextRecordPosition")
    next_pos = int(_text(next_el)) if next_el is not None and _text(next_el) else None

    records = []
    for rec_el in _findall_local(root, "record"):
        data_el = _find_local(rec_el, "recordData")
        if data_el is None:
            continue
        records.append(_extract_fields(data_el))

    return total, next_pos, records


def _extract_fields(data_el: etree._Element) -> dict:
    """
    Extraheer velden uit een gzd:gzd-recordData-element.

    GZD-structuur:
      gzd:originalData / overheidwetgeving:meta / owmskern  → identifier, title, type, creator, modified
      gzd:originalData / overheidwetgeving:meta / tpmeta    → publicatienaam
      gzd:enrichedData                                       → preferredUrl, url
    """
    # Identifier (bv. "gmb-2026-209810")
    identifier_raw = _text(_find_local(data_el, "identifier"))

    # Preferred URL (HTML-weergave op officielebekendmakingen.nl)
    preferred_url = _text(_find_local(data_el, "preferredUrl"))
    identifier = preferred_url or identifier_raw

    title       = _text(_find_local(data_el, "title"))
    creator     = _text(_find_local(data_el, "creator"))
    pub_type    = _text(_find_local(data_el, "type"))
    pub_name    = _text(_find_local(data_el, "publicatienaam"))

    # Datum: prefereer dcterms:modified, val terug op dc:date
    date: str | None = None
    for el in data_el.iter():
        ln = _local(el)
        if ln == "modified" and el.text:
            date = el.text.strip()
            break
        if ln == "date" and date is None and el.text:
            date = el.text.strip()

    # Volledige tekst voor snippet en keyword-matching
    full_text = etree.tostring(data_el, encoding="unicode", method="text")
    full_text = re.sub(r"\s+", " ", full_text).strip()

    # Gebruik de titel als primaire snippet (bevat vaak het adres)
    snippet = title or (full_text[:600] if full_text else None)

    search_corpus = f"{title or ''} {full_text or ''}"
    matched  = _find_keywords(search_corpus)
    has_addr = _detect_address(search_corpus)

    return {
        "identifier":       identifier,
        "document_id":      identifier_raw,
        "titel":            title,
        "publicatiedatum":  date,
        "gemeente":         creator,
        "publicatietype":   pub_type,
        "publicatienaam":   pub_name,
        "snippet":          snippet[:800] if snippet else None,
        "matched_keywords": sorted(matched),
        "has_address_hint": has_addr,
    }


def _find_keywords(text: str) -> set[str]:
    text_lower = text.lower()
    return {kw for kw in KEYWORDS if kw in text_lower}


def _detect_address(text: str) -> bool:
    if not text:
        return False
    return bool(_RE_POSTCODE.search(text) or _RE_STRAAT.search(text))


# ── Samenvatting ───────────────────────────────────────────────────────────────

def build_summary(records: list[dict], since_date: str, end_date: str) -> dict:
    gemeente_counts = Counter(r["gemeente"] for r in records if r["gemeente"])
    keyword_counts  = Counter()
    for r in records:
        for kw in r["matched_keywords"]:
            keyword_counts[kw] += 1

    no_address = [r for r in records if not r["has_address_hint"]]
    duplicates = _find_duplicate_titles(records)

    observations: list[str] = []
    if no_address:
        pct = len(no_address) / len(records) * 100 if records else 0
        observations.append(
            f"{len(no_address)} publicaties ({pct:.0f}%) zonder detecteerbare adresinformatie"
        )
    if duplicates:
        observations.append(
            f"{len(duplicates)} dubbele titels (mogelijke herplaatsingen of meerdere beschikkingen)"
        )
    eenmalig = [g for g, c in gemeente_counts.items() if c == 1]
    if eenmalig:
        observations.append(
            f"{len(eenmalig)} gemeenten met slechts 1 publicatie in de periode"
        )

    return {
        "totaal_publicaties":       len(records),
        "datumbereik":              {"van": since_date, "tot": end_date},
        "top_20_gemeenten":         dict(gemeente_counts.most_common(20)),
        "per_trefwoord":            dict(keyword_counts.most_common()),
        "publicaties_zonder_adres": len(no_address),
        "mogelijke_duplicaten":     duplicates[:20],
        "opvallende_observaties":   observations,
    }


def _find_duplicate_titles(records: list[dict]) -> list[str]:
    counts = Counter(r["titel"] for r in records if r["titel"])
    return [t for t, c in counts.items() if c > 1]


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Haalt sloop/asbest bekendmakingen op via KOOP SRU API",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--days",        type=int, default=7,            help="Terugkijkperiode in dagen")
    parser.add_argument("--out",         default="results.json",         help="Output JSON-bestand")
    parser.add_argument("--max-records", type=int, default=100,          help="Records per pagina (max 100)")
    args = parser.parse_args()

    end_dt    = datetime.now()
    start_dt  = end_dt - timedelta(days=args.days)
    since_str = start_dt.strftime("%Y-%m-%d")
    end_str   = end_dt.strftime("%Y-%m-%d")

    print(f"Zoekperiode : {since_str} t/m {end_str}  ({args.days} dagen)")
    print(f"Trefwoorden : {', '.join(KEYWORDS)}")
    print("Filter      : Gemeenteblad")
    print(f"Endpoint    : {SRU_ENDPOINT}")
    print()

    query   = build_query(since_str)
    session = requests.Session()
    session.headers["User-Agent"] = "SloopradarSRU/1.0 (research)"

    all_records: list[dict] = []
    start_record = 1
    total_hits   = None
    page         = 1

    while True:
        end_of_page = start_record + args.max_records - 1
        print(f"Pagina {page:>3}: records {start_record}–{end_of_page} ophalen...", end=" ", flush=True)

        try:
            xml_bytes = fetch_page(query, start_record, args.max_records, session)
        except Exception as exc:
            print(f"\nFATAL: {exc}", file=sys.stderr)
            break

        hits, next_pos, records = parse_response(xml_bytes)

        if total_hits is None:
            total_hits = hits
            print(f"(totaal gevonden: {total_hits})", end=" ")

        print(f"→ {len(records)} records ontvangen")

        if not records:
            break

        all_records.extend(records)

        # Gebruik nextRecordPosition van de API zelf
        if next_pos is None or (total_hits and next_pos > total_hits):
            break

        start_record = next_pos
        page        += 1
        time.sleep(0.3)  # beleefd rate-limiting

    print(f"\nTotaal verwerkt : {len(all_records)} publicaties")

    summary = build_summary(all_records, since_str, end_str)

    output = {
        "samenvatting": summary,
        "publicaties":  all_records,
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2, default=str)

    print(f"Output           : {args.out}")
    print()

    if summary["top_20_gemeenten"]:
        print("Top 5 gemeenten:")
        for gemeente, count in list(summary["top_20_gemeenten"].items())[:5]:
            print(f"  {gemeente:<40} {count}")

    if summary["per_trefwoord"]:
        print("\nPer trefwoord:")
        for kw, count in summary["per_trefwoord"].items():
            print(f"  {kw:<40} {count}")

    if summary["opvallende_observaties"]:
        print("\nObservaties:")
        for obs in summary["opvallende_observaties"]:
            print(f"  • {obs}")


if __name__ == "__main__":
    main()
