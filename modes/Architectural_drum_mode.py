"""
Architectural Drum Mode (Global Mode)
Orchestrates all 11 chandelier segments as a unified 3-tier drum & frequency sculpture:
- Vertical Pillars (v1..v4): Bass & Kick hydraulic pistons with falling gravity crowns.
- Horizontal Bridges (h10, h11, h31, h32): Snare & Mid-range center-out cross-waves.
- High Canopy (h00, h20, h30): Continuous 2D room-space Hi-Hat & Treble panoramic aurora.
Zero runtime heap allocations (AXIOM-01, AXIOM-02).
"""
from typing import Any, Dict, List, Optional, Sequence
import math
import numpy as np
import modes.Mode as Mode
from utils.global_mode import SegmentSpatialProfile


class Architectural_drum_mode(Mode.Mode):
    """Global 3-tier architectural drum & spectrum sculpture across pillars, bridges, and canopy.

    Lead: spectrum (16-band Mel split into bass pistons, mid cross-waves, and treble canopy aurora). Secondary: beat (piston kick and phase-locked wave drive). Macro: palette, decay via mood_trail.
    """
    IS_GLOBAL: bool = True
    LEAD: str = "spectrum"
    SECONDARY: tuple = ("beat",)

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "bass_punch",
                "label": "Pillar Bass Drive",
                "control": "slider",
                "valueType": "number",
                "min": 0.5,
                "max": 2.0,
                "step": 0.05,
                "default": 1.15,
                "attr": "bass_punch",
            },
            {
                "key": "snare_width",
                "label": "Bridge Snare Spread",
                "control": "slider",
                "valueType": "number",
                "min": 0.5,
                "max": 2.0,
                "step": 0.05,
                "default": 1.10,
                "attr": "snare_width",
            },
            {
                "key": "hat_shimmer",
                "label": "Canopy Treble Shimmer",
                "control": "slider",
                "valueType": "number",
                "min": 0.4,
                "max": 2.0,
                "step": 0.05,
                "default": 1.15,
                "attr": "hat_shimmer",
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

        self.bass_punch: float = float(infos.get("arch_drum_bass_punch", 1.15))
        self.snare_width: float = float(infos.get("arch_drum_snare_width", 1.10))
        self.hat_shimmer: float = float(infos.get("arch_drum_hat_shimmer", 1.15))

        self.spatial = SegmentSpatialProfile(segment_name, self.nb_of_leds)

        # Persistent kinetic state (scalars only -> zero allocation)
        self.piston_level: float = 0.0
        self.crown_pos: float = 0.0
        self.bridge_reach: float = 0.0
        self.wave_scroll: float = 0.0
        self.canopy_scroll: float = 0.0
        self.prev_phase: float = 0.0

        # Pre-allocated vector buffers of size n
        n = max(1, self.nb_of_leds)
        self.target_rgb: np.ndarray = np.zeros((n, 3), dtype=np.float64)
        self.scratch_vec: np.ndarray = np.zeros(n, dtype=np.float64)
        self.scratch_vec2: np.ndarray = np.zeros(n, dtype=np.float64)
        self.lut_t: np.ndarray = np.zeros(n, dtype=np.float64)
        self.lut_rgb: np.ndarray = np.zeros((n, 3), dtype=np.int32)
        self.color_a: np.ndarray = np.zeros(3, dtype=np.float64)
        self.color_b: np.ndarray = np.zeros(3, dtype=np.float64)

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind physical segment role, tags, and 2D coordinates from Segment."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)

    def _extract_zone_energies(self) -> tuple:
        """Decompose 8/16-band Mel spectrum into (sub_bass, upper_bass, low_mid, high_mid, treble)."""
        bands = getattr(self.listener, "asserved_fft_band", None)
        if bands is None or len(bands) == 0:
            p = float(getattr(self.listener, "asserved_total_power", 0.0))
            return p, p, p, p, p

        nb = len(bands)
        if nb >= 16:
            sub_bass = 0.60 * float(bands[0]) + 0.40 * float(bands[1])
            upper_bass = (float(bands[1]) + float(bands[2]) + float(bands[3])) / 3.0
            low_mid = (float(bands[4]) + float(bands[5]) + float(bands[6])) / 3.0
            high_mid = (float(bands[7]) + float(bands[8]) + float(bands[9])) / 3.0
            treble = float(np.mean(bands[10:16]))
        else:
            b0 = float(bands[0])
            b1 = float(bands[min(1, nb - 1)])
            b2 = float(bands[min(2, nb - 1)])
            b3 = float(bands[min(3, nb - 1)])
            b4 = float(bands[min(4, nb - 1)])
            b5 = float(bands[min(5, nb - 1)])
            sub_bass = 0.65 * b0 + 0.35 * b1
            upper_bass = 0.50 * b1 + 0.50 * b2
            low_mid = 0.50 * b2 + 0.50 * b3
            high_mid = 0.50 * b3 + 0.50 * b4
            treble = float(np.mean(bands[min(5, nb - 1):]))
        return sub_bass, upper_bass, low_mid, high_mid, treble

    def _render_pillar_slice(
        self,
        out_rgb: np.ndarray,
        u_slice: np.ndarray,
        bass_drive: float,
        beat_kick: float,
    ) -> None:
        """Render Bass & Kick Hydraulic Piston + falling gravity crown into out_rgb."""
        n = len(u_slice)
        if n <= 0:
            return

        mood = self.mood_colors
        hi = self.highlight_color
        accent = self.mood_accent
        fps_ratio = self.fps_ratio

        # Lead = bass_drive (~78%), Secondary = beat_kick (~22%)
        combined = min(1.0, (0.78 * bass_drive * self.bass_punch + 0.22 * beat_kick) * self.transition_scale)
        self.piston_level += self.alpha(16.0) * (combined - self.piston_level)

        if self.piston_level >= self.crown_pos:
            self.crown_pos = min(1.0, self.piston_level + 0.04)
        else:
            gravity = (0.018 * fps_ratio * self.mood_pace) / max(0.5, self.mood_trail)
            self.crown_pos = max(0.0, self.crown_pos - gravity)

        # Piston body mask with soft compression head
        sv = self.scratch_vec[:n]
        sv2 = self.scratch_vec2[:n]
        np.subtract(self.piston_level, u_slice, out=sv)
        np.multiply(sv, 14.0, out=sv)
        np.clip(sv, 0.0, 1.0, out=sv)
        # Modulate column brightness directly by bass_drive so spectral dynamics shine
        col_bright = 0.25 + 0.75 * min(1.0, bass_drive * self.bass_punch)
        np.multiply(sv, col_bright, out=sv)

        # Head flare near piston_level
        np.subtract(u_slice, self.piston_level, out=sv2)
        np.abs(sv2, out=sv2)
        np.multiply(sv2, -22.0, out=sv2)
        np.exp(sv2, out=sv2)
        sv2 *= min(1.0, 0.55 * bass_drive + 0.45 * beat_kick)

        # Floating gravity crown dot
        crown_dist = np.abs(u_slice - self.crown_pos, out=self.lut_t[:n])
        np.multiply(crown_dist, -32.0, out=crown_dist)
        np.exp(crown_dist, out=crown_dist)
        crown_dist *= min(1.0, 0.40 + 0.60 * self.crown_pos)

        m0, m1 = mood[0], mood[1]
        for c in range(3):
            base_c = (1.0 - u_slice) * float(m0[c]) + u_slice * float(m1[c])
            head_c = (1.0 - accent) * float(m1[c]) + accent * float(hi[c])
            out_rgb[:, c] = sv * base_c + sv2 * head_c + crown_dist * float(hi[c])

    def _render_bridge_slice(
        self,
        out_rgb: np.ndarray,
        u_center_slice: np.ndarray,
        x_slice: np.ndarray,
        mid_drive: float,
        beat_kick: float,
        tilt: float,
    ) -> None:
        """Render Snare & Mid-Range symmetric cross-waves into out_rgb."""
        n = len(u_center_slice)
        if n <= 0:
            return

        hi = self.highlight_color
        accent = self.mood_accent

        # Lead = mid_drive (~78%), Secondary = beat_kick (~22%)
        target_reach = min(1.0, (0.78 * mid_drive * self.snare_width + 0.22 * beat_kick) * self.transition_scale)
        self.bridge_reach += self.alpha(15.0) * (target_reach - self.bridge_reach)

        sv = self.scratch_vec[:n]
        sv2 = self.scratch_vec2[:n]

        # Symmetric bar from bridge center (u_center = 0) outward
        np.subtract(self.bridge_reach, u_center_slice, out=sv)
        np.multiply(sv, 9.0, out=sv)
        np.clip(sv, 0.0, 1.0, out=sv)

        # Traveling cross-wave ripple along room X & center distance
        np.multiply(u_center_slice, 8.5, out=sv2)
        np.subtract(sv2, self.wave_scroll, out=sv2)
        np.cos(sv2, out=sv2)
        np.multiply(sv2, 0.35, out=sv2)
        np.add(sv2, 0.65, out=sv2)
        np.multiply(sv, sv2, out=sv)
        np.multiply(sv, 0.20 + 0.80 * min(1.0, mid_drive * self.snare_width), out=sv)

        # Sample palette across [0.30 .. 0.85] shifted by spectral_tilt
        lt = self.lut_t[:n]
        tilt_shift = 0.12 * max(-1.0, min(1.0, tilt))
        np.multiply(x_slice, 0.45, out=lt)
        np.add(lt, 0.35 + tilt_shift, out=lt)
        np.clip(lt, 0.0, 1.0, out=lt)
        lrgb = self.lut_rgb[:n]
        self.palette_sample(lt, lrgb)

        # Leading wavefront crest near bridge_reach
        np.subtract(u_center_slice, self.bridge_reach, out=sv2)
        np.abs(sv2, out=sv2)
        np.multiply(sv2, -18.0, out=sv2)
        np.exp(sv2, out=sv2)
        sv2 *= min(1.0, 0.65 * mid_drive + 0.35 * beat_kick)

        for c in range(3):
            out_rgb[:, c] = sv * lrgb[:, c] + sv2 * ((1.0 - accent) * lrgb[:, c] + (0.55 + 0.45 * accent) * float(hi[c]))

    def _render_canopy_slice(
        self,
        out_rgb: np.ndarray,
        x_slice: np.ndarray,
        treble_drive: float,
        v_center: float,
        beat_kick: float,
    ) -> None:
        """Render Hi-Hat & Treble panoramic room-X aurora into out_rgb."""
        n = len(x_slice)
        if n <= 0:
            return

        mood = self.mood_colors
        hi = self.highlight_color
        accent = self.mood_accent

        sv = self.scratch_vec[:n]
        sv2 = self.scratch_vec2[:n]

        # Dual counter-propagating room-X interference waves across the 432-column canopy
        np.multiply(x_slice, 16.0, out=sv)
        np.subtract(sv, self.canopy_scroll, out=sv)
        np.sin(sv, out=sv)

        np.multiply(x_slice, 29.0, out=sv2)
        np.add(sv2, self.canopy_scroll * 0.65, out=sv2)
        np.cos(sv2, out=sv2)

        # Combine into aurora envelope + high-hat diamond peaks
        np.multiply(sv, 0.5, out=sv)
        np.add(sv, 0.5, out=sv)
        np.multiply(sv2, 0.5, out=sv2)
        np.add(sv2, 0.5, out=sv2)

        # Lead = treble_drive + vertical_center lift (~80%), Secondary = beat_kick (~20%)
        aurora_gain = min(
            1.0,
            (0.80 * treble_drive * self.hat_shimmer * (0.75 + 0.25 * v_center) + 0.20 * beat_kick)
            * self.transition_scale,
        )
        np.multiply(sv, aurora_gain, out=sv)

        # Sharp hi-hat sparkle nodes where both waves constructively interfere
        sparkle = self.lut_t[:n]
        np.multiply(sv, sv2, out=sparkle)
        np.square(sparkle, out=sparkle)
        sparkle *= min(1.0, treble_drive * self.hat_shimmer * 1.25)

        m1, m2 = mood[1], mood[2]
        for c in range(3):
            bed_c = (1.0 - x_slice) * float(m1[c]) + x_slice * float(m2[c])
            spark_c = (1.0 - accent) * float(hi[c]) + accent * 255.0
            out_rgb[:, c] = sv * bed_c + sparkle * spark_c

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        if is_silent:
            self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
            return

        dt = self.dt
        tension = float(ctx.tension if ctx is not None else 0.0)
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        beat_tag = str(getattr(self.listener, "beat_tag", "Bass/Kick"))
        lock = self.rhythm_lock

        sub_bass, upper_bass, low_mid, high_mid, treble = self._extract_zone_energies()

        # Advance continuous wave scroll speeds (blending beat_phase delta when locked with acoustic drift)
        phase_delta = (phase - self.prev_phase) % 1.0
        if phase_delta > 0.5:
            phase_delta = 0.0
        self.prev_phase = phase

        pace_mult = self.mood_pace * (1.0 + 0.25 * tension + 0.20 * self.drop_decay)
        rhythmic_step = phase_delta * 2.0 * math.pi
        acoustic_step = dt * 3.6 * pace_mult
        step = lock * rhythmic_step + (1.0 - lock) * acoustic_step
        self.wave_scroll = (self.wave_scroll + step * (1.0 + 0.8 * (low_mid + high_mid))) % (20.0 * math.pi)
        self.canopy_scroll = (self.canopy_scroll + step * (1.2 + 1.2 * treble)) % (20.0 * math.pi)

        # Secondary beat envelope with subtle per-instrument tag emphasis
        base_pulse = self.beat_pulse(2.3)
        kick_pulse = min(1.0, base_pulse * (1.18 if beat_tag == "Bass/Kick" else 0.92) + 0.25 * self.drop_decay)
        snare_pulse = min(1.0, base_pulse * (1.18 if beat_tag == "Snare/Mid" else 0.92) + 0.25 * self.drop_decay)
        hat_pulse = min(1.0, base_pulse * (1.18 if beat_tag == "Hi-hat/Cymbal" else 0.92) + 0.20 * self.drop_decay)

        n = self.nb_of_leds
        out = self.target_rgb[:n]
        out.fill(0.0)
        role = self.spatial.role

        if role == "pillar":
            bass_sig = sub_bass if self.spatial.is_inner_pillar else (0.45 * sub_bass + 0.55 * upper_bass)
            self._render_pillar_slice(out, self.spatial.u[:n], bass_sig, kick_pulse)
        elif role == "bridge":
            mid_sig = (0.70 * low_mid + 0.30 * high_mid) if self.spatial.tier == "low" else (0.30 * low_mid + 0.70 * high_mid)
            self._render_bridge_slice(out, self.spatial.u_center[:n], self.spatial.x_norm[:n], mid_sig, snare_pulse, tilt)
        elif role == "canopy":
            self._render_canopy_slice(out, self.spatial.x_norm[:n], treble, v_center, hat_pulse)
        else:
            # Composite 3-zone preview for 1D mode_studio / unit test strips
            s1 = max(1, min(n, self.spatial.split_1))
            s2 = max(s1, min(n, self.spatial.split_2))
            if s1 > 0:
                self._render_pillar_slice(out[:s1], self.spatial.u[:s1] * (n / float(s1)), 0.6 * sub_bass + 0.4 * upper_bass, kick_pulse)
            if s2 > s1:
                mid_len = s2 - s1
                u_mid = self.spatial.u[:mid_len] * (n / float(mid_len))
                self._render_bridge_slice(out[s1:s2], np.abs(u_mid * 2.0 - 1.0), u_mid, 0.5 * (low_mid + high_mid), snare_pulse, tilt)
            if n > s2:
                top_len = n - s2
                u_top = self.spatial.u[:top_len] * (n / float(top_len))
                self._render_canopy_slice(out[s2:n], u_top, treble, v_center, hat_pulse)

        np.clip(out, 0.0, 255.0, out=out)
        blend_rate = self.alpha(18.0 / max(0.6, self.mood_trail))
        self.smooth_segment_vectorized(blend_rate, 0, n - 1, out)
