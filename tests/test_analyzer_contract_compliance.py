"""
tests/test_analyzer_contract_compliance.py

Executable version of docs/reference/audio_analyzer_contract.md (Group A rhythm core, Group C structure,
interface & runtime). The same checklist runs against every production rhythm analyzer
(MultiBandOnsetAudioAnalyzer = stable fallback, DyadicMetricalAudioAnalyzer = production default),
and Dyadic-specific metrical sub-pulse invariants are checked on top.
"""

import logging
import time
import unittest

import numpy as np

from music.BaseAudioAnalyzer import BaseAudioAnalyzer
from music.DyadicMetricalAudioAnalyzer import DyadicMetricalAudioAnalyzer
from music.Listener import Listener, ANALYZER_REGISTRY, DEFAULT_ANALYZER_MODEL
from music.MultiBandOnsetAudioAnalyzer import MultiBandOnsetAudioAnalyzer

FPS = 60.0
DT = 1.0 / FPS
VALID_TAGS = {"Bass/Kick", "Snare/Mid", "Hi-hat/Cymbal"}
PRODUCTION_ANALYZERS = ("MultiBandOnsetAudioAnalyzer", "DyadicMetricalAudioAnalyzer")


def make_listener(model=None, fake_delay=5.0, **extra_infos):
    infos = {
        "startServer": False,
        "useMicrophone": False,
        "HARDWARE_MODE": "simulation",
        "onRaspberry": False,
        "fakeDelay": fake_delay,
    }
    infos.update(extra_infos)
    if model is not None:
        infos["analyzer_model"] = model
    return Listener(infos)


def drive_click_train(listener, n_frames=900, period=30):
    """Feeds a 120 BPM kick train through the analyzer and records every frame's public state."""
    ing, an = listener.ingestion, listener.analyzer
    frames = []
    for f in range(n_frames):
        mb = ing.multiband_fft_values
        mb.fill(0.0)
        mb[0:3] = [200.0, 150.0, 100.0] if f % period == 0 else [2.0, 1.0, 0.5]
        an.update_structural_novelty(f * DT, DT, 1.0)
        an.detect_band_peaks(f * DT, DT, 1.0)
        frames.append({
            "t": f * DT,
            "phase": an.beat_phase,
            "bpm": getattr(an, "effective_bpm", an.bpm),
            "is_beat": an.is_beat,
            "is_real": an.is_real_beat,
            "is_dropped": an.is_dropped_beat,
            "count": an.beat_count,
            "song_change": an.is_song_change,
            "tag": an.current_beat_tag,
            "status": an.flywheel_status,
            "conf": an.beat_confidence,
            "sal": an.rhythm_salience,
            "live_sal": an.live_rhythm_salience,
            "trust": an.live_beat_trust,
        })
    return frames


class TestSharedAnalyzerContract(unittest.TestCase):
    """Group A + interface checks, run against every production analyzer."""

    def test_interface_and_inheritance(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                an = make_listener(name).analyzer
                self.assertIsInstance(an, BaseAudioAnalyzer)
                for method in ("update", "reset", "update_structural_novelty", "detect_band_peaks",
                               "capture_frame_telemetry", "get_model_metadata"):
                    self.assertTrue(callable(getattr(an, method)), method)
                for prop in ("silence_frames", "song_changes_times", "structural_changes_times",
                             "standalone_phase", "standalone_bpm", "live_beat_trust"):
                    self.assertTrue(hasattr(an, prop), prop)
                self.assertFalse(hasattr(an, "band_peak"))
                self.assertEqual(an.get_model_metadata()["model_class"], name)

    def test_rhythm_core_invariants_on_click_train(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                frames = drive_click_train(make_listener(name))
                beats = [f for f in frames if f["is_beat"]]
                self.assertGreater(len(beats), 8, "flywheel must produce beats")
                last_count = 0
                for f in frames:
                    self.assertTrue(0.0 <= f["phase"] < 1.0, f"beat_phase out of range: {f['phase']}")
                    self.assertTrue(60.0 <= f["bpm"] <= 260.0, f"bpm out of range: {f['bpm']}")
                    self.assertIn(f["status"], ("locked", "coasting"))
                    self.assertTrue(-1.0 <= f["conf"] <= 1.0)
                    self.assertTrue(0.0 <= f["trust"] <= 1.0)
                    self.assertTrue(0.0 <= f["sal"] <= 1.0)
                    self.assertTrue(0.0 <= f["live_sal"] <= 1.0)
                    self.assertIn(f["tag"], VALID_TAGS)
                    # is_dropped_beat == is_beat and not is_real_beat
                    self.assertEqual(f["is_dropped"], f["is_beat"] and not f["is_real"])
                    # beat_count increments exactly on every is_beat; the only allowed drop is the
                    # contractual reset to 0 on a song change
                    if f["count"] < last_count:
                        self.assertTrue(f["song_change"], "beat_count may only reset on a song change")
                        self.assertEqual(f["count"], 1 if f["is_beat"] else 0)
                    else:
                        self.assertEqual(f["count"], last_count + (1 if f["is_beat"] else 0))
                    last_count = f["count"]
                    # is_beat is the tick when beat_phase wraps: phase has just restarted
                    if f["is_beat"]:
                        self.assertLess(f["phase"], 0.15, "is_beat must coincide with the phase wrap")

    def test_tracks_120_bpm(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                frames = drive_click_train(make_listener(name))
                self.assertAlmostEqual(frames[-1]["bpm"], 120.0, delta=6.0)
                self.assertGreater(frames[-1]["conf"], 0.2)
                self.assertEqual(frames[-1]["status"], "locked")

    def test_refractory_lockout(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                frames = drive_click_train(make_listener(name))
                times = [f["t"] for f in frames if f["is_beat"]]
                gaps = np.diff(times)
                # tactus beats: >= max(0.18s, 0.4*60/bpm); sub-pulse beats: >= 0.12s
                self.assertTrue(np.all(gaps >= 0.12 - 1e-9), f"min gap {gaps.min():.3f}s")

    def test_reset_restores_initial_state(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                listener = make_listener(name)
                drive_click_train(listener, n_frames=400)
                listener.analyzer.reset()
                an = listener.analyzer
                self.assertEqual(an.beat_count, 0)
                self.assertAlmostEqual(an.bpm, 120.0)
                self.assertAlmostEqual(an.beat_phase, 0.0)
                self.assertFalse(an.is_beat)
                self.assertEqual(an.flywheel_status, "coasting")
                self.assertAlmostEqual(an.rhythm_salience, 0.0)

    def test_telemetry_keys(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                tel = make_listener(name).analyzer.capture_frame_telemetry()
                for key in ("bpm", "beat_phase", "confidence", "status", "is_beat", "is_real_beat",
                            "is_dropped_beat", "beat_tag", "rhythm_salience"):
                    self.assertIn(key, tel)

    def test_per_frame_cpu_budget(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                listener = make_listener(name)
                an, ing = listener.analyzer, listener.ingestion
                rng = np.random.default_rng(0)
                durations = []
                for f in range(600):
                    ing.multiband_fft_values[:] = rng.uniform(0.0, 50.0, size=32)
                    if f % 30 == 0:
                        ing.multiband_fft_values[0:3] = 200.0
                    t0 = time.perf_counter()
                    an.update(f * DT, DT, 1.0)
                    durations.append(time.perf_counter() - t0)
                # Production target is <= 0.5 ms; allow 2x headroom for slow CI machines.
                self.assertLess(float(np.mean(durations)) * 1000.0, 1.0)


class TestListenerContractWiring(unittest.TestCase):
    """Facade-level contract: model selection, 8-band band_flux, metrical bpm."""

    def test_default_model_is_dyadic(self):
        self.assertEqual(DEFAULT_ANALYZER_MODEL, "DyadicMetricalAudioAnalyzer")
        self.assertIsInstance(make_listener().analyzer, DyadicMetricalAudioAnalyzer)

    def test_registry_selects_each_model(self):
        for name, cls in ANALYZER_REGISTRY.items():
            with self.subTest(model=name):
                self.assertIs(type(make_listener(name).analyzer), cls)
        self.assertIs(type(make_listener("MultiBandOnsetAudioAnalyzer").analyzer), MultiBandOnsetAudioAnalyzer)

    def test_unknown_model_warns_instead_of_silently_falling_back(self):
        with self.assertLogs("music.Listener", level=logging.WARNING) as logs:
            listener = make_listener("NoSuchAnalyzer")
        self.assertTrue(any("NoSuchAnalyzer" in line for line in logs.output))
        self.assertIsInstance(listener.analyzer, DyadicMetricalAudioAnalyzer)

    def test_band_flux_is_8_band_mel_flux(self):
        """Contract: band_flux = max(0, E_b[t]-E_b[t-1]) over the 8 Mel bands (not the 8 lowest fine bands)."""
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                listener = make_listener(name, fake_delay=0.0)
                ing = listener.ingestion
                ing.fft_band_values[:] = 0.0
                listener._update_ring_buffers(0.0)
                ing.fft_band_values[7] = 100.0  # hi-hat region of the 8-band spectrum
                listener._update_ring_buffers(DT)
                w = (listener._ring_write - 1) % listener._ring_capacity
                flux = listener._ring_band_flux[w]
                self.assertEqual(len(flux), 8)
                self.assertAlmostEqual(float(flux[7]), 100.0)
                self.assertAlmostEqual(float(np.sum(flux[:7])), 0.0)
                # falling edge is half-wave rectified to zero
                ing.fft_band_values[7] = 10.0
                listener._update_ring_buffers(2 * DT)
                w = (listener._ring_write - 1) % listener._ring_capacity
                self.assertAlmostEqual(float(listener._ring_band_flux[w][7]), 0.0)

    def test_listener_bpm_is_metrical_rate(self):
        listener = make_listener("DyadicMetricalAudioAnalyzer")
        an = listener.analyzer
        an.bpm = 100.0
        an.subpulse_active = False
        self.assertAlmostEqual(listener.bpm, 100.0)
        an.subpulse_active = True
        self.assertAlmostEqual(listener.bpm, 200.0)
        self.assertAlmostEqual(listener.standalone_bpm, 200.0)


class TestDyadicMetricalInvariants(unittest.TestCase):
    """Sub-pulse beats must be real metrical beats that satisfy the same contract."""

    def setUp(self):
        self.listener = make_listener("DyadicMetricalAudioAnalyzer", fake_delay=5.0)
        self.an = self.listener.analyzer
        self.an.reset()

    def _arm_subpulse_crossing(self):
        """Tactus at 120 BPM, phase just below 0.5, percussive energy at the speaker window."""
        an = self.an
        an.bpm = 120.0
        an.subpulse_active = True
        an.speaker_phase = 0.49
        an.last_beat_time = -100.0
        an.rolling_flux_baseline = 1.0
        spk_c = an.odf_buffer_size - 1 - int(an.lookahead_seconds * an.odf_fps)
        an.kick_odf_buffer[spk_c - 3:spk_c + 4] = 30.0
        an.snare_odf_buffer[spk_c - 3:spk_c + 4] = 30.0
        an.hat_odf_buffer[spk_c - 3:spk_c + 4] = 0.0

    def test_subpulse_is_a_full_contract_beat(self):
        self._arm_subpulse_crossing()
        an = self.an
        count_before = an.beat_count
        an.is_beat = an.is_real_beat = an.is_dropped_beat = False
        an._advance_speaker_flywheel(1.0, DT)
        self.assertTrue(an.is_beat)
        self.assertTrue(an.is_real_beat)
        self.assertFalse(an.is_dropped_beat)
        self.assertEqual(an.beat_count, count_before + 1)          # increments on every is_beat
        self.assertEqual(an.intermediate_beat_count, 1)
        self.assertIn(an.current_beat_tag, VALID_TAGS)             # no out-of-contract tag
        self.assertLess(an.beat_phase, 0.15)                       # metrical phase wrapped
        self.assertAlmostEqual(an.effective_bpm, 240.0)            # metrical rate is doubled
        self.assertEqual(an._real_beat_history[0], 1.0)            # feeds the pulse-density pillar

    def test_subpulse_requires_physical_energy(self):
        self._arm_subpulse_crossing()
        an = self.an
        an.kick_odf_buffer[:] = 0.0
        an.snare_odf_buffer[:] = 0.0
        an.is_beat = False
        an._advance_speaker_flywheel(1.0, DT)
        self.assertFalse(an.is_beat, "silent sub-pulse must not emit a beat")

    def test_inactive_subpulse_keeps_tactus_semantics(self):
        an = self.an
        an.bpm = 120.0
        an.subpulse_active = False
        an.speaker_phase = 0.25
        self.assertAlmostEqual(an.beat_phase, 0.25)
        self.assertAlmostEqual(an.effective_bpm, 120.0)

    def test_reset_clears_subpulse_state(self):
        an = self.an
        an.subpulse_active = True
        an.subpulse_latch = 0.9
        an.intermediate_beat_count = 7
        an._tactus_beats = 9
        an.snare_odf_buffer[:] = 3.0
        an.reset()
        self.assertFalse(an.subpulse_active)
        self.assertEqual(an.subpulse_latch, 0.0)
        self.assertEqual(an.intermediate_beat_count, 0)
        self.assertEqual(an._tactus_beats, 0)
        self.assertTrue(np.all(an.snare_odf_buffer == 0.0))


class TestBackProjectionLatencySigns(unittest.TestCase):
    """AXIOM-05: D_net = lookahead - dynamic_audio_latency - hardware_latency.

    The benchmark runs with zero latencies, so it cannot see a wrong sign. Two otherwise identical
    runs fed the same click train must differ in locked speaker phase by (bpm/60) * (dyn + hw):
    a larger dyn or hw shortens the back-shift, so the phase moves *forward*.
    """

    DYN = 0.05
    HW = 0.04

    @staticmethod
    def _final_phase(name, dyn, led=0.0, audio_out=0.0):
        listener = make_listener(name, led_latency=led, audio_output_latency=audio_out)
        listener.ingestion.dynamic_audio_latency = dyn
        frames = drive_click_train(listener, n_frames=1200)
        return frames[-1]["phase"], frames[-1]["bpm"], frames[-1]["status"]

    @staticmethod
    def _circular_delta(a, b):
        return (a - b + 0.5) % 1.0 - 0.5

    def _check(self, name, dyn, hw):
        base_phase, bpm, status0 = self._final_phase(name, 0.0, 0.0)
        shifted_phase, _, status1 = self._final_phase(name, dyn, hw)
        self.assertEqual((status0, status1), ("locked", "locked"))
        expected = (bpm / 60.0) * (dyn + hw)
        measured = self._circular_delta(shifted_phase, base_phase)
        self.assertAlmostEqual(
            measured, expected, delta=0.06,
            msg=f"{name}: phase shift {measured:+.3f}, expected {expected:+.3f} (wrong sign would give {-expected:+.3f})")

    def test_dynamic_latency_reduces_back_shift(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                self._check(name, self.DYN + self.HW, 0.0)

    def test_hardware_latency_reduces_back_shift(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                self._check(name, 0.0, self.DYN + self.HW)

    def test_both_terms_add_up(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                self._check(name, self.DYN, self.HW)

    def test_audio_output_latency_increases_back_shift(self):
        """Slow speakers (Bluetooth...) mean the sound is heard later: the lights may wait longer."""
        out = 0.08
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                base_phase, bpm, _ = self._final_phase(name, 0.0)
                phase, _, status = self._final_phase(name, 0.0, audio_out=out)
                self.assertEqual(status, "locked")
                measured = self._circular_delta(phase, base_phase)
                self.assertAlmostEqual(measured, -(bpm / 60.0) * out, delta=0.06)

    def test_led_and_audio_output_lag_cancel_when_equal(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                base_phase, _, _ = self._final_phase(name, 0.0)
                phase, _, _ = self._final_phase(name, 0.0, led=0.06, audio_out=0.06)
                self.assertAlmostEqual(self._circular_delta(phase, base_phase), 0.0, delta=0.03)


class TestHardwareLatencyConfig(unittest.TestCase):
    """hardware_latency = led_latency - audio_output_latency; the legacy 'latency' key is ignored."""

    def test_net_is_led_minus_audio_output(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                an = make_listener(name, led_latency=0.12, audio_output_latency=0.05).analyzer
                self.assertAlmostEqual(an.hardware_latency, 0.07)

    def test_defaults_to_zero(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                self.assertEqual(make_listener(name).analyzer.hardware_latency, 0.0)

    def test_legacy_latency_key_is_ignored_with_warning(self):
        for name in PRODUCTION_ANALYZERS:
            with self.subTest(model=name):
                with self.assertLogs("music.BaseAudioAnalyzer", level="WARNING") as logs:
                    an = make_listener(name, latency=0.2).analyzer
                self.assertEqual(an.hardware_latency, 0.0)
                self.assertTrue(any("led_latency" in m for m in logs.output))


if __name__ == "__main__":
    unittest.main()
