"""
utils/choreography.py
Choreography Doctrine constants, driver-mute proxy, synthetic stimulus runner,
and response metrics (see docs/contracts/mode_contract.md Law 7: One Lead Timescale).
"""
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
import math
import numpy as np

# The four audio drivers a mode may declare as LEAD or SECONDARY.
DRIVERS: Tuple[str, ...] = ("beat", "level", "spectrum", "transient")

# All five mute channels supported by DriverMuteProxy and Mode Studio ("macro" is a mute channel only).
MUTE_CHANNELS: Tuple[str, ...] = ("beat", "level", "spectrum", "transient", "macro")

NEUTRAL_MOOD_MODIFIERS: np.ndarray = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)
NEUTRAL_MOOD_MODIFIERS.flags.writeable = False


class _ContextMuteProxy:
    """Wraps listener.context (`MusicalContextEngine`) to substitute muted driver signals."""

    def __init__(self, parent: "DriverMuteProxy") -> None:
        self._parent = parent

    @property
    def _ctx(self) -> Any:
        return getattr(self._parent._listener, "context", None)

    @property
    def beat_trust(self) -> float:
        if "beat" in self._parent._muted:
            return 1.0
        ctx = self._ctx
        return float(getattr(ctx, "beat_trust", getattr(self._parent._listener, "beat_trust", 0.0)))

    @property
    def salience(self) -> float:
        if "beat" in self._parent._muted:
            return 1.0
        ctx = self._ctx
        return float(getattr(ctx, "salience", getattr(self._parent._listener, "rhythm_salience", 0.0)))

    @property
    def is_locked(self) -> bool:
        if "beat" in self._parent._muted:
            return True
        ctx = self._ctx
        return bool(getattr(ctx, "is_locked", False))

    @property
    def energy(self) -> float:
        if "level" in self._parent._muted:
            return self._parent._mean_energy
        ctx = self._ctx
        return float(getattr(ctx, "energy", getattr(self._parent._listener, "asserved_total_power", 0.0)))

    @property
    def power(self) -> float:
        if "level" in self._parent._muted:
            return self._parent._mean_power
        ctx = self._ctx
        return float(getattr(ctx, "power", getattr(self._parent._listener, "asserved_total_power", 0.0)))

    @property
    def spectral_tilt(self) -> float:
        if "spectrum" in self._parent._muted:
            return self._parent._mean_tilt
        ctx = self._ctx
        return float(getattr(ctx, "spectral_tilt", 0.0))

    @property
    def vertical_center(self) -> float:
        if "spectrum" in self._parent._muted:
            return self._parent._mean_vcenter
        ctx = self._ctx
        return float(getattr(ctx, "vertical_center", 0.5))

    @property
    def is_real_beat(self) -> bool:
        if "transient" in self._parent._muted:
            return False
        ctx = self._ctx
        return bool(getattr(ctx, "is_real_beat", getattr(self._parent._listener, "is_real_beat", False)))

    @property
    def is_drop_impact(self) -> bool:
        if "transient" in self._parent._muted:
            return False
        ctx = self._ctx
        return bool(getattr(ctx, "is_drop_impact", False))

    @property
    def is_syncopated(self) -> bool:
        if "transient" in self._parent._muted:
            return False
        ctx = self._ctx
        return bool(getattr(ctx, "is_syncopated", False))

    @property
    def tension(self) -> float:
        if "macro" in self._parent._muted:
            return 0.0
        ctx = self._ctx
        return float(getattr(ctx, "tension", 0.0))

    @property
    def drop_progress(self) -> float:
        if "macro" in self._parent._muted:
            return 0.0
        ctx = self._ctx
        return float(getattr(ctx, "drop_progress", 0.0))

    def __getattr__(self, name: str) -> Any:
        ctx = self._ctx
        if ctx is None:
            raise AttributeError(name)
        return getattr(ctx, name)

    def __dir__(self) -> List[str]:
        ctx = self._ctx
        base = set(super().__dir__())
        if ctx is not None:
            base.update(dir(ctx))
        return sorted(base)


class DriverMuteProxy:
    """
    Wraps a `Listener` (and its `.context`) to selectively mute any of the 4 audio drivers
    (`beat`, `level`, `spectrum`, `transient`) plus the `macro` mute channel.

    Shared between automated choreography stimulus tests and `tools/mode_studio.py`.
    """

    def __init__(self, listener: Any, initial_mutes: Iterable[str] = ()) -> None:
        self._listener = listener
        self._muted: Set[str] = set()
        self._ctx_proxy = _ContextMuteProxy(self)

        nb_bands = int(getattr(listener, "nb_of_fft_band", 8)) if listener is not None else 8
        self._nb_bands: int = max(1, nb_bands)
        # Neutral mid-decay phase where (1 - phase) ** 2.2 equals its cycle mean (~0.35)
        self._frozen_beat_phase: float = 0.38
        self._frozen_beat_count: int = 0
        self._mean_energy: float = 0.50
        self._mean_power: float = 0.50
        self._mean_tilt: float = 0.0
        self._mean_vcenter: float = 0.50
        self._mean_bands: np.ndarray = np.full(self._nb_bands, 0.35, dtype=np.float64)
        self._mean_proportion: np.ndarray = np.full(self._nb_bands, 1.0 / self._nb_bands, dtype=np.float64)
        self._zero_flux: np.ndarray = np.zeros(self._nb_bands, dtype=np.float64)
        self._has_observed: bool = False

        for ch in initial_mutes:
            self.set_muted(ch, True)

    def _ensure_band_buffers(self, n: int) -> None:
        if n > 0 and n != self._nb_bands:
            self._nb_bands = n
            self._mean_bands = np.full(n, 0.35, dtype=np.float64)
            self._mean_proportion = np.full(n, 1.0 / n, dtype=np.float64)
            self._zero_flux = np.zeros(n, dtype=np.float64)

    def observe(self, alpha: float = 0.05) -> None:
        """Update running means from the live underlying listener (call once per frame)."""
        listener = self._listener
        if listener is None:
            return
        ctx = getattr(listener, "context", None)

        if "beat" not in self._muted:
            self._frozen_beat_count = int(getattr(listener, "beat_count", self._frozen_beat_count))

        raw_power = float(getattr(listener, "asserved_total_power", 0.5))
        raw_energy = float(getattr(ctx, "energy", raw_power)) if ctx is not None else raw_power
        raw_tilt = float(getattr(ctx, "spectral_tilt", 0.0)) if ctx is not None else 0.0
        raw_vcenter = float(getattr(ctx, "vertical_center", 0.5)) if ctx is not None else 0.5

        bands = getattr(listener, "asserved_fft_band", None)
        if bands is not None and len(bands) > 0:
            self._ensure_band_buffers(len(bands))

        if not self._has_observed:
            self._mean_energy = raw_energy
            self._mean_power = raw_power
            self._mean_tilt = raw_tilt
            self._mean_vcenter = raw_vcenter
            if bands is not None and len(bands) == self._nb_bands:
                self._mean_bands[:] = bands
                tot = float(np.sum(bands))
                if tot > 1e-6:
                    np.divide(bands, tot, out=self._mean_proportion)
            self._has_observed = True
            return

        if "level" not in self._muted:
            self._mean_energy += alpha * (raw_energy - self._mean_energy)
            self._mean_power += alpha * (raw_power - self._mean_power)

        if "spectrum" not in self._muted:
            self._mean_tilt += alpha * (raw_tilt - self._mean_tilt)
            self._mean_vcenter += alpha * (raw_vcenter - self._mean_vcenter)
            if bands is not None and len(bands) == self._nb_bands:
                self._mean_bands += alpha * (np.asarray(bands, dtype=np.float64) - self._mean_bands)
                tot = float(np.sum(self._mean_bands))
                if tot > 1e-6:
                    np.divide(self._mean_bands, tot, out=self._mean_proportion)

    @property
    def muted(self) -> Tuple[str, ...]:
        """Return currently muted channels in canonical MUTE_CHANNELS order."""
        return tuple(ch for ch in MUTE_CHANNELS if ch in self._muted)

    def is_muted(self, channel: str) -> bool:
        return channel in self._muted

    def set_muted(self, channel: str, is_muted: bool = True) -> None:
        if channel not in MUTE_CHANNELS:
            raise ValueError(f"Unknown mute channel {channel!r}; expected one of {MUTE_CHANNELS}")
        if is_muted:
            self._muted.add(channel)
        else:
            self._muted.discard(channel)

    def toggle_mute(self, channel: str) -> bool:
        """Toggle a mute channel and return its new muted state."""
        new_state = channel not in self._muted
        self.set_muted(channel, new_state)
        return new_state

    def clear_mutes(self) -> None:
        self._muted.clear()

    def sync_macro_modifiers(self, mode_base_cls: Any, live_modifiers: np.ndarray) -> None:
        """Bind neutral (1, 1, 1, 0) mood modifiers when 'macro' is muted, else live modifiers."""
        if "macro" in self._muted:
            mode_base_cls.bind_mood_modifiers(NEUTRAL_MOOD_MODIFIERS)
        else:
            mode_base_cls.bind_mood_modifiers(live_modifiers)

    def format_hud_line(self, mode: Any) -> str:
        """Format the compact choreography status line for Mode Studio HUD."""
        lead = getattr(mode, "LEAD", "") or "undeclared"
        sec_tuple = getattr(mode, "SECONDARY", ())
        sec = sec_tuple[0] if sec_tuple else "none"
        muted_list = ", ".join(self.muted) if self._muted else "none"
        return f"LEAD: {lead} · SECONDARY: {sec} · muted: [{muted_list}]"

    # --- Proxied Listener properties ---

    @property
    def context(self) -> Optional[_ContextMuteProxy]:
        if getattr(self._listener, "context", None) is None:
            return None
        return self._ctx_proxy

    @property
    def beat_phase(self) -> float:
        if "beat" in self._muted:
            return self._frozen_beat_phase
        return float(getattr(self._listener, "beat_phase", 0.0))

    @property
    def standalone_phase(self) -> float:
        return self.beat_phase

    @property
    def beat_count(self) -> int:
        if "beat" in self._muted:
            return self._frozen_beat_count
        return int(getattr(self._listener, "beat_count", 0))

    @property
    def beat_trust(self) -> float:
        if "beat" in self._muted:
            return 1.0
        return float(getattr(self._listener, "beat_trust", 0.0))

    @property
    def beat_confidence(self) -> float:
        if "beat" in self._muted:
            return 1.0
        return float(getattr(self._listener, "beat_confidence", getattr(self._listener, "beat_trust", 0.0)))

    @property
    def rhythm_salience(self) -> float:
        if "beat" in self._muted:
            return 1.0
        return float(getattr(self._listener, "rhythm_salience", 0.0))

    @property
    def asserved_total_power(self) -> float:
        if "level" in self._muted:
            return self._mean_power
        return float(getattr(self._listener, "asserved_total_power", 0.0))

    @property
    def smoothed_total_power(self) -> float:
        if "level" in self._muted:
            return self._mean_power
        return float(getattr(self._listener, "smoothed_total_power", 0.0))

    @property
    def live_asserved_total_power(self) -> float:
        if "level" in self._muted:
            return self._mean_power
        return float(getattr(self._listener, "live_asserved_total_power", 0.0))

    @property
    def asserved_fft_band(self) -> np.ndarray:
        real = getattr(self._listener, "asserved_fft_band", None)
        if real is not None:
            self._ensure_band_buffers(len(real))
        if "spectrum" in self._muted:
            return self._mean_bands
        return real if real is not None else self._mean_bands

    @property
    def _delayed_asserved_fft_band(self) -> np.ndarray:
        return self.asserved_fft_band

    @property
    def smoothed_fft_band_values(self) -> np.ndarray:
        if "spectrum" in self._muted:
            return self._mean_bands
        real = getattr(self._listener, "smoothed_fft_band_values", None)
        return real if real is not None else self.asserved_fft_band

    @property
    def fft_band_values(self) -> np.ndarray:
        if "spectrum" in self._muted:
            return self._mean_bands
        real = getattr(self._listener, "fft_band_values", None)
        return real if real is not None else self.asserved_fft_band

    @property
    def band_proportion(self) -> np.ndarray:
        real = getattr(self._listener, "band_proportion", None)
        if real is not None:
            self._ensure_band_buffers(len(real))
        if "spectrum" in self._muted:
            return self._mean_proportion
        if real is not None:
            return real
        bands = self.asserved_fft_band
        tot = float(np.sum(bands))
        if tot > 1e-6:
            return np.asarray(bands, dtype=np.float64) / tot
        return self._mean_proportion

    @property
    def is_beat(self) -> bool:
        if "transient" in self._muted:
            return False
        return bool(getattr(self._listener, "is_beat", False))

    @property
    def is_real_beat(self) -> bool:
        if "transient" in self._muted:
            return False
        return bool(getattr(self._listener, "is_real_beat", False))

    @property
    def band_flux(self) -> np.ndarray:
        real = getattr(self._listener, "band_flux", None)
        if real is not None:
            self._ensure_band_buffers(len(real))
        if "transient" in self._muted:
            return self._zero_flux
        return real if real is not None else self._zero_flux

    def __getattr__(self, name: str) -> Any:
        return getattr(self._listener, name)

    def __dir__(self) -> List[str]:
        base = set(super().__dir__())
        if self._listener is not None:
            base.update(dir(self._listener))
        return sorted(base)


def compute_response_metrics(frames: np.ndarray) -> Tuple[float, float]:
    """
    Compute (R_std, R_diff) over a (T, nb_of_leds, 3) frame history.
    - R_std: mean per-LED temporal standard deviation (amplitude budget metric).
    - R_diff: mean per-LED frame-to-frame absolute delta (velocity / busyness indicator).
    """
    if frames.ndim != 3 or frames.shape[0] < 2:
        return 0.0, 0.0
    f64 = frames.astype(np.float64)
    r_std = float(np.mean(np.std(f64, axis=0)))
    r_diff = float(np.mean(np.abs(np.diff(f64, axis=0))))
    return r_std, r_diff


class _SyntheticContext:
    def __init__(self) -> None:
        self.is_silent: bool = False
        self.energy: float = 0.5
        self.power: float = 0.5
        self.tension: float = 0.2
        self.beat_trust: float = 0.90
        self.salience: float = 0.85
        self.is_locked: bool = True
        self.is_real_beat: bool = False
        self.is_syncopated: bool = False
        self.is_drop_impact: bool = False
        self.is_drop_imminent: bool = False
        self.is_structural_cut: bool = False
        self.drop_progress: float = 0.0
        self.drop_countdown: float = 0.0
        self.scene: str = "GROOVE"
        self.spectral_tilt: float = 0.0
        self.vertical_center: float = 0.5


class _SyntheticListener:
    def __init__(self, nb_bands: int = 8) -> None:
        self.dt: float = 1.0 / 60.0
        self.fps_ratio: float = 1.0
        self.bpm: float = 124.0
        self.beat_phase: float = 0.0
        self.beat_count: int = 0
        self.is_beat: bool = False
        self.is_real_beat: bool = False
        self.beat_confidence: float = 0.90
        self.beat_trust: float = 0.90
        self.rhythm_salience: float = 0.85
        self.live_rhythm_salience: float = 0.85
        self.asserved_total_power: float = 0.5
        self.smoothed_total_power: float = 0.5
        self.live_asserved_total_power: float = 0.5
        self.asserved_novelty: float = 0.2
        self.nb_of_fft_band: int = nb_bands
        self.asserved_fft_band: np.ndarray = np.full(nb_bands, 0.35, dtype=np.float64)
        self._delayed_asserved_fft_band: np.ndarray = self.asserved_fft_band.copy()
        self.smoothed_fft_band_values: np.ndarray = self.asserved_fft_band.copy()
        self.fft_band_values: np.ndarray = self.asserved_fft_band.copy()
        self.band_proportion: np.ndarray = np.full(nb_bands, 1.0 / nb_bands, dtype=np.float64)
        self.band_flux: np.ndarray = np.zeros(nb_bands, dtype=np.float64)
        self.beat_tag: str = "Bass/Kick"
        self.is_song_change: bool = False
        self.is_verse_chorus_change: bool = False
        self.context: _SyntheticContext = _SyntheticContext()


def step_synthetic_music(listener: _SyntheticListener, frame_idx: int, live_modifiers: np.ndarray) -> None:
    """
    Advance the deterministic synthetic music clip by one 60 Hz frame.
    Simultaneously exercises beat, level, spectrum, transient, and macro channels
    with non-harmonic frequencies so their temporal contributions are orthogonal.
    """
    dt = listener.dt
    t = frame_idx * dt
    ctx = listener.context
    nb = listener.nb_of_fft_band

    # 1. Beat envelope (124 BPM = 2.0667 Hz)
    prev_phase = listener.beat_phase
    listener.beat_phase = (t * (listener.bpm / 60.0)) % 1.0
    wrapped = frame_idx > 0 and listener.beat_phase < prev_phase
    if wrapped:
        listener.beat_count += 1

    # 2. Level swell (slow 0.55 Hz + 1.17 Hz envelope in [0.12, 0.94])
    lvl = 0.53 + 0.30 * math.sin(2.0 * math.pi * 0.55 * t) + 0.11 * math.cos(2.0 * math.pi * 1.17 * t)
    lvl = max(0.08, min(0.98, lvl))
    listener.asserved_total_power = lvl
    listener.smoothed_total_power = lvl
    listener.live_asserved_total_power = lvl
    ctx.energy = lvl
    ctx.power = lvl

    # 3. Spectrum movement (traveling spectral peak at 0.83 Hz)
    center_pos = 0.50 + 0.38 * math.sin(2.0 * math.pi * 0.83 * t)
    for b in range(nb):
        b_norm = b / max(1.0, float(nb - 1))
        dist = b_norm - center_pos
        val = 0.10 + 0.80 * math.exp(-(dist * dist) / 0.08)
        listener.asserved_fft_band[b] = val
    listener._delayed_asserved_fft_band[:] = listener.asserved_fft_band
    listener.smoothed_fft_band_values[:] = listener.asserved_fft_band
    listener.fft_band_values[:] = listener.asserved_fft_band
    tot_b = float(np.sum(listener.asserved_fft_band))
    if tot_b > 1e-6:
        listener.band_proportion[:] = listener.asserved_fft_band / tot_b
    half = nb // 2
    bass_sum = float(np.sum(listener.asserved_fft_band[:half]))
    high_sum = float(np.sum(listener.asserved_fft_band[half:]))
    ctx.spectral_tilt = (high_sum - bass_sum) / max(1e-6, high_sum + bass_sum)
    ctx.vertical_center = float(
        np.sum(np.arange(nb, dtype=np.float64) * listener.asserved_fft_band) / max(1e-6, (nb - 1) * tot_b)
    )

    # 4. Transients (1-frame beat hits, spectral flux bursts, and periodic drop_hit)
    listener.is_beat = wrapped
    listener.is_real_beat = wrapped
    ctx.is_real_beat = wrapped
    ctx.is_drop_impact = (frame_idx in (90, 210))
    tags = ("Bass/Kick", "Snare/Mid", "Hi-hat/Cymbal")
    listener.beat_tag = tags[listener.beat_count % 3]
    listener.band_flux.fill(0.0)
    if wrapped or (frame_idx % 19 == 0):
        active_b = (frame_idx // 19 + listener.beat_count) % nb
        listener.band_flux[active_b] = 28.0
        listener.band_flux[0] = max(listener.band_flux[0], 0.85 if wrapped else 0.45)

    # 5. Macro modifiers & tension
    ctx.tension = 0.45 + 0.35 * math.sin(2.0 * math.pi * 0.31 * t)
    ctx.drop_progress = max(0.0, 1.0 - ((frame_idx - 90) / 45.0)) if 90 <= frame_idx < 135 else 0.0
    live_modifiers[0] = 1.0 + 0.18 * math.sin(2.0 * math.pi * 0.25 * t)  # mood_pace
    live_modifiers[1] = 1.0 + 0.15 * math.cos(2.0 * math.pi * 0.25 * t)  # mood_sharpness
    live_modifiers[2] = 1.0 - 0.10 * math.sin(2.0 * math.pi * 0.25 * t)  # mood_trail
    live_modifiers[3] = 0.12 + 0.10 * math.sin(2.0 * math.pi * 0.35 * t)  # mood_accent


def run_mode_under_mutes(
    mode_cls: Any,
    muted_channels: Sequence[str] = (),
    num_leds: int = 60,
    warmup_frames: int = 60,
    eval_frames: int = 240,
) -> Tuple[float, float]:
    """Run `mode_cls` on the deterministic synthetic music clip under `muted_channels` and return `(R_std, R_diff)`."""
    import random
    import modes.Mode as BaseModeMod

    random.seed(42)
    np.random.seed(42)

    listener = _SyntheticListener(nb_bands=8)
    proxy = DriverMuteProxy(listener)
    live_modifiers = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)

    # Pre-seed running means over 60 unmuted frames so frozen values are true clip means
    for f in range(60):
        step_synthetic_music(listener, f, live_modifiers)
        proxy.observe(alpha=0.10)

    for ch in muted_channels:
        proxy.set_muted(ch, True)

    rgb_list = np.zeros((num_leds, 3), dtype=np.int32)
    indexes = list(range(num_leds))
    mode = mode_cls(mode_cls.__name__, "test_segment", proxy, None, indexes, rgb_list, {})

    recorded = np.zeros((eval_frames, num_leds, 3), dtype=np.int32)
    total_frames = warmup_frames + eval_frames
    try:
        for f in range(total_frames):
            step_synthetic_music(listener, f, live_modifiers)
            proxy.observe(alpha=0.05)
            proxy.sync_macro_modifiers(BaseModeMod.Mode, live_modifiers)
            mode.run()
            if f >= warmup_frames:
                recorded[f - warmup_frames] = mode.rgb_list
    finally:
        BaseModeMod.Mode.reset_mood_colors()

    return compute_response_metrics(recorded)


def measure_mode_choreography(
    mode_cls: Any,
    num_leds: int = 60,
    warmup_frames: int = 60,
    eval_frames: int = 240,
) -> Dict[str, Any]:
    """
    Evaluate a mode across `full`, `mute_lead`, `mute_sec`, `mute_all`, and all 4 individual driver mutes.
    Returns a dictionary of R_std, R_diff, and ablation contributions `R_std(full) - R_std(mute_d)`.
    """
    lead = getattr(mode_cls, "LEAD", "")
    sec_tuple = getattr(mode_cls, "SECONDARY", ())
    sec = sec_tuple[0] if sec_tuple else None

    r_std_full, r_diff_full = run_mode_under_mutes(mode_cls, (), num_leds, warmup_frames, eval_frames)
    by_driver: Dict[str, Tuple[float, float]] = {}
    for drv in DRIVERS:
        by_driver[drv] = run_mode_under_mutes(mode_cls, (drv,), num_leds, warmup_frames, eval_frames)

    r_std_mute_lead, r_diff_mute_lead = by_driver.get(lead, (r_std_full, r_diff_full))
    if sec is not None:
        r_std_mute_sec, r_diff_mute_sec = by_driver[sec]
    else:
        r_std_mute_sec, r_diff_mute_sec = r_std_full, r_diff_full

    r_std_mute_all, r_diff_mute_all = run_mode_under_mutes(
        mode_cls, MUTE_CHANNELS, num_leds, warmup_frames, eval_frames
    )

    contributions = {drv: r_std_full - by_driver[drv][0] for drv in DRIVERS}
    lead_contrib = contributions.get(lead, 0.0)
    sec_contrib = contributions.get(sec, 0.0) if sec is not None else 0.0

    return {
        "mode": mode_cls.__name__,
        "lead": lead,
        "secondary": sec or "none",
        "r_std_full": r_std_full,
        "r_diff_full": r_diff_full,
        "r_std_mute_lead": r_std_mute_lead,
        "r_diff_mute_lead": r_diff_mute_lead,
        "r_std_mute_sec": r_std_mute_sec,
        "r_diff_mute_sec": r_diff_mute_sec,
        "r_std_mute_all": r_std_mute_all,
        "r_diff_mute_all": r_diff_mute_all,
        "lead_contrib": lead_contrib,
        "sec_contrib": sec_contrib,
        "lead_share": (lead_contrib / r_std_full) if r_std_full > 1e-6 else 0.0,
        "sec_retained": (r_std_mute_sec / r_std_full) if r_std_full > 1e-6 else 1.0,
        "contributions": contributions,
    }


def measure_all_registered_modes(
    num_leds: int = 60,
    warmup_frames: int = 60,
    eval_frames: int = 240,
) -> List[Dict[str, Any]]:
    """Measure all modes registered in `config/modes.json` in canonical catalog order."""
    import importlib
    import json
    import os

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    modes_json = os.path.join(repo_root, "config", "modes.json")
    with open(modes_json, "r", encoding="utf-8") as f:
        entries = json.load(f).get("standard_modes", [])

    results: List[Dict[str, Any]] = []
    for entry in entries:
        mod = importlib.import_module(f"modes.{entry['module']}")
        cls = getattr(mod, entry["class"])
        results.append(measure_mode_choreography(cls, num_leds, warmup_frames, eval_frames))
    return results


def format_measurement_report(results: Sequence[Dict[str, Any]]) -> str:
    """Format the 13 x 4 conditions matrix and per-driver ablation table."""
    lines: List[str] = []
    header = (
        f"{'Mode':<28} {'Lead':<10} {'Sec':<10} "
        f"{'R_std(full)':>11} {'R_std(-lead)':>12} {'R_std(-sec)':>11} {'R_std(-all)':>11} "
        f"{'d(lead)':>9} {'d(sec)':>9} {'R_diff':>8}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for r in results:
        lines.append(
            f"{r['mode']:<28} {r['lead']:<10} {r['secondary']:<10} "
            f"{r['r_std_full']:11.2f} {r['r_std_mute_lead']:12.2f} {r['r_std_mute_sec']:11.2f} {r['r_std_mute_all']:11.2f} "
            f"{r['lead_contrib']:+9.2f} {r['sec_contrib']:+9.2f} {r['r_diff_full']:8.2f}"
        )
    lines.append("")
    ablation_hdr = (
        f"{'Mode':<28} {'Lead':<10} {'d(beat)':>10} {'d(level)':>10} "
        f"{'d(spectrum)':>12} {'d(transient)':>13}"
    )
    lines.append(ablation_hdr)
    lines.append("-" * len(ablation_hdr))
    for r in results:
        c = r["contributions"]
        lines.append(
            f"{r['mode']:<28} {r['lead']:<10} {c['beat']:+10.2f} {c['level']:+10.2f} "
            f"{c['spectrum']:+12.2f} {c['transient']:+13.2f}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_measurement_report(measure_all_registered_modes()))

