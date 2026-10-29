import pytest
from tools.listener_config import build_listener_infos
from music.Listener import Listener
from music.DyadicMetricalAudioAnalyzer import DyadicMetricalAudioAnalyzer


def test_infos_default_is_production_8_and_has_no_multiband_key():
    infos = build_listener_infos()
    assert infos["nb_of_fft_band"] == 8
    assert "nb_multiband" not in infos


@pytest.mark.parametrize("bands", [8, 16])
def test_listener_visual_bands_and_coarse_flux_path(bands):
    L = Listener(build_listener_infos(bands), analyzer_class=DyadicMetricalAudioAnalyzer)
    assert L.ingestion.nb_of_fft_band == bands
    assert len(L.band_flux) == bands                    # modes see `bands`-wide flux
    assert len(L.analyzer.band_flux) != bands           # analyzer keeps its 32-band filterbank (coarse-flux path is used)
