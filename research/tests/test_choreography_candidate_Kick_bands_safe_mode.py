"""Tests of the lab mode Kick_bands_safe_mode (work list C01): the flash ration and the limit on the resting light.

The mode is drawn on the whole installation (one copy per segment, as the lab does) with made-up signals written
straight into a stand-in listener, so the tests are fast and need no song. Flashes are counted with the lab's own
counter (profile.flashes_per_second), on the whole installation and on each third of its height, as the gate does.
"""
import unittest

import numpy as np

from modes.Mode import Mode
from research.choreography.candidates.Kick_bands_safe_mode import FULL_GAP_S, REST_LIGHT_MAX, Kick_bands_safe_mode
from research.choreography.layout import load_layout
from research.choreography.profile import FLASH_LIMIT, flashes_per_second, light
from research.choreography.render import brightness

FPS = 60.0


class _Signals:
    kick = 0.0
    snare = 0.0
    drop = False
    band_bass = 0.3
    band_mid = 0.3
    band_high = 0.3


class _NoSignals:
    kick = snare = drop = band_bass = band_mid = band_high = None


class _Listener:
    """What the mode reads from a listener, and nothing else."""

    def __init__(self, signals) -> None:
        self.signals = signals
        self.dt = 1.0 / FPS
        self.context = None
        self.asserved_fft_band = np.full(16, 0.3)
        self.is_beat = False
        self.beat_trust = 0.0
        self.beat_tag = ""


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
            modes.append(Kick_bands_safe_mode("Kick_bands_safe_mode", seg.name, listener, None, list(range(seg.size)), rgb,
                                              {"tags": seg.tags, "orientation": seg.orientation}))
            buffers.append(rgb)
        frames = np.zeros((int(seconds * FPS), layout.total, 3), dtype=np.uint8)
        for i in range(len(frames)):
            script(i, listener.signals)
            for mode, rgb in zip(modes, buffers):
                mode.render(buffer=rgb)
            for seg, rgb in zip(layout.segments, buffers):
                frames[i, seg.offset : seg.offset + seg.size] = np.clip(rgb, 0, 255)
    finally:
        Mode.reset_mood_colors()
    return frames, layout


def _zones(frames, layout):
    """Light given off by the whole installation and by each third of its height, per frame (as profile.py cuts them)."""
    emitted = light(frames)
    alt = 1.0 - layout.xy[:, 1] / 245.0
    low, top = alt < 1.0 / 3.0, alt > 2.0 / 3.0
    return {"whole": emitted.mean(axis=1), "low": emitted[:, low].mean(axis=1),
            "mid": emitted[:, ~low & ~top].mean(axis=1), "top": emitted[:, top].mean(axis=1)}


def _most_flashes(frames, layout):
    return max(flashes_per_second(curve, FPS) for curve in _zones(frames, layout).values())


def _bands_flip(i, s):
    s.kick = s.snare = 0.0
    s.drop = False
    s.band_bass = s.band_mid = s.band_high = 1.0 if (i // 15) % 2 == 0 else 0.0      # silence to full, twice a second


def _hits_ten_a_second(i, s):
    s.kick = 0.9 if i % 6 == 0 else 0.0
    s.snare = 0.9 if i % 6 == 3 else 0.0
    s.drop = i % 150 == 0
    flip = 1.0 if (i // 10) % 2 == 0 else 0.0
    s.band_bass, s.band_mid, s.band_high = flip, 1.0 - flip, flip


WHITE = [(255, 255, 255)] * 4            # the palette that gives the most light for a drive value


class TestRestingLayer(unittest.TestCase):
    def test_the_resting_light_never_goes_over_its_limit_and_cannot_flash(self):
        for palette in (None, WHITE):
            frames, layout = _draw(_bands_flip, 6.0, palette=palette)
            zones = _zones(frames, layout)
            for name, curve in zones.items():
                self.assertLessEqual(float(curve.max()), REST_LIGHT_MAX + 1e-6, name)
                self.assertEqual(flashes_per_second(curve, FPS), 0.0, name)
            self.assertGreater(float(np.ptp(brightness(frames))), 0.05)          # and yet the eye sees the levels move


class TestFlashRation(unittest.TestCase):
    def test_hits_ten_times_a_second_stay_within_three_flashes_a_second(self):
        for palette in (None, WHITE):
            frames, layout = _draw(_hits_ten_a_second, 12.0, palette=palette)
            self.assertLessEqual(_most_flashes(frames, layout), FLASH_LIMIT)

    def test_a_steady_kick_slower_than_the_ration_gets_a_full_punch_every_time(self):
        period = int(round(0.5 * FPS))
        self.assertGreaterEqual(period / FPS, FULL_GAP_S)

        def script(i, s):
            s.kick = 0.9 if i % period == 0 else 0.0
            s.snare, s.drop = 0.0, False

        frames, layout = _draw(script, 6.0)
        seen = brightness(frames)
        low = _zones(frames, layout)["low"]
        for k in range(period, len(frames), period):                          # the first kick is skipped: the levels are settling
            self.assertGreater(float(seen[k] - seen[k - 1]), 0.10, k)            # visible at once, on the frame of the kick
            self.assertGreater(float(low[k] - low[k - 1]), 0.10, k)              # a full punch low down, not a soft pulse

    def test_a_kick_that_comes_too_soon_gets_a_soft_pulse_not_a_flash(self):
        soon = int(round(0.5 * FULL_GAP_S * FPS))

        def script(i, s):
            s.kick = 0.9 if i in (120, 120 + soon) else 0.0
            s.snare, s.drop = 0.0, False

        frames, layout = _draw(script, 4.0)
        low = _zones(frames, layout)["low"]
        self.assertGreater(float(low[120] - low[119]), 0.10)                    # the first kick: a full punch
        self.assertLess(float(low[120 + soon] - low[120 + soon - 1]), 0.10)     # the second: under what counts as a flash
        quiet, _ = _draw(lambda i, s: setattr(s, "kick", 0.9 if i == 120 else 0.0), 4.0)
        self.assertFalse(np.array_equal(frames[120 + soon], quiet[120 + soon]))  # but it does draw something


class TestJoinedHits(unittest.TestCase):
    """A hit that falls while a full punch is held at its top joins that punch."""

    def test_a_drop_two_frames_after_its_kick_still_lights_everything(self):
        def script(i, s):
            s.kick = 0.9 if i == 120 else 0.0
            s.snare = 0.0
            s.drop = i == 122

        frames, layout = _draw(script, 4.0)
        top = _zones(frames, layout)["top"]
        self.assertLess(float(top[121]), 0.05)                                # the kick alone leaves the canopy at rest
        self.assertGreater(float(top[122] - top[121]), 0.30)                  # the drop lights it

    def test_a_second_kick_that_joins_the_punch_does_not_make_a_second_flash(self):
        def script(i, s):
            s.kick = 0.9 if i in (120, 123) else 0.0
            s.snare, s.drop = 0.0, False

        frames, layout = _draw(script, 4.0)
        for name, curve in _zones(frames, layout).items():
            self.assertLessEqual(flashes_per_second(curve, FPS), 1.0, name)     # one rise and one fall, nowhere more


class TestFallbacks(unittest.TestCase):
    def test_empty_slots_fall_back_and_the_mode_still_draws(self):
        frames, _ = _draw(lambda i, s: None, 2.0, signals=_NoSignals())
        self.assertGreater(float(brightness(frames).mean()), 0.05)

    def test_same_input_gives_the_same_frames(self):
        a, _ = _draw(_hits_ten_a_second, 2.0)
        b, _ = _draw(_hits_ten_a_second, 2.0)
        np.testing.assert_array_equal(a, b)


if __name__ == "__main__":
    unittest.main()
