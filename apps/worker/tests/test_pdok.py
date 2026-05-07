"""Unit tests voor PDOK Locatieserver parsing-functies."""
import pytest

from src.sources.pdok import _parse_centroide, _parse_doc


class TestParseCentroide:
    def test_valide_point(self):
        x, y = _parse_centroide("POINT(122000 487000)")
        assert x == 122000.0
        assert y == 487000.0

    def test_none_input(self):
        x, y = _parse_centroide(None)
        assert x is None
        assert y is None

    def test_leeg_string(self):
        x, y = _parse_centroide("")
        assert x is None
        assert y is None

    def test_invalide_format(self):
        x, y = _parse_centroide("niet-valide")
        assert x is None
        assert y is None


class TestParseDoc:
    def test_volledige_doc(self):
        doc = {
            "pand_id": "0344100000065895",
            "weergavenaam": "Eikenlaan 7, 9471AA Zuidlaren",
            "postcode": "9471AA",
            "gemeentenaam": "Tynaarlo",
            "provincienaam": "Drenthe",
            "centroide_rd": "POINT(238456 559123)",
            "centroide_ll": "POINT(6.7 53.0)",
            "score": 12.5,
        }
        result = _parse_doc(doc)
        assert result.pand_id == "0344100000065895"
        assert result.postcode == "9471AA"
        assert result.gemeente == "Tynaarlo"
        assert result.provincie == "Drenthe"
        assert result.rd_x == 238456.0
        assert result.rd_y == 559123.0

    def test_minimale_doc(self):
        """Lege doc crasht niet."""
        result = _parse_doc({})
        assert result.pand_id is None
        assert result.rd_x is None
