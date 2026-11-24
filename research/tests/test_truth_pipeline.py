"""Tests for the direct measurements and bar counting of the truth pipeline (research/truth/)."""
import unittest

import numpy as np

from research.truth import measures, meter
from research.truth.labels import apply_labels, finalize
from research.truth.sections import bar_lines, section_changes

SR = 22050


def _kick_track(seconds: float, kick_spans, bpm: float = 120.0) -> np.ndarray:
    """Noise bed with 60 Hz bursts on every beat inside kick_spans."""
    rng = np.random.default_rng(0)
    y = 0.01 * rng.standard_normal(int(seconds * SR)).astype(np.float32)
    burst_t = np.arange(int(0.12 * SR)) / SR
    burst = (0.8 * np.sin(2 * np.pi * 60.0 * burst_t) * np.exp(-burst_t / 0.04)).astype(np.float32)
    for a, b in kick_spans:
        for t in np.arange(a, b, 60.0 / bpm):
            i = int(t * SR)
            y[i : i + len(burst)] += burst[: len(y) - i]
    return y


class TestMeasures(unittest.TestCase):
    def test_full_scale_sine_reads_minus_three_db(self):
        t = np.arange(2 * SR) / SR
        power, freqs = measures.spectra(np.sin(2 * np.pi * 440.0 * t).astype(np.float32), SR)
        db = measures.band_db(power, freqs, 0.0, SR)
        self.assertAlmostEqual(float(np.median(db)), -3.0, delta=0.3)

    def test_regions_bridge_and_minimum_length(self):
        mask = np.zeros(200, dtype=bool)
        mask[20:60] = True      # 1.0 to 3.0 s
        mask[64:100] = True     # 3.2 to 5.0 s, gap of 0.2 s
        mask[150:154] = True    # 0.2 s blip
        self.assertEqual(measures.regions(mask, min_s=0.5, bridge_s=0.3), [[1.0, 5.0]])

    def test_kick_stretches_and_breakdown(self):
        y = _kick_track(40.0, [(2.0, 14.0), (26.0, 38.0)])
        power, freqs = measures.spectra(y, SR)
        mix_db = measures.band_db(power, freqs, 0.0, SR)
        kick_db = measures.band_db(power, freqs, *measures.KICK_BAND)
        regs, times, ref = measures.kick_regions(kick_db, mix_db)
        self.assertEqual(len(regs), 2)
        self.assertAlmostEqual(regs[0][0], 2.0, delta=0.15)
        self.assertAlmostEqual(regs[1][0], 26.0, delta=0.15)
        self.assertAlmostEqual(regs[0][1], 13.5, delta=0.6)
        breaks, moments = measures.breakdowns(regs, mix_db)
        self.assertEqual(len(breaks), 1)
        self.assertEqual([m["kind"] for m in moments], ["kick_out", "kick_return"])
        self.assertGreater(moments[1]["loudness_jump_db"], 3.0)

    def test_silence_and_riser(self):
        rng = np.random.default_rng(1)
        n = 20 * SR
        noise = rng.standard_normal(n).astype(np.float32)
        # brightness sweep: low-passed noise whose cutoff rises from 200 Hz to 6 kHz between 5 s and 15 s
        spec_hop = SR // 20
        out = np.zeros(n, dtype=np.float32)
        for i in range(0, n - 2048, spec_hop):
            t = i / SR
            cut = 200.0 * (30.0 ** np.clip((t - 5.0) / 10.0, 0.0, 1.0))
            seg = np.fft.rfft(noise[i : i + 2048] * np.hanning(2048))
            seg[np.fft.rfftfreq(2048, 1 / SR) > cut] = 0
            out[i : i + 2048] += np.fft.irfft(seg).astype(np.float32) * 0.2
        out[: 2 * SR] = 0.0
        power, freqs = measures.spectra(out, SR)
        mix_db = measures.band_db(power, freqs, 0.0, SR)
        silence = measures.regions(mix_db < measures.SILENCE_DB, min_s=measures.SILENCE_MIN_S)
        self.assertEqual(len(silence), 1)
        self.assertAlmostEqual(silence[0][1], 2.0, delta=0.2)
        risers = measures.riser_regions(measures.centroid_oct(power, freqs), mix_db)
        self.assertGreaterEqual(len(risers), 1)
        self.assertTrue(any(r["start"] < 12.0 and r["end"] > 8.0 and r["rise_oct"] > 0.7 for r in risers))

    def test_stem_presence_needs_level_and_share(self):
        mix = np.full(200, -12.0)
        stem = np.full(200, -60.0)
        stem[60:140] = -20.0
        mask = measures.stem_presence(stem, mix, 18.0)
        self.assertFalse(mask[:40].any())
        self.assertTrue(mask[70:130].all())


class TestMeter(unittest.TestCase):
    def setUp(self):
        self.t = np.arange(64) * 0.5
        self.no_beat = np.zeros(64, dtype=bool)

    def test_agreeing_trackers_give_agreed_positions(self):
        downs = self.t[2::4]                      # the "1" is every 4th beat, starting on beat 2
        fa = meter.flag_downbeats(self.t, downs)
        fb = meter.flag_downbeats(self.t, downs + 0.02)
        self.assertEqual(meter.beats_per_bar(fa), 4)
        bars = meter.bar_positions(self.t, self.no_beat, fa, fb, 4)
        self.assertTrue(bars["agreed"].all())
        self.assertTrue((bars["pos"][2::4] == 1).all())
        self.assertEqual(int(bars["pos"][3]), 2)

    def test_disagreeing_trackers_are_not_agreed(self):
        fa = meter.flag_downbeats(self.t, self.t[0::4])
        fb = meter.flag_downbeats(self.t, self.t[2::4])
        bars = meter.bar_positions(self.t, self.no_beat, fa, fb, 4)
        self.assertFalse(bars["agreed"].any())
        self.assertTrue((bars["pos"][0::4] == 1).all())   # the lead tracker is followed

    def test_main_beats_are_the_confirmed_half(self):
        confirmed = np.zeros(64, dtype=bool)
        confirmed[0::2] = True
        main = meter.main_beat_mask(self.t, self.no_beat, confirmed)
        self.assertTrue(main[0::2].all())
        self.assertFalse(main[1::2].any())
        self.assertTrue(meter.main_beat_mask(self.t, self.no_beat, np.ones(64, dtype=bool)).all())

    def test_local_bpm_and_run_break(self):
        t = np.concatenate([np.arange(16) * 0.5, 20.0 + np.arange(16) * 0.4])
        bpm = meter.local_bpm(t, np.zeros(32, dtype=bool))
        self.assertAlmostEqual(float(bpm[5]), 120.0, delta=0.5)
        self.assertAlmostEqual(float(bpm[25]), 150.0, delta=0.5)
        self.assertEqual(len(meter.beat_runs(t, np.zeros(32, dtype=bool))), 2)


class TestOwnerLabels(unittest.TestCase):
    def _truth(self):
        return {
            "beats": [{"t": 0.5 * i, "main": True, "level": "M2", "bar_pos": i % 4 + 1, "bar_pos_level": "M2", "strength": 1.0} for i in range(16)],
            "regions": {"no_beat": [], "kick_present": [{"start": 0.0, "end": 8.0, "level": "M2"}]},
            "drums": {"pieces": {"kick": [[0.5 * i, 0.9, "M2"] for i in range(16)], "snare": [[1.0, 0.5, "W"]]}},
        }

    def test_untouched_truth_is_only_finalized(self):
        truth = finalize(apply_labels(self._truth(), None))
        self.assertNotIn("owner", truth)
        self.assertEqual(truth["beats"][3]["bpm"], 120.0)
        self.assertEqual(truth["beats"][2]["drums"], ["kick"])      # the weak snare at 1.0 s is not counted
        self.assertFalse(truth["beats"][0]["no_beat"])

    def test_owner_layers_replace_the_draft(self):
        labels = {"saved": "2026-11-23T10:00:00", "layers": {
            "no_beat": {"reviewed": False, "items": [{"start": 4.0, "end": 6.0, "by": "owner"}]},
            "kick": {"reviewed": True, "items": [{"t": 0.0, "s": 0.9, "lvl": "M1"}, {"t": 0.52, "by": "owner"}]},
            "beats": {"reviewed": False, "items": [
                {"t": 0.5 * i + (0.03 if i == 2 else 0.0), "main": True, "pos": i % 4 + 1, "lvl": "M2", "plvl": "M2",
                 **({"by": "owner"} if i == 2 else {}), **({"posBy": "owner"} if i == 4 else {})} for i in range(16)]},
            "drop": {"reviewed": False, "items": [{"t": 6.0, "by": "owner"}]},
        }}
        truth = finalize(apply_labels(self._truth(), labels))
        self.assertEqual(truth["regions"]["no_beat"], [{"start": 4.0, "end": 6.0, "level": "H", "source": "owner"}])
        self.assertEqual(truth["regions"]["kick_present"][0]["level"], "M2")          # untouched layer kept
        self.assertEqual(truth["drums"]["pieces"]["kick"], [[0.0, 0.9, "A"], [0.52, 1.0, "H"]])
        self.assertEqual(truth["drums"]["pieces"]["snare"], [[1.0, 0.5, "W"]])
        self.assertEqual(truth["beats"][2]["level"], "H")
        self.assertEqual(truth["beats"][3]["level"], "M2")
        self.assertEqual(truth["beats"][4]["bar_pos_level"], "H")
        self.assertTrue(truth["beats"][9]["no_beat"])
        self.assertFalse(truth["beats"][12]["no_beat"])
        self.assertEqual(truth["drops"], [{"t": 6.0, "level": "H"}])
        self.assertEqual(truth["owner"]["layers"]["kick"], {"reviewed": True, "by_owner": 1, "items": 2})


class TestSectionChanges(unittest.TestCase):
    def test_kick_entering_and_leaving_are_found_on_the_beat(self):
        hz, bpm, duration = 20, 120.0, 128.0
        beats = [{"t": 0.5 * i, "main": True, "bar_pos": i % 4 + 1, "no_beat": False} for i in range(int(duration / 0.5))]
        n = int(duration * hz)
        t = np.arange(n) / hz
        kick_on = (t >= 32.0) & (t < 96.0)                     # the kick plays from bar 17 to bar 48
        curves = {
            "loud_db": np.where(kick_on, -10.0, -16.0),
            "kick_db": np.where(kick_on, -12.0, -60.0),
            "stem_drums_db": np.where(kick_on, -12.0, -60.0),
            "stem_other_db": np.full(n, -18.0),
            "bright_oct": np.full(n, 10.0),
            "fullness": np.full(n, 0.6),
        }
        self.assertAlmostEqual(float(np.median(np.diff(bar_lines(beats, duration)))), 2.0, places=6)
        changes = section_changes(beats, curves, hz, duration)
        self.assertEqual(len(changes), 2)
        self.assertAlmostEqual(changes[0]["t"], 32.0, delta=0.06)
        self.assertAlmostEqual(changes[1]["t"], 96.0, delta=0.06)
        self.assertIn("kick in", changes[0]["why"])
        self.assertIn("kick out", changes[1]["why"])

    def test_steady_music_has_no_section_change(self):
        hz, duration = 20, 64.0
        beats = [{"t": 0.5 * i, "main": True, "bar_pos": i % 4 + 1, "no_beat": False} for i in range(128)]
        n = int(duration * hz)
        curves = {"loud_db": np.full(n, -12.0), "kick_db": np.full(n, -14.0), "fullness": np.full(n, 0.5)}
        self.assertEqual(section_changes(beats, curves, hz, duration), [])


if __name__ == "__main__":
    unittest.main()
