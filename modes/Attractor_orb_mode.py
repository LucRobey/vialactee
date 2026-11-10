"""
Attractor Orb Mode (Global Mode)
Orchestrates all 11 chandelier segments as a unified 2D room-space gravitational field
around a roaming Lissajous plasma sphere and counter-orbiting satellite orb:
- Lead (level): Drives the 2D orb's physical radius, gravitational field reach, and core
  supernova brightness across the 432 x 246 room.
- Secondary (spectrum): Steers the orb's 2D vertical altitude via vertical_center and
  modulates the outer spectral corona ring via spectral_tilt and FFT bands.
- Macro: Mood palette aura, highlight core, pace, and phosphor trail persistence.
Zero runtime heap allocations (AXIOM-01, AXIOM-02).
"""
from typing import Any, Dict, List, Optional, Sequence
import math
import numpy as np
import modes.Mode as Mode
from utils.global_mode import SegmentSpatialProfile


class Attractor_orb_mode(Mode.Mode):
    """Global 2D roaming Lissajous plasma sphere and gravitational field across the chandelier.

    Lead: level (2D orb radius, gravitational field reach, and core brightness). Secondary: spectrum (vertical_center altitude steer and outer corona shimmer). Macro: palette aura, mood_pace orbit drift, mood_trail phosphor decay.
    """
    IS_GLOBAL: bool = True
    LEAD: str = "level"
    SECONDARY: tuple = ("spectrum",)

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "orb_size",
                "label": "Orb Field Radius",
                "control": "slider",
                "valueType": "number",
                "min": 0.4,
                "max": 2.0,
                "step": 0.05,
                "default": 1.0,
                "attr": "orb_size",
            },
            {
                "key": "orbit_speed",
                "label": "Lissajous Orbit Speed",
                "control": "slider",
                "valueType": "number",
                "min": 0.2,
                "max": 2.5,
                "step": 0.05,
                "default": 1.0,
                "attr": "orbit_speed",
            },
            {
                "key": "core_halo",
                "label": "Core & Corona Halo",
                "control": "slider",
                "valueType": "number",
                "min": 0.3,
                "max": 2.0,
                "step": 0.05,
                "default": 1.0,
                "attr": "core_halo",
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

        self.orb_size: float = float(infos.get("orb_size", 1.0))
        self.orbit_speed: float = float(infos.get("orbit_speed", 1.0))
        self.core_halo: float = float(infos.get("core_halo", 1.0))

        self.spatial = SegmentSpatialProfile(segment_name, self.nb_of_leds)

        # Persistent scalar kinetic state (zero heap allocations)
        self.orbit_phase: float = 0.35
        self.level_env: float = 0.35
        self.altitude_env: float = 0.50
        self.corona_env: float = 0.35

        # Pre-allocated 1D & 2D vector buffers of size n (AXIOM-02)
        n = max(1, self.nb_of_leds)
        self.target_rgb: np.ndarray = np.zeros((n, 3), dtype=np.float64)
        self.scratch_rgb: np.ndarray = np.zeros((n, 3), dtype=np.float64)
        self.dx_buf: np.ndarray = np.zeros(n, dtype=np.float64)
        self.dy_buf: np.ndarray = np.zeros(n, dtype=np.float64)
        self.d2_buf: np.ndarray = np.zeros(n, dtype=np.float64)
        self.sat_d2_buf: np.ndarray = np.zeros(n, dtype=np.float64)
        self.aura_buf: np.ndarray = np.zeros(n, dtype=np.float64)
        self.core_buf: np.ndarray = np.zeros(n, dtype=np.float64)
        self.corona_buf: np.ndarray = np.zeros(n, dtype=np.float64)
        self.lut_t: np.ndarray = np.zeros(n, dtype=np.float64)
        self.lut_rgb: np.ndarray = np.zeros((n, 3), dtype=np.int32)
        self.core_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.corona_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind physical segment role, tags, and 2D coordinates from Segment."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)

    def _extract_spectral_features(self) -> tuple:
        """Return (bass_energy, treble_energy, spectral_spread) across 8 or 16 FFT bands."""
        bands = getattr(self.listener, "asserved_fft_band", None)
        if bands is None or len(bands) == 0:
            return 0.35, 0.35, 0.35

        nb = len(bands)
        q1 = max(1, nb // 4)
        q3 = max(q1 + 1, (3 * nb) // 4)

        bass_sum = 0.0
        for i in range(q1):
            bass_sum += float(bands[i])
        bass = bass_sum / float(q1)

        treble_sum = 0.0
        n_treb = max(1, nb - q3)
        for i in range(q3, nb):
            treble_sum += float(bands[i])
        treble = treble_sum / float(n_treb)

        mid_idx = nb // 2
        mid = float(bands[mid_idx])
        spread = abs(treble - bass) + 0.5 * abs(mid - 0.5 * (bass + treble))
        return bass, treble, min(1.0, spread)

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
        energy = float(
            ctx.energy
            if ctx is not None
            else getattr(self.listener, "asserved_total_power", 0.0)
        )
        tension = float(ctx.tension if ctx is not None else 0.0)
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)

        orb_size = max(0.25, float(self.orb_size))
        orbit_speed = max(0.1, float(self.orbit_speed))
        core_halo = max(0.1, float(self.core_halo))

        # 1. Lead (level): smooth energy envelope + quadratic contrast swell (~75% of variance)
        self.level_env += self.alpha(18.0) * (energy - self.level_env)
        eff_level = 0.65 * energy + 0.35 * self.level_env
        macro_boost = 1.0 + 0.15 * tension + 0.18 * self.drop_decay
        clamped_level = max(0.0, min(1.15, eff_level * macro_boost))
        level_swell = clamped_level * clamped_level

        # 2. Secondary (spectrum): altitude steer via vertical_center & corona shimmer
        bass_e, treble_e, spec_spread = self._extract_spectral_features()
        self.altitude_env += self.alpha(16.0) * (v_center - self.altitude_env)
        spec_shimmer = min(1.0, 0.75 * treble_e + 0.25 * spec_spread)
        self.corona_env += self.alpha(16.0) * (spec_shimmer - self.corona_env)

        # 3. 2D Lissajous Figure-8 Trajectory across the 432 x 246 room
        # Orbit advances smoothly with mood_pace and orbit_speed
        omega = dt * 0.58 * orbit_speed * self.mood_pace * (1.0 + 0.15 * tension)
        self.orbit_phase = (self.orbit_phase + omega) % (2.0 * math.pi)

        # Level slightly expands the Lissajous excursion span while spectrum steers vertical altitude
        excursion = 0.22 + 0.16 * clamped_level
        alt_shift = (self.altitude_env - 0.50) * 0.68

        orb_x = 0.50 + excursion * math.sin(self.orbit_phase)
        orb_y = max(
            0.04,
            min(0.96, 0.50 + excursion * 0.82 * math.sin(2.0 * self.orbit_phase) - alt_shift),
        )

        # Counter-orbiting satellite orb in conjugate figure-8 phase
        sat_x = 0.50 - excursion * 0.88 * math.cos(self.orbit_phase + 0.85)
        sat_y = max(
            0.04,
            min(0.96, 0.50 - excursion * 0.78 * math.sin(2.0 * self.orbit_phase + 0.60) + 0.85 * alt_shift),
        )

        # 4. 2D Squared Distance computation in place for every LED on this segment
        x_norm = self.spatial.x_norm[:n]
        y_norm = self.spatial.y_norm[:n]
        dx = self.dx_buf[:n]
        dy = self.dy_buf[:n]
        d2 = self.d2_buf[:n]
        sat_d2 = self.sat_d2_buf[:n]

        np.subtract(x_norm, orb_x, out=dx)
        np.square(dx, out=dx)
        np.subtract(y_norm, orb_y, out=dy)
        np.square(dy, out=dy)
        np.add(dx, dy, out=d2)

        np.subtract(x_norm, sat_x, out=dx)
        np.square(dx, out=dx)
        np.subtract(y_norm, sat_y, out=dy)
        np.square(dy, out=dy)
        np.add(dx, dy, out=sat_d2)

        # 5. Lead-driven 2D Orb Radius & Supernova Brightness Envelope
        # When level swells, radius expands from a tight star into a room-spanning plasma sphere
        orb_radius = (0.09 + 0.58 * level_swell) * orb_size
        inv_2sigma2 = -1.0 / max(0.003, 2.0 * orb_radius * orb_radius)
        sat_radius = 0.78 * orb_radius
        inv_2sat_sigma2 = -1.0 / max(0.003, 2.0 * sat_radius * sat_radius)

        level_gain = (0.03 + 0.97 * level_swell) * self.transition_scale

        # Plasma aura Gaussian field: primary orb + counter-orbiting satellite
        aura = self.aura_buf[:n]
        np.multiply(d2, inv_2sigma2, out=aura)
        np.exp(aura, out=aura)

        np.multiply(sat_d2, inv_2sat_sigma2, out=dx)
        np.exp(dx, out=dx)
        np.multiply(dx, 0.72, out=dx)
        np.add(aura, dx, out=aura)
        np.clip(aura, 0.0, 1.0, out=aura)
        np.multiply(aura, level_gain, out=aura)

        # White-hot inner core (tighter Gaussian weighted by core_halo and level_gain)
        core = self.core_buf[:n]
        np.multiply(d2, inv_2sigma2 * 4.2, out=core)
        np.exp(core, out=core)
        np.multiply(sat_d2, inv_2sat_sigma2 * 4.2, out=dx)
        np.exp(dx, out=dx)
        np.multiply(dx, 0.55, out=dx)
        np.add(core, dx, out=core)
        core_gain = min(1.35, level_gain * core_halo * (0.75 + 0.25 * self.mood_accent))
        np.multiply(core, core_gain, out=core)
        np.clip(core, 0.0, 1.0, out=core)

        # 6. Secondary-driven Outer Spectral Corona Ring
        # Ring peaks around d2 == corona_r2 and shimmers with spectral energy & tilt
        corona = self.corona_buf[:n]
        corona_r2 = 0.55 * orb_radius * orb_radius
        inv_ring_w = -1.0 / max(0.002, 0.45 * orb_radius * orb_radius)
        np.subtract(d2, corona_r2, out=corona)
        np.abs(corona, out=corona)
        np.multiply(corona, inv_ring_w, out=corona)
        np.exp(corona, out=corona)

        # Add spectral ripple across room coordinates so spectrum adds fine corona texture
        np.multiply(x_norm, 7.5, out=dx)
        np.add(dx, self.altitude_env * 6.0 + tilt * 2.5, out=dx)
        np.cos(dx, out=dx)
        np.multiply(dx, 0.35, out=dx)
        np.add(dx, 0.65, out=dx)
        np.multiply(corona, dx, out=corona)

        corona_gain = (0.12 + 0.88 * level_gain) * (0.20 + 0.80 * self.corona_env) * (0.65 + 0.35 * core_halo)
        np.multiply(corona, min(1.0, corona_gain), out=corona)

        # 7. Palette gradient sampling across radial distance + spectral_tilt shift
        lt = self.lut_t[:n]
        tilt_shift = 0.22 * max(-1.0, min(1.0, tilt)) + 0.18 * (self.altitude_env - 0.5)
        np.multiply(d2, 1.8 / max(0.02, orb_radius * orb_radius), out=lt)
        np.add(lt, 0.15 + tilt_shift, out=lt)
        np.clip(lt, 0.0, 1.0, out=lt)
        lrgb = self.lut_rgb[:n]
        self.palette_sample(lt, lrgb)

        # 8. Assemble RGB frame in place (zero allocations)
        mood = self.mood_colors
        hi = self.highlight_color
        accent = self.mood_accent
        m1, m2 = mood[1], mood[2]
        treb_mix = min(1.0, max(0.0, 0.5 + 0.5 * tilt))
        for c in range(3):
            self.core_color[c] = (1.0 - accent) * float(hi[c]) + accent * 255.0
            self.corona_color[c] = (
                (1.0 - treb_mix) * float(m1[c]) + treb_mix * float(m2[c])
            ) * 0.70 + 0.30 * float(hi[c])

        out = self.target_rgb[:n]
        scratch = self.scratch_rgb[:n]
        np.copyto(out, lrgb, casting="unsafe")
        np.multiply(out, aura[:, None], out=out)

        np.multiply(corona[:, None], self.corona_color, out=scratch)
        np.add(out, scratch, out=out)

        np.multiply(core[:, None], self.core_color, out=scratch)
        np.add(out, scratch, out=out)

        np.clip(out, 0.0, 255.0, out=out)
        blend_rate = self.alpha(16.0 / max(0.6, self.mood_trail))
        self.smooth_segment_vectorized(blend_rate, 0, n - 1, out)
