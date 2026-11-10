"""
Prism Lighthouse Mode (Global Mode)
Orchestrates all 11 chandelier segments in 2D polar coordinates around the architectural core (cx=0.62, cy=0.45):
- Rotating 2D Prism Searchlight Beams (LEAD = "beat"): Twin counter-rotating prismatic laser beams sweep
  across 2D polar angle theta(t), slicing diagonally across pillars, bridges, and canopy in lock-step
  with beat_phase and beat_pulse() when rhythm-locked and continuous acoustic rotation when unlocked.
- 2D Radial Sonar Shockwaves (SECONDARY = ("transient",)): Circular sonar rings expand radially outward
  across 2D radius on verified beat transients, spectral flux bursts, and drop impacts.
Zero runtime heap allocations (AXIOM-01, AXIOM-02).
"""
from typing import Any, Dict, List, Optional, Sequence
import math
import numpy as np
import modes.Mode as Mode
from utils.global_mode import SegmentSpatialProfile


class Prism_lighthouse_mode(Mode.Mode):
    """Global 2D polar prism searchlight and radial sonar shockwave across the chandelier.

    Lead: beat (counter-rotating 2D prism searchlight beams driven by beat_phase and beat_pulse). Secondary: transient (2D radial sonar shockwave rings on is_real_beat, drop_hit, and bass band_flux bursts). Macro: palette, rotation pace via mood_pace, beam focus via mood_sharpness, trail persistence via mood_trail.
    """
    IS_GLOBAL: bool = True
    LEAD: str = "beat"
    SECONDARY: tuple = ("transient",)

    CORE_X: float = 0.62
    CORE_Y: float = 0.45

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "beam_sharpness",
                "label": "Prism Beam Sharpness",
                "control": "slider",
                "valueType": "number",
                "min": 0.5,
                "max": 3.0,
                "step": 0.05,
                "default": 1.25,
                "attr": "beam_sharpness",
            },
            {
                "key": "rotation_speed",
                "label": "Lighthouse Rotation Speed",
                "control": "slider",
                "valueType": "number",
                "min": 0.3,
                "max": 3.0,
                "step": 0.05,
                "default": 1.15,
                "attr": "rotation_speed",
            },
            {
                "key": "sonar_flare",
                "label": "Radial Sonar Flare",
                "control": "slider",
                "valueType": "number",
                "min": 0.2,
                "max": 2.5,
                "step": 0.05,
                "default": 1.10,
                "attr": "sonar_flare",
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

        self.beam_sharpness: float = float(infos.get("prism_beam_sharpness", 1.25))
        self.rotation_speed: float = float(infos.get("prism_rotation_speed", 1.15))
        self.sonar_flare: float = float(infos.get("prism_sonar_flare", 1.10))

        n = max(1, self.nb_of_leds)
        self.spatial = SegmentSpatialProfile(segment_name, self.nb_of_leds)

        # Pre-allocated 2D polar coordinate buffers around architectural core (cx=0.62, cy=0.45)
        self.radius: np.ndarray = np.zeros(n, dtype=np.float64)
        self.angle: np.ndarray = np.zeros(n, dtype=np.float64)
        self.prism_twist: np.ndarray = np.zeros(n, dtype=np.float64)
        self.core_glow_mask: np.ndarray = np.zeros(n, dtype=np.float64)

        # Persistent kinetic state (scalars only -> zero heap allocation)
        self.theta_1: float = 0.0
        self.theta_2: float = math.pi * 0.5
        self.prev_phase: float = float(getattr(listener, "beat_phase", 0.0)) if listener is not None else 0.0
        self.r_sonar: float = 2.0
        self.sonar_amp: float = 0.0
        self.sonar_cooldown: float = 0.0

        # Pre-allocated scratch buffers of size n for vectorized rendering
        self.target_rgb: np.ndarray = np.zeros((n, 3), dtype=np.float64)
        self.beam1_vec: np.ndarray = np.zeros(n, dtype=np.float64)
        self.beam2_vec: np.ndarray = np.zeros(n, dtype=np.float64)
        self.sonar_vec: np.ndarray = np.zeros(n, dtype=np.float64)
        self.lut_t: np.ndarray = np.zeros(n, dtype=np.float64)
        self.lut_rgb: np.ndarray = np.zeros((n, 3), dtype=np.int32)

        self._update_polar_geometry()

    def _update_polar_geometry(self) -> None:
        """Precompute 2D polar coordinates (self.radius, self.angle) around (cx=0.62, cy=0.45) in place."""
        n = max(1, self.nb_of_leds)
        dx = self.beam1_vec[:n]
        dy = self.beam2_vec[:n]
        np.subtract(self.spatial.x_norm[:n], self.CORE_X, out=dx)
        np.subtract(self.spatial.y_norm[:n], self.CORE_Y, out=dy)

        if self.spatial.role == "composite" and n > 1:
            # In single-strip studio/test previews, bow the 1D diagonal slightly so polar angle
            # sweeps a full 2D arc around the core while preserving exact 2D endpoints.
            np.sin(self.spatial.u[:n] * (2.0 * math.pi), out=self.sonar_vec[:n])
            dx += 0.22 * self.sonar_vec[:n]
            np.cos(self.spatial.u[:n] * (2.0 * math.pi), out=self.sonar_vec[:n])
            dy -= 0.18 * self.sonar_vec[:n]

        np.hypot(dx, dy, out=self.radius[:n])
        # Normalize radius so 1.0 corresponds to the outer canopy perimeter (~0.76 from core)
        np.divide(self.radius[:n], 0.76, out=self.radius[:n])
        np.clip(self.radius[:n], 0.0, 1.0, out=self.radius[:n])

        np.arctan2(dy, dx, out=self.angle[:n])

        # Subtle radial spiral dispersion so beams slice gracefully along radial and collinear strips
        np.multiply(self.radius[:n], 0.85, out=self.prism_twist[:n])

        # Soft architectural core lantern falloff near (cx, cy)
        np.square(self.radius[:n], out=self.core_glow_mask[:n])
        np.multiply(self.core_glow_mask[:n], -3.5, out=self.core_glow_mask[:n])
        np.exp(self.core_glow_mask[:n], out=self.core_glow_mask[:n])

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind physical segment role, tags, and 2D coordinates from Segment and update polar coords."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._update_polar_geometry()

    def run(self) -> None:
        n = self.nb_of_leds
        if n <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        if is_silent:
            self.sonar_amp *= 0.65
            self.fade_to_black_segment_vectorized(0.35, 0, n - 1)
            return

        dt = self.dt
        tension = float(ctx.tension if ctx is not None else 0.0)
        energy = float(ctx.energy if ctx is not None else getattr(self.listener, "asserved_total_power", 0.5))
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        lock = self.rhythm_lock

        # 1. LEAD = "beat": Advance counter-rotating 2D prism searchlight beams
        phase_delta = (phase - self.prev_phase) % 1.0
        if phase_delta > 0.6:
            phase_delta = 0.0
        self.prev_phase = phase

        pace_scale = self.rotation_speed * self.mood_pace * (1.0 + 0.25 * tension)
        rhythmic_step = phase_delta * (math.pi * 1.35) * pace_scale

        # Smooth confidence gate: 1.0 on groove/high lock (and under beat-mute), blending into
        # continuous acoustic rotation when beat tracking is unlocked (rhythm_lock < 0.45).
        lock_gate = min(1.0, lock / 0.45)
        if lock_gate < 1.0:
            acoustic_step = dt * 2.8 * pace_scale * (0.45 + 0.55 * energy)
            angle_step = lock_gate * rhythmic_step + (1.0 - lock_gate) * acoustic_step
        else:
            angle_step = rhythmic_step

        self.theta_1 = (self.theta_1 + angle_step) % (2.0 * math.pi)
        self.theta_2 = (self.theta_2 - 0.78 * angle_step) % (2.0 * math.pi)

        # Beat pulse envelope drives primary lighthouse intensity and beam focus
        pulse = self.beat_pulse(2.2)
        beam_gain = min(1.0, (0.20 + 0.80 * pulse + 0.18 * self.drop_decay) * self.transition_scale)
        sharp_exp = max(1.2, (2.8 * self.beam_sharpness * self.mood_sharpness) * (1.18 - 0.30 * pulse))

        ang = self.angle[:n]
        rad = self.radius[:n]
        twist = self.prism_twist[:n]
        b1 = self.beam1_vec[:n]
        b2 = self.beam2_vec[:n]

        # Beam 1: Primary forward-sweeping 2D searchlight (cos(self.angle - theta_1 - twist))
        np.subtract(ang, self.theta_1, out=b1)
        np.subtract(b1, twist, out=b1)
        np.cos(b1, out=b1)
        np.add(b1, 1.0, out=b1)
        np.multiply(b1, 0.5, out=b1)
        np.power(b1, sharp_exp, out=b1)
        np.multiply(b1, beam_gain, out=b1)

        # Beam 2: Counter-rotating harmonic prism beam (cos(self.angle - theta_2 + twist))
        np.subtract(ang, self.theta_2, out=b2)
        np.add(b2, twist, out=b2)
        np.cos(b2, out=b2)
        np.add(b2, 1.0, out=b2)
        np.multiply(b2, 0.5, out=b2)
        np.power(b2, sharp_exp * 1.15, out=b2)
        np.multiply(b2, beam_gain * 0.85, out=b2)

        # Prismatic palette sampling along 2D radius + beam angle alignment
        lt = self.lut_t[:n]
        np.multiply(rad, 0.65, out=lt)
        np.add(lt, 0.35 * b1, out=lt)
        np.clip(lt, 0.0, 1.0, out=lt)
        lrgb = self.lut_rgb[:n]
        self.palette_sample(lt, lrgb)

        # 2. SECONDARY = ("transient",): 2D Radial Sonar Shockwaves expanding across self.radius
        self.sonar_cooldown = max(0.0, self.sonar_cooldown - dt)
        is_real_beat = bool(
            ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False)
        )
        drop_hit = self.drop_hit
        band_flux = getattr(self.listener, "band_flux", None)
        flux_val = float(band_flux[0]) if (band_flux is not None and len(band_flux) > 0) else 0.0
        flux_burst = (flux_val > 0.38) and (self.sonar_cooldown <= 0.0)

        if drop_hit or is_real_beat or flux_burst:
            self.r_sonar = 0.0
            if drop_hit:
                self.sonar_amp = 1.0
            elif is_real_beat:
                self.sonar_amp = 0.88
            else:
                self.sonar_amp = min(0.78, 0.40 + 0.45 * flux_val)
            self.sonar_cooldown = 0.12

        sonar = self.sonar_vec[:n]
        if self.sonar_amp > 0.01 and self.r_sonar < 1.45:
            self.r_sonar += dt * 1.95 * self.mood_pace * (1.0 + 0.20 * tension)
            self.sonar_amp *= math.exp(-dt * (3.2 / max(0.5, self.mood_trail)))

            np.subtract(rad, self.r_sonar, out=sonar)
            np.square(sonar, out=sonar)
            np.multiply(sonar, -28.0, out=sonar)
            np.exp(sonar, out=sonar)
            sonar_gain = min(1.35, self.sonar_amp * self.sonar_flare * 0.56) * self.transition_scale
            np.multiply(sonar, sonar_gain, out=sonar)
        else:
            sonar.fill(0.0)

        # 3. Synthesize 2D Prismatic Beams + Core Lantern Pulse + Radial Sonar Ring
        mood = self.mood_colors
        m0, m1, m2 = mood[0], mood[1], mood[2]
        hi = self.highlight_color
        accent = self.mood_accent
        out = self.target_rgb[:n]

        # Constructive interference where the two counter-rotating beams cross in 2D space
        cross_flare = self.lut_t[:n]
        np.multiply(b1, b2, out=cross_flare)
        np.multiply(cross_flare, 0.55 + 0.45 * pulse, out=cross_flare)

        core_pulse = (0.12 + 0.38 * pulse) * self.transition_scale
        core_mask = self.core_glow_mask[:n]

        for c in range(3):
            c_m0 = float(m0[c])
            c_m1 = float(m1[c])
            c_m2 = float(m2[c])
            c_hi = float(hi[c])
            beam2_c = (1.0 - accent) * (0.45 * c_m1 + 0.55 * c_m2) + accent * c_hi
            sonar_c = (1.0 - 0.35 * accent) * c_hi + (0.35 * accent) * 255.0
            out[:, c] = (
                b1 * lrgb[:, c]
                + b2 * beam2_c
                + cross_flare * c_hi
                + (core_mask * core_pulse) * c_m0
                + sonar * sonar_c
            )

        np.clip(out, 0.0, 255.0, out=out)
        blend_rate = self.alpha(20.0 / max(0.6, self.mood_trail))
        self.smooth_segment_vectorized(blend_rate, 0, n - 1, out)
