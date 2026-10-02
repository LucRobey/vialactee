"""
tests/test_musical_context_engine.py
Unit tests and governance verification for core/MusicalContextEngine.py (Offer 4):
- Unified 3-Tier Musical Context verification:
  - Tier 1: Continuous Dynamic Kinetics (energy, tension, drop_progress, spectral_tilt, vertical_center, gradients)
  - Tier 2: 4 Macro Scenes (CHILL, GROOVE, BUILDUP, DROP_IMPACT) with Schmitt hysteresis, dwell locks, crossfading
  - Tier 3: Micro Physical Badges (is_locked, is_syncopated, is_real_beat, is_silent, is_drop_impact, is_drop_imminent, is_structural_cut)
- Backward compatibility layer (MusicalRegime alias, legacy helpers, get_state_snapshot)
- AXIOM-01 frame budget (<= 0.15 ms) and AXIOM-02 zero dynamic heap allocation in steady state
"""

import unittest
import time
import tracemalloc
import numpy as np

from core.MusicalContextEngine import MusicalContextEngine, MusicalScene, MusicalRegime
from modes.Beat_runner_mode import Beat_runner_mode
from modes.Impact_shockwave_mode import Impact_shockwave_mode
from modes.Rhythm_breather_mode import Rhythm_breather_mode


class MockListener:
    """Mock Listener exposing the complete contract required by MusicalContextEngine."""

    def __init__(self, lookahead: float = 5.0) -> None:
        self.rhythm_salience = 0.0
        self.live_rhythm_salience = 0.0
        self.beat_trust = 0.0
        self.asserved_total_power = 0.50  # Nominal audio playback power
        self.live_asserved_total_power = 0.50
        self.asserved_novelty = 0.0
        self.asserved_fft_band = np.full(8, 0.5, dtype=np.float64)
        self.is_song_change = False
        self.is_verse_chorus_change = False
        self.live_is_song_change = False
        self.live_is_verse_chorus_change = False
        self.is_beat = False
        self.analyzer = type("MockAnalyzer", (), {"lookahead_seconds": lookahead})()


class TestMusicalContextEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.listener = MockListener(lookahead=5.0)
        self.engine = MusicalContextEngine(self.listener)

    # =========================================================================
    # 1. INITIAL STATE & BACKWARD COMPATIBILITY
    # =========================================================================

    def test_initial_state(self) -> None:
        """Verify initial defaults on engine instantiation across all 3 tiers."""
        # Tier 1 Kinetics
        self.assertEqual(self.engine.energy, 0.0)
        self.assertEqual(self.engine.tension, 0.0)
        self.assertEqual(self.engine.drop_progress, 0.0)
        self.assertEqual(self.engine.spectral_tilt, 0.0)
        self.assertEqual(self.engine.vertical_center, 0.5)
        self.assertEqual(self.engine.salience_gradient, 0.0)
        self.assertEqual(self.engine.power_gradient, 0.0)
        self.assertEqual(self.engine.drop_countdown, 0.0)

        # Tier 2 Macro Scenes
        self.assertEqual(self.engine.scene, MusicalScene.CHILL)
        self.assertEqual(self.engine.previous_scene, MusicalScene.CHILL)
        self.assertEqual(self.engine.scene_blend, 1.0)
        self.assertEqual(self.engine.scene_dwell_time, 0.0)

        # Tier 3 Micro Badges
        self.assertFalse(self.engine.is_locked)
        self.assertFalse(self.engine.is_syncopated)
        self.assertFalse(self.engine.is_real_beat)
        self.assertTrue(self.engine.is_silent)
        self.assertFalse(self.engine.is_drop_impact)
        self.assertFalse(self.engine.is_drop_imminent)
        self.assertFalse(self.engine.is_structural_cut)

        # Backward compatibility properties
        self.assertEqual(self.engine.current_regime, MusicalScene.CHILL)
        self.assertEqual(self.engine.previous_regime, MusicalScene.CHILL)
        self.assertEqual(self.engine.regime_blend, 1.0)
        self.assertEqual(self.engine.regime_dwell_time, 0.0)
        self.assertTrue(self.engine.is_ambient)
        self.assertFalse(self.engine.is_rhythmic)
        self.assertFalse(self.engine.is_buildup)
        self.assertFalse(self.engine.is_in_pocket)
        self.assertFalse(self.engine.is_structural_change)

    def test_backward_compatibility_layer_mappings(self) -> None:
        """Verify legacy MusicalRegime enum aliases and string comparisons."""
        self.assertIs(MusicalRegime, MusicalScene)
        self.assertEqual(MusicalRegime.DEEP_AMBIENT, MusicalScene.CHILL)
        self.assertEqual(MusicalRegime.FLOATING_PULSE, MusicalScene.CHILL)
        self.assertEqual(MusicalRegime.THE_POCKET, MusicalScene.GROOVE)
        self.assertEqual(MusicalRegime.CHAOTIC_FILL, MusicalScene.GROOVE)
        self.assertEqual(MusicalRegime.PRE_DROP_BUILDUP, MusicalScene.BUILDUP)
        self.assertEqual(MusicalRegime.STRUCTURAL_CHANGE, "STRUCTURAL_CHANGE")
        self.assertEqual(MusicalRegime.STRUCTURAL_CHANGE.value, "STRUCTURAL_CHANGE")
        self.assertEqual(MusicalScene.STRUCTURAL_CHANGE.value, "STRUCTURAL_CHANGE")
        self.assertNotEqual(MusicalRegime.STRUCTURAL_CHANGE, MusicalScene.CHILL)

        # String equality with legacy regime names
        self.assertEqual(MusicalScene.CHILL, "DEEP_AMBIENT")
        self.assertEqual(MusicalScene.CHILL, "FLOATING_PULSE")
        self.assertNotEqual(MusicalScene.CHILL, "STRUCTURAL_CHANGE")
        self.assertEqual(MusicalScene.GROOVE, "THE_POCKET")
        self.assertEqual(MusicalScene.GROOVE, "CHAOTIC_FILL")
        self.assertEqual(MusicalScene.BUILDUP, "PRE_DROP_BUILDUP")

    # =========================================================================
    # 2. TIER 1: CONTINUOUS DYNAMIC KINETICS
    # =========================================================================

    def test_fused_master_visual_energy(self) -> None:
        """Verify energy = 0.50*P + 0.30*S + 0.20*(S*T) clamped in [0.0, 1.0]."""
        self.listener.asserved_total_power = 0.60
        self.listener.rhythm_salience = 0.40
        self.listener.beat_trust = 0.50
        self.engine.update(0.1)

        # Expected: 0.50*0.60 + 0.30*0.40 + 0.20*(0.40*0.50) = 0.30 + 0.12 + 0.04 = 0.46
        self.assertAlmostEqual(self.engine.energy, 0.46, places=3)

    def test_spectral_tilt_and_vertical_center(self) -> None:
        """Verify spectral_tilt [-1.0, 1.0] and vertical_center [0.0, 1.0] across 8 bands."""
        # 1. Pure Bass (band 0 only)
        self.listener.asserved_fft_band = np.array([1.0, 0, 0, 0, 0, 0, 0, 0], dtype=np.float64)
        self.engine.update(0.1)
        self.assertAlmostEqual(self.engine.spectral_tilt, -1.0, places=2)
        self.assertAlmostEqual(self.engine.vertical_center, 0.0, places=2)

        # 2. Pure Treble (band 7 only)
        self.listener.asserved_fft_band = np.array([0, 0, 0, 0, 0, 0, 0, 1.0], dtype=np.float64)
        self.engine.update(0.1)
        self.assertAlmostEqual(self.engine.spectral_tilt, 1.0, places=2)
        self.assertAlmostEqual(self.engine.vertical_center, 1.0, places=2)

        # 3. Balanced Spectrum (equal across all 8 bands)
        self.listener.asserved_fft_band = np.full(8, 0.5, dtype=np.float64)
        self.engine.update(0.1)
        self.assertAlmostEqual(self.engine.spectral_tilt, 0.0, places=2)
        self.assertAlmostEqual(self.engine.vertical_center, 0.5, places=2)

        # 4. Silence fallback
        self.listener.asserved_fft_band = np.zeros(8, dtype=np.float64)
        self.engine.update(0.1)
        self.assertAlmostEqual(self.engine.spectral_tilt, 0.0, places=2)
        self.assertAlmostEqual(self.engine.vertical_center, 0.5, places=2)

    def test_tension_curve_and_gradients(self) -> None:
        """Verify tension reflects novelty, anticipation, and buildup curve."""
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        self.listener.asserved_novelty = 0.0
        self.engine.update(0.1)
        self.assertAlmostEqual(self.engine.tension, 0.0, places=2)

        # Novelty drive
        self.listener.asserved_novelty = 0.70
        self.engine.update(0.1)
        self.assertAlmostEqual(self.engine.tension, 0.70, places=2)

        # Salience & Power Gradients
        self.listener.live_rhythm_salience = 0.60
        self.listener.asserved_total_power = 0.20
        self.listener.live_asserved_total_power = 0.50
        self.engine.update(0.1)
        self.assertAlmostEqual(self.engine.salience_gradient, 0.50, places=2)
        self.assertAlmostEqual(self.engine.power_gradient, 0.30, places=2)

    # =========================================================================
    # 3. TIER 2: 4 MACRO SCENES & TRANSITIONS
    # =========================================================================

    def test_macro_scenes_chill_and_groove(self) -> None:
        """Verify CHILL vs GROOVE steady-state transitions guarded by min_dwell_time."""
        dt = 0.05

        # 1. Quiet atmospheric sound -> CHILL
        self.listener.asserved_total_power = 0.02
        self.listener.live_asserved_total_power = 0.02
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        for _ in range(25):
            self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.CHILL)
        self.assertTrue(self.engine.is_ambient)
        self.assertFalse(self.engine.is_rhythmic)

        # 2. Rhythmic beat enters (S >= 0.45 and P >= 0.35) -> GROOVE after dwell
        self.listener.asserved_total_power = 0.60
        self.listener.live_asserved_total_power = 0.60
        self.listener.rhythm_salience = 0.75
        self.listener.live_rhythm_salience = 0.75
        self.listener.beat_trust = 0.80

        # After 1 frame: dwell time from CHILL is >= 1.0s, so switches to GROOVE
        self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.GROOVE)
        self.assertTrue(self.engine.is_rhythmic)
        self.assertTrue(self.engine.is_in_pocket)

        # 3. Dwell guard: quick drop in S cannot switch back to CHILL before 1.0s
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        self.listener.beat_trust = 0.10
        for _ in range(10):  # 0.5s < 1.0s
            self.engine.update(dt)
            self.assertEqual(self.engine.scene, MusicalScene.GROOVE)

        # After remaining frames (> 1.0s dwell), switches back to CHILL
        for _ in range(15):
            self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.CHILL)

    def test_drop_buildup_and_impact_scene_lifecycle(self) -> None:
        """Verify BUILDUP countdown, imminent flag, 1-frame DROP_IMPACT pulse and 1.5s scene dwell."""
        dt = 0.1
        lookahead = 5.0
        self.listener.analyzer.lookahead_seconds = lookahead

        # Start settled in CHILL
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        self.listener.asserved_total_power = 0.20
        self.listener.live_asserved_total_power = 0.20
        for _ in range(15):
            self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.CHILL)

        # Trigger BUILDUP via ΔR = 0.80 - 0.10 = 0.70 >= 0.40
        self.listener.live_rhythm_salience = 0.80
        self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)
        self.assertTrue(self.engine.is_buildup)
        self.assertAlmostEqual(self.engine.drop_countdown, lookahead, places=2)
        self.assertFalse(self.engine.is_drop_impact)
        self.assertFalse(self.engine.is_drop_imminent)

        # Advance until countdown <= 0.40s
        while self.engine.drop_countdown > 0.40:
            self.engine.update(dt)
        self.assertTrue(self.engine.is_drop_imminent)
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)

        # Step until countdown expires (drop lands)
        while self.engine.scene == MusicalScene.BUILDUP and self.engine.drop_countdown > 0.0:
            self.engine.update(dt)

        # Exactly on the impact frame:
        self.assertEqual(self.engine.scene, MusicalScene.DROP_IMPACT)
        self.assertTrue(self.engine.is_drop_impact, "is_drop_impact must fire True on impact frame")
        self.assertAlmostEqual(self.engine.drop_progress, 1.0, places=2)
        self.assertAlmostEqual(self.engine.tension, 1.0, places=2)

        # Next frame: is_drop_impact clears to False, but scene stays in DROP_IMPACT
        self.listener.asserved_total_power = 0.70
        self.engine.update(dt)
        self.assertFalse(self.engine.is_drop_impact, "is_drop_impact must clear to False after 1 frame")
        self.assertEqual(self.engine.scene, MusicalScene.DROP_IMPACT, "Must remain in DROP_IMPACT scene for 1.5s dwell")

        # Advance 1.0s (total dwell 1.1s < 1.5s): remains in DROP_IMPACT
        for _ in range(10):
            self.engine.update(dt)
            self.assertEqual(self.engine.scene, MusicalScene.DROP_IMPACT)

        # Advance past 1.5s dwell: transitions to GROOVE
        for _ in range(6):
            self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.GROOVE)

    def test_drop_impact_transitions_to_chill_if_power_low(self) -> None:
        """Verify DROP_IMPACT transitions to CHILL after 1.5s if power < 0.20."""
        dt = 0.1
        self.listener.analyzer.lookahead_seconds = 2.0
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.80  # ΔR >= 0.40
        self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)

        # Countdown expires
        while self.engine.scene == MusicalScene.BUILDUP and self.engine.drop_countdown > 0.0:
            self.engine.update(dt)

        self.assertEqual(self.engine.scene, MusicalScene.DROP_IMPACT)

        # Keep audio power very low (< 0.20)
        self.listener.asserved_total_power = 0.05
        self.listener.live_asserved_total_power = 0.05
        for _ in range(16):  # 1.6s > 1.5s
            self.engine.update(dt)

        self.assertEqual(self.engine.scene, MusicalScene.CHILL)

    def test_silence_cut_drop_buildup_and_post_silence_surge(self) -> None:
        """Verify pre-drop silence cut triggers buildup and post-silence acoustic surge lands drop."""
        dt = 0.1
        self.listener.analyzer.lookahead_seconds = 5.0
        self.listener.asserved_total_power = 0.60  # Loud playing
        self.listener.live_asserved_total_power = 0.04  # Sudden silence cut 5s ahead
        self.engine.update(dt)

        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)
        self.assertTrue(self.engine.is_buildup)

        # Advance 2.5s: silence-cut buildup survives
        for _ in range(25):
            self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)

        # Speaker enters silence cut
        self.listener.asserved_total_power = 0.02
        self.engine.update(dt)
        self.assertTrue(self.engine.is_silent)
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)

        # Post-silence acoustic surge arrives at speaker
        self.listener.asserved_total_power = 0.85
        self.listener.rhythm_salience = 0.80
        self.engine.update(dt)

        # Must trigger 1-frame drop impact pulse and enter DROP_IMPACT
        self.assertTrue(self.engine.is_drop_impact)
        self.assertEqual(self.engine.scene, MusicalScene.DROP_IMPACT)

    def test_scene_blend_progression(self) -> None:
        """Verify scene_blend starts at 0.0 upon switch and ramps smoothly to 1.0."""
        dt = 0.1
        self.engine.transition_time = 0.5
        self.engine.min_dwell_time = 0.0

        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        self.engine.update(dt)
        self.assertEqual(self.engine.scene_blend, 1.0)

        # Force switch to GROOVE
        self.listener.rhythm_salience = 0.80
        self.listener.live_rhythm_salience = 0.80
        self.listener.beat_trust = 0.80
        self.engine.update(dt)

        self.assertEqual(self.engine.scene, MusicalScene.GROOVE)
        self.assertEqual(self.engine.previous_scene, MusicalScene.CHILL)
        self.assertAlmostEqual(self.engine.scene_blend, 0.0, places=2)

        self.engine.update(dt)
        self.assertAlmostEqual(self.engine.scene_blend, 0.2, places=2)

        for _ in range(4):
            self.engine.update(dt)
        self.assertAlmostEqual(self.engine.scene_blend, 1.0, places=2)

    def test_zero_lookahead_disarms_buildup(self) -> None:
        """Verify that when lookahead_seconds <= 0.0, BUILDUP does not trigger (0-lookahead live mic)."""
        self.listener.analyzer.lookahead_seconds = 0.0
        self.listener.live_rhythm_salience = 0.90
        self.listener.rhythm_salience = 0.10
        self.listener.live_asserved_total_power = 0.90
        self.listener.asserved_total_power = 0.10
        self.engine.update(0.1)

        self.assertNotEqual(self.engine.scene, MusicalScene.BUILDUP)
        self.assertFalse(self.engine.is_buildup)
        self.assertEqual(self.engine.drop_countdown, 0.0)

    def test_drop_impact_kinetic_decay(self) -> None:
        """Verify drop_progress and tension smoothly decay from 1.0 to 0.0 across 1.5s DROP_IMPACT dwell."""
        dt = 0.1
        self.listener.analyzer.lookahead_seconds = 2.0
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.80
        self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)

        # Step until drop lands
        while self.engine.scene == MusicalScene.BUILDUP and self.engine.drop_countdown > 0.0:
            self.engine.update(dt)

        # Frame 1: Impact frame
        self.assertEqual(self.engine.scene, MusicalScene.DROP_IMPACT)
        self.assertTrue(self.engine.is_drop_impact)
        self.assertAlmostEqual(self.engine.drop_progress, 1.0, places=2)
        self.assertAlmostEqual(self.engine.tension, 1.0, places=2)

        # Frame 2: 1-frame badge clears, but drop_progress and tension must sustain and decay smoothly
        self.engine.update(dt)
        self.assertFalse(self.engine.is_drop_impact)
        self.assertEqual(self.engine.scene, MusicalScene.DROP_IMPACT)
        self.assertGreater(self.engine.drop_progress, 0.85, "drop_progress must not collapse to 0.0 on frame 2")
        self.assertLess(self.engine.drop_progress, 1.0)
        self.assertGreater(self.engine.tension, 0.85, "tension must not collapse to 0.0 on frame 2")

        # Halfway through dwell (0.7s - 0.8s)
        for _ in range(6):
            self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.DROP_IMPACT)
        self.assertAlmostEqual(self.engine.drop_progress, 0.50, delta=0.15)
        self.assertAlmostEqual(self.engine.tension, 0.50, delta=0.15)

        # Past 1.5s dwell: exits DROP_IMPACT
        for _ in range(10):
            self.engine.update(dt)
        self.assertNotEqual(self.engine.scene, MusicalScene.DROP_IMPACT)
        self.assertEqual(self.engine.drop_progress, 0.0)

    def test_buildup_riser_immunity(self) -> None:
        """Verify volume/salience risers during BUILDUP do not prematurely trip drop_arrived while countdown > 0.40s."""
        dt = 0.1
        self.listener.analyzer.lookahead_seconds = 5.0
        self.listener.asserved_total_power = 0.20
        self.listener.live_asserved_total_power = 0.70  # ΔP >= 0.35 triggers BUILDUP
        self.engine.update(dt)

        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)
        self.assertAlmostEqual(self.engine.drop_countdown, 5.0, places=2)

        # Advance 1.0s: countdown = 4.0s > 0.40s
        for _ in range(10):
            self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)

        # Crescendo riser: power and salience surge at speakers during buildup
        self.listener.asserved_total_power = 0.80  # Loud crescendo riser
        self.listener.rhythm_salience = 0.85       # Snare roll riser
        self.engine.update(dt)

        # Must NOT trip drop_arrived prematurely!
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP, "Crescendo riser must not trip drop prematurely")
        self.assertFalse(self.engine.is_drop_impact)
        self.assertGreater(self.engine.drop_countdown, 3.0)

        # Advance until imminent window (<= 0.40s) and expiration
        while self.engine.scene == MusicalScene.BUILDUP and self.engine.drop_countdown > 0.0:
            self.engine.update(dt)

        # Drop lands upon natural countdown expiration
        self.assertEqual(self.engine.scene, MusicalScene.DROP_IMPACT)
        self.assertTrue(self.engine.is_drop_impact)

    def test_buildup_riser_immunity_from_silence(self) -> None:
        """Verify volume risers starting from silence do NOT prematurely trip drop_arrived."""
        dt = 0.1
        self.listener.analyzer.lookahead_seconds = 5.0
        self.listener.asserved_total_power = 0.02
        self.listener.live_asserved_total_power = 0.02
        self.listener.rhythm_salience = 0.0
        self.listener.live_rhythm_salience = 0.0
        for _ in range(20):
            self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.CHILL)
        self.assertTrue(self.engine.is_silent)

        # Lookahead triggers buildup 5s ahead
        self.listener.live_asserved_total_power = 0.80
        self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)

        # Still silent at speaker for 2 frames
        self.engine.update(dt)
        self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)

        # Volume riser starts at speakers (power rises from 0.02 to 0.65)
        self.listener.asserved_total_power = 0.65
        self.engine.update(dt)

        # Must remain in BUILDUP and not trip premature drop impact!
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)
        self.assertFalse(self.engine.is_drop_impact)
        self.assertGreater(self.engine.drop_countdown, 3.5)

    def test_song_change_cancels_active_buildup(self) -> None:
        """Verify song change / verse chorus at speaker cancels active BUILDUP and arms cooldown."""
        dt = 0.1
        self.listener.analyzer.lookahead_seconds = 5.0
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.80
        self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)

        # Advance 1.5s into buildup
        for _ in range(15):
            self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.BUILDUP)

        # Song change occurs at speaker
        self.listener.is_song_change = True
        self.engine.update(dt)

        # Active buildup must be canceled immediately
        self.assertNotEqual(self.engine.scene, MusicalScene.BUILDUP)
        self.assertFalse(self.engine.is_buildup)
        self.assertEqual(self.engine.drop_countdown, 0.0)
        self.assertTrue(self.engine.is_structural_cut)
        self.assertEqual(self.engine.current_regime, "STRUCTURAL_CHANGE")
        self.assertEqual(self.engine.current_regime.value, "STRUCTURAL_CHANGE")

    def test_lookahead_song_change_prevents_false_buildup(self) -> None:
        """Verify live_is_song_change in lookahead audio prevents incoming track spikes from triggering BUILDUP."""
        dt = 0.1
        self.listener.analyzer.lookahead_seconds = 5.0
        # Speaker and lookahead both playing quiet outro of song 1
        self.listener.asserved_total_power = 0.10
        self.listener.live_asserved_total_power = 0.10
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        for _ in range(15):
            self.engine.update(dt)
        self.assertEqual(self.engine.scene, MusicalScene.CHILL)

        # Song 2 arrives in lookahead with massive power surge, but unbuffered detector flags live_is_song_change
        self.listener.live_asserved_total_power = 0.90  # ΔP = 0.80 >= 0.35
        self.listener.live_rhythm_salience = 0.80       # ΔR = 0.70 >= 0.40
        self.listener.live_is_song_change = True
        self.engine.update(dt)

        # Must NOT trigger BUILDUP
        self.assertNotEqual(self.engine.scene, MusicalScene.BUILDUP)
        self.assertFalse(self.engine.is_buildup)
        self.assertEqual(self.engine.drop_countdown, 0.0)

    # =========================================================================
    # 4. TIER 3: MICRO PHYSICAL BADGES
    # =========================================================================

    def test_micro_badge_is_locked(self) -> None:
        """Verify is_locked Schmitt trigger: True when T >= 0.50, False when T < 0.35."""
        dt = 0.05
        self.listener.beat_trust = 0.20
        self.engine.update(dt)
        self.assertFalse(self.engine.is_locked)

        # Inside deadband [0.35, 0.50]
        self.listener.beat_trust = 0.42
        self.engine.update(dt)
        self.assertFalse(self.engine.is_locked)

        # Cross 0.50 -> Latches True
        self.listener.beat_trust = 0.55
        self.engine.update(dt)
        self.assertTrue(self.engine.is_locked)

        # Fall into deadband -> Stays True
        self.listener.beat_trust = 0.42
        self.engine.update(dt)
        self.assertTrue(self.engine.is_locked)

        # Fall below 0.35 -> Drops to False
        self.listener.beat_trust = 0.30
        self.engine.update(dt)
        self.assertFalse(self.engine.is_locked)

    def test_micro_badge_is_syncopated(self) -> None:
        """Verify is_syncopated: True when S >= 0.45 and T < 0.35 (breakcore/syncopation)."""
        dt = 0.05
        # High S, High T -> Locked groove, not syncopated
        self.listener.rhythm_salience = 0.80
        self.listener.beat_trust = 0.80
        self.engine.update(dt)
        self.assertFalse(self.engine.is_syncopated)

        # High S, Low T -> Syncopated / drum fill
        self.listener.beat_trust = 0.20
        self.engine.update(dt)
        self.assertTrue(self.engine.is_syncopated)

        # Low S, Low T -> Ambient drift, not syncopated
        self.listener.rhythm_salience = 0.20
        self.engine.update(dt)
        self.assertFalse(self.engine.is_syncopated)

    def test_micro_badge_is_real_beat(self) -> None:
        """Verify is_real_beat: True when is_beat is True and P >= 0.20."""
        # 1. is_beat False
        self.listener.is_beat = False
        self.listener.asserved_total_power = 0.60
        self.engine.update(0.1)
        self.assertFalse(self.engine.is_real_beat)

        # 2. is_beat True but low acoustic power
        self.listener.is_beat = True
        self.listener.asserved_total_power = 0.10
        self.engine.update(0.1)
        self.assertFalse(self.engine.is_real_beat)

        # 3. is_beat True and acoustic power >= 0.20
        self.listener.asserved_total_power = 0.50
        self.engine.update(0.1)
        self.assertTrue(self.engine.is_real_beat)

    def test_micro_badge_is_silent(self) -> None:
        """Verify is_silent: True when P < 0.05, False when P >= 0.08."""
        dt = 0.05
        self.listener.asserved_total_power = 0.02
        self.engine.update(dt)
        self.assertTrue(self.engine.is_silent)

        # Inside deadband [0.05, 0.08] remains silent
        self.listener.asserved_total_power = 0.06
        self.engine.update(dt)
        self.assertTrue(self.engine.is_silent)

        # Cross 0.08 -> Exits silence
        self.listener.asserved_total_power = 0.12
        self.engine.update(dt)
        self.assertFalse(self.engine.is_silent)

        # Fall into deadband -> Stays non-silent
        self.listener.asserved_total_power = 0.06
        self.engine.update(dt)
        self.assertFalse(self.engine.is_silent)

        # Fall below 0.05 -> Latches silence
        self.listener.asserved_total_power = 0.03
        self.engine.update(dt)
        self.assertTrue(self.engine.is_silent)

    def test_micro_badge_is_structural_cut(self) -> None:
        """Verify is_structural_cut: True for 1.2s dwell upon is_song_change or is_verse_chorus_change."""
        dt = 0.1
        self.engine.structural_dwell_time = 1.2

        self.assertFalse(self.engine.is_structural_cut)

        # Trigger song change
        self.listener.is_song_change = True
        self.engine.update(dt)
        self.assertTrue(self.engine.is_structural_cut)
        self.assertTrue(self.engine.is_structural_change)

        self.listener.is_song_change = False
        # Advance 1.0s (dwell not expired)
        for _ in range(10):
            self.engine.update(dt)
            self.assertTrue(self.engine.is_structural_cut)

        # Advance past 1.2s
        for _ in range(4):
            self.engine.update(dt)
        self.assertFalse(self.engine.is_structural_cut)
        self.assertFalse(self.engine.is_structural_change)

    # =========================================================================
    # 5. STATE SNAPSHOT & TELEMETRY
    # =========================================================================

    def test_state_snapshot_contains_all_tiers_and_legacy_keys(self) -> None:
        """Verify get_state_snapshot() contains all Tier 1, 2, 3 and legacy keys."""
        snap = self.engine.get_state_snapshot()
        expected_keys = {
            # Tier 2 Macro Scenes
            "scene", "previous_scene", "scene_blend", "scene_dwell_time",
            # Legacy regime keys
            "current_regime", "previous_regime", "regime_blend", "regime_dwell_time",
            # Tier 3 Micro Physical Badges
            "is_locked", "is_syncopated", "is_real_beat", "is_silent",
            "is_drop_impact", "is_drop_imminent", "is_structural_cut",
            # Legacy helpers
            "is_ambient", "is_rhythmic", "is_buildup", "is_in_pocket", "is_structural_change",
            # Tier 1 Dynamic Kinetics & Ingested Scalars
            "energy", "tension", "drop_progress", "drop_countdown",
            "salience_gradient", "power_gradient", "salience", "beat_trust",
            "power", "live_power", "novelty", "is_salience_high",
            "is_trust_high", "is_power_high", "spectral_tilt", "vertical_center"
        }
        self.assertEqual(set(snap.keys()), expected_keys)
        self.assertIsInstance(snap["scene"], str)
        self.assertIsInstance(snap["energy"], float)
        self.assertIsInstance(snap["tension"], float)
        self.assertIsInstance(snap["is_locked"], bool)
        self.assertIsInstance(snap["is_syncopated"], bool)
        self.assertIsInstance(snap["is_real_beat"], bool)

    # =========================================================================
    # 6. RESET & ROBUSTNESS
    # =========================================================================

    def test_reset_restores_all_tiers(self) -> None:
        """Verify reset() restores defaults across all 3 tiers."""
        self.listener.rhythm_salience = 0.90
        self.listener.live_rhythm_salience = 0.90
        self.listener.beat_trust = 0.90
        self.listener.asserved_total_power = 0.90
        for _ in range(25):
            self.engine.update(0.05)
        self.assertEqual(self.engine.scene, MusicalScene.GROOVE)
        self.assertTrue(self.engine.is_locked)

        self.engine.reset()
        self.assertEqual(self.engine.scene, MusicalScene.CHILL)
        self.assertEqual(self.engine.previous_scene, MusicalScene.CHILL)
        self.assertEqual(self.engine.scene_blend, 1.0)
        self.assertEqual(self.engine.energy, 0.0)
        self.assertFalse(self.engine.is_locked)
        self.assertTrue(self.engine.is_silent)

    def test_edge_cases_nan_and_bounds(self) -> None:
        """Verify robustness against NaN, infinite, negative, and None inputs."""
        self.listener.rhythm_salience = float("nan")
        self.listener.live_rhythm_salience = float("nan")
        self.listener.beat_trust = float("nan")
        self.listener.asserved_total_power = float("nan")
        self.listener.live_asserved_total_power = float("nan")
        self.listener.asserved_novelty = float("nan")
        self.engine.update(0.0)

        self.assertEqual(self.engine.salience, 0.0)
        self.assertEqual(self.engine.beat_trust, 0.0)
        self.assertEqual(self.engine.power, 0.0)

        # None inputs
        self.listener.rhythm_salience = None
        self.listener.live_rhythm_salience = None
        self.listener.beat_trust = None
        self.listener.asserved_total_power = None
        self.listener.asserved_fft_band = None
        self.listener.fft_band_values = None
        self.engine.update(0.1)

        self.assertEqual(self.engine.salience, 0.0)
        self.assertEqual(self.engine.power, 0.0)
        self.assertEqual(self.engine.spectral_tilt, 0.0)
        self.assertEqual(self.engine.vertical_center, 0.5)

    # =========================================================================
    # 7. GOVERNANCE: AXIOM-01 & AXIOM-02
    # =========================================================================

    def test_axiom_01_frame_budget(self) -> None:
        """Verify MusicalContextEngine.update() executes in <= 0.15 ms per frame (AXIOM-01)."""
        for _ in range(50):
            self.engine.update(1 / 60)

        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            self.engine.update(1 / 60)
        elapsed_sec = time.perf_counter() - start
        avg_time_ms = (elapsed_sec / iterations) * 1000.0

        self.assertLess(avg_time_ms, 0.15, f"Engine frame budget exceeded: {avg_time_ms:.4f} ms > 0.15 ms")

    def test_axiom_02_zero_dynamic_allocation_in_steady_state(self) -> None:
        """Verify zero dynamic heap memory allocations during update() hot path (AXIOM-02)."""
        # Warm up past 1.0s dwell time so steady state is settled
        for _ in range(80):
            self.engine.update(1 / 60)

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        for _ in range(50):
            self.engine.update(1 / 60)

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
        engine_stats = [
            stat for stat in top_stats
            if "MusicalContextEngine.py" in stat.traceback[0].filename
        ]
        total_allocated_bytes = sum(stat.size_diff for stat in engine_stats if stat.size_diff > 0)
        self.assertEqual(
            total_allocated_bytes, 0,
            f"AXIOM-02 violation: {total_allocated_bytes} bytes allocated in hot path:\n"
            + "\n".join(str(s) for s in engine_stats)
        )

    def test_pilot_modes_drop_impact_dwell_decay(self) -> None:
        """Verify Beat_runner, Impact_shockwave, and Rhythm_breather sustain kinetic intensity across DROP_IMPACT dwell."""
        self.listener.context = self.engine
        rgb_runner = np.zeros((80, 3), dtype=np.int32)
        mode_runner = Beat_runner_mode("Runner", "s1", self.listener, None, list(range(80)), rgb_runner, {})

        rgb_shockwave = np.zeros((80, 3), dtype=np.int32)
        mode_shockwave = Impact_shockwave_mode("Shockwave", "s2", self.listener, None, list(range(80)), rgb_shockwave, {})

        rgb_breather = np.zeros((80, 3), dtype=np.int32)
        mode_breather = Rhythm_breather_mode("Breather", "s3", self.listener, None, list(range(80)), rgb_breather, {})

        # Trigger drop
        self.listener.analyzer.lookahead_seconds = 2.0
        self.listener.live_rhythm_salience = 0.80
        self.engine.update(0.1)
        while self.engine.scene == MusicalScene.BUILDUP and self.engine.drop_countdown > 0.0:
            self.engine.update(0.1)

        # Frame 1: Impact frame
        self.assertEqual(self.engine.scene, MusicalScene.DROP_IMPACT)
        self.assertTrue(self.engine.is_drop_impact)
        mode_runner.run()
        mode_shockwave.run()
        mode_breather.run()
        f1_runner_max = float(np.max(mode_runner.vals))
        f1_shock_glow = float(mode_shockwave.half_intensity[0])
        self.assertGreaterEqual(f1_runner_max, 0.90)
        self.assertGreaterEqual(f1_shock_glow, 0.40)

        # Frame 2: is_drop_impact badge clears, but engine is in DROP_IMPACT dwell
        self.engine.update(0.1)
        self.assertFalse(self.engine.is_drop_impact)
        self.assertEqual(self.engine.scene, MusicalScene.DROP_IMPACT)
        self.assertGreater(self.engine.drop_progress, 0.85)

        mode_runner.run()
        mode_shockwave.run()
        mode_breather.run()
        f2_runner_max = float(np.max(mode_runner.vals))
        f2_shock_glow = float(mode_shockwave.half_intensity[0])

        # Verify sustained flare across dwell (must NOT collapse to zero!)
        self.assertGreater(f2_runner_max, 0.70, "Beat_runner flare must sustain across dwell")
        self.assertGreater(f2_shock_glow, 0.35, "Impact_shockwave core glow must sustain across dwell")

        # Step past 1.5s dwell: exits DROP_IMPACT
        for _ in range(16):
            self.engine.update(0.1)
        self.assertNotEqual(self.engine.scene, MusicalScene.DROP_IMPACT)
        self.assertEqual(self.engine.drop_progress, 0.0)


if __name__ == "__main__":
    unittest.main()
