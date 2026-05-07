"""Integratietest voor de KOOP SRU XML-parser.

Gebruik fixture-XML (opgeslagen lokaal) om zonder netwerk te testen.
"""
import json
import pytest
from pathlib import Path

from src.sources.koop import parse_response, build_query


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


class TestBuildQuery:
    def test_bevat_gemeenteblad(self):
        q = build_query("2026-01-01")
        assert "Gemeenteblad" in q

    def test_bevat_datum(self):
        q = build_query("2026-05-01")
        assert "2026-05-01" in q

    def test_bevat_sloopmelding_keyword(self):
        q = build_query("2026-01-01")
        assert "sloopmelding" in q.lower()


class TestParseResponse:
    def test_lege_response(self):
        """Een lege maar valide XML-response retourneert 0 records."""
        empty_xml = b"""<?xml version="1.0"?>
        <searchRetrieveResponse xmlns="http://docs.oasis-open.org/ns/search-ws/sruResponse">
            <numberOfRecords>0</numberOfRecords>
        </searchRetrieveResponse>"""
        total, next_pos, records = parse_response(empty_xml)
        assert total == 0
        assert records == []

    def test_invalide_xml(self):
        """Invalide XML crasht niet maar retourneert lege lijst."""
        total, next_pos, records = parse_response(b"dit is geen xml")
        assert total == 0
        assert records == []

    @pytest.mark.skipif(
        not (FIXTURE_DIR / "sample_response.xml").exists(),
        reason="Fixture niet aanwezig — run eerst: python -m src.sources.koop --days 7 --out tests/fixtures/sample_response.xml"
    )
    def test_parse_fixture(self):
        """Parse een echte API-response fixture."""
        xml_bytes = _load_fixture("sample_response.xml")
        total, next_pos, records = parse_response(xml_bytes)

        assert total > 0
        assert len(records) > 0

        # Elk record heeft minimaal een identifier
        for rec in records:
            assert rec.get("identifier") or rec.get("document_id"), \
                f"Record zonder identifier: {rec}"

    @pytest.mark.skipif(
        not (FIXTURE_DIR / "sample_response.xml").exists(),
        reason="Fixture niet aanwezig"
    )
    def test_records_hebben_verwachte_velden(self):
        xml_bytes = _load_fixture("sample_response.xml")
        _, _, records = parse_response(xml_bytes)

        for rec in records[:10]:
            assert "identifier" in rec
            assert "matched_keywords" in rec
            assert isinstance(rec["matched_keywords"], list)
            assert "has_address_hint" in rec

    @pytest.mark.skipif(
        not (FIXTURE_DIR / "sample_response.xml").exists(),
        reason="Fixture niet aanwezig"
    )
    def test_adresdetectie_ratio(self):
        """Minimaal 70% van de records heeft adresinformatie (gebaseerd op rapport: 82%)."""
        xml_bytes = _load_fixture("sample_response.xml")
        _, _, records = parse_response(xml_bytes)

        if not records:
            pytest.skip("Geen records in fixture")

        with_address = sum(1 for r in records if r.get("has_address_hint"))
        ratio = with_address / len(records)
        assert ratio >= 0.70, f"Adresdetectie-ratio te laag: {ratio:.1%}"
