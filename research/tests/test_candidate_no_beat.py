"""Tests for the lab candidate NoBeatSlotAudioAnalyzer (run 2026-11-27_no_beat) inside the production Listener.

A synthetic song of 24 s: steady quiet noise, a 60 Hz thump every half second from 4 s to 14 s, then noise only.
"""
import unittest

import numpy as np


class TestNoBeatCandidateInTheListener(unittest.TestCase):
    LOOKAHEAD = 5.0

    @classmethod
    def setUpClass(cls):
        from music.api import Listener
        from research.experiments.models.NoBeatSlotAudioAnalyzer import NoBeatSlotAudioAnalyzer
        from tools.choreography_probe import HOP, OfflineClock, step_listener
        from tools.listener_config import build_listener_infos

        sr = 44100
        rng = np.random.default_rng(0)
        mono = (0.02 * rng.standard_normal(24 * sr)).astype(np.float32)
        burst_t = np.arange(int(0.12 * sr)) / sr
        burst = (0.8 * np.sin(2 * np.pi * 60.0 * burst_t) * np.exp(-burst_t / 0.04)).astype(np.float32)
        for t in np.arange(4.0, 14.0, 0.5):
            i = int(t * sr)
            mono[i : i + len(burst)] += burst
        infos = build_listener_infos()
        infos["fakeDelay"] = cls.LOOKAHEAD
        lead = int(cls.LOOKAHEAD * 60)
        n = len(mono) // HOP
        cls.no_beat = np.full(n, np.nan)
        cls.early = []
        cls.values = set()
        cls.kick_present = np.full(n, np.nan)
        with OfflineClock() as clock:
            listener = Listener(infos, analyzer_class=NoBeatSlotAudioAnalyzer)
            listener.dynamic_audio_latency = 0.0
            for k in range(n + lead):
                step_listener(listener, mono, k * HOP, clock)
                s = listener.signals
                if k < lead - 2:
                    cls.early.append(s.no_beat)
                i = k - lead
                if i >= 0 and s.no_beat is not None:
                    cls.values.add(s.no_beat)
                    cls.no_beat[i] = float(s.no_beat)
                if i >= 0 and s.kick_present is not None:
                    cls.kick_present[i] = float(bool(s.kick_present))

    def test_slot_stays_empty_until_the_speakers_reach_the_music(self):
        self.assertTrue(self.early)
        self.assertTrue(all(v is None for v in self.early))

    def test_values_are_true_or_false_once_known(self):
        self.assertTrue(self.values)
        self.assertTrue(all(v is True or v is False for v in self.values))
        self.assertLessEqual(int(np.isnan(self.no_beat).sum()), 2)        # known from the first frames of the song on

    def test_a_steady_kick_is_a_beat(self):
        t = np.arange(len(self.no_beat)) / 60.0
        self.assertLess(np.nanmean(self.no_beat[(t > 6.5) & (t < 12.0)]), 0.05)

    def test_noise_without_kick_is_no_beat(self):
        t = np.arange(len(self.no_beat)) / 60.0
        self.assertGreater(np.nanmean(self.no_beat[(t > 19.0) & (t < 23.5)]), 0.95)

    def test_the_production_slots_are_still_written(self):
        t = np.arange(len(self.kick_present)) / 60.0
        self.assertGreater(np.nanmean(self.kick_present[(t > 6.5) & (t < 12.0)]), 0.95)


if __name__ == "__main__":
    unittest.main()
