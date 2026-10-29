"""tools/listener_config.py - Listener configuration shared by Mode Studio and the choreography probe."""
from typing import Any, Dict

PRODUCTION_VISUAL_FFT_BANDS: int = 8   # AudioIngestion default; modes consume this many bands in production


def build_listener_infos(nb_fft_bands: int = PRODUCTION_VISUAL_FFT_BANDS) -> Dict[str, Any]:
    """Listener infos matching the production visual band count. No 'nb_multiband' key: ingestion defaults it to 32."""
    return {
        "useMicrophone": True,
        "fakeDelay": 5.0,
        "luminosity": 100,
        "sensibility": 100,
        "nb_of_fft_band": int(nb_fft_bands),
        "nb_of_chroma": 12,
        "sample_rate": 44100,
        "buffer_size": 4096,
    }
