"""
core/MusicalContextEngine.py - Real-Time Musical Context & Regime Classification Engine.

Consumes acoustic and rhythmic signals from Listener (rhythm_salience, beat_trust,
spectral power, novelty, and lookahead salience gradient) to classify the music into
one of 6 canonical musical regimes.

Guarantees:
- AXIOM-01: Execution time <= 0.01 ms (well within 0.15 ms DSP budget).
- AXIOM-02: Zero dynamic heap allocations in hot path update().
- AXIOM-06: Perceptual stability via Schmitt trigger hysteresis and minimum dwell times.
- AXIOM-07: Code governance line cap <= 500 lines.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, Any, Optional
import math
import numpy as np


class MusicalRegime(str, Enum):
    """
    The 6 canonical musical regimes of the Vialactée chandelier.
    Inheriting from (str, Enum) enables direct string equality:
        regime == "THE_POCKET" or regime == MusicalRegime.THE_POCKET
    """
    DEEP_AMBIENT = "DEEP_AMBIENT"
    FLOATING_PULSE = "FLOATING_PULSE"
    THE_POCKET = "THE_POCKET"
    CHAOTIC_FILL = "CHAOTIC_FILL"
    PRE_DROP_BUILDUP = "PRE_DROP_BUILDUP"
    STRUCTURAL_CHANGE = "STRUCTURAL_CHANGE"


class MusicalContextEngine:
    """
    Evaluates real-time musical context and manages transitions across 6 canonical regimes.
    """

    def __init__(self, listener: Any, config: Optional[Dict[str, Any]] = None) -> None:
        self.listener = listener
        cfg = config or {}

        # 1. Hysteresis Thresholds (Schmitt Triggers)
        self.salience_high: float = float(cfg.get("salience_high", 0.45))
        self.salience_low: float = float(cfg.get("salience_low", 0.35))
        self.trust_high: float = float(cfg.get("trust_high", 0.50))
        self.trust_low: float = float(cfg.get("trust_low", 0.35))

        # 2. Timing & Transition Parameters
        self.drop_buildup_threshold: float = float(cfg.get("drop_buildup_threshold", 0.40))
        self.min_dwell_time: float = float(cfg.get("min_dwell_time", 1.0))
        self.transition_time: float = float(cfg.get("transition_time", 0.5))
        self.structural_dwell_time: float = float(cfg.get("structural_dwell_time", 1.2))
        self.pre_drop_cooldown_time: float = float(cfg.get("pre_drop_cooldown", 3.0))

        # 3. Pre-allocated State Variables (Zero Hot-Loop Allocations)
        self._current_regime: MusicalRegime = MusicalRegime.DEEP_AMBIENT
        self._previous_regime: MusicalRegime = MusicalRegime.DEEP_AMBIENT
        self._regime_blend: float = 1.0
        self._regime_dwell_time: float = 0.0
        self._drop_countdown: float = 0.0
        self._salience_gradient: float = 0.0
        self._pre_drop_cooldown: float = 0.0
        self._is_salience_high: bool = False
        self._is_trust_high: bool = False
        self._salience: float = 0.0
        self._beat_trust: float = 0.0
        self._power: float = 0.0
        self._novelty: float = 0.0

    def reset(self) -> None:
        """Resets all regimes, timers, and hysteresis flags to initial defaults."""
        self._current_regime = MusicalRegime.DEEP_AMBIENT
        self._previous_regime = MusicalRegime.DEEP_AMBIENT
        self._regime_blend = 1.0
        self._regime_dwell_time = 0.0
        self._drop_countdown = 0.0
        self._salience_gradient = 0.0
        self._pre_drop_cooldown = 0.0
        self._is_salience_high = False
        self._is_trust_high = False
        self._salience = 0.0
        self._beat_trust = 0.0
        self._power = 0.0
        self._novelty = 0.0

    def update(self, dt: float) -> None:
        """
        Executes one frame tick of regime classification and blend crossfading.
        Must be called once per frame from Listener.update().
        """
        safe_dt = max(0.0001, float(dt))

        # --- 1. Signal Extraction & Input Sanitization ---
        raw_salience = getattr(self.listener, "rhythm_salience", 0.0)
        raw_live_salience = getattr(self.listener, "live_rhythm_salience", raw_salience)
        raw_trust = getattr(self.listener, "beat_trust", 0.0)
        raw_power = getattr(self.listener, "asserved_total_power", 0.0)
        raw_novelty = getattr(self.listener, "asserved_novelty", 0.0)
        is_song_change = bool(getattr(self.listener, "is_song_change", False))
        is_verse_chorus = bool(getattr(self.listener, "is_verse_chorus_change", False))

        # Safe scalar bounds clamping (pure math.isnan to avoid NumPy wrapper allocation)
        s = 0.0 if math.isnan(raw_salience) else max(0.0, min(1.0, float(raw_salience)))
        s_live = 0.0 if math.isnan(raw_live_salience) else max(0.0, min(1.0, float(raw_live_salience)))
        t = 0.0 if math.isnan(raw_trust) else max(0.0, min(1.0, float(raw_trust)))
        p = 0.0 if math.isnan(raw_power) else max(0.0, float(raw_power))
        nov = 0.0 if math.isnan(raw_novelty) else max(0.0, float(raw_novelty))

        self._salience = s
        self._beat_trust = t
        self._power = p
        self._novelty = nov
        self._salience_gradient = s_live - s

        # --- 2. Schmitt Trigger Hysteresis Update ---
        if self._is_salience_high:
            if s < self.salience_low:
                self._is_salience_high = False
        else:
            if s >= self.salience_high:
                self._is_salience_high = True

        if self._is_trust_high:
            if t < self.trust_low:
                self._is_trust_high = False
        else:
            if t >= self.trust_high:
                self._is_trust_high = True

        # --- 3. Evaluate Steady-State Target ---
        if self._is_salience_high and self._is_trust_high:
            steady_target = MusicalRegime.THE_POCKET
        elif self._is_salience_high and not self._is_trust_high:
            steady_target = MusicalRegime.CHAOTIC_FILL
        elif not self._is_salience_high and self._is_trust_high:
            steady_target = MusicalRegime.FLOATING_PULSE
        else:
            steady_target = MusicalRegime.DEEP_AMBIENT

        # --- 4. Dwell Time & Crossfade Progression ---
        self._regime_dwell_time += safe_dt
        if self._pre_drop_cooldown > 0.0:
            self._pre_drop_cooldown = max(0.0, self._pre_drop_cooldown - safe_dt)

        if self._regime_blend < 1.0:
            if self.transition_time > 0.0:
                self._regime_blend = min(1.0, self._regime_blend + safe_dt / self.transition_time)
            else:
                self._regime_blend = 1.0

        # --- 5. Priority 1: Macro Structural Change ---
        if is_song_change or is_verse_chorus:
            if self._current_regime == MusicalRegime.STRUCTURAL_CHANGE:
                # Re-trigger full dwell duration and crossfade for subsequent macro event
                self._regime_dwell_time = 0.0
                self._regime_blend = 0.0
            else:
                self._switch_regime(MusicalRegime.STRUCTURAL_CHANGE)
            self._drop_countdown = 0.0
            return

        if self._current_regime == MusicalRegime.STRUCTURAL_CHANGE:
            if self._regime_dwell_time >= self.structural_dwell_time:
                self._switch_regime(steady_target)
            return

        # --- 6. Priority 2: Pre-Drop Buildup ---
        lookahead = float(getattr(getattr(self.listener, "analyzer", None), "lookahead_seconds", 5.0))

        if self._current_regime == MusicalRegime.PRE_DROP_BUILDUP:
            self._drop_countdown = max(0.0, self._drop_countdown - safe_dt)
            # Exit conditions: countdown reached zero, or drop arrived at speakers (high salience)
            if self._drop_countdown <= 0.0 or self._is_salience_high:
                self._switch_regime(steady_target)
                self._drop_countdown = 0.0
                self._pre_drop_cooldown = self.pre_drop_cooldown_time
            elif self._salience_gradient < 0.10 and self._drop_countdown < (lookahead * 0.5) and not self._is_salience_high:
                # False alarm / aborted drop
                self._switch_regime(steady_target)
                self._drop_countdown = 0.0
                self._pre_drop_cooldown = self.pre_drop_cooldown_time
            return
        else:
            # Trigger pre-drop if gradient >= threshold, cooldown expired, lookahead exists, and not already in high salience
            if (lookahead > 0.1
                    and self._pre_drop_cooldown <= 0.0
                    and self._salience_gradient >= self.drop_buildup_threshold
                    and not self._is_salience_high):
                self._switch_regime(MusicalRegime.PRE_DROP_BUILDUP)
                self._drop_countdown = lookahead
                return

        # --- 7. Priority 3: Steady-State Transition (Governed by Min Dwell Time) ---
        if self._current_regime != steady_target:
            if self._regime_dwell_time >= self.min_dwell_time:
                self._switch_regime(steady_target)

    def _switch_regime(self, new_regime: MusicalRegime | str) -> None:
        """Internal helper to switch regimes and reset crossfade progression."""
        regime_enum = MusicalRegime(new_regime) if not isinstance(new_regime, MusicalRegime) else new_regime
        if regime_enum != self._current_regime:
            self._previous_regime = self._current_regime
            self._current_regime = regime_enum
            self._regime_blend = 0.0
            self._regime_dwell_time = 0.0

    # ==========================================
    # PUBLIC PROPERTIES & FACADE
    # ==========================================

    @property
    def current_regime(self) -> MusicalRegime:
        """The currently active canonical musical regime."""
        return self._current_regime

    @property
    def previous_regime(self) -> MusicalRegime:
        """The regime preceding the current one, used for crossfading."""
        return self._previous_regime

    @property
    def regime_blend(self) -> float:
        """
        Crossfade weight in [0.0, 1.0].
        0.0 = just switched from previous regime, 1.0 = fully transitioned.
        """
        return float(self._regime_blend)

    @property
    def drop_countdown(self) -> float:
        """Estimated seconds remaining until drop impact during PRE_DROP_BUILDUP."""
        return float(self._drop_countdown)

    @property
    def salience_gradient(self) -> float:
        """Difference between lookahead rhythm salience and speaker rhythm salience (ΔR)."""
        return float(self._salience_gradient)

    @property
    def regime_dwell_time(self) -> float:
        """Time in seconds spent in the current regime."""
        return float(self._regime_dwell_time)

    @property
    def salience(self) -> float:
        """Current speaker-aligned rhythm salience [0.0, 1.0]."""
        return float(self._salience)

    @property
    def beat_trust(self) -> float:
        """Current speaker-aligned beat trust [0.0, 1.0]."""
        return float(self._beat_trust)

    @property
    def power(self) -> float:
        """Current speaker-aligned total audio power."""
        return float(self._power)

    @property
    def novelty(self) -> float:
        """Current speaker-aligned spectral novelty."""
        return float(self._novelty)

    @property
    def is_ambient(self) -> bool:
        """True if in DEEP_AMBIENT or FLOATING_PULSE."""
        return self._current_regime in (MusicalRegime.DEEP_AMBIENT, MusicalRegime.FLOATING_PULSE)

    @property
    def is_rhythmic(self) -> bool:
        """True if in THE_POCKET or CHAOTIC_FILL."""
        return self._current_regime in (MusicalRegime.THE_POCKET, MusicalRegime.CHAOTIC_FILL)

    @property
    def is_buildup(self) -> bool:
        """True if in PRE_DROP_BUILDUP."""
        return self._current_regime == MusicalRegime.PRE_DROP_BUILDUP

    @property
    def is_in_pocket(self) -> bool:
        """True if in THE_POCKET."""
        return self._current_regime == MusicalRegime.THE_POCKET

    @property
    def is_structural_change(self) -> bool:
        """True if in STRUCTURAL_CHANGE."""
        return self._current_regime == MusicalRegime.STRUCTURAL_CHANGE

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Provides a complete serializable state snapshot for diagnostics and telemetry."""
        cur = self._current_regime.value if hasattr(self._current_regime, "value") else str(self._current_regime)
        prev = self._previous_regime.value if hasattr(self._previous_regime, "value") else str(self._previous_regime)
        return {
            "current_regime": cur,
            "previous_regime": prev,
            "regime_blend": round(self._regime_blend, 4),
            "regime_dwell_time": round(self._regime_dwell_time, 3),
            "drop_countdown": round(self._drop_countdown, 3),
            "salience_gradient": round(self._salience_gradient, 4),
            "salience": round(self._salience, 4),
            "beat_trust": round(self._beat_trust, 4),
            "power": round(self._power, 4),
            "novelty": round(self._novelty, 4),
            "is_salience_high": self._is_salience_high,
            "is_trust_high": self._is_trust_high,
        }
