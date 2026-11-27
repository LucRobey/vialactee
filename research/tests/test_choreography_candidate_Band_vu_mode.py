"""Tests of the lab mode Band_vu_mode (work list C12): flash safety on levels that jump, the kick cap, bass and
treble in their places, and the fallbacks.

The mode is drawn on the whole installation (one copy per segment, as the lab does) with made-up signals written
straight into a stand-in listener. Flashes are counted with the lab's own counter (profile.flashes_per_second), on
the whole installation and on each third of its height, as the gate does.
"""
import unittest

import numpy as np

from research.choreography.candidates.Band_vu_mode import Band_vu_mode
from research.choreography.layout import load_layout
from research.choreography.profile import FLASH_LIMIT, flashes_per_second, light
from research.choreography.render import brightness

FPS = 60.0


class _Signals:
    kick = 0.0
    kick_present = True
    no_beat = False
    band_bass = 0.6
    band_mid = 0.6
    band_high = 0.6


class _NoSignals:
    kick = kick_present = no_beat = band_bass = band_mid = band_high = None


class _Listener:
    def __init__(self, signals) -> None:
        self.signals = signals
        self.dt = 1.0 / FPS
        self.context = None
        self.asserved_fft_band = np.full(16, 0.7)
        self.is_beat = False
        self.beat_trust = 0.0
        self.beat_tag = ""
        self.beat_phase = 0.0


def _draw(script, seconds, signals=None):
    """Frames of the whole installation, shape (frames, 1304, 3), and the layout."""
    layout = load_layout()
    listener = _Listener(signals if signals is not None else _Signals())
    modes, buffers = [], []
    for seg in layout.segments:
        rgb = np.zeros((seg.size, 3), dtype=np.int32)
        modes.append(Band_vu_mode("Band_vu_mode", seg.name, listener, None, list(range(seg.size)), rgb,
                                  {"tags": seg.tags, "orientation": seg.orientation}))
        buffers.append(rgb)
    frames = np.zeros((int(seconds * FPS), layout.total, 3), dtype=np.uint8)
    for i in range(len(frames)):
        script(i, listener.signals)
        for mode, rgb in zip(modes, buffers):
            mode.render(buffer=rgb)
        for seg, rgb in zip(layout.segments, buffers):
            frames[i, seg.offset : seg.offset + seg.size] = np.clip(rgb, 0, 255)
    return frames, layout


def _zones(frames, layout):
    emitted = light(frames)
    alt = 1.0 - layout.xy[:, 1] / 245.0
    low, top = alt < 1.0 / 3.0, alt > 2.0 / 3.0
    return {"whole": emitted.mean(axis=1), "low": emitted[:, low].mean(axis=1),
            "mid": emitted[:, ~low & ~top].mean(axis=1), "top": emitted[:, top].mean(axis=1)}


def _most_flashes(frames, layout):
    return max(flashes_per_second(curve, FPS) for curve in _zones(frames, layout).values())


def _segment(frames, layout, name):
    seg = next(s for s in layout.segments if s.name == "Segment " + name)
    return frames[:, seg.offset : seg.offset + seg.size]


class TestFlashSafety(unittest.TestCase):
    def test_levels_that_jump_from_silence_to_full_at_any_rate_stay_within_the_limit(self):
        for half_period in (2, 3, 4, 5, 6, 8, 10, 15, 20):                    # 15 down to 1.5 jumps a second
            def script(i, s, p=half_period):
                v = 1.0 if (i // p) % 2 == 0 else 0.0
                s.band_bass = s.band_mid = s.band_high = v
            frames, layout = _draw(script, 6.0)
            self.assertLessEqual(_most_flashes(frames, layout), FLASH_LIMIT, half_period)

    def test_random_levels_and_irregular_kicks_stay_within_the_limit(self):
        rng = np.random.default_rng(11)
        for trial in range(20):
            levels = rng.uniform(0.0, 1.0, size=(400, 3))
            hold = int(rng.integers(1, 12))
            kicks = set(np.cumsum(rng.integers(2, 30, size=200)).tolist())

            def script(i, s, lv=levels, h=hold, k=kicks):
                s.band_bass, s.band_mid, s.band_high = (float(x) for x in lv[(i // h) % 400])
                s.kick = 0.9 if i in k else 0.0
            frames, layout = _draw(script, 6.0)
            self.assertLessEqual(_most_flashes(frames, layout), FLASH_LIMIT, trial)


class TestKickCap(unittest.TestCase):
    def test_a_heard_kick_punches_the_whole_bass_meter_and_nothing_else(self):
        frames, layout = _draw(lambda i, s: setattr(s, "kick", 0.9 if i == 60 else 0.0), 2.0)
        outer = brightness(_segment(frames, layout, "v1"))
        self.assertGreater(float(outer[60] - outer[59]), 0.25)                 # the outer pillar jumps at once
        inner = _segment(frames, layout, "v2")
        np.testing.assert_array_equal(inner[60], inner[59])                    # the middle meter does not move

    def test_a_kick_too_soon_after_a_punch_gets_the_cap_only(self):
        frames, layout = _draw(lambda i, s: setattr(s, "kick", 0.9 if i in (60, 72) else 0.0), 2.0)
        outer = _segment(frames, layout, "v1").astype(int)
        self.assertGreater(int(outer[72].min(axis=1).max()), 150)              # a near-white cap somewhere
        seen = brightness(outer)
        self.assertLess(float(seen[72] - seen[71]), 0.10)                       # but no second punch

    def test_no_cap_while_the_kick_is_away(self):
        def script(i, s):
            s.kick = 0.9 if i == 60 else 0.0
            s.kick_present = False
        frames, layout = _draw(script, 2.0)
        outer = _segment(frames, layout, "v1")
        np.testing.assert_array_equal(outer[60], outer[59])


class TestBandsInTheirPlaces(unittest.TestCase):
    def test_bass_lights_the_outer_pillars_and_treble_the_canopy(self):
        def bass_only(i, s):
            s.band_bass, s.band_mid, s.band_high = 0.95, 0.0, 0.0

        def treble_only(i, s):
            s.band_bass, s.band_mid, s.band_high = 0.0, 0.0, 0.95

        b, layout = _draw(bass_only, 1.0)
        t, _ = _draw(treble_only, 1.0)
        seen_b, seen_t = brightness(_segment(b, layout, "v1")[-1:]), brightness(_segment(t, layout, "v1")[-1:])
        self.assertGreater(float(seen_b[0]), float(seen_t[0]) + 0.2)
        canopy_b, canopy_t = brightness(_segment(b, layout, "h00")[-1:]), brightness(_segment(t, layout, "h00")[-1:])
        self.assertGreater(float(canopy_t[0]), float(canopy_b[0]) + 0.2)


class TestFallbacks(unittest.TestCase):
    def test_empty_slots_fall_back_and_the_mode_still_draws(self):
        frames, _ = _draw(lambda i, s: None, 2.0, signals=_NoSignals())
        self.assertGreater(float(brightness(frames).mean()), 0.05)

    def test_same_input_gives_the_same_frames(self):
        rng = np.random.default_rng(3)
        levels = rng.uniform(0.0, 1.0, size=(120, 3))

        def script(i, s):
            s.band_bass, s.band_mid, s.band_high = (float(x) for x in levels[i])
            s.kick = 0.9 if i % 20 == 0 else 0.0
        a, _ = _draw(script, 2.0)
        b, _ = _draw(script, 2.0)
        np.testing.assert_array_equal(a, b)


if __name__ == "__main__":
    unittest.main()
