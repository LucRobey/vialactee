"""
tests/test_musical_context_engine.py
Unit tests and governance verification for core/MusicalContextEngine.py:
- Canonical 6-regime state transitions
- Schmitt trigger hysteresis & anti-flicker deadbands
- Minimum dwell time enforcement
- Lookahead salience gradient (ΔR) and pre-drop countdown
- Structural change priority override & dwell
- Regime blend crossfading [0.0, 1.0]
- AXIOM-01 frame budget (<= 0.15 ms)
- AXIOM-02 zero dynamic heap allocation in steady state
"""

import unittest
import time
import tracemalloc
import numpy as np

from core.MusicalContextEngine import MusicalContextEngine, MusicalRegime


class MockListener:
    """Mock Listener exposing the minimal contract required by MusicalContextEngine."""

    def __init__(self, lookahead: float = 5.0) -> None:
        self.rhythm_salience = 0.0
        self.live_rhythm_salience = 0.0
        self.beat_trust = 0.0
        self.asserved_total_power = 0.0
        self.asserved_novelty = 0.0
        self.is_song_change = False
        self.is_verse_chorus_change = False
        self.analyzer = type("MockAnalyzer", (), {"lookahead_seconds": lookahead})()


class TestMusicalContextEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.listener = MockListener(lookahead=5.0)
        self.engine = MusicalContextEngine(self.listener)

    def test_initial_state(self) -> None:
        """Verify initial defaults on engine instantiation."""
        self.assertEqual(self.engine.current_regime, MusicalRegime.DEEP_AMBIENT)
        self.assertEqual(self.engine.previous_regime, MusicalRegime.DEEP_AMBIENT)
        self.assertEqual(self.engine.regime_blend, 1.0)
        self.assertEqual(self.engine.drop_countdown, 0.0)
        self.assertEqual(self.engine.salience_gradient, 0.0)
        self.assertEqual(self.engine.regime_dwell_time, 0.0)
        self.assertTrue(self.engine.is_ambient)
        self.assertFalse(self.engine.is_rhythmic)
        self.assertFalse(self.engine.is_buildup)
        self.assertFalse(self.engine.is_in_pocket)
        self.assertFalse(self.engine.is_structural_change)

    def test_steady_state_matrix_transitions(self) -> None:
        """Verify all 4 steady-state quadrants after min_dwell_time."""
        dt = 0.05  # 50ms per frame

        # Quadrant 1: DEEP_AMBIENT (Low S, Low T)
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        self.listener.beat_trust = 0.10
        for _ in range(25):  # 1.25s > 1.0s dwell
            self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.DEEP_AMBIENT)
        self.assertTrue(self.engine.is_ambient)

        # Quadrant 2: FLOATING_PULSE (Low S, High T)
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        self.listener.beat_trust = 0.80
        for _ in range(25):  # 1.25s > 1.0s dwell
            self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.FLOATING_PULSE)
        self.assertTrue(self.engine.is_ambient)

        # Quadrant 3: THE_POCKET (High S, High T)
        self.listener.rhythm_salience = 0.80
        self.listener.live_rhythm_salience = 0.80
        self.listener.beat_trust = 0.80
        for _ in range(25):  # 1.25s > 1.0s dwell
            self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.THE_POCKET)
        self.assertTrue(self.engine.is_rhythmic)
        self.assertTrue(self.engine.is_in_pocket)

        # Quadrant 4: CHAOTIC_FILL (High S, Low T)
        self.listener.rhythm_salience = 0.80
        self.listener.live_rhythm_salience = 0.80
        self.listener.beat_trust = 0.10
        for _ in range(25):  # 1.25s > 1.0s dwell
            self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.CHAOTIC_FILL)
        self.assertTrue(self.engine.is_rhythmic)
        self.assertFalse(self.engine.is_in_pocket)

    def test_schmitt_trigger_hysteresis(self) -> None:
        """Verify that deadband [0.35, 0.45] for S and [0.35, 0.50] for T prevents chattering."""
        dt = 0.05
        # Set low state initially
        self.listener.rhythm_salience = 0.20
        self.listener.live_rhythm_salience = 0.20
        self.listener.beat_trust = 0.20
        for _ in range(25):
            self.engine.update(dt)
        self.assertFalse(self.engine._is_salience_high)
        self.assertFalse(self.engine._is_trust_high)

        # Move into deadband [0.35, 0.45]
        self.listener.rhythm_salience = 0.40
        self.listener.live_rhythm_salience = 0.40
        self.engine.update(dt)
        self.assertFalse(self.engine._is_salience_high, "Must remain False inside deadband before high threshold")

        # Exceed salience_high (0.45)
        self.listener.rhythm_salience = 0.48
        self.listener.live_rhythm_salience = 0.48
        self.engine.update(dt)
        self.assertTrue(self.engine._is_salience_high, "Must latch True once above high threshold")

        # Drop back into deadband (0.40)
        self.listener.rhythm_salience = 0.40
        self.listener.live_rhythm_salience = 0.40
        self.engine.update(dt)
        self.assertTrue(self.engine._is_salience_high, "Must remain True inside deadband after latching high")

        # Fall below salience_low (0.35)
        self.listener.rhythm_salience = 0.30
        self.listener.live_rhythm_salience = 0.30
        self.engine.update(dt)
        self.assertFalse(self.engine._is_salience_high, "Must drop to False when falling below low threshold")

    def test_minimum_dwell_time(self) -> None:
        """Verify that steady-state regime transitions are locked until min_dwell_time passes."""
        dt = 0.1
        self.engine.min_dwell_time = 1.0

        # Start in DEEP_AMBIENT
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        self.listener.beat_trust = 0.10
        for _ in range(15):  # 1.5s
            self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.DEEP_AMBIENT)

        # Switch input to THE_POCKET (S=0.8, T=0.8)
        self.listener.rhythm_salience = 0.80
        self.listener.live_rhythm_salience = 0.80
        self.listener.beat_trust = 0.80

        # Run 1 frame (0.1s dwell): must NOT switch yet
        self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.THE_POCKET)  # Note: previous state had dwelt 1.5s >= 1.0s, so it switches!

        # Now we are in THE_POCKET with dwell time = 0.1s.
        # Switch input to CHAOTIC_FILL (S=0.8, T=0.1)
        self.listener.beat_trust = 0.10
        # For 5 frames (0.5s < 1.0s): must remain THE_POCKET
        for _ in range(5):
            self.engine.update(dt)
            self.assertEqual(self.engine.current_regime, MusicalRegime.THE_POCKET, "Must not switch before dwell expires")

        # For another 6 frames (total 1.1s > 1.0s): now it switches
        for _ in range(6):
            self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.CHAOTIC_FILL)

    def test_lookahead_pre_drop_buildup(self) -> None:
        """Verify PRE_DROP_BUILDUP trigger on ΔR >= 0.40, countdown decrement, and drop transition."""
        dt = 0.1
        lookahead = 5.0
        self.listener.analyzer.lookahead_seconds = lookahead

        # Start in quiet ambient: delayed S=0.10, live S=0.10
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        self.listener.beat_trust = 0.10
        for _ in range(15):
            self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.DEEP_AMBIENT)

        # Lookahead detector spots incoming drop! live S spikes to 0.85, delayed S is still 0.10
        # ΔR = 0.85 - 0.10 = 0.75 >= 0.40
        self.listener.live_rhythm_salience = 0.85
        self.engine.update(dt)

        self.assertEqual(self.engine.current_regime, MusicalRegime.PRE_DROP_BUILDUP)
        self.assertTrue(self.engine.is_buildup)
        self.assertAlmostEqual(self.engine.drop_countdown, lookahead, places=2)
        self.assertAlmostEqual(self.engine.salience_gradient, 0.75, places=2)

        # Advance 2 seconds of countdown
        for _ in range(20):  # 20 * 0.1s = 2.0s
            self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.PRE_DROP_BUILDUP)
        self.assertAlmostEqual(self.engine.drop_countdown, 3.0, places=1)

        # Drop arrives! Speaker audio catches up to lookahead stream:
        self.listener.rhythm_salience = 0.85
        self.listener.beat_trust = 0.80

        # Advance until countdown expires (3.0s more)
        for _ in range(35):
            self.engine.update(dt)

        # When countdown hits 0, it transitions to THE_POCKET
        self.assertEqual(self.engine.current_regime, MusicalRegime.THE_POCKET)
        self.assertEqual(self.engine.drop_countdown, 0.0)

    def test_structural_change_priority_and_dwell(self) -> None:
        """Verify that is_song_change interrupts any regime and dwells for structural_dwell_time."""
        dt = 0.1
        self.engine.structural_dwell_time = 1.0

        # Start in THE_POCKET
        self.listener.rhythm_salience = 0.80
        self.listener.live_rhythm_salience = 0.80
        self.listener.beat_trust = 0.80
        for _ in range(15):
            self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.THE_POCKET)

        # Fire is_song_change
        self.listener.is_song_change = True
        self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.STRUCTURAL_CHANGE)
        self.assertTrue(self.engine.is_structural_change)
        self.assertEqual(self.engine.previous_regime, MusicalRegime.THE_POCKET)

        # Reset flag (as Listener does each frame)
        self.listener.is_song_change = False

        # During structural dwell (e.g. 5 frames = 0.5s < 1.0s), must stay in STRUCTURAL_CHANGE
        for _ in range(5):
            self.engine.update(dt)
            self.assertEqual(self.engine.current_regime, MusicalRegime.STRUCTURAL_CHANGE)

        # After dwell expires (6 more frames = 1.1s > 1.0s), transitions back to THE_POCKET
        for _ in range(6):
            self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.THE_POCKET)

    def test_chaotic_drop_arrival_exits_buildup_immediately(self) -> None:
        """Verify that drop arrival (S >= 0.45) with low trust (T < 0.35) immediately exits buildup to CHAOTIC_FILL."""
        dt = 0.1
        lookahead = 5.0
        self.listener.analyzer.lookahead_seconds = lookahead

        # Start in DEEP_AMBIENT
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        self.listener.beat_trust = 0.10
        for _ in range(15):
            self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.DEEP_AMBIENT)

        # Trigger PRE_DROP_BUILDUP
        self.listener.live_rhythm_salience = 0.85
        self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.PRE_DROP_BUILDUP)
        self.assertAlmostEqual(self.engine.drop_countdown, 5.0, places=2)

        # Drop arrives at speaker with high salience (0.85) but LOW trust (0.20) -> CHAOTIC_FILL
        self.listener.rhythm_salience = 0.85
        self.listener.live_rhythm_salience = 0.85
        self.listener.beat_trust = 0.20

        # On the very first frame of drop arrival, it must immediately transition to CHAOTIC_FILL
        self.engine.update(dt)
        self.assertEqual(
            self.engine.current_regime, MusicalRegime.CHAOTIC_FILL,
            "Must exit PRE_DROP_BUILDUP immediately upon drop arrival even if beat trust is low"
        )
        self.assertAlmostEqual(self.engine.drop_countdown, 0.0)

    def test_structural_change_retrigger_resets_dwell_and_blend(self) -> None:
        """Verify that a subsequent structural event during STRUCTURAL_CHANGE resets dwell and blend."""
        dt = 0.1
        self.engine.structural_dwell_time = 1.0

        # Trigger first structural change
        self.listener.is_song_change = True
        self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.STRUCTURAL_CHANGE)
        self.assertEqual(self.engine.regime_dwell_time, 0.0)
        self.listener.is_song_change = False

        # Advance 0.8s
        for _ in range(8):
            self.engine.update(dt)
        self.assertAlmostEqual(self.engine.regime_dwell_time, 0.8, places=2)

        # Second structural event fires: is_verse_chorus_change = True
        self.listener.is_verse_chorus_change = True
        self.engine.update(dt)
        self.assertEqual(self.engine.current_regime, MusicalRegime.STRUCTURAL_CHANGE)
        # Dwell time must be reset to 0.0 so the new section gets its full dwell duration
        self.assertEqual(self.engine.regime_dwell_time, 0.0)
        self.assertEqual(self.engine.regime_blend, 0.0)

    def test_regime_blend_progression(self) -> None:
        """Verify regime_blend starts at 0.0 upon switch and ramps smoothly to 1.0."""
        dt = 0.1
        self.engine.transition_time = 0.5
        self.engine.min_dwell_time = 0.0  # allow immediate transition for test

        # Start in DEEP_AMBIENT
        self.listener.rhythm_salience = 0.10
        self.listener.live_rhythm_salience = 0.10
        self.listener.beat_trust = 0.10
        self.engine.update(dt)
        self.assertEqual(self.engine.regime_blend, 1.0)

        # Force switch to THE_POCKET
        self.listener.rhythm_salience = 0.80
        self.listener.live_rhythm_salience = 0.80
        self.listener.beat_trust = 0.80
        self.engine.update(dt)

        self.assertEqual(self.engine.current_regime, MusicalRegime.THE_POCKET)
        self.assertEqual(self.engine.previous_regime, MusicalRegime.DEEP_AMBIENT)
        # On exact frame of switch: blend is 0.0
        self.assertAlmostEqual(self.engine.regime_blend, 0.0, places=2)

        # Step next frame: advances by dt / 0.5 = 0.1 / 0.5 = 0.2
        self.engine.update(dt)
        self.assertAlmostEqual(self.engine.regime_blend, 0.2, places=2)

        # Step remaining 4 frames to reach 1.0 (total 0.5s)
        for _ in range(4):
            self.engine.update(dt)
        self.assertAlmostEqual(self.engine.regime_blend, 1.0, places=2)

    def test_reset_clears_state(self) -> None:
        """Verify reset() restores initial state."""
        self.listener.rhythm_salience = 0.90
        self.listener.live_rhythm_salience = 0.90
        self.listener.beat_trust = 0.90
        for _ in range(20):
            self.engine.update(0.1)
        self.assertEqual(self.engine.current_regime, MusicalRegime.THE_POCKET)

        self.engine.reset()
        self.assertEqual(self.engine.current_regime, MusicalRegime.DEEP_AMBIENT)
        self.assertEqual(self.engine.previous_regime, MusicalRegime.DEEP_AMBIENT)
        self.assertEqual(self.engine.regime_blend, 1.0)
        self.assertEqual(self.engine.regime_dwell_time, 0.0)
        self.assertEqual(self.engine.drop_countdown, 0.0)
        self.assertEqual(self.engine.salience_gradient, 0.0)

    def test_edge_cases_nan_and_bounds(self) -> None:
        """Verify robustness against NaN, negative, out-of-range, and zero/negative dt."""
        self.listener.rhythm_salience = float("nan")
        self.listener.live_rhythm_salience = float("nan")
        self.listener.beat_trust = float("nan")
        # Must not raise exceptions
        self.engine.update(0.0)
        self.assertAlmostEqual(self.engine.salience, 0.0)
        self.assertAlmostEqual(self.engine.beat_trust, 0.0)

        # Out-of-bounds clamping
        self.listener.rhythm_salience = 5.0
        self.listener.live_rhythm_salience = -2.0
        self.listener.beat_trust = 10.0
        self.engine.update(-0.05)
        self.assertAlmostEqual(self.engine.salience, 1.0)
        self.assertAlmostEqual(self.engine.beat_trust, 1.0)

    def test_state_snapshot_serializable(self) -> None:
        """Verify get_state_snapshot() returns all required keys and valid types."""
        snap = self.engine.get_state_snapshot()
        expected_keys = {
            "current_regime", "previous_regime", "regime_blend",
            "regime_dwell_time", "drop_countdown", "salience_gradient",
            "salience", "beat_trust", "power", "novelty",
            "is_salience_high", "is_trust_high"
        }
        self.assertEqual(set(snap.keys()), expected_keys)
        self.assertIsInstance(snap["current_regime"], str)
        self.assertIsInstance(snap["regime_blend"], float)

    def test_power_and_novelty_ingestion(self) -> None:
        """Verify power and novelty signals are correctly ingested, clamped, and exposed."""
        self.listener.asserved_total_power = 0.73
        self.listener.asserved_novelty = 0.42
        self.engine.update(0.1)

        self.assertAlmostEqual(self.engine.power, 0.73)
        self.assertAlmostEqual(self.engine.novelty, 0.42)

        snap = self.engine.get_state_snapshot()
        self.assertAlmostEqual(snap["power"], 0.73)
        self.assertAlmostEqual(snap["novelty"], 0.42)

        self.engine.reset()
        self.assertAlmostEqual(self.engine.power, 0.0)
        self.assertAlmostEqual(self.engine.novelty, 0.0)

    def test_string_regime_coercion_and_snapshot_safety(self) -> None:
        """Verify _switch_regime handles string input and snapshot does not crash on string assignment."""
        self.engine._switch_regime("THE_POCKET")
        self.assertEqual(self.engine.current_regime, MusicalRegime.THE_POCKET)

        # Directly assigned string must not crash get_state_snapshot()
        self.engine._current_regime = "CHAOTIC_FILL"
        snap = self.engine.get_state_snapshot()
        self.assertEqual(snap["current_regime"], "CHAOTIC_FILL")

    def test_zero_lookahead_disarms_buildup(self) -> None:
        """Verify that when lookahead_seconds <= 0.0, PRE_DROP_BUILDUP does not trigger."""
        self.listener.analyzer.lookahead_seconds = 0.0
        self.listener.live_rhythm_salience = 0.90
        self.listener.rhythm_salience = 0.10
        self.engine.update(0.1)

        self.assertNotEqual(self.engine.current_regime, MusicalRegime.PRE_DROP_BUILDUP)
        self.assertEqual(self.engine.drop_countdown, 0.0)

    def test_axiom_01_frame_budget(self) -> None:
        """Verify MusicalContextEngine.update() executes in <= 0.15 ms per frame (AXIOM-01)."""
        # Warmup
        for _ in range(50):
            self.engine.update(1/60)

        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            self.engine.update(1/60)
        elapsed_sec = time.perf_counter() - start
        avg_time_ms = (elapsed_sec / iterations) * 1000.0

        # Must comfortably beat 0.15 ms budget
        self.assertLess(avg_time_ms, 0.15, f"Engine frame budget exceeded: {avg_time_ms:.4f} ms > 0.15 ms")

    def test_axiom_02_zero_dynamic_allocation_in_steady_state(self) -> None:
        """Verify zero dynamic heap memory allocations during update() hot path (AXIOM-02)."""
        # Warm up JIT/caches
        for _ in range(50):
            self.engine.update(1/60)

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        # Run 50 frames in steady state
        for _ in range(50):
            self.engine.update(1/60)

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
        # Filter stats for MusicalContextEngine.py
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


if __name__ == "__main__":
    unittest.main()
