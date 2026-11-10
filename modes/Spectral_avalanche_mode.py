"""
modes/Spectral_avalanche_mode.py
Continuous top-to-bottom kinetic cascade driven by 16-band spectrum.
Lead: spectrum
Secondary: beat
"""

import math
from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from modes.Mode import Mode
from utils.global_mode import SegmentSpatialProfile


class Spectral_avalanche_mode(Mode):
    """
    Spectral Avalanche: High-energy frequency-to-gravity sound waterfall.
    Lead: spectrum (>= 70% algorithmic, >= 85% perceptual)
    Secondary: beat (<= 20%)
    """

    IS_GLOBAL: bool = True
    LEAD: str = "spectrum"
    SECONDARY: tuple = ("beat",)

    def __init__(
        self,
        name: str,
        segment_name: str,
        listener: Any,
        leds: Any,
        indexes: List[int],
        rgb_list: np.ndarray,
        infos: Dict[str, Any],
    ) -> None:
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.spatial = SegmentSpatialProfile(
            segment_name=segment_name,
            nb_of_leds=self.nb_of_leds,
            tags=infos.get("tags", ()),
            orientation=infos.get("orientation"),
        )

        self.gravity: float = float(infos.get("gravity", 1.0))
        self.flow_offset: float = 0.0
        self.prev_bands_16 = np.zeros(16, dtype=np.float64)
        self.prev_bands_8 = np.zeros(8, dtype=np.float64)
        self.prev_bands = self.prev_bands_16
        self._flux_scratch_16 = np.zeros(16, dtype=np.float64)
        self._flux_scratch_8 = np.zeros(8, dtype=np.float64)
        self._zero_bands_16 = np.zeros(16, dtype=np.float64)
        self._bands_buf_8 = np.zeros(8, dtype=np.float64)

        n = max(1, self.nb_of_leds)
        self._intensity = np.zeros(n, dtype=np.float64)
        self._intensity_col = self._intensity[:, np.newaxis]
        self._wave_scratch = np.zeros(n, dtype=np.float64)
        self._phase_scratch = np.zeros(n, dtype=np.float64)
        self._spec_profile = np.zeros(n, dtype=np.float64)
        self._target_rgb = np.zeros((n, 3), dtype=np.float64)
        self._base_rgb = np.zeros((n, 3), dtype=np.int32)

        self._z = self.spatial.altitude
        self._band_indices_16 = np.zeros(n, dtype=np.int32)
        self._band_indices_8 = np.zeros(n, dtype=np.int32)
        self._band_indices = self._band_indices_16
        self._lut_indices = np.zeros(n, dtype=np.int32)
        self._sync_altitude_indices()

    def _sync_altitude_indices(self) -> None:
        z = self.spatial.altitude
        self._z = z
        self._band_indices_16[:] = np.clip((z * 15.0).astype(np.int32), 0, 15)
        self._band_indices_8[:] = np.clip((z * 7.0).astype(np.int32), 0, 7)
        self._lut_indices[:] = np.clip((z * 255.0).astype(np.int32), 0, 255)

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind physical segment role, tags, and 2D coordinates from Segment."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._sync_altitude_indices()

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "gravity",
                "label": "Downward Flow Speed",
                "valueType": "number",
                "min": 0.5,
                "max": 2.5,
                "default": 1.0,
                "step": 0.1,
                "attr": "gravity",
            },
        ]

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)

        if ctx is not None and getattr(ctx, "is_silent", False):
            self.prev_bands_16.fill(0.0)
            self.prev_bands_8.fill(0.0)
            self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
            return

        bands = getattr(self.listener, "asserved_fft_band", None)
        nb = len(bands) if bands is not None else 0
        if nb == 0:
            bands_arr = self._zero_bands_16
            prev_b = self.prev_bands_16
            flux_scratch = self._flux_scratch_16
            band_indices = self._band_indices_16
        elif nb >= 16:
            bands_arr = bands if nb == 16 else bands[:16]
            prev_b = self.prev_bands_16
            flux_scratch = self._flux_scratch_16
            band_indices = self._band_indices_16
        elif nb >= 8:
            bands_arr = bands if nb == 8 else bands[:8]
            prev_b = self.prev_bands_8
            flux_scratch = self._flux_scratch_8
            band_indices = self._band_indices_8
        else:
            self._bands_buf_8[:nb] = bands
            self._bands_buf_8[nb:] = bands[nb - 1]
            bands_arr = self._bands_buf_8
            prev_b = self.prev_bands_8
            flux_scratch = self._flux_scratch_8
            band_indices = self._band_indices_8

        # Dynamic spectral flux drives the waterfall (Audio Dynamics >= 70%)
        np.subtract(bands_arr, prev_b, out=flux_scratch)
        np.abs(flux_scratch, out=flux_scratch)
        spec_flux = float(np.mean(flux_scratch))
        prev_b[:] = bands_arr

        # Flow halts completely if spectral audio is muted (0.0 autonomous motion)
        step = spec_flux * 45.0 * self.gravity * self.mood_pace
        self.flow_offset = (self.flow_offset + step) % 1.0

        # Traveling downward wave along altitude Z
        np.add(self._z, self.flow_offset, out=self._phase_scratch)
        np.multiply(self._phase_scratch, 4.0 * math.pi, out=self._phase_scratch)
        np.sin(self._phase_scratch, out=self._wave_scratch)
        np.add(self._wave_scratch, 1.0, out=self._wave_scratch)
        np.multiply(self._wave_scratch, 0.5, out=self._wave_scratch)

        # Direct per-LED spectral sampling: altitude z directly indexes the Mel bands
        np.take(bands_arr, band_indices, out=self._spec_profile, mode="clip")
        np.multiply(self._wave_scratch, self._spec_profile, out=self._intensity)

        # Subtle secondary beat pulse (15% variance allocation)
        pulse = self.beat_pulse(sharpness=2.0)
        gain = 0.85 + 0.15 * pulse
        np.multiply(self._intensity, gain, out=self._intensity)
        np.clip(self._intensity, 0.0, 1.0, out=self._intensity)

        # Sample along palette LUT preserving S >= 0.92
        np.take(self.palette_lut, self._lut_indices, axis=0, out=self._base_rgb, mode="clip")
        np.multiply(self._base_rgb, self._intensity_col, out=self._target_rgb)

        np.maximum(0.0, self._target_rgb, out=self._target_rgb)
        np.minimum(255.0, self._target_rgb, out=self._target_rgb)
        np.copyto(self.rgb_list, self._target_rgb, casting="unsafe")


SpectralAvalanche = Spectral_avalanche_mode
