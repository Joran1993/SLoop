"""Unit tests voor scoring-functies."""
import pytest

from src.scoring.scores import (
    score_asbest_risico,
    score_omvang,
    score_circulair_potentieel,
    calculate_total_score,
    estimate_materiaalvolumes,
)


class TestAsbestRisico:
    def test_vooroorlogs_hoog(self):
        assert score_asbest_risico(1930) == 95

    def test_jaren_60_hoog(self):
        assert score_asbest_risico(1965) == 90

    def test_jaren_80_verhoogd(self):
        assert score_asbest_risico(1985) == 70

    def test_net_na_verbod_laag(self):
        assert score_asbest_risico(1994) == 25

    def test_modern_zeer_laag(self):
        assert score_asbest_risico(2010) == 5

    def test_onbekend_conservatief(self):
        assert score_asbest_risico(None) == 40

    def test_grenswaarde_1993(self):
        assert score_asbest_risico(1993) == 70  # net voor verbod

    def test_grenswaarde_2001(self):
        assert score_asbest_risico(2001) == 5


class TestOmvang:
    def test_klein_pand(self):
        score = score_omvang(50)
        assert 15 <= score <= 25

    def test_gemiddeld_pand(self):
        assert score_omvang(500) == 60  # ankerpunt

    def test_groot_pand(self):
        assert score_omvang(5000) == 90  # ankerpunt

    def test_enorm_pand(self):
        score = score_omvang(50_000)
        assert score == 100

    def test_onbekend_laag(self):
        assert score_omvang(None) == 20

    def test_nul_laag(self):
        assert score_omvang(0) == 20

    def test_boven_max_geen_overshoot(self):
        assert score_omvang(999_999) <= 100


class TestCirculairPotentieel:
    def test_oud_pand_slecht_label(self):
        score = score_circulair_potentieel(1930, "G")
        assert score >= 80

    def test_modern_pand_goed_label(self):
        score = score_circulair_potentieel(2020, "A+")
        assert score <= 15

    def test_onbekend_bouwjaar(self):
        score = score_circulair_potentieel(None, "D")
        assert 30 <= score <= 60

    def test_geen_energielabel(self):
        score = score_circulair_potentieel(1970, None)
        assert score > 0  # bouwjaar-component telt mee

    def test_maximum_niet_overschreden(self):
        assert score_circulair_potentieel(1900, "G") <= 100


class TestTotaalScore:
    def test_slooppriority_hoog(self):
        """Groot, oud, slecht label = hoge score."""
        result = calculate_total_score(
            bouwjaar=1960, oppervlakte_m2=3000, energielabel="G"
        )
        assert result.total >= 70

    def test_nieuwe_kleine_woning_laag(self):
        """Klein, nieuw, goed label = lage score."""
        result = calculate_total_score(
            bouwjaar=2020, oppervlakte_m2=80, energielabel="A+"
        )
        assert result.total <= 40

    def test_custom_weights(self):
        """Enterprise custom gewichten worden verwerkt."""
        result = calculate_total_score(
            bouwjaar=1975, oppervlakte_m2=1000, energielabel="D",
            weights={"asbest_risico": 0.5, "omvang": 0.3, "bereikbaarheid": 0.1, "circulair": 0.1}
        )
        assert 0 <= result.total <= 100
        assert result.weights_used["asbest_risico"] == 0.5

    def test_score_binnen_bereik(self):
        for bouwjaar in [1920, 1960, 1985, 2000, 2015]:
            for opp in [50, 500, 5000]:
                for label in ["A", "D", "G", None]:
                    result = calculate_total_score(bouwjaar, opp, label)
                    assert 0 <= result.total <= 100, (
                        f"Score {result.total} buiten bereik voor "
                        f"bouwjaar={bouwjaar}, opp={opp}, label={label}"
                    )


class TestMateriaaalVolumes:
    def test_woonfunctie_beton(self):
        volumes = estimate_materiaalvolumes(["woonfunctie"], 100)
        assert volumes["beton_kg"] == 150_000

    def test_industriefunctie_metaal(self):
        volumes = estimate_materiaalvolumes(["industriefunctie"], 1000)
        assert volumes["metaal_kg"] == 80_000

    def test_geen_oppervlakte(self):
        assert estimate_materiaalvolumes(["woonfunctie"], None) == {}

    def test_onbekend_gebruiksdoel(self):
        volumes = estimate_materiaalvolumes(["onbekendfunctie"], 200)
        assert "beton_kg" in volumes  # default wordt gebruikt

    def test_geen_gebruiksdoel(self):
        volumes = estimate_materiaalvolumes([], 500)
        assert "beton_kg" in volumes
