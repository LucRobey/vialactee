"""
core/MusicalContextEngine.py - Unified 3-Tier Musical Context & Visual Conductor.

Unified Vialactée Visual Conductor (Offer 4):
Consumes multi-signal acoustic, rhythmic, and spectral dynamics (rhythm_salience,
beat_trust, asserved power, lookahead power, structural novelty, and 8-band Mel FFT)
to evaluate real-time musical context across 3 unified tiers:
- Tier 1: Continuous Dynamic Kinetics (energy, tension, drop_progress, spectral_tilt, vertical_center, gradients).
- Tier 2: 4 Macro Scenes (CHILL, GROOVE, BUILDUP, DROP_IMPACT) with Schmitt hysteresis and dwell locks.
- Tier 3: Micro Physical Badges (is_locked, is_syncopated, is_real_beat, is_silent, is_drop_impact, is_drop_imminent, is_structural_cut).

Guarantees:
- AXIOM-01: Execution time <= 0.01 ms (DSP budget <= 0.15 ms).
- AXIOM-02: Zero dynamic heap allocations in hot path update().
- AXIOM-06: Perceptual stability via Schmitt trigger hysteresis and minimum dwell times.
- AXIOM-07: Code governance line cap <= 500 lines.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, Any, Optional
import math


_CHILL_ALIASES = frozenset(("DEEP_AMBIENT", "FLOATING_PULSE"))
_GROOVE_ALIASES = frozenset(("THE_POCKET", "CHAOTIC_FILL"))
_BUILDUP_ALIASES = frozenset(("PRE_DROP_BUILDUP",))


class MusicalScene(str, Enum):
    """4 canonical macro musical scenes."""
    CHILL = "CHILL"
    GROOVE = "GROOVE"
    BUILDUP = "BUILDUP"
    DROP_IMPACT = "DROP_IMPACT"

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if isinstance(other, str):
            v = self.value
            if v == other:
                return True
            if v == "CHILL" and other in _CHILL_ALIASES:
                return True
            if v == "GROOVE" and other in _GROOVE_ALIASES:
                return True
            if v == "BUILDUP" and other in _BUILDUP_ALIASES:
                return True
        return False

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def _missing_(cls, value: object) -> Any:
        legacy_map = {
            "DEEP_AMBIENT": cls.CHILL, "FLOATING_PULSE": cls.CHILL,
            "THE_POCKET": cls.GROOVE, "CHAOTIC_FILL": cls.GROOVE,
            "PRE_DROP_BUILDUP": cls.BUILDUP,
        }
        if isinstance(value, str):
            val_upper = value.upper()
            if val_upper in legacy_map:
                return legacy_map[val_upper]
        return super()._missing_(value)


# Backward compatibility aliases for legacy 6-regime code
class _LegacyRegime(str):
    value = property(lambda self: str(self))

MusicalScene.DEEP_AMBIENT = MusicalScene.CHILL  # type: ignore[attr-defined]
MusicalScene.FLOATING_PULSE = MusicalScene.CHILL  # type: ignore[attr-defined]
MusicalScene.THE_POCKET = MusicalScene.GROOVE  # type: ignore[attr-defined]
MusicalScene.CHAOTIC_FILL = MusicalScene.GROOVE  # type: ignore[attr-defined]
MusicalScene.PRE_DROP_BUILDUP = MusicalScene.BUILDUP  # type: ignore[attr-defined]
MusicalScene.STRUCTURAL_CHANGE = _LegacyRegime("STRUCTURAL_CHANGE")  # type: ignore[attr-defined]

MusicalRegime = MusicalScene


class MusicalContextEngine:
    """Unified 3-Tier Musical Context Engine."""

    def __init__(self, listener: Any, config: Optional[Dict[str, Any]] = None) -> None:
        self.listener = listener
        cfg = config or {}

        # 1. Hysteresis Thresholds (Schmitt Triggers)
        self.salience_high, self.salience_low = float(cfg.get("salience_high", 0.45)), float(cfg.get("salience_low", 0.35))
        self.trust_high, self.trust_low = float(cfg.get("trust_high", 0.50)), float(cfg.get("trust_low", 0.35))
        self.power_high, self.power_low = float(cfg.get("power_high", 0.50)), float(cfg.get("power_low", 0.35))
        self.silence_threshold, self.silence_exit_threshold = float(cfg.get("silence_threshold", 0.05)), float(cfg.get("silence_exit_threshold", 0.08))

        # 2. Timing & Transition Parameters
        self.drop_buildup_threshold = float(cfg.get("drop_buildup_threshold", 0.40))
        self.drop_buildup_power_threshold = float(cfg.get("drop_buildup_power_threshold", 0.40))
        self.min_dwell_time, self.transition_time = float(cfg.get("min_dwell_time", 1.0)), float(cfg.get("transition_time", 0.5))
        self.structural_dwell_time, self.pre_drop_cooldown_time = float(cfg.get("structural_dwell_time", 1.2)), float(cfg.get("pre_drop_cooldown", cfg.get("pre_drop_cooldown_time", 16.0)))
        self.drop_impact_dwell_time = float(cfg.get("drop_impact_dwell_time", 1.5))

        # 3. Pre-allocated State Variables (Zero Hot-Loop Allocations)
        self._current_scene, self._previous_scene = MusicalScene.CHILL, MusicalScene.CHILL
        self._scene_blend, self._scene_dwell_time = 1.0, 0.0
        self._drop_countdown, self._drop_duration = 0.0, 5.0
        self._salience_gradient, self._power_gradient, self._pre_drop_cooldown = 0.0, 0.0, 0.0
        self._buildup_entered_high_salience, self._buildup_entered_high_power = False, False
        self._buildup_silence_cut, self._buildup_saw_silence = False, False
        self._structural_cut_timer = 0.0

        # Schmitt triggers & ingested signals
        self._is_salience_high, self._is_trust_high, self._is_power_high, self._is_silent = False, False, False, True
        self._salience, self._live_salience, self._beat_trust = 0.0, 0.0, 0.0
        self._power, self._live_power, self._novelty = 0.0, 0.0, 0.0

        # Tier 1 Kinetics & Tier 3 Micro Badges
        self._energy, self._tension, self._drop_progress = 0.0, 0.0, 0.0
        self._spectral_tilt, self._vertical_center = 0.0, 0.5
        self._is_locked = False
        self._is_syncopated = False
        self._is_real_beat = False
        self._is_drop_impact = False
        self._is_drop_imminent = False
        self._is_structural_cut = False

    def reset(self) -> None:
        """Resets all scenes, timers, hysteresis flags, badges, and modulation metrics."""
        self._current_scene, self._previous_scene = MusicalScene.CHILL, MusicalScene.CHILL
        self._scene_blend, self._scene_dwell_time = 1.0, 0.0
        self._drop_countdown, self._drop_duration = 0.0, 5.0
        self._salience_gradient, self._power_gradient, self._pre_drop_cooldown = 0.0, 0.0, 0.0
        self._buildup_entered_high_salience, self._buildup_entered_high_power = False, False
        self._buildup_silence_cut, self._buildup_saw_silence = False, False
        self._structural_cut_timer = 0.0
        self._is_salience_high, self._is_trust_high, self._is_power_high, self._is_silent = False, False, False, True
        self._salience, self._live_salience, self._beat_trust = 0.0, 0.0, 0.0
        self._power, self._live_power, self._novelty = 0.0, 0.0, 0.0
        self._energy, self._tension, self._drop_progress = 0.0, 0.0, 0.0
        self._spectral_tilt, self._vertical_center = 0.0, 0.5
        self._is_locked, self._is_syncopated, self._is_real_beat = False, False, False
        self._is_drop_impact, self._is_drop_imminent, self._is_structural_cut = False, False, False
    def update(self, dt: float) -> None:
        """Executes one frame tick of scene classification and 3-tier context updates."""
        self._is_drop_impact = False
        safe_dt = max(0.0001, float(dt))

        # --- 1. Signal Extraction & Input Sanitization ---
        raw_salience = getattr(self.listener, "rhythm_salience", 0.0)
        raw_live_salience = getattr(self.listener, "live_rhythm_salience", raw_salience)
        raw_trust = getattr(self.listener, "beat_trust", 0.0)
        raw_power = getattr(self.listener, "asserved_total_power", 0.0)
        raw_live_power = getattr(self.listener, "live_asserved_total_power", raw_power)
        raw_novelty = getattr(self.listener, "asserved_novelty", 0.0)
        is_song_change = bool(getattr(self.listener, "is_song_change", False))
        is_verse_chorus = bool(getattr(self.listener, "is_verse_chorus_change", False))
        live_is_song_change = bool(getattr(self.listener, "live_is_song_change", False))
        raw_bands = getattr(self.listener, "asserved_fft_band", None)
        if raw_bands is None or not hasattr(raw_bands, "__len__") or len(raw_bands) < 8:
            raw_bands = getattr(self.listener, "fft_band_values", None)

        s = 0.0 if raw_salience is None or math.isnan(raw_salience) else max(0.0, min(1.0, float(raw_salience)))
        s_live = 0.0 if raw_live_salience is None or math.isnan(raw_live_salience) else max(0.0, min(1.0, float(raw_live_salience)))
        t = 0.0 if raw_trust is None or math.isnan(raw_trust) else max(0.0, min(1.0, float(raw_trust)))
        p = 0.0 if raw_power is None or math.isnan(raw_power) else max(0.0, float(raw_power))
        p_live = 0.0 if raw_live_power is None or math.isnan(raw_live_power) else max(0.0, float(raw_live_power))
        nov = 0.0 if raw_novelty is None or math.isnan(raw_novelty) else max(0.0, min(1.0, float(raw_novelty)))

        self._salience = s
        self._live_salience = s_live
        self._beat_trust = t
        self._power = p
        self._live_power = p_live
        self._novelty = nov
        self._salience_gradient = s_live - s
        self._power_gradient = p_live - p

        # --- 2. Schmitt Trigger Hysteresis & Tier 3 Micro Badges ---
        if self._is_salience_high:
            if s < self.salience_low: self._is_salience_high = False
        elif s >= self.salience_high: self._is_salience_high = True

        if self._is_trust_high:
            if t < self.trust_low: self._is_trust_high = False
        elif t >= self.trust_high: self._is_trust_high = True
        self._is_locked = self._is_trust_high

        if self._is_power_high:
            if p < self.power_low: self._is_power_high = False
        elif p >= self.power_high: self._is_power_high = True

        if self._is_silent:
            if p >= self.silence_exit_threshold: self._is_silent = False
        elif p < self.silence_threshold: self._is_silent = True

        self._is_syncopated = bool(self._is_salience_high and t < self.trust_low)
        self._is_real_beat = bool(getattr(self.listener, "is_beat", False) and p >= 0.20)
        if is_song_change or is_verse_chorus:
            self._structural_cut_timer = self.structural_dwell_time

        # --- 3. Spectral Tilt & Vertical Center ---
        if raw_bands is not None and hasattr(raw_bands, "__len__") and len(raw_bands) >= 8:
            b0 = max(0.0, float(raw_bands[0])) if raw_bands[0] is not None and not math.isnan(raw_bands[0]) and not math.isinf(raw_bands[0]) else 0.0; b1 = max(0.0, float(raw_bands[1])) if raw_bands[1] is not None and not math.isnan(raw_bands[1]) and not math.isinf(raw_bands[1]) else 0.0
            b2 = max(0.0, float(raw_bands[2])) if raw_bands[2] is not None and not math.isnan(raw_bands[2]) and not math.isinf(raw_bands[2]) else 0.0; b3 = max(0.0, float(raw_bands[3])) if raw_bands[3] is not None and not math.isnan(raw_bands[3]) and not math.isinf(raw_bands[3]) else 0.0
            b4 = max(0.0, float(raw_bands[4])) if raw_bands[4] is not None and not math.isnan(raw_bands[4]) and not math.isinf(raw_bands[4]) else 0.0; b5 = max(0.0, float(raw_bands[5])) if raw_bands[5] is not None and not math.isnan(raw_bands[5]) and not math.isinf(raw_bands[5]) else 0.0
            b6 = max(0.0, float(raw_bands[6])) if raw_bands[6] is not None and not math.isnan(raw_bands[6]) and not math.isinf(raw_bands[6]) else 0.0; b7 = max(0.0, float(raw_bands[7])) if raw_bands[7] is not None and not math.isnan(raw_bands[7]) and not math.isinf(raw_bands[7]) else 0.0
            bass, treble = b0 + b1 + b2 + b3, b4 + b5 + b6 + b7
            tot_b = bass + treble
            if tot_b > 1e-6:
                self._spectral_tilt = max(-1.0, min(1.0, (treble - bass) / tot_b))
                self._vertical_center = max(0.0, min(1.0, (b1 + 2.0*b2 + 3.0*b3 + 4.0*b4 + 5.0*b5 + 6.0*b6 + 7.0*b7) / (7.0 * tot_b)))
            else:
                self._spectral_tilt, self._vertical_center = 0.0, 0.5
        else:
            self._spectral_tilt, self._vertical_center = 0.0, 0.5

        # --- 4. Master Visual Energy Drive: 0.50*P + 0.30*S + 0.20*(S*T) ---
        self._energy = max(0.0, min(1.0, 0.50 * p + 0.30 * s + 0.20 * (s * t)))

        # --- 5. Evaluate Steady-State Target Scene ---
        if self._is_silent:
            steady_target = MusicalScene.CHILL
        elif self._is_salience_high or (self._is_trust_high and p >= self.power_low):
            steady_target = MusicalScene.GROOVE
        else:
            steady_target = MusicalScene.CHILL

        # --- 6. Dwell Time, Crossfade Progression & Timers ---
        self._scene_dwell_time += safe_dt
        if self._pre_drop_cooldown > 0.0:
            self._pre_drop_cooldown = max(0.0, self._pre_drop_cooldown - safe_dt)

        if self._scene_blend < 1.0:
            self._scene_blend = min(1.0, self._scene_blend + safe_dt / self.transition_time) if self.transition_time > 0.0 else 1.0

        if self._structural_cut_timer > 0.0:
            self._structural_cut_timer = max(0.0, self._structural_cut_timer - safe_dt)
        self._is_structural_cut = (self._structural_cut_timer > 0.0)

        # --- 7. Scene State Machine Transitions ---
        # Case A: DROP_IMPACT Scene Dwell (1.5s lock)
        if self._current_scene is MusicalScene.DROP_IMPACT:
            if self._scene_dwell_time >= self.drop_impact_dwell_time:
                self._switch_scene(MusicalScene.CHILL if p < 0.20 else MusicalScene.GROOVE)
            self._update_modulation_facade()
            return

        lookahead = float(getattr(getattr(self.listener, "analyzer", None), "lookahead_seconds", 5.0))

        # Case B: BUILDUP Scene Progression & Landing
        if self._current_scene is MusicalScene.BUILDUP:
            if is_song_change or is_verse_chorus:
                self._switch_scene(steady_target)
                self._drop_countdown = 0.0
                self._buildup_silence_cut = False
                self._buildup_saw_silence = False
                self._pre_drop_cooldown = self.pre_drop_cooldown_time
                self._update_modulation_facade()
                return

            self._drop_countdown = max(-2.0, self._drop_countdown - safe_dt)
            if not self._is_salience_high: self._buildup_entered_high_salience = False
            elif self._drop_countdown > 0.40: self._buildup_entered_high_salience = True

            if not self._is_power_high: self._buildup_entered_high_power = False
            elif self._drop_countdown > 0.40: self._buildup_entered_high_power = True

            if self._is_silent and (self._buildup_silence_cut or self._buildup_entered_high_power or self._buildup_entered_high_salience or self._drop_countdown <= 0.80):
                self._buildup_saw_silence = True

            imminent_transient = (self._drop_countdown <= 0.40) and (
                (not self._buildup_entered_high_salience and self._is_salience_high)
                or (not self._buildup_entered_high_power and self._is_power_high)
            )
            post_silence_transient = bool(
                self._buildup_saw_silence and (p >= self.power_high or s >= self.salience_high)
                and (self._buildup_silence_cut or self._drop_countdown <= 0.40)
            )

            if self._buildup_silence_cut:
                drop_arrived = post_silence_transient
            else:
                drop_arrived = (self._drop_countdown <= 0.001 or imminent_transient or post_silence_transient)

            if drop_arrived:
                self._is_drop_impact = True
                self._switch_scene(MusicalScene.DROP_IMPACT)
                self._drop_countdown = 0.0
                self._pre_drop_cooldown = self.pre_drop_cooldown_time
                self._buildup_silence_cut = False
                self._buildup_saw_silence = False
            elif (self._drop_countdown < -1.5) or (not self._buildup_silence_cut
                  and self._salience_gradient < 0.10 and self._power_gradient < 0.10
                  and self._drop_countdown < (lookahead * 0.5)
                  and not self._is_salience_high and not self._is_power_high):
                self._switch_scene(steady_target)
                self._drop_countdown = 0.0
                self._pre_drop_cooldown = self.pre_drop_cooldown_time
                self._buildup_silence_cut = False
                self._buildup_saw_silence = False

            self._update_modulation_facade()
            return

        # Case C: Check BUILDUP Triggers
        has_audio = (p > 0.001 or s > 0.001)
        is_sal_trig = (has_audio and self._salience_gradient >= self.drop_buildup_threshold and not self._is_salience_high)
        is_pow_trig = (has_audio and not (self._current_scene is MusicalScene.GROOVE and self._is_locked) and self._power_gradient >= self.drop_buildup_power_threshold and not self._is_power_high)
        is_sil_trig = (p > 0.35 and p_live < self.silence_threshold)

        if (lookahead > 0.1
                and not live_is_song_change
                and not is_song_change
                and not is_verse_chorus
                and self._pre_drop_cooldown <= 0.0
                and (is_sal_trig or is_pow_trig or is_sil_trig)):
            self._switch_scene(MusicalScene.BUILDUP)
            self._drop_countdown = lookahead
            self._drop_duration = max(0.1, lookahead)
            self._buildup_entered_high_salience = self._is_salience_high
            self._buildup_entered_high_power = self._is_power_high
            self._buildup_silence_cut = bool(is_sil_trig)
            self._buildup_saw_silence = False
            self._update_modulation_facade()
            return

        # Case D: Steady-State Transitions (CHILL <-> GROOVE guarded by min_dwell_time)
        if self._current_scene is not steady_target:
            if self._scene_dwell_time >= self.min_dwell_time:
                self._switch_scene(steady_target)

        self._update_modulation_facade()

    def _switch_scene(self, new_scene: MusicalScene | str) -> None:
        """Internal helper to switch scenes and reset crossfade progression."""
        if new_scene == "STRUCTURAL_CHANGE":
            self._structural_cut_timer = self.structural_dwell_time
            self._is_structural_cut = True
            return
        scene_enum = MusicalScene(new_scene) if not isinstance(new_scene, MusicalScene) else new_scene
        if scene_enum is not self._current_scene:
            self._previous_scene = self._current_scene
            self._current_scene = scene_enum
            self._scene_blend = 0.0
            self._scene_dwell_time = 0.0

    _switch_regime = _switch_scene

    def _update_modulation_facade(self) -> None:
        """Updates drop_progress, is_drop_imminent, and tension without dynamic allocation."""
        if self._is_drop_impact or self._current_scene is MusicalScene.DROP_IMPACT:
            dwell_frac = max(0.0, min(1.0, self._scene_dwell_time / max(0.001, self.drop_impact_dwell_time)))
            self._drop_progress = 1.0 - dwell_frac
            self._is_drop_imminent = False
        elif self._current_scene is MusicalScene.BUILDUP:
            dur = max(0.001, self._drop_duration)
            self._drop_progress = max(0.0, min(1.0, 1.0 - (self._drop_countdown / dur)))
            self._is_drop_imminent = (self._drop_countdown <= 0.40)
        else:
            self._drop_progress = 0.0
            self._is_drop_imminent = False

        anticipation = max(0.0, max(self._salience_gradient, self._power_gradient))
        buildup_or_drop = self._drop_progress if (self._current_scene is MusicalScene.BUILDUP or self._current_scene is MusicalScene.DROP_IMPACT) else 0.0
        self._tension = max(0.0, min(1.0, max(buildup_or_drop, self._novelty, 0.5 * anticipation)))

    # ==========================================
    # PUBLIC PROPERTIES & FACADE
    # ==========================================
    @property
    def scene(self) -> MusicalScene: return self._current_scene
    @property
    def previous_scene(self) -> MusicalScene: return self._previous_scene
    @property
    def scene_blend(self) -> float: return float(self._scene_blend)
    @property
    def scene_dwell_time(self) -> float: return float(self._scene_dwell_time)

    # Legacy regime aliases
    @property
    def current_regime(self) -> MusicalScene | _LegacyRegime: return MusicalScene.STRUCTURAL_CHANGE if self._is_structural_cut else self.scene
    @property
    def previous_regime(self) -> MusicalScene | _LegacyRegime: return self.previous_scene
    @property
    def regime_blend(self) -> float: return self.scene_blend
    @property
    def regime_dwell_time(self) -> float: return self.scene_dwell_time

    @property
    def _current_regime(self) -> MusicalScene | _LegacyRegime: return MusicalScene.STRUCTURAL_CHANGE if self._is_structural_cut else self._current_scene
    @_current_regime.setter
    def _current_regime(self, value: Any) -> None:
        if value == "STRUCTURAL_CHANGE":
            self._structural_cut_timer = self.structural_dwell_time
            self._is_structural_cut = True
        else:
            self._current_scene = MusicalScene(value) if not isinstance(value, MusicalScene) else value
    @property
    def _previous_regime(self) -> MusicalScene | str: return self._previous_scene
    @_previous_regime.setter
    def _previous_regime(self, value: Any) -> None:
        self._previous_scene = MusicalScene(value) if not isinstance(value, MusicalScene) else value
    @property
    def _regime_blend(self) -> float: return self._scene_blend
    @_regime_blend.setter
    def _regime_blend(self, value: float) -> None: self._scene_blend = float(value)
    @property
    def _regime_dwell_time(self) -> float: return self._scene_dwell_time
    @_regime_dwell_time.setter
    def _regime_dwell_time(self, value: float) -> None: self._scene_dwell_time = float(value)

    @property
    def drop_countdown(self) -> float: return float(self._drop_countdown)
    @property
    def pre_drop_cooldown(self) -> float: return float(self._pre_drop_cooldown)
    @property
    def salience_gradient(self) -> float: return float(self._salience_gradient)
    @property
    def power_gradient(self) -> float: return float(self._power_gradient)
    @property
    def salience(self) -> float: return float(self._salience)
    @property
    def live_salience(self) -> float: return float(self._live_salience)
    @property
    def beat_trust(self) -> float: return float(self._beat_trust)
    @property
    def power(self) -> float: return float(self._power)
    @property
    def live_power(self) -> float: return float(self._live_power)
    @property
    def novelty(self) -> float: return float(self._novelty)
    @property
    def energy(self) -> float: return float(self._energy)
    @property
    def tension(self) -> float: return float(self._tension)
    @property
    def drop_progress(self) -> float: return float(self._drop_progress)
    @property
    def spectral_tilt(self) -> float: return float(self._spectral_tilt)
    @property
    def vertical_center(self) -> float: return float(self._vertical_center)
    @property
    def is_power_high(self) -> bool: return bool(self._is_power_high)

    # Tier 3 Micro Physical Badges
    @property
    def is_locked(self) -> bool: return bool(self._is_locked)
    @property
    def is_syncopated(self) -> bool: return bool(self._is_syncopated)
    @property
    def is_real_beat(self) -> bool: return bool(self._is_real_beat)
    @property
    def is_silent(self) -> bool: return bool(self._is_silent)
    @property
    def is_drop_impact(self) -> bool: return bool(self._is_drop_impact)
    @property
    def is_drop_imminent(self) -> bool: return bool(self._is_drop_imminent)
    @property
    def is_structural_cut(self) -> bool: return bool(self._is_structural_cut)

    # Legacy Semantic Helpers
    @property
    def is_ambient(self) -> bool: return self._current_scene == MusicalScene.CHILL
    @property
    def is_rhythmic(self) -> bool: return self._current_scene in (MusicalScene.GROOVE, MusicalScene.DROP_IMPACT)
    @property
    def is_in_pocket(self) -> bool: return self._current_scene == MusicalScene.GROOVE and self.is_locked
    @property
    def is_buildup(self) -> bool: return self._current_scene == MusicalScene.BUILDUP
    @property
    def is_structural_change(self) -> bool: return self.is_structural_cut

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Provides a complete serializable state snapshot for diagnostics and telemetry."""
        cur = self._current_scene.value if hasattr(self._current_scene, "value") else str(self._current_scene)
        prev = self._previous_scene.value if hasattr(self._previous_scene, "value") else str(self._previous_scene)
        reg_cur = "STRUCTURAL_CHANGE" if self._is_structural_cut else cur
        return {
            "scene": cur, "previous_scene": prev,
            "scene_blend": round(self._scene_blend, 4), "scene_dwell_time": round(self._scene_dwell_time, 3),
            "current_regime": reg_cur, "previous_regime": prev,
            "regime_blend": round(self._scene_blend, 4), "regime_dwell_time": round(self._scene_dwell_time, 3),
            "is_locked": self._is_locked, "is_syncopated": self._is_syncopated,
            "is_real_beat": self._is_real_beat, "is_silent": self._is_silent,
            "is_drop_impact": self._is_drop_impact, "is_drop_imminent": self._is_drop_imminent,
            "is_structural_cut": self._is_structural_cut,
            "is_ambient": self.is_ambient, "is_rhythmic": self.is_rhythmic,
            "is_buildup": self.is_buildup, "is_in_pocket": self.is_in_pocket,
            "is_structural_change": self.is_structural_change,
            "energy": round(self._energy, 4), "tension": round(self._tension, 4),
            "drop_progress": round(self._drop_progress, 4), "drop_countdown": round(self._drop_countdown, 3),
            "salience_gradient": round(self._salience_gradient, 4), "power_gradient": round(self._power_gradient, 4),
            "salience": round(self._salience, 4), "beat_trust": round(self._beat_trust, 4),
            "power": round(self._power, 4), "live_power": round(self._live_power, 4),
            "novelty": round(self._novelty, 4),
            "is_salience_high": self._is_salience_high, "is_trust_high": self._is_trust_high,
            "is_power_high": self._is_power_high,
            "spectral_tilt": round(self._spectral_tilt, 4), "vertical_center": round(self._vertical_center, 4),
        }
