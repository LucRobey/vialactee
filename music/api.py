"""
music/api.py - THE DOOR of the sealed music analysis sector.

This is the only module that production code outside `music/` may import.

Rules (enforced by tests/governance/test_music_isolation.py and test_docs_parity.py):
- Nothing in `music/` imports project code outside `music/`.
- Production code outside `music/` imports only `music.api`.
- Every public signal on `Listener` and `MusicalContextEngine` belongs to
  exactly one trust set below and is documented in
  `docs/contracts/music_analyzer_contract.md`.
"""

from typing import Any, Dict, FrozenSet, Protocol, runtime_checkable
import numpy as np

from music.Listener import (
    Listener,
    ANALYZER_REGISTRY,
    DEFAULT_ANALYZER_MODEL,
    resolve_analyzer_class,
)
from music.MusicalContextEngine import (
    MusicalScene,
    MusicalContextEngine,
)


# =============================================================================
# TRUST-RATED SIGNAL SETS & INTERNAL ALLOWLISTS
# =============================================================================

LISTENER_INTERNAL_ATTRS: FrozenSet[str] = frozenset({
    "analyzer",
    "context",
    "ingestion",
    "reset",
    "update",
    "process_raw_audio",
})

LISTENER_CONFIG_TRUST: FrozenSet[str] = frozenset({
    "luminosite",
    "sensi",
    "nb_of_fft_band",
})
LISTENER_CONFIG_ATTRS: FrozenSet[str] = LISTENER_CONFIG_TRUST

LISTENER_HIGH_TRUST: FrozenSet[str] = frozenset({
    "fft_band_values",
    "smoothed_fft_band_values",
    "asserved_fft_band",
    "band_proportion",
    "band_means",
    "band_flux",
    "chroma_values",
    "smoothed_chroma_values",
    "smoothed_total_power",
    "asserved_total_power",
    "live_asserved_total_power",
    "dynamic_audio_latency",
})

LISTENER_MEDIUM_TRUST: FrozenSet[str] = frozenset({
    "bpm",
    "beat_phase",
    "beat_count",
    "is_beat",
    "is_real_beat",
    "is_dropped_beat",
    "beat_tag",
    "beat_confidence",
    "beat_trust",
    "live_beat_trust",
    "rhythm_salience",
    "live_rhythm_salience",
    "standalone_bpm",
    "standalone_phase",
    "flywheel_status",
})

LISTENER_LOW_TRUST: FrozenSet[str] = frozenset({
    "is_song_change",
    "is_verse_chorus_change",
    "live_is_song_change",
    "live_is_verse_chorus_change",
    "asserved_novelty",
    "combined_novelty",
    "live_asserved_novelty",
    "live_combined_novelty",
    "novelty_lm",
    "novelty_gm",
    "salience_gradient",
    "power_gradient",
})

LISTENER_TRUST_SETS: Dict[str, FrozenSet[str]] = {
    "HIGH": LISTENER_HIGH_TRUST,
    "MEDIUM": LISTENER_MEDIUM_TRUST,
    "LOW": LISTENER_LOW_TRUST,
    "CONFIG": LISTENER_CONFIG_TRUST,
}

CONTEXT_INTERNAL_ATTRS: FrozenSet[str] = frozenset({
    "listener",
    "reset",
    "update",
    "get_state_snapshot",
    "salience_high",
    "salience_low",
    "trust_high",
    "trust_low",
    "power_high",
    "power_low",
    "silence_threshold",
    "silence_exit_threshold",
    "drop_buildup_threshold",
    "drop_buildup_power_threshold",
    "min_dwell_time",
    "transition_time",
    "structural_dwell_time",
    "pre_drop_cooldown_time",
    "drop_impact_dwell_time",
})

CONTEXT_HIGH_TRUST: FrozenSet[str] = frozenset({
    "energy",
    "power",
    "live_power",
    "spectral_tilt",
    "vertical_center",
    "is_power_high",
    "is_silent",
})

CONTEXT_MEDIUM_TRUST: FrozenSet[str] = frozenset({
    "salience",
    "live_salience",
    "beat_trust",
    "is_locked",
    "is_real_beat",
    "is_syncopated",
})

CONTEXT_LOW_TRUST: FrozenSet[str] = frozenset({
    "scene",
    "previous_scene",
    "scene_blend",
    "scene_dwell_time",
    "is_ambient",
    "is_rhythmic",
    "is_in_pocket",
    "is_buildup",
    "drop_countdown",
    "drop_progress",
    "pre_drop_cooldown",
    "is_drop_imminent",
    "is_drop_impact",
    "is_structural_cut",
    "novelty",
    "tension",
    "salience_gradient",
    "power_gradient",
})

CONTEXT_TRUST_SETS: Dict[str, FrozenSet[str]] = {
    "HIGH": CONTEXT_HIGH_TRUST,
    "MEDIUM": CONTEXT_MEDIUM_TRUST,
    "LOW": CONTEXT_LOW_TRUST,
}


# =============================================================================
# STATIC CONSUMER PROTOCOLS
# =============================================================================

@runtime_checkable
class MusicalContextProtocol(Protocol):
    """Static protocol documenting the public signals of `listener.context`."""

    # 🟢 HIGH trust (physical / Schmitt-stabilized)
    @property
    def energy(self) -> float: ...
    @property
    def power(self) -> float: ...
    @property
    def live_power(self) -> float: ...
    @property
    def spectral_tilt(self) -> float: ...
    @property
    def vertical_center(self) -> float: ...
    @property
    def is_power_high(self) -> bool: ...
    @property
    def is_silent(self) -> bool: ...

    # 🟡 MEDIUM trust (confidence-gated rhythm)
    @property
    def salience(self) -> float: ...
    @property
    def live_salience(self) -> float: ...
    @property
    def beat_trust(self) -> float: ...
    @property
    def is_locked(self) -> bool: ...
    @property
    def is_real_beat(self) -> bool: ...
    @property
    def is_syncopated(self) -> bool: ...

    # 🟠 LOW trust (scene & boundary heuristics — forbidden in concrete modes)
    @property
    def scene(self) -> MusicalScene: ...
    @property
    def previous_scene(self) -> MusicalScene: ...
    @property
    def scene_blend(self) -> float: ...
    @property
    def scene_dwell_time(self) -> float: ...
    @property
    def is_ambient(self) -> bool: ...
    @property
    def is_rhythmic(self) -> bool: ...
    @property
    def is_in_pocket(self) -> bool: ...
    @property
    def is_buildup(self) -> bool: ...
    @property
    def drop_countdown(self) -> float: ...
    @property
    def drop_progress(self) -> float: ...
    @property
    def pre_drop_cooldown(self) -> float: ...
    @property
    def is_drop_imminent(self) -> bool: ...
    @property
    def is_drop_impact(self) -> bool: ...
    @property
    def is_structural_cut(self) -> bool: ...
    @property
    def novelty(self) -> float: ...
    @property
    def tension(self) -> float: ...
    @property
    def salience_gradient(self) -> float: ...
    @property
    def power_gradient(self) -> float: ...


@runtime_checkable
class ListenerProtocol(Protocol):
    """Static protocol documenting the public surface of `Listener`."""

    context: MusicalContextProtocol

    # ⚙️ CONFIG properties
    @property
    def luminosite(self) -> float: ...
    @property
    def sensi(self) -> float: ...
    @property
    def nb_of_fft_band(self) -> int: ...

    # 🟢 HIGH trust (physical spectral & power measurements)
    @property
    def fft_band_values(self) -> np.ndarray: ...
    @property
    def smoothed_fft_band_values(self) -> np.ndarray: ...
    @property
    def asserved_fft_band(self) -> np.ndarray: ...
    @property
    def band_proportion(self) -> np.ndarray: ...
    @property
    def band_means(self) -> np.ndarray: ...
    @property
    def band_flux(self) -> np.ndarray: ...
    @property
    def chroma_values(self) -> np.ndarray: ...
    @property
    def smoothed_chroma_values(self) -> np.ndarray: ...
    @property
    def smoothed_total_power(self) -> float: ...
    @property
    def asserved_total_power(self) -> float: ...
    @property
    def live_asserved_total_power(self) -> float: ...
    @property
    def dynamic_audio_latency(self) -> float: ...

    # 🟡 MEDIUM trust (flywheel tempo, phase & confidence)
    @property
    def bpm(self) -> float: ...
    @property
    def beat_phase(self) -> float: ...
    @property
    def beat_count(self) -> int: ...
    @property
    def is_beat(self) -> bool: ...
    @property
    def is_real_beat(self) -> bool: ...
    @property
    def is_dropped_beat(self) -> bool: ...
    @property
    def beat_tag(self) -> str: ...
    @property
    def beat_confidence(self) -> float: ...
    @property
    def beat_trust(self) -> float: ...
    @property
    def live_beat_trust(self) -> float: ...
    @property
    def rhythm_salience(self) -> float: ...
    @property
    def live_rhythm_salience(self) -> float: ...
    @property
    def standalone_bpm(self) -> float: ...
    @property
    def standalone_phase(self) -> float: ...
    @property
    def flywheel_status(self) -> str: ...

    # 🟠 LOW trust (novelty, boundary flags & gradients)
    @property
    def is_song_change(self) -> bool: ...
    @property
    def is_verse_chorus_change(self) -> bool: ...
    @property
    def live_is_song_change(self) -> bool: ...
    @property
    def live_is_verse_chorus_change(self) -> bool: ...
    @property
    def asserved_novelty(self) -> float: ...
    @property
    def combined_novelty(self) -> float: ...
    @property
    def live_asserved_novelty(self) -> float: ...
    @property
    def live_combined_novelty(self) -> float: ...
    @property
    def novelty_lm(self) -> float: ...
    @property
    def novelty_gm(self) -> float: ...
    @property
    def salience_gradient(self) -> float: ...
    @property
    def power_gradient(self) -> float: ...


__all__ = [
    "Listener",
    "ANALYZER_REGISTRY",
    "DEFAULT_ANALYZER_MODEL",
    "resolve_analyzer_class",
    "MusicalScene",
    "MusicalContextEngine",
    "ListenerProtocol",
    "MusicalContextProtocol",
    "LISTENER_INTERNAL_ATTRS",
    "LISTENER_CONFIG_TRUST",
    "LISTENER_CONFIG_ATTRS",
    "LISTENER_HIGH_TRUST",
    "LISTENER_MEDIUM_TRUST",
    "LISTENER_LOW_TRUST",
    "LISTENER_TRUST_SETS",
    "CONTEXT_INTERNAL_ATTRS",
    "CONTEXT_HIGH_TRUST",
    "CONTEXT_MEDIUM_TRUST",
    "CONTEXT_LOW_TRUST",
    "CONTEXT_TRUST_SETS",
]
