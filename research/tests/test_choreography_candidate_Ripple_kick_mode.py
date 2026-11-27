"""Tests of the lab mode Ripple_kick_mode (work list C11): the white heart rationed, no flash without kicks,
the calm while the kick is away, and the fallbacks.

The mode is drawn on the whole installation (one copy per segment, as the lab does) with made-up signals written
straight into a stand-in listener. Flashes are counted with the lab's own counter (profile.flashes_per_second), on
the whole installation and on each third of its height, as the gate does.
"""
import unittest

import numpy as np

from modes.Mode import Mode
from research.choreography.candidates.Ripple_kick_mode import FULL_GAP_S, Ripple_kick_mode
from research.choreography.layout import load_layout
from research.choreography.profile import FLASH_LIMIT, flashes_per_second, light
from research.choreography.render import brightness

FPS = 60.0


class _Signals:
    kick = 0.0
    drop = False
    kick_present = True
    no_beat = False
    band_bass = 0.6
    band_mid = 0.6
    band_high = 0.6
    loudness = 0.6


class _NoSignals:
    kick = drop = kick_present = no_beat = band_bass = band_mid = band_high = loudness = None


class _Listener:
    """What the mode reads from a listener, and nothing else. The beat phase turns at 120 beats a minute."""

    def __init__(self, signals) -> None:
        self.signals = signals
        self.dt = 1.0 / FPS
        self.context = None
        self.asserved_fft_band = np.full(16, 0.5)
        self.beat_phase = 0.0
        self.beat_confidence = 0.0


def _draw(script, seconds, signals=None, palette=None):
    """Frames of the whole installation, shape (frames, 1304, 3); `script(i, signals)` sets the signals of frame i."""
    layout = load_layout()
    listener = _Listener(signals if signals is not None else _Signals())
    if palette is not None:
        Mode.bind_mood_colors(np.array(palette, dtype=np.int32))
    try:
        modes, buffers = [], []
        for seg in layout.segments:
            rgb = np.zeros((seg.size, 3), dtype=np.int32)
            modes.append(Ripple_kick_mode("Ripple_kick_mode", seg.name, listener, None, list(range(seg.size)), rgb,
                                              {"tags": seg.tags, "orientation": seg.orientation}))
            buffers.append(rgb)
        frames = np.zeros((int(seconds * FPS), layout.total, 3), dtype=np.uint8)
        for i in range(len(frames)):
            listener.beat_phase = (i / FPS * 2.0) % 1.0
            script(i, listener.signals)
            for mode, rgb in zip(modes, buffers):
                mode.render(buffer=rgb)
            for seg, rgb in zip(layout.segments, buffers):
                frames[i, seg.offset : seg.offset + seg.size] = np.clip(rgb, 0, 255)
    finally:
        Mode.reset_mood_colors()
    return frames, layout


def _zones(frames, layout):
    emitted = light(frames)
    alt = 1.0 - layout.xy[:, 1] / 245.0
    low, top = alt < 1.0 / 3.0, alt > 2.0 / 3.0
    return {"whole": emitted.mean(axis=1), "low": emitted[:, low].mean(axis=1),
            "mid": emitted[:, ~low & ~top].mean(axis=1), "top": emitted[:, top].mean(axis=1)}


def _most_flashes(frames, layout):
    return max(flashes_per_second(curve, FPS) for curve in _zones(frames, layout).values())


def _bands_flip(i, s):
    s.kick, s.drop = 0.0, False
    s.band_bass = s.band_mid = s.band_high = 1.0 if (i // 15) % 2 == 0 else 0.0


def _hits_ten_a_second(i, s):
    s.kick = 0.9 if i % 6 == 0 else 0.0
    s.drop = i % 150 == 0
    flip = 1.0 if (i // 10) % 2 == 0 else 0.0
    s.band_bass, s.band_mid, s.band_high = flip, 1.0 - flip, flip
    s.kick_present = (i // 45) % 3 != 0                 # the kick leaves and comes back every 1.5 s


WHITE = [(255, 255, 255)] * 4


class TestNoKick(unittest.TestCase):
    def test_without_kicks_the_bands_and_the_bed_cannot_flash(self):
        for palette in (None, WHITE):
            frames, layout = _draw(_bands_flip, 6.0, palette=palette)
            for name, curve in _zones(frames, layout).items():
                self.assertEqual(flashes_per_second(curve, FPS), 0.0, name)
            self.assertGreater(float(np.ptp(brightness(frames))), 0.02)


class TestFlashRation(unittest.TestCase):
    def test_hits_ten_times_a_second_stay_within_three_flashes_a_second(self):
        for palette in (None, WHITE):
            frames, layout = _draw(_hits_ten_a_second, 12.0, palette=palette)
            self.assertLessEqual(_most_flashes(frames, layout), FLASH_LIMIT)

    def test_kicks_at_every_frame_rate_of_fast_music_stay_within_the_limit(self):
        for period in (3, 4, 5, 7, 8, 9, 13, 14, 20):                         # 1200 down to 180 hits a minute
            frames, layout = _draw(lambda i, s, p=period: setattr(s, "kick", 0.9 if i % p == 0 else 0.0), 6.0)
            self.assertLessEqual(_most_flashes(frames, layout), FLASH_LIMIT, period)

    def test_random_irregular_hits_stay_within_the_limit(self):
        rng = np.random.default_rng(7)
        for trial in range(25):
            gaps = rng.integers(2, 40, size=200)                                 # 3 to 30 hits a second, irregular
            hit_frames = set(np.cumsum(gaps).tolist())
            strengths = rng.uniform(0.2, 1.0, size=1)
            frames, layout = _draw(lambda i, s, h=hit_frames, k=float(strengths[0]): setattr(s, "kick", k if i in h else 0.0), 6.0)
            self.assertLessEqual(_most_flashes(frames, layout), FLASH_LIMIT, trial)

    def test_a_steady_kick_slower_than_the_ration_gets_a_full_punch_every_time(self):
        period = int(round(0.5 * FPS))
        self.assertGreaterEqual(period / FPS, FULL_GAP_S)
        frames, layout = _draw(lambda i, s: setattr(s, "kick", 0.9 if i % period == 0 else 0.0), 6.0)
        seen = brightness(frames)
        for k in range(period, len(frames), period):
            self.assertGreater(float(seen[k] - seen[k - 1]), 0.10, k)           # visible at once, on the frame of the kick


class TestBreak(unittest.TestCase):
    def test_no_full_punch_while_the_kick_is_away_but_the_rings_still_move(self):
        def script(i, s):
            s.kick = 0.9 if i % 30 == 0 else 0.0
            s.kick_present = False

        frames, layout = _draw(script, 6.0)
        for name, curve in _zones(frames, layout).items():
            self.assertEqual(flashes_per_second(curve, FPS), 0.0, name)
        self.assertFalse(np.array_equal(frames[200], frames[215]))              # it drifts, it is not frozen

    def test_no_beat_also_calms_it(self):
        def script(i, s):
            s.kick = 0.9 if i % 30 == 0 else 0.0
            s.no_beat = True

        frames, layout = _draw(script, 4.0)
        self.assertEqual(_most_flashes(frames, layout), 0.0)

    def test_the_first_kick_after_the_break_gets_a_full_punch(self):
        def script(i, s):
            s.kick_present = i >= 180
            s.kick = 0.9 if i in (150, 190) else 0.0

        frames, _ = _draw(script, 4.0)
        seen = brightness(frames)
        self.assertLess(float(seen[150] - seen[149]), 0.10)
        self.assertGreater(float(seen[190] - seen[189]), 0.10)


class TestFallbacks(unittest.TestCase):
    def test_empty_slots_fall_back_and_the_mode_still_draws(self):
        frames, _ = _draw(lambda i, s: None, 2.0, signals=_NoSignals())
        self.assertGreater(float(brightness(frames).mean()), 0.02)

    def test_same_input_gives_the_same_frames(self):
        a, _ = _draw(_hits_ten_a_second, 2.0)
        b, _ = _draw(_hits_ten_a_second, 2.0)
        np.testing.assert_array_equal(a, b)


if __name__ == "__main__":
    unittest.main()
