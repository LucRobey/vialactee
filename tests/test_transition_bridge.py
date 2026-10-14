"""Tests for core/TransitionBridge.py: project objects <-> sector doors."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from core import TransitionBridge as bridge
from transitions.api import SegmentOrder, TransitionOrders


class TestMusicSnapshot(unittest.TestCase):
    def test_reads_context_and_listener(self):
        ctx = SimpleNamespace(energy=0.8, salience=0.6, beat_trust=0.7, novelty=0.2, tension=0.1,
                              power=0.5, scene=SimpleNamespace(value="GROOVE"), is_drop_impact=True,
                              is_syncopated=False, is_locked=True, is_rhythmic=True, is_silent=False)
        listener = SimpleNamespace(context=ctx, beat_phase=0.25, is_beat=True,
                                   is_song_change=True, is_verse_chorus_change=False,
                                   live_is_song_change=True, live_is_verse_chorus_change=False,
                                   analyzer=SimpleNamespace(lookahead_seconds=4.0))
        m = bridge.build_music_snapshot(listener)
        self.assertEqual((m.energy, m.salience, m.scene), (0.8, 0.6, "GROOVE"))
        self.assertTrue(m.is_drop_impact and m.live_is_song_change and m.is_rhythmic and m.is_song_change)
        self.assertFalse(m.is_verse_chorus_change)
        self.assertEqual((m.beat_phase, m.lookahead_seconds), (0.25, 4.0))

    def test_falls_back_without_context(self):
        listener = SimpleNamespace(context=None, asserved_total_power=0.3, rhythm_salience=0.9, beat_trust=0.1)
        m = bridge.build_music_snapshot(listener)
        self.assertEqual((m.energy, m.salience, m.beat_trust), (0.3, 0.9, 0.1))

    def test_survives_garbage_values(self):
        listener = SimpleNamespace(context=SimpleNamespace(energy=None, salience="x"), beat_phase=None)
        m = bridge.build_music_snapshot(listener)
        self.assertEqual(m.energy, 0.5)
        self.assertEqual(m.beat_phase, 0.0)


class TestInstallationSnapshot(unittest.TestCase):
    def test_describes_segments(self):
        seg = SimpleNamespace(name="Segment v1", orientation="vertical", modes={"A": 1, "B": 2},
                              activ_mode="A", isBlocked=True)
        snap = bridge.build_installation_snapshot([seg], (10, 20))
        d = snap.segments[0]
        self.assertEqual((d.name, d.orientation, d.available_modes, d.active_mode, d.is_blocked),
                         ("Segment v1", "vertical", ("A", "B"), "A", True))
        self.assertEqual(snap.room_bounds, (10, 20))


class TestApplyOrders(unittest.TestCase):
    def _mm(self, segments):
        mm = MagicMock()
        mm._find_segment_by_name = lambda n: segments.get(n)
        return mm

    def test_accepts_started_transitions_and_refuses_the_rest(self):
        ok = MagicMock(isBlocked=False, is_in_transition=True)
        busy = MagicMock(isBlocked=False, is_in_transition=False)
        blocked = MagicMock(isBlocked=True)
        mm = self._mm({"a": ok, "b": busy, "c": blocked})
        orders = TransitionOrders(orders=(
            SegmentOrder("a", "Rainbow", "global_change", 2.0, direction="DOWN"),
            SegmentOrder("b", "Rainbow", "global_change", 2.0),
            SegmentOrder("c", "Rainbow", "global_change", 2.0),
            SegmentOrder("missing", "Rainbow", "global_change", 2.0),
        ))
        ack = bridge.apply_orders(mm, orders)
        self.assertEqual(ack.accepted, ("a",))
        self.assertEqual(set(ack.refused), {"b", "c", "missing"})
        ok.change_mode.assert_called_once_with("Rainbow", {"type": "global_change", "duration": 2.0})
        ok.change_way.assert_called_once_with("DOWN")
        blocked.change_mode.assert_not_called()
        self.assertTrue(mm._state_dirty)


if __name__ == "__main__":
    unittest.main()
