"""
tests/test_listener_display_hold.py
One-frame signals are held for the display loop (docs/contracts/music_analyzer_contract.md, section 1.1).

The analyzer ticks 60 times a second, the display draws 30 times a second. A beat flag that lasts one tick must
still be seen by the display, once, whatever the two rates; and tools that read after every tick must see no
change.
"""
import unittest
from typing import Any, Dict

from music.api import Listener
from music.BaseAudioAnalyzer import BaseAudioAnalyzer
from music.MusicSignals import EVENTS, FLAGS


class _Scripted(BaseAudioAnalyzer):
    """An analyzer that raises its one-frame flags on the ticks it is told to."""

    script: Dict[int, Dict[str, Any]] = {}

    def __init__(self, ingestion: Any, infos: Dict[str, Any], config: Any = None) -> None:
        super().__init__(ingestion, infos, config)
        self.tick = 0
        self._song = self._section = False

    def update(self, current_time: float, dt: float, fps_ratio: float) -> None:
        now = self.script.get(self.tick, {})
        self.is_beat = bool(now.get("beat"))
        self.is_real_beat = bool(now.get("real"))
        self.is_dropped_beat = bool(now.get("dropped"))
        self._song = bool(now.get("song"))
        self.signals.kick = now.get("kick", 0.0)
        if self.is_beat:
            self.beat_count += 1
        self.tick += 1

    def update_structural_novelty(self, current_time: float, dt: float, fps_ratio: float) -> None:
        pass

    def reset(self) -> None:
        self.tick = 0

    @property
    def beat_phase(self) -> float:
        return 0.0

    @property
    def is_song_change(self) -> bool:
        return self._song


def _listener(script: Dict[int, Dict[str, Any]]) -> Listener:
    _Scripted.script = script
    return Listener({"useMicrophone": True, "fakeDelay": 0.0}, analyzer_class=_Scripted)


class TestReadersOfEveryTickSeeNoChange(unittest.TestCase):
    def test_flags_last_one_tick_when_no_display_loop_is_involved(self):
        listener = _listener({2: {"beat": True, "real": True, "kick": 0.8}})
        seen = []
        for _ in range(5):
            listener.update(fixed_dt=1 / 60)
            seen.append((listener.is_beat, listener.is_real_beat, listener.signals.kick))
        self.assertEqual(seen[2], (True, True, 0.8))
        self.assertEqual([s[0] for s in seen], [False, False, True, False, False])
        self.assertIs(listener.signals, listener.analyzer.signals)


class TestTheDisplayLoopMissesNothing(unittest.TestCase):
    def _run(self, script, ticks_per_frame, frames):
        """Tick the analyzer `ticks_per_frame` times, then let the display read once; repeat."""
        listener = _listener(script)
        seen = []
        for _ in range(frames):
            for _ in range(ticks_per_frame):
                listener.update(fixed_dt=1 / 60)
            listener.begin_display_frame()
            seen.append({"beat": listener.is_beat, "real": listener.is_real_beat, "dropped": listener.is_dropped_beat,
                         "song": listener.live_is_song_change, "kick": listener.signals.kick, "slot_beat": listener.signals.beat})
        return listener, seen

    def test_a_flag_raised_and_cleared_between_two_frames_is_still_seen_once(self):
        # two ticks per display frame; the beat is on the FIRST tick of frame 1 and is cleared by the second
        _, seen = self._run({2: {"beat": True, "real": True, "song": True, "kick": 0.6}}, ticks_per_frame=2, frames=4)
        self.assertEqual([s["beat"] for s in seen], [False, True, False, False])
        self.assertEqual([s["real"] for s in seen], [False, True, False, False])
        self.assertEqual([s["song"] for s in seen], [False, True, False, False])
        self.assertEqual([s["kick"] for s in seen], [0.0, 0.6, 0.0, 0.0])
        self.assertEqual([s["slot_beat"] for s in seen], [False, True, False, False])

    def test_every_beat_is_seen_exactly_once_at_any_pace(self):
        beats = {t: {"beat": True} for t in range(3, 120, 7)}
        for ticks_per_frame in (1, 2, 3):
            with self.subTest(ticks_per_frame=ticks_per_frame):
                listener, seen = self._run(beats, ticks_per_frame, frames=120 // ticks_per_frame)
                self.assertEqual(sum(s["beat"] for s in seen), listener.beat_count)
                self.assertEqual(listener.beat_count, len(beats))

    def test_the_strongest_hit_of_the_frame_is_kept(self):
        _, seen = self._run({2: {"kick": 0.3}, 3: {"kick": 0.9}}, ticks_per_frame=2, frames=3)
        self.assertEqual(seen[1]["kick"], 0.9)

    def test_a_frame_without_a_tick_shows_nothing_new(self):
        listener = _listener({0: {"beat": True}})
        listener.update(fixed_dt=1 / 60)
        listener.begin_display_frame()
        self.assertTrue(listener.is_beat)
        listener.begin_display_frame()                       # the display came back before the analyzer ticked
        self.assertFalse(listener.is_beat)

    def test_reset_forgets_what_was_held(self):
        listener = _listener({0: {"beat": True, "kick": 0.5}})
        listener.update(fixed_dt=1 / 60)
        listener.begin_display_frame()
        listener.reset()
        self.assertFalse(listener.is_beat)
        self.assertIsNone(listener.signals.kick)

    def test_the_context_badges_are_held_too(self):
        listener = _listener({})
        listener.begin_display_frame()                       # the display loop has declared itself
        ctx = listener.context
        ctx._is_drop_impact = True                           # a drop lands on one tick...
        ctx._hold_events()
        ctx._is_drop_impact = False                          # ...and is gone on the next
        ctx._hold_events()
        self.assertFalse(ctx.is_drop_impact)                 # not yet collected
        listener.begin_display_frame()
        self.assertTrue(ctx.is_drop_impact)
        listener.begin_display_frame()
        self.assertFalse(ctx.is_drop_impact)

    def test_the_context_still_reads_the_tick_inside_the_sector(self):
        # With the display holding an old beat, the context's own per-tick logic must see the current tick.
        listener = _listener({1: {"beat": True}})
        listener.update(fixed_dt=1 / 60)
        listener.begin_display_frame()
        listener.update(fixed_dt=1 / 60)                     # the beat tick: the display has not collected it yet
        self.assertFalse(listener.is_beat)
        self.assertTrue(listener._tick("is_beat"))
        self.assertTrue(listener.context._now("is_beat"))


class TestTheListsAreInStep(unittest.TestCase):
    def test_event_slots_and_flags_exist(self):
        listener = _listener({})
        for name in FLAGS:
            self.assertTrue(hasattr(Listener, name), name)
        for name in EVENTS:
            self.assertTrue(hasattr(listener.signals, name), name)


if __name__ == "__main__":
    unittest.main()
