"""
utils/driver_mute.py
DriverMuteProxy and ContextMuteProxy wrapping Listener and MusicalContextEngine
to selectively mute any of the 4 audio drivers plus the macro mute channel.
"""
from typing import Any, Iterable, List, Optional, Set, Tuple
import numpy as np

from utils.choreography import MUTE_CHANNELS, NEUTRAL_MOOD_MODIFIERS


class ContextMuteProxy:
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
            return self._parent._mean_salience
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
        self._ctx_proxy = ContextMuteProxy(self)

        nb_bands = int(getattr(listener, "nb_of_fft_band", 8)) if listener is not None else 8
        self._nb_bands: int = max(1, nb_bands)
        # Neutral mid-decay phase where (1 - phase) ** 2.2 equals its cycle mean (~0.35)
        self._frozen_beat_phase: float = 0.38
        self._frozen_beat_count: int = 0
        self._mean_salience: float = 0.85
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

        raw_salience = (
            float(getattr(ctx, "salience", getattr(listener, "rhythm_salience", 0.85)))
            if ctx is not None
            else float(getattr(listener, "rhythm_salience", 0.85))
        )
        raw_power = float(getattr(listener, "asserved_total_power", 0.5))
        raw_energy = float(getattr(ctx, "energy", raw_power)) if ctx is not None else raw_power
        raw_tilt = float(getattr(ctx, "spectral_tilt", 0.0)) if ctx is not None else 0.0
        raw_vcenter = float(getattr(ctx, "vertical_center", 0.5)) if ctx is not None else 0.5

        bands = getattr(listener, "asserved_fft_band", None)
        if bands is not None and len(bands) > 0:
            self._ensure_band_buffers(len(bands))

        if not self._has_observed:
            self._mean_salience = raw_salience
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

        if "beat" not in self._muted:
            self._mean_salience += alpha * (raw_salience - self._mean_salience)

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

    # --- Proxied Listener properties ---

    @property
    def context(self) -> Optional[ContextMuteProxy]:
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
            return self._mean_salience
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
