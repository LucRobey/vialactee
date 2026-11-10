"""
Synaptic Grid Mode (Global Mode)
Tron Light-Cycles & Junction-Jumping Sparks routed across the exact physical 2D wiring
topology of the 11 chandelier segments:
- Vertical Pillars (v2, v3 -> v1, v4): High-velocity light-cycle packets launch from the floor
  and split at exact physical T-junctions onto horizontal bridges.
- Horizontal Bridges (h10, h11, h31, h32): 90-degree branch packets jump across pillars and
  ignite mid-pillar and dual-direction cascades on v1 and v4.
- High Canopy (h20 -> h30, v1 -> h00): Elevated packets sweep across the 432-column canopy wings.
- Junction Nodes: Localized highlight flares ignite at every physical segment intersection.
Zero runtime heap allocations (AXIOM-01, AXIOM-02).
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple
import math
import numpy as np
import modes.Mode as Mode
from utils.global_mode import SegmentSpatialProfile

# Segment topological routing table:
#   routes: tuple of (u_start, u_end, tau_start, tau_end, weight)
#   junctions: tuple of (u_junc, tau_junc, weight)
_TOPOLOGY_TABLE: Dict[
    str,
    Tuple[
        Tuple[Tuple[float, float, float, float, float], ...],
        Tuple[Tuple[float, float, float], ...],
    ],
] = {
    "v2": (
        ((0.00, 1.00, 0.00, 1.00, 1.00),),
        ((0.00, 0.00, 0.90), (0.33, 0.33, 1.10), (1.00, 1.00, 1.20)),
    ),
    "h10": (((1.00, 0.00, 0.33, 0.83, 1.00),), ((1.00, 0.33, 1.10), (0.00, 0.83, 1.10))),
    "h11": (((1.00, 0.00, 1.00, 1.50, 1.00),), ((1.00, 1.00, 1.15), (0.00, 1.50, 1.15))),
    "v1": (
        ((0.00, 1.00, 0.83, 1.75, 1.00), (0.67, 1.00, 1.50, 1.75, 0.80)),
        ((0.00, 0.83, 1.10), (0.67, 1.50, 1.20), (1.00, 1.75, 1.20)),
    ),
    "h00": (
        ((1.00, 0.00, 1.75, 2.65, 1.00),),
        ((1.00, 1.75, 1.20), (0.50, 2.20, 0.90), (0.00, 2.65, 1.05)),
    ),
    "h20": (((0.00, 1.00, 1.00, 1.55, 1.00),), ((0.00, 1.00, 1.15), (1.00, 1.55, 1.10))),
    "h30": (((0.00, 1.00, 1.55, 1.95, 1.00),), ((0.00, 1.55, 1.10), (1.00, 1.95, 1.15))),
    "v3": (
        ((0.00, 1.00, 0.00, 1.00, 1.00),),
        ((0.00, 0.00, 0.90), (0.43, 0.43, 1.10), (0.93, 0.93, 1.10), (1.00, 1.00, 1.00)),
    ),
    "h31": (((0.00, 1.00, 0.43, 0.80, 1.00),), ((0.00, 0.43, 1.10), (1.00, 0.80, 1.15))),
    "h32": (((0.00, 1.00, 0.93, 1.30, 1.00),), ((0.00, 0.93, 1.10), (1.00, 1.30, 1.15))),
    "v4": (
        (
            (0.19, 1.00, 0.80, 1.65, 0.95),
            (0.19, 0.00, 0.80, 1.05, 0.90),
            (0.69, 1.00, 1.30, 1.65, 0.95),
            (0.69, 0.00, 1.30, 1.95, 0.90),
        ),
        ((0.19, 0.80, 1.20), (0.69, 1.30, 1.20), (1.00, 1.65, 1.05), (1.00, 1.95, 1.10)),
    ),
    "s2": (
        ((0.00, 1.00, 0.00, 1.00, 1.00),),
        ((0.00, 0.00, 0.95), (0.33, 0.33, 1.05), (0.67, 0.67, 1.05), (1.00, 1.00, 1.15)),
    ),
    "s3": (
        ((0.00, 1.00, 0.33, 1.33, 1.00),),
        ((0.00, 0.33, 1.10), (0.33, 0.66, 1.00), (0.67, 1.00, 1.05), (1.00, 1.33, 1.15)),
    ),
    "s1": (
        ((1.00, 0.00, 1.00, 2.00, 1.00),),
        ((1.00, 1.00, 1.15), (0.67, 1.33, 1.00), (0.33, 1.67, 1.00), (0.00, 2.00, 1.10)),
    ),
}

_COMPOSITE_TOPOLOGY: Tuple[
    Tuple[Tuple[float, float, float, float, float], ...],
    Tuple[Tuple[float, float, float], ...],
] = (
    (
        (0.00, 1.00, 0.00, 1.50, 0.95),
        (0.00, 0.33, 0.00, 0.50, 0.70),
        (0.33, 0.67, 0.50, 1.05, 0.70),
        (1.00, 0.67, 1.05, 1.65, 0.75),
    ),
    ((0.00, 0.00, 1.00), (0.33, 0.50, 1.15), (0.67, 1.05, 1.15), (1.00, 1.50, 1.10)),
)


class Synaptic_grid_mode(Mode.Mode):
    """Global topological light-cycle grid & junction-jumping sparks across all 11 segments.

    Lead: beat (phase-locked topological light-cycle cascades and junction flash envelope). Secondary: spectrum (per-band phosphor tail shimmer and chromatic shift). Macro: palette, cycle_speed via mood_pace, tail decay via mood_trail.
    """

    IS_GLOBAL: bool = True
    LEAD: str = "beat"
    SECONDARY: tuple = ("spectrum",)

    MAX_ROUTES: int = 4
    MAX_JUNCTIONS: int = 4
    NUM_CASCADES: int = 3
    CYCLE_PERIOD: float = 2.65

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "cycle_speed",
                "label": "Light-Cycle Velocity",
                "control": "slider",
                "valueType": "number",
                "min": 0.4,
                "max": 2.5,
                "step": 0.05,
                "default": 1.0,
                "attr": "cycle_speed",
            },
            {
                "key": "tail_length",
                "label": "Phosphor Tail Length",
                "control": "slider",
                "valueType": "number",
                "min": 0.3,
                "max": 2.5,
                "step": 0.05,
                "default": 1.0,
                "attr": "tail_length",
            },
            {
                "key": "junction_flare",
                "label": "Junction Spark Flare",
                "control": "slider",
                "valueType": "number",
                "min": 0.3,
                "max": 2.5,
                "step": 0.05,
                "default": 1.15,
                "attr": "junction_flare",
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

        self.cycle_speed: float = float(infos.get("synaptic_cycle_speed", 1.0))
        self.tail_length: float = float(infos.get("synaptic_tail_length", 1.0))
        self.junction_flare: float = float(infos.get("synaptic_junction_flare", 1.15))

        self.spatial = SegmentSpatialProfile(segment_name, self.nb_of_leds)

        # Persistent kinetic state (scalars only -> zero heap allocation)
        self.clock_tau: float = 0.0
        self.prev_phase: float = 0.0

        n = max(1, self.nb_of_leds)
        self.nb_bands: int = max(
            2, int(getattr(listener, "nb_of_fft_band", 16)) if listener is not None else 16
        )

        # Pre-allocated topological route and junction tables
        self.num_routes: int = 0
        self.route_s: np.ndarray = np.zeros((self.MAX_ROUTES, n), dtype=np.float64)
        self.route_mask: np.ndarray = np.zeros((self.MAX_ROUTES, n), dtype=np.float64)
        self.route_tau_start: np.ndarray = np.zeros(self.MAX_ROUTES, dtype=np.float64)
        self.route_inv_dur: np.ndarray = np.zeros(self.MAX_ROUTES, dtype=np.float64)
        self.route_weight: np.ndarray = np.zeros(self.MAX_ROUTES, dtype=np.float64)

        self.num_junctions: int = 0
        self.junc_spatial: np.ndarray = np.zeros((self.MAX_JUNCTIONS, n), dtype=np.float64)
        self.junc_tau: np.ndarray = np.zeros(self.MAX_JUNCTIONS, dtype=np.float64)
        self.junc_weight: np.ndarray = np.zeros(self.MAX_JUNCTIONS, dtype=np.float64)

        # Pre-allocated FFT spectrum interpolation buffers
        self.fft_bands: np.ndarray = np.zeros(self.nb_bands, dtype=np.float64)
        self.low_band_idx: np.ndarray = np.zeros(n, dtype=np.intp)
        self.high_band_idx: np.ndarray = np.zeros(n, dtype=np.intp)
        self.band_frac: np.ndarray = np.zeros(n, dtype=np.float64)
        self.spec_vec: np.ndarray = np.zeros(n, dtype=np.float64)

        # Pre-allocated per-frame vector scratch buffers
        self.target_rgb: np.ndarray = np.zeros((n, 3), dtype=np.float64)
        self.scratch_rgb: np.ndarray = np.zeros((n, 3), dtype=np.float64)
        self.tail_accum: np.ndarray = np.zeros(n, dtype=np.float64)
        self.head_accum: np.ndarray = np.zeros(n, dtype=np.float64)
        self.flare_accum: np.ndarray = np.zeros(n, dtype=np.float64)
        self.tail_2d: np.ndarray = self.tail_accum[:, None]
        self.head_2d: np.ndarray = self.head_accum[:, None]
        self.flare_2d: np.ndarray = self.flare_accum[:, None]
        self.head_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.flare_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.scratch_d: np.ndarray = np.zeros(n, dtype=np.float64)
        self.scratch_a: np.ndarray = np.zeros(n, dtype=np.float64)
        self.scratch_b: np.ndarray = np.zeros(n, dtype=np.float64)
        self.lut_t: np.ndarray = np.zeros(n, dtype=np.float64)
        self.lut_rgb: np.ndarray = np.zeros((n, 3), dtype=np.int32)

        self._rebuild_band_mapping(self.nb_bands)
        self._rebuild_topology()

    def _rebuild_band_mapping(self, nb: int) -> None:
        """Precompute per-LED linear interpolation indices into the FFT spectrum."""
        self.nb_bands = max(2, int(nb))
        if len(self.fft_bands) != self.nb_bands:
            self.fft_bands = np.zeros(self.nb_bands, dtype=np.float64)
        n = max(1, self.nb_of_leds)
        u = self.spatial.u[:n]
        span = float(self.nb_bands - 1)
        pos = np.clip(u * span, 0.0, span)
        self.low_band_idx[:n] = pos.astype(np.intp)
        self.high_band_idx[:n] = np.clip(self.low_band_idx[:n] + 1, 0, self.nb_bands - 1)
        self.band_frac[:n] = pos - self.low_band_idx[:n]

    def _rebuild_topology(self) -> None:
        """Precompute directed packet coordinate maps and junction Gaussian profiles in place."""
        n = max(1, self.nb_of_leds)
        u = self.spatial.u[:n]
        seg_id = self.spatial.seg_id

        if seg_id in _TOPOLOGY_TABLE:
            routes, junctions = _TOPOLOGY_TABLE[seg_id]
        elif self.spatial.role == "pillar":
            routes, junctions = _TOPOLOGY_TABLE["s2"]
        elif self.spatial.role == "bridge":
            routes, junctions = _TOPOLOGY_TABLE["s3"]
        elif self.spatial.role == "canopy":
            routes, junctions = _TOPOLOGY_TABLE["s1"]
        else:
            routes, junctions = _COMPOSITE_TOPOLOGY

        self.route_s.fill(0.0)
        self.route_mask.fill(0.0)
        self.num_routes = min(self.MAX_ROUTES, len(routes))
        for r in range(self.num_routes):
            u0, u1, t0, t1, w = routes[r]
            du = u1 - u0
            inv_du = 1.0 / du if abs(du) > 1e-6 else 1.0
            s_vec = (u - u0) * inv_du
            self.route_s[r, :n] = s_vec
            self.route_mask[r, :n] = w * ((s_vec >= -0.02) & (s_vec <= 1.02)).astype(np.float64)
            self.route_tau_start[r] = t0
            self.route_inv_dur[r] = 1.0 / max(0.05, t1 - t0)
            self.route_weight[r] = w

        self.junc_spatial.fill(0.0)
        self.num_junctions = min(self.MAX_JUNCTIONS, len(junctions))
        # Narrower Gaussian on long strips, wider on compact bridges so sparks span ~4-6 LEDs
        sigma_u = max(0.045, min(0.11, 3.2 / max(8.0, float(n))))
        inv_two_sigma_u_sq = -1.0 / (2.0 * sigma_u * sigma_u)
        for j in range(self.num_junctions):
            uj, tj, wj = junctions[j]
            dist = u - uj
            self.junc_spatial[j, :n] = np.exp((dist * dist) * inv_two_sigma_u_sq)
            self.junc_tau[j] = tj
            self.junc_weight[j] = wj

    def bind_segment_geometry(
        self,
        seg_id: Optional[str] = None,
        orientation: Optional[str] = None,
        tags: Sequence[str] = (),
        coords_array: Optional[np.ndarray] = None,
    ) -> None:
        """Bind physical segment role, tags, and 2D coordinates from Segment."""
        self.spatial.bind(seg_id, orientation, tags, coords_array)
        self._rebuild_topology()

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        if is_silent:
            self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
            return

        n = self.nb_of_leds
        dt = self.dt
        tension = float(ctx.tension if ctx is not None else 0.0)
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        v_center = float(ctx.vertical_center if ctx is not None else 0.5)
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        lock = self.rhythm_lock

        # 1. Read & interpolate FFT spectrum (Secondary driver: spectrum)
        bands = getattr(self.listener, "asserved_fft_band", None)
        if bands is not None and len(bands) >= 2:
            if len(bands) != self.nb_bands:
                self._rebuild_band_mapping(len(bands))
            self.fft_bands[:] = bands[: self.nb_bands]
        else:
            self.fft_bands.fill(0.35)

        spec_v = self.spec_vec[:n]
        sv_b = self.scratch_b[:n]
        np.take(self.fft_bands, self.low_band_idx[:n], out=spec_v)
        np.take(self.fft_bands, self.high_band_idx[:n], out=sv_b)
        np.subtract(sv_b, spec_v, out=sv_b)
        np.multiply(sv_b, self.band_frac[:n], out=sv_b)
        np.add(spec_v, sv_b, out=spec_v)
        spec_mean = float(np.mean(self.fft_bands))

        # 2. Advance global topological cascade clock tau (Lead driver: beat)
        phase_delta = (phase - self.prev_phase) % 1.0
        if phase_delta > 0.5:
            phase_delta = 0.0
        self.prev_phase = phase

        cycle_spd = max(0.2, float(self.cycle_speed))
        tail_len = max(0.2, float(self.tail_length))
        junc_flare = max(0.1, float(self.junction_flare))

        # Smooth confidence ramp: fully phase-locked for lock >= 0.45 (high_lock & groove_lock),
        # smoothly blending in continuous acoustic velocity when beat tracking loosens (loose_lock / unlocked).
        lock_weight = min(1.0, lock / 0.45)
        pace_mult = cycle_spd * self.mood_pace * (1.0 + 0.25 * tension + 0.15 * self.drop_decay)
        rhythmic_step = phase_delta * 1.25 * pace_mult
        acoustic_step = dt * 1.95 * pace_mult * (0.65 + 0.70 * spec_mean)
        step = lock_weight * rhythmic_step + (1.0 - lock_weight) * acoustic_step
        period = self.CYCLE_PERIOD
        self.clock_tau = (self.clock_tau + step) % period

        # Lead rhythmic envelope from beat_pulse
        pulse = self.beat_pulse(2.2)
        beat_drive = min(1.35, 0.48 + 0.62 * pulse + 0.20 * self.drop_decay)

        # 3. Accumulate Light-Cycle packets + phosphor tails across staggered cascades
        tail_acc = self.tail_accum[:n]
        head_acc = self.head_accum[:n]
        flare_acc = self.flare_accum[:n]
        tail_acc.fill(0.0)
        head_acc.fill(0.0)
        flare_acc.fill(0.0)

        sv_d = self.scratch_d[:n]
        sv_a = self.scratch_a[:n]

        lam_tail = max(0.08, (0.14 + 0.22 * tail_len) * self.mood_trail)
        inv_tail = 1.0 / lam_tail
        inv_front = 28.0
        max_p = 1.0 + 2.8 * lam_tail
        cascade_spacing = period / float(self.NUM_CASCADES)

        for r in range(self.num_routes):
            t_start = float(self.route_tau_start[r])
            inv_dur = float(self.route_inv_dur[r])
            r_s = self.route_s[r, :n]
            r_mask = self.route_mask[r, :n]

            for k in range(self.NUM_CASCADES):
                tau_k = (self.clock_tau + k * cascade_spacing) % period
                # Handle wrap-around near period boundary
                dtau = tau_k - t_start
                if dtau < -0.5 * period:
                    dtau += period
                p = dtau * inv_dur
                if p < -0.08 or p > max_p:
                    continue

                # Distance behind light-cycle head: d = p - s
                np.subtract(p, r_s, out=sv_d)
                # Asymmetric exponential profile via min(d * inv_front, -d * inv_tail)
                np.multiply(sv_d, inv_front, out=sv_a)
                np.multiply(sv_d, -inv_tail, out=sv_b)
                np.minimum(sv_a, sv_b, out=sv_a)
                np.clip(sv_a, -14.0, 0.0, out=sv_a)
                np.exp(sv_a, out=sv_a)
                np.multiply(sv_a, r_mask, out=sv_a)
                np.maximum(tail_acc, sv_a, out=tail_acc)

                # Razor-sharp light-cycle nose cone at d ≈ 0 (zero-exp triangle core)
                np.abs(sv_d, out=sv_b)
                np.multiply(sv_b, -15.0, out=sv_b)
                np.add(sv_b, 1.0, out=sv_b)
                np.clip(sv_b, 0.0, 1.0, out=sv_b)
                np.square(sv_b, out=sv_b)
                np.multiply(sv_b, r_mask, out=sv_b)
                np.maximum(head_acc, sv_b, out=head_acc)

        # 4. Accumulate localized Junction Flashes when any cascade crosses tau_j
        inv_two_sigma_tau_sq = -1.0 / (2.0 * (0.085 * 0.085))
        for j in range(self.num_junctions):
            tj = float(self.junc_tau[j])
            wj = float(self.junc_weight[j])
            j_amp = 0.0
            for k in range(self.NUM_CASCADES):
                tau_k = (self.clock_tau + k * cascade_spacing) % period
                dtau = abs(tau_k - tj)
                if dtau > 0.5 * period:
                    dtau = period - dtau
                if dtau < 0.24:
                    j_amp += math.exp((dtau * dtau) * inv_two_sigma_tau_sq)
            if j_amp > 1e-3:
                scale_j = min(1.4, j_amp * wj) * junc_flare * (0.55 + 0.45 * pulse)
                np.multiply(self.junc_spatial[j, :n], scale_j, out=sv_a)
                np.add(flare_acc, sv_a, out=flare_acc)

        # 5. Secondary (spectrum) modulation: phosphor tail shimmer + chromatic palette shift
        # Tail intensity is driven primarily by beat_drive (~75%) and modulated by squared spec_v (~20%)
        np.square(spec_v, out=sv_a)
        np.multiply(sv_a, 0.90, out=sv_b)
        np.add(sv_b, 0.45, out=sv_b)
        np.multiply(tail_acc, sv_b, out=tail_acc)
        np.multiply(tail_acc, beat_drive, out=tail_acc)

        # Synaptic conduit glow along the segment modulated by spectrum & beat_drive
        np.multiply(sv_a, 0.11 * (0.35 + 0.65 * beat_drive), out=sv_b)
        np.add(tail_acc, sv_b, out=tail_acc)
        np.clip(tail_acc, 0.0, 1.15, out=tail_acc)

        np.multiply(head_acc, 0.65 + 0.55 * pulse, out=head_acc)
        np.multiply(spec_v, 0.45, out=sv_b)
        np.add(sv_b, 0.72, out=sv_b)
        np.multiply(flare_acc, sv_b, out=flare_acc)
        np.clip(flare_acc, 0.0, 1.35, out=flare_acc)

        # Sample mood palette across strip altitude/u shifted by spectral_tilt & spec_v
        lt = self.lut_t[:n]
        tilt_shift = 0.20 * max(-1.0, min(1.0, tilt)) + 0.14 * (v_center - 0.5)
        np.multiply(self.spatial.u[:n], 0.45, out=lt)
        np.multiply(spec_v, 0.36, out=sv_a)
        np.add(lt, sv_a, out=lt)
        np.add(lt, 0.10 + tilt_shift, out=lt)
        np.clip(lt, 0.0, 1.0, out=lt)
        lrgb = self.lut_rgb[:n]
        self.palette_sample(lt, lrgb)

        # Compose final RGB in place: palette tail + highlight-tinted cycle head + junction spark flare
        out = self.target_rgb[:n]
        s_rgb = self.scratch_rgb[:n]
        hi = self.highlight_color
        mood = self.mood_colors
        m2 = mood[2]
        accent = self.mood_accent
        t_scale = self.transition_scale

        for c in range(3):
            hi_c = float(hi[c])
            self.head_color[c] = ((1.0 - accent) * hi_c + accent * 255.0) * t_scale
            self.flare_color[c] = (0.65 * hi_c + 0.20 * float(m2[c]) + 0.15 * 255.0) * t_scale

        np.multiply(tail_acc, t_scale, out=tail_acc)
        np.multiply(lrgb, self.tail_2d[:n], out=out)
        np.multiply(self.head_2d[:n], self.head_color, out=s_rgb)
        np.add(out, s_rgb, out=out)
        np.multiply(self.flare_2d[:n], self.flare_color, out=s_rgb)
        np.add(out, s_rgb, out=out)

        np.clip(out, 0.0, 255.0, out=out)
        blend_rate = self.alpha(20.0 / max(0.6, self.mood_trail))
        self.smooth_segment_vectorized(blend_rate, 0, n - 1, out)
