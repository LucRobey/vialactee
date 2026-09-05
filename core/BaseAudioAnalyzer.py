"""
core/BaseAudioAnalyzer.py - Abstract Contract for all Audio & Rhythm Analyzers.

Any rhythm model (Pearson Flywheel, Multi-band, Kalman Filter, Neural Net)
must inherit from this base class to be compatible with both the production
Listener facade and the immutable Benchmark Harness.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import numpy as np


class BaseAudioAnalyzer(ABC):
    """
    Unified abstract contract for Vialactée music analysis engines.
    Provides sane default fallbacks for all features so experimental
    models only need to implement the core math they are actively testing.
    """

    def __init__(self, ingestion: Any, infos: Dict[str, Any], config: Optional[Any] = None) -> None:
        self.ingestion = ingestion
        self.infos = infos
        self.config = config
        self.lookahead_seconds: float = float(infos.get("fakeDelay", 5.0))
        self.hardware_latency: float = float(infos.get("latency", 0.0))

        # 1. Rhythmic & Metronome State Defaults
        self.bpm: float = 120.0
        self.is_beat: bool = False
        self.is_real_beat: bool = False
        self.is_dropped_beat: bool = False
        self.beat_count: int = 0
        self.flywheel_status: str = "locked"

        # Downbeat & Metric Bar Tracking (1, 2, 3, 4)
        self.is_downbeat: bool = False
        self.bar_phase: float = 0.0
        self.time_signature: Tuple[int, int] = (4, 4)

        # 2. Spectral & Transient Dynamics Defaults
        nb_bands = getattr(self.ingestion, 'nb_of_fft_band', 8)
        self.band_flux: np.ndarray = np.zeros(nb_bands)
        self.band_peak: np.ndarray = np.zeros(nb_bands, dtype=int)
        self.spectral_centroid: float = 0.5

        # 3. Macro-Structure & Form Defaults
        self.is_energy_drop: bool = False

        # 4. Semantic & Tonal Tags Defaults
        self.current_beat_tag: str = "Bass/Kick"
        self.vocals_present: bool = False
        self.musical_key: str = "Unknown"
        self.mood_valence_arousal: Tuple[float, float] = (0.0, 0.0)

    # =========================================================================
    # LIFECYCLE & EXECUTION (The Driving Clock)
    # =========================================================================

    @abstractmethod
    def update(self, current_time: float, dt: float, fps_ratio: float) -> None:
        """
        Primary per-frame processing step. Ingests current audio buffer,
        updates internal filters, advances phase, and triggers events.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        Resets all internal history buffers, phase accumulators, and flywheels.
        Called when switching songs or starting a new benchmark track.
        """
        pass

    # Backwards compatibility with existing Listener calls
    def detect_band_peaks(self, current_time: float, dt: float, fps_ratio: float) -> None:
        """Alias or sub-routine called by Listener.update()."""
        self.update(current_time, dt, fps_ratio)

    def update_structural_novelty(self, current_time: float, dt: float, fps_ratio: float) -> None:
        """Hook for structural novelty computation if separated from peak detection."""
        pass

    # =========================================================================
    # RHYTHM & PHASE PROPERTY
    # =========================================================================

    @property
    @abstractmethod
    def beat_phase(self) -> float:
        """
        Normalized fractional phase in [0.0, 1.0) of the current beat
        strictly synchronized to speaker playback time (T_speaker).
        0.0 = exact beat impact point, 0.5 = exact upbeat.
        """
        pass

    @property
    def beat_confidence(self) -> float:
        """Internal model confidence score in [0.0, 1.0]."""
        return float(getattr(self, 'confidence_score', getattr(self, '_beat_confidence', 1.0)))

    @beat_confidence.setter
    def beat_confidence(self, val: float) -> None:
        self._beat_confidence = float(val)

    # Aliases for backwards compatibility
    @property
    def standalone_bpm(self) -> float:
        return float(self.bpm)

    @property
    def standalone_phase(self) -> float:
        return float(self.beat_phase)

    # Macro-Structure Properties (with fallback defaults)
    @property
    def is_song_change(self) -> bool:
        return getattr(self, '_is_song_change', False)

    @is_song_change.setter
    def is_song_change(self, val: bool) -> None:
        self._is_song_change = bool(val)

    @property
    def is_verse_chorus_change(self) -> bool:
        return getattr(self, '_is_verse_chorus_change', False)

    @is_verse_chorus_change.setter
    def is_verse_chorus_change(self, val: bool) -> None:
        self._is_verse_chorus_change = bool(val)

    @property
    def asserved_novelty(self) -> float:
        return float(getattr(self, '_asserved_novelty', 0.0))

    @property
    def combined_novelty(self) -> float:
        return float(getattr(self, '_combined_novelty', 0.0))

    # =========================================================================
    # AI-READY TELEMETRY & DIAGNOSTICS (Data for LLM Agent Pattern Mining)
    # =========================================================================

    def capture_frame_telemetry(self) -> Dict[str, Any]:
        """
        Called by the benchmark recorder at 60Hz or on beat events.
        Captures internal mathematical tensors/scalars for AI pattern discovery.
        """
        return {
            "bpm": float(self.bpm),
            "beat_phase": float(self.beat_phase),
            "confidence": float(getattr(self, 'confidence_score', getattr(self, 'beat_confidence', 1.0))),
            "status": str(self.flywheel_status),
            "is_beat": bool(self.is_beat),
            "is_real_beat": bool(self.is_real_beat),
            "is_dropped_beat": bool(self.is_dropped_beat),
            "beat_tag": str(self.current_beat_tag),
        }

    def get_model_metadata(self) -> Dict[str, Any]:
        """
        Returns model identity, algorithm class, and active hyperparameter dictionary.
        Logged into experiment manifest.json for 100% reproducibility.
        """
        return {
            "model_class": self.__class__.__name__,
            "lookahead_seconds": self.lookahead_seconds,
            "hardware_latency": self.hardware_latency,
            "config": vars(self.config) if hasattr(self, 'config') and self.config else {},
        }
