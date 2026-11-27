"""Tests for the gate and the before/after comparison (research/scoreboard/compare.py), and for the pilot
candidate BandKickSlotsAudioAnalyzer running inside the production Listener."""
import unittest

import numpy as np

from research.scoreboard import compare


def _cell(score, checked=True, produced=True):
    return {"produced": produced, "checked": score if checked else None, "all": score, "detail": {}}


def _result(base_scores, cand_scores):
    """Four tracks (01..04); each argument maps a signal name to its four scores (None = not produced)."""
    def model(scores):
        return {f"{i + 1:02d}": {"signals": {n: _cell(v[i], produced=v[i] is not None) for n, v in scores.items()}, "frame_ms": 0.5}
                for i in range(4)}

    return {"built": "2026-11-27", "lookahead_s": 5.0, "tracks": {f"{i + 1:02d}": {"file": f"song{i + 1}.mp3", "group": "x"} for i in range(4)},
            "models": {"base": model(base_scores), "cand": model(cand_scores)}}


class TestGate(unittest.TestCase):
    def test_unchanged_signals_pass_and_new_ones_are_not_gated(self):
        res = _result({"beat": [0.8] * 4, "kick": [None] * 4}, {"beat": [0.8] * 4, "kick": [0.9, 0.5, 0.7, 0.7]})
        rows = compare.gate(res, "base", "cand")
        self.assertEqual([r["signal"] for r in rows], ["beat"])
        self.assertTrue(rows[0]["passed"])
        new = compare.new_signals(res, "base", "cand")
        self.assertEqual([r["signal"] for r in new], ["kick"])
        self.assertAlmostEqual(new[0]["open"], 0.8)       # tracks 01 and 03
        self.assertAlmostEqual(new[0]["check"], 0.6)      # tracks 02 and 04
        self.assertEqual(new[0]["weakest"][0], (0.5, "02"))

    def test_a_worse_signal_fails_the_gate(self):
        res = _result({"beat": [0.8] * 4}, {"beat": [0.8, 0.8, 0.8, 0.7]})
        row = compare.gate(res, "base", "cand")[0]
        self.assertFalse(row["passed"])                   # the average lost 2.5 points
        self.assertEqual(row["track_drops"], ["04"])

    def test_a_single_track_drop_is_listed_even_when_the_average_holds(self):
        res = _result({"beat": [0.8] * 4}, {"beat": [0.9, 0.8, 0.8, 0.7]})
        row = compare.gate(res, "base", "cand")[0]
        self.assertTrue(row["passed"])
        self.assertEqual(row["track_drops"], ["04"])

    def test_a_signal_the_candidate_stops_producing_fails(self):
        res = _result({"beat": [0.8] * 4}, {"beat": [None] * 4})
        self.assertFalse(compare.gate(res, "base", "cand")[0]["passed"])


class TestBandKickCandidateInTheListener(unittest.TestCase):
    """A synthetic song: steady noise bed, a 60 Hz thump every half second from 2 s to 10 s, then no kick."""

    LOOKAHEAD = 1.0

    @classmethod
    def setUpClass(cls):
        from music.api import Listener
        from research.experiments.models.BandKickSlotsAudioAnalyzer import BandKickSlotsAudioAnalyzer
        from tools.choreography_probe import HOP, OfflineClock, step_listener
        from tools.listener_config import build_listener_infos

        sr = 44100
        rng = np.random.default_rng(0)
        mono = (0.02 * rng.standard_normal(16 * sr)).astype(np.float32)
        burst_t = np.arange(int(0.12 * sr)) / sr
        burst = (0.8 * np.sin(2 * np.pi * 60.0 * burst_t) * np.exp(-burst_t / 0.04)).astype(np.float32)
        cls.kicks = np.arange(2.0, 10.0, 0.5)
        for t in cls.kicks:
            i = int(t * sr)
            mono[i : i + len(burst)] += burst
        infos = build_listener_infos()
        infos["fakeDelay"] = cls.LOOKAHEAD
        lead = int(cls.LOOKAHEAD * 60)
        n = len(mono) // HOP
        cls.kick = np.full(n, np.nan)
        cls.present = np.full(n, np.nan)
        cls.bass = np.full(n, np.nan)
        cls.early = []
        with OfflineClock() as clock:
            listener = Listener(infos, analyzer_class=BandKickSlotsAudioAnalyzer)
            listener.dynamic_audio_latency = 0.0
            for k in range(n + lead):
                step_listener(listener, mono, k * HOP, clock)
                s = listener.signals
                if k < lead - 2:
                    cls.early.append((s.kick, s.band_bass, s.kick_present))
                i = k - lead
                if i >= 0 and s.kick is not None:
                    cls.kick[i], cls.present[i], cls.bass[i] = s.kick, float(bool(s.kick_present)), s.band_bass

    def test_slots_stay_empty_until_the_speakers_reach_the_music(self):
        self.assertTrue(all(v == (None, None, None) for v in self.early))

    def test_kicks_land_at_speaker_time(self):
        found = np.flatnonzero(np.nan_to_num(self.kick) > 0) / 60.0
        hits = sum(1 for t in self.kicks[2:] if np.min(np.abs(found - t)) <= 0.05)     # after two kicks of settling
        self.assertGreaterEqual(hits, len(self.kicks[2:]) - 1)
        self.assertLessEqual(len(found), len(self.kicks) + 2)

    def test_kick_present_follows_the_kick_stretch(self):
        t = np.arange(len(self.present)) / 60.0
        self.assertGreater(np.nanmean(self.present[(t > 4.0) & (t < 9.0)]), 0.95)
        self.assertLess(np.nanmean(self.present[(t > 11.0) & (t < 15.0)]), 0.05)

    def test_levels_are_between_zero_and_one(self):
        ok = np.isfinite(self.bass)
        self.assertTrue(ok.any())
        self.assertGreaterEqual(float(self.bass[ok].min()), 0.0)
        self.assertLessEqual(float(self.bass[ok].max()), 1.0)


if __name__ == "__main__":
    unittest.main()
