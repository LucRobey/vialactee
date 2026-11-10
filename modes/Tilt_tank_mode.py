"""
Tilt Tank Mode (Global Mode)
Treats the entire 432 x 246 chandelier as a single 2D glass tank of sloshing bioluminescent liquid:
- 2D Liquid Surface Horizon (`surface_alt(x)`): Base fill height tracks the 16-band Mel spectrum and spectral centroid (`vertical_center`), tilting diagonally across the room width (`(x_norm - 0.5) * tilt_angle`) with `spectral_tilt * tilt_gain` and beat-locked sloshing (`sin(2*pi*beat_phase)`), topped with 2D capillary ripples (`wave_chop`).
- Depth-Graded Submerged Liquid & Glowing Foam Meniscus: Submerged LEDs (`altitude <= surface_alt(x)`) render a smooth bioluminescent depth gradient from deep ocean floor (`mood_colors[0]`) to surface (`mood_colors[1]` / `mood_colors[2]`), while LEDs along the tilted meniscus blaze with a `highlight_color` foam crest (`crest_glow`) and upward spray droplets.
Zero runtime heap allocations (AXIOM-01, AXIOM-02).
"""
from typing import Any, Dict, List, Optional, Sequence
import math
import numpy as np
import modes.Mode as Mode
from utils.global_mode import SegmentSpatialProfile


class Tilt_tank_mode(Mode.Mode):
    """Global 2D tilt-tank of sloshing bioluminescent liquid with a tilted spectral horizon and foam meniscus.

    Lead: spectrum (16-band Mel fill height, spectral centroid lift, and diagonal spectral_tilt horizon). Secondary: beat (phase-locked sloshing oscillation and meniscus crest surge). Macro: palette, decay via mood_trail.
    """
    IS_GLOBAL: bool = True
    LEAD: str = "spectrum"
    SECONDARY: tuple = ("beat",)

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "tilt_gain",
                "label": "Horizon Tilt Gain",
                "control": "slider",
                "valueType": "number",
                "min": 0.3,
                "max": 2.0,
                "step": 0.05,
                "default": 1.15,
                "attr": "tilt_gain",
            },
            {
                "key": "wave_chop",
                "label": "Surface Wave Chop",
                "control": "slider",
                "valueType": "number",
                "min": 0.2,
                "max": 2.0,
                "step": 0.05,
                "default": 1.0,
                "attr": "wave_chop",
            },
            {
                "key": "crest_glow",
                "label": "Meniscus Crest Glow",
                "control": "slider",
                "valueType": "number",
                "min": 0.4,
                "max": 2.0,
                "step": 0.05,
                "default": 1.15,
                "attr": "crest_glow",
            },
        ]

    def __init__(
        self,
        name: str,
        segment_name: str,
        listener: Any,
        leds: Any,
        indexes: List[int],
        rgb_list: np.ndarray,
        infos: Dict[str, Any],
    ):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.tilt_gain: float = float(
            infos.get("tilt_gain", infos.get("tilt_tank_tilt_gain", 1.15))
        )
        self.wave_chop: float = float(
            infos.get("wave_chop", infos.get("tilt_tank_wave_chop", 1.0))
        )
        self.crest_glow: float = float(
            infos.get("crest_glow", infos.get("tilt_tank_crest_glow", 1.15))
        )

        self.spatial = SegmentSpatialProfile(segment_name, self.nb_of_leds)

        # Persistent kinetic state (scalars only -> zero allocation)
        self.fill_level: float = 0.45
        self.tilt_angle: float = 0.0
        self.wave_scroll: float = 0.0
        self.prev_phase: float = 0.0

        # Pre-allocated vector buffers of size n
        n = max(1, self.nb_of_leds)
        self.target_rgb: np.ndarray = np.zeros((n, 3), dtype=np.float64)
        self.surface_vec: np.ndarray = np.zeros(n, dtype=np.float64)
        self.dist_vec: np.ndarray = np.zeros(n, dtype=np.float64)
        self.sub_mask: np.ndarray = np.zeros(n, dtype=np.float64)
        self.crest_vec: np.ndarray = np.zeros(n, dtype=np.float64)
        self.ripple_vec: np.ndarray = np.zeros(n, dtype=np.float64)
        self.scratch_vec: np.ndarray = np.zeros(n, dtype=np.float64)
        self.lut_t: np.ndarray = np.zeros(n, dtype=np.float64)
        self.lut_rgb: np.ndarray = np.zeros((n, 3), dtype=np.int32)
        self._out_cols: tuple = (
            self.target_rgb[:, 0],
            self.target_rgb[:, 1],
            self.target_rgb[:, 2],
        )
        self._lrgb_cols: tuple = (
            self.lut_rgb[:, 0],
            self.lut_rgb[:, 1],
            self.lut_rgb[:, 2],
        )

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind physical segment role, tags, and 2D coordinates from Segment."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)

    def _extract_spectrum_zones(self) -> tuple:
        """Extract (bass_e, mid_e, high_e) from 8/16-band Mel spectrum with zero heap allocations."""
        bands = getattr(self.listener, "asserved_fft_band", None)
        if bands is None or len(bands) == 0:
            p = float(getattr(self.listener, "asserved_total_power", 0.0))
            return p, p, p

        nb = len(bands)
        if nb >= 16:
            bass_e = (
                float(bands[0]) + float(bands[1]) + float(bands[2]) + float(bands[3])
            ) * 0.25
            mid_e = (
                float(bands[4])
                + float(bands[5])
                + float(bands[6])
                + float(bands[7])
                + float(bands[8])
                + float(bands[9])
            ) / 6.0
            high_e = (
                float(bands[10])
                + float(bands[11])
                + float(bands[12])
                + float(bands[13])
                + float(bands[14])
                + float(bands[15])
            ) / 6.0
        else:
            b0 = float(bands[0])
            b1 = float(bands[min(1, nb - 1)])
            b2 = float(bands[min(2, nb - 1)])
            b3 = float(bands[min(3, nb - 1)])
            b4 = float(bands[min(4, nb - 1)])
            b5 = float(bands[min(5, nb - 1)])
            bass_e = 0.55 * b0 + 0.45 * b1
            mid_e = 0.50 * b2 + 0.50 * b3
            high_e = 0.50 * b4 + 0.50 * b5
        return bass_e, mid_e, high_e

    def run(self) -> None:
        n = self.nb_of_leds
        if n <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        if is_silent:
            self.fade_to_black_segment_vectorized(0.35, 0, n - 1)
            return

        dt = self.dt
        tension = float(ctx.tension if ctx is not None else 0.0)
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        lock = self.rhythm_lock

        # Read all 3 live-tunable settings in run()
        tilt_gain = float(self.tilt_gain)
        wave_chop = float(self.wave_chop)
        crest_glow = float(self.crest_glow)

        bass_e, mid_e, high_e = self._extract_spectrum_zones()

        # Secondary beat signals (~20% choreography share)
        beat_env = self.beat_pulse(2.2)
        beat_wave = lock * math.sin(2.0 * math.pi * phase)
        beat_swell = 0.45 * beat_env + 0.55 * lock * (0.5 - 0.5 * math.cos(2.0 * math.pi * phase))
        phase_delta = (phase - self.prev_phase) % 1.0
        if phase_delta > 0.5:
            phase_delta = 0.0
        self.prev_phase = phase

        # Advance 2D surface ripple scroll (blending beat_phase lock with continuous acoustic drift)
        pace_mult = self.mood_pace * (1.0 + 0.25 * tension + 0.20 * self.drop_decay)
        rhythmic_step = phase_delta * 2.0 * math.pi
        acoustic_step = dt * 1.8 * pace_mult
        step = lock * rhythmic_step + (1.0 - lock) * acoustic_step
        self.wave_scroll = (self.wave_scroll + step * (0.85 + 0.65 * wave_chop * (mid_e + high_e))) % (20.0 * math.pi)

        # 1. Base liquid fill height: Lead = spectrum (~78%), Secondary = beat (~22%)
        spec_fill = min(
            1.0,
            max(0.0, 0.58 * mid_e + 0.32 * bass_e + 0.28 * v_center),
        )
        target_fill = max(0.06, min(0.94, (0.10 + 0.68 * spec_fill + 0.18 * beat_swell) * self.transition_scale))
        self.fill_level += self.alpha(16.0) * (target_fill - self.fill_level)

        # 2. Diagonal 2D horizon tilt angle: Lead = spectral_tilt (~78%), Secondary = beat slosh (~22%)
        spec_tilt = (0.65 * tilt + 0.35 * (high_e - bass_e)) * tilt_gain
        raw_tilt = (0.78 * spec_tilt + 0.22 * beat_wave * tilt_gain) * (1.0 + 0.20 * tension)
        target_tilt = max(-0.90, min(0.90, raw_tilt))
        self.tilt_angle += self.alpha(15.0) * (target_tilt - self.tilt_angle)

        x = self.spatial.x_norm[:n]
        alt = self.spatial.altitude[:n]
        surf = self.surface_vec[:n]
        dist = self.dist_vec[:n]
        sub = self.sub_mask[:n]
        crest = self.crest_vec[:n]
        ripple = self.ripple_vec[:n]
        sv = self.scratch_vec[:n]
        lt = self.lut_t[:n]
        lrgb = self.lut_rgb[:n]
        out = self.target_rgb[:n]

        # Compute 2D surface ripples: sin(x_norm * 10 - scroll) * wave_chop + capillary harmonic
        np.multiply(x, 10.0, out=ripple)
        np.subtract(ripple, self.wave_scroll, out=ripple)
        np.sin(ripple, out=ripple)

        np.multiply(x, 21.0, out=sv)
        np.add(sv, self.wave_scroll * 1.35, out=sv)
        np.cos(sv, out=sv)
        np.multiply(sv, 0.35, out=sv)
        np.add(ripple, sv, out=ripple)

        chop_amp = 0.065 * wave_chop * (0.25 + 0.75 * min(1.0, mid_e + high_e) + 0.20 * beat_env)
        np.multiply(ripple, chop_amp, out=ripple)

        # Construct 2D tilted liquid horizon: surface_alt(x) = fill_level + (x - 0.5) * tilt_angle + ripple
        np.subtract(x, 0.5, out=surf)
        np.multiply(surf, self.tilt_angle, out=surf)
        np.add(surf, self.fill_level, out=surf)
        np.add(surf, ripple, out=surf)
        np.clip(surf, 0.05, 0.95, out=surf)

        # Signed vertical distance from liquid surface: dist = surf - altitude (positive when submerged)
        np.subtract(surf, alt, out=dist)

        # Submerged liquid mask (altitude <= surface_alt(x)) with soft anti-aliased meniscus
        np.multiply(dist, 16.0, out=sub)
        np.add(sub, 0.5, out=sub)
        np.clip(sub, 0.0, 1.0, out=sub)

        # Normalized depth gradient coordinate [0 = ocean floor, 1 = liquid surface]
        inv_surf = 1.0 / max(0.12, self.fill_level + 0.15)
        np.multiply(alt, inv_surf, out=lt)
        np.clip(lt, 0.0, 1.0, out=lt)

        # Modulate submerged brightness by spectral energy & depth caustics
        spec_bright = min(
            1.0,
            max(
                0.10,
                (0.22 + 0.62 * (0.30 * bass_e + 0.35 * mid_e + 0.35 * high_e) + 0.26 * v_center + 0.18 * beat_swell)
                * self.transition_scale,
            ),
        )
        np.multiply(lt, 0.55, out=sv)
        np.add(sv, 0.45, out=sv)
        np.multiply(sub, sv, out=sub)
        np.multiply(sub, spec_bright, out=sub)

        # Sample mood_colors[0] -> mood_colors[1] -> mood_colors[2] gradient shifted by spectral centroid
        np.multiply(lt, 0.78, out=lt)
        np.add(lt, 0.05 + 0.17 * v_center, out=lt)
        np.clip(lt, 0.0, 1.0, out=lt)
        self.palette_sample(lt, lrgb)

        # Glowing foam meniscus crest along |altitude - surface_alt(x)| < crest_width + upward spray droplets
        crest_sharpness = -1.0 / max(0.025, 0.055 + 0.025 * wave_chop)
        np.abs(dist, out=crest)
        np.multiply(crest, crest_sharpness, out=crest)
        np.exp(crest, out=crest)

        # Upward bioluminescent spray droplets above wave crests (where dist < 0 and ripple > 0)
        np.minimum(dist, 0.0, out=sv)
        np.multiply(sv, 11.0, out=sv)
        np.exp(sv, out=sv)
        # Gate spray to wave peaks above the meniscus
        np.maximum(ripple, 0.0, out=lt)
        np.multiply(lt, 8.0 * wave_chop, out=lt)
        np.clip(lt, 0.0, 1.0, out=lt)
        np.multiply(sv, lt, out=sv)
        np.subtract(1.0, sub, out=ripple)
        np.multiply(sv, ripple, out=sv)

        crest_drive = min(
            1.35,
            max(
                0.15,
                crest_glow
                * (0.20 + 0.58 * min(1.0, mid_e + high_e + 0.35 * abs(tilt)) + 0.24 * beat_swell + 0.22 * self.drop_decay)
                * self.transition_scale,
            ),
        )
        np.multiply(crest, crest_drive, out=crest)
        np.multiply(sv, 0.45 * crest_drive, out=sv)
        np.add(crest, sv, out=crest)

        # Combine depth-graded submerged liquid with bright highlight_color foam crest (zero-allocation per channel)
        hi = self.highlight_color
        m2 = self.mood_colors[2]
        accent = self.mood_accent
        out_cols = self._out_cols
        lrgb_cols = self._lrgb_cols
        for c in range(3):
            foam_c = (1.0 - accent) * float(hi[c]) + accent * (0.65 * float(hi[c]) + 0.35 * float(m2[c]))
            out_c = out_cols[c][:n]
            np.multiply(sub, lrgb_cols[c][:n], out=out_c)
            np.multiply(crest, foam_c, out=sv)
            np.add(out_c, sv, out=out_c)

        np.clip(out, 0.0, 255.0, out=out)
        blend_rate = self.alpha(18.0 / max(0.6, self.mood_trail))
        self.smooth_segment_vectorized(blend_rate, 0, n - 1, out)
