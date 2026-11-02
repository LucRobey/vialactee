"""
Unit tests for music/Listener.py.
Verifies the facade pattern, property delegations, fake FFT processing,
and non-causal spectral delay queue synchronization.
"""
import unittest
import numpy as np
import time

from music.Listener import Listener
from music.MusicalContextEngine import MusicalScene


class TestListener(unittest.TestCase):
    def setUp(self):
        self.infos = {
            "useMicrophone": False,
            "fakeDelay": 5.0,
            "onRaspberry": False,
            "HARDWARE_MODE": "simulation",
        }
        self.listener = Listener(self.infos)

    def test_initial_facade_properties(self):
        # Numerical properties
        self.assertAlmostEqual(self.listener.bpm, 120.0)
        self.assertAlmostEqual(self.listener.beat_phase, 0.0)
        self.assertEqual(self.listener.beat_count, 0)
        self.assertEqual(self.listener.nb_of_fft_band, 16)
        self.assertEqual(len(self.listener.fft_band_values), 16)
        self.assertEqual(len(self.listener.chroma_values), 12)
        self.assertEqual(len(self.listener.asserved_fft_band), 16)
        self.assertEqual(len(self.listener.band_flux), 16)
        self.assertFalse(hasattr(self.listener, "band_peak"))
        self.assertFalse(hasattr(self.listener, "_ring_band_peak"))

        # Boolean flags
        self.assertFalse(self.listener.is_beat)
        self.assertFalse(self.listener.is_real_beat)
        self.assertFalse(self.listener.is_dropped_beat)
        self.assertFalse(self.listener.is_song_change)
        self.assertFalse(self.listener.is_verse_chorus_change)
        self.assertFalse(self.listener.live_is_song_change)
        self.assertFalse(self.listener.live_is_verse_chorus_change)

        # Novelty properties
        self.assertAlmostEqual(self.listener.asserved_novelty, 0.0)
        self.assertAlmostEqual(self.listener.combined_novelty, 0.0)
        self.assertAlmostEqual(self.listener.live_asserved_novelty, 0.0)
        self.assertAlmostEqual(self.listener.live_combined_novelty, 0.0)

        # Salience & Trust properties
        self.assertAlmostEqual(self.listener.rhythm_salience, 0.0)
        self.assertAlmostEqual(self.listener.live_rhythm_salience, 0.0)
        self.assertAlmostEqual(self.listener.beat_trust, 0.0)
        self.assertAlmostEqual(self.listener.live_beat_trust, 0.0)
        self.assertAlmostEqual(self.listener.salience_gradient, 0.0)

        # Context engine
        self.assertTrue(hasattr(self.listener, "context"))
        self.assertEqual(self.listener.context.scene, "CHILL")

        # Status & tags
        self.assertIn(self.listener.beat_tag, ["Bass/Kick", "Snare/Mid", "Hi-hat/Cymbal"])
        self.assertEqual(self.listener.flywheel_status, "coasting")

    def test_setters_and_getters(self):
        self.listener.sensi = 0.75
        self.assertAlmostEqual(self.listener.sensi, 0.75)

        self.listener.luminosite = 0.85
        self.assertAlmostEqual(self.listener.luminosite, 0.85)

        self.listener.dynamic_audio_latency = 0.045
        self.assertAlmostEqual(self.listener.dynamic_audio_latency, 0.045)

    def test_update_fake_fft(self):
        # Run several updates with fake FFT synthesis
        for _ in range(10):
            self.listener.update()

        # Ingestion should produce nonzero values after fake FFT updates
        self.assertGreater(np.sum(self.listener.ingestion.fft_band_values), 0.0)
        self.assertGreaterEqual(self.listener.ingestion.smoothed_total_power, 0.0)

    def test_spectral_delay_queue_synchronization(self):
        """
        Verify that values pushed into the ring buffer via Listener.update()
        emerge on public properties only after lookahead_seconds.
        """
        import unittest.mock

        t0 = 1000.0
        dt = 1.0 / 60.0
        synthetic_bands = np.arange(1, 17, dtype=np.float64) * 11.0

        # Disable random fake FFT synthesis so ingestion uses our deterministic 16-band input
        self.listener.ingestion.useMicrophone = True

        nov = self.listener.analyzer.novelty_detector
        with unittest.mock.patch.object(self.listener.analyzer, "update_structural_novelty"), \
             unittest.mock.patch.object(self.listener.analyzer, "detect_band_peaks"):
            # 1. Push synthetic 16-band frame and structural novelty flags at t = t0
            self.listener.ingestion.fft_band_values[:] = synthetic_bands
            nov.is_song_change = True
            nov.is_verse_chorus_change = True
            nov.asserved_novelty = 0.88
            nov.combined_novelty = 0.95

            with unittest.mock.patch("music.Listener.time.time", return_value=t0):
                self.listener.update(fixed_dt=dt)

            # Immediately at t0, the 5.0s lookahead has not expired yet
            np.testing.assert_array_equal(self.listener.fft_band_values, np.zeros(16))
            self.assertFalse(self.listener.is_song_change)
            self.assertFalse(self.listener.is_verse_chorus_change)

            # 2. Scenario A: Before lookahead expires (t = t0 + 2.0s < t0 + 5.0s)
            self.listener.ingestion.fft_band_values.fill(0.0)
            nov.is_song_change = False
            nov.is_verse_chorus_change = False
            nov.asserved_novelty = 0.0
            nov.combined_novelty = 0.0

            with unittest.mock.patch("music.Listener.time.time", return_value=t0 + 2.0):
                self.listener.update(fixed_dt=dt)

            self.assertEqual(self.listener._ring_count, 2)
            np.testing.assert_array_equal(self.listener.fft_band_values, np.zeros(16))
            self.assertFalse(self.listener.is_song_change)
            self.assertFalse(self.listener.is_verse_chorus_change)
            self.assertAlmostEqual(self.listener.asserved_novelty, 0.0)
            self.assertAlmostEqual(self.listener.combined_novelty, 0.0)

            # 3. Scenario B: After lookahead expires (t = t0 + 5.1s >= t0 + 5.0s)
            with unittest.mock.patch("music.Listener.time.time", return_value=t0 + 5.1):
                self.listener.update(fixed_dt=dt)

            np.testing.assert_array_equal(self.listener.fft_band_values, synthetic_bands)
            self.assertTrue(self.listener.is_song_change)
            self.assertTrue(self.listener.is_verse_chorus_change)
            self.assertAlmostEqual(self.listener.asserved_novelty, 0.88)
            self.assertAlmostEqual(self.listener.combined_novelty, 0.95)

    def test_listener_rhythm_salience_and_reset(self):
        """Verify delayed rhythm_salience, unbuffered live_rhythm_salience, and reset."""
        self.listener._delayed_rhythm_salience = 0.75
        self.listener._ring_rhythm_salience[0] = 0.75
        self.assertAlmostEqual(self.listener.rhythm_salience, 0.75)

        # live_rhythm_salience comes directly from analyzer
        self.listener.analyzer._live_rhythm_salience = 0.88
        self.assertAlmostEqual(self.listener.live_rhythm_salience, 0.88)

        # Calling reset clears delayed and ring buffer states
        self.listener.reset()
        self.assertAlmostEqual(self.listener.rhythm_salience, 0.0)
        self.assertTrue(np.all(self.listener._ring_rhythm_salience == 0.0))
        self.assertAlmostEqual(self.listener.live_rhythm_salience, 0.0)

    def test_listener_beat_trust_and_context(self):
        """Verify delayed beat_trust, live_beat_trust, and context engine integration."""
        self.listener._delayed_beat_trust = 0.65
        self.listener._ring_beat_trust[0] = 0.65
        self.assertAlmostEqual(self.listener.beat_trust, 0.65)

        # live_beat_trust comes from confidence_score
        self.listener.analyzer.confidence_score = 0.82
        self.assertAlmostEqual(self.listener.live_beat_trust, 0.82)

        # Calling reset clears beat_trust ring buffer and delayed state, and resets context
        self.listener.context._current_scene = MusicalScene.GROOVE
        self.listener.reset()
        self.assertAlmostEqual(self.listener.beat_trust, 0.0)
        self.assertTrue(np.all(self.listener._ring_beat_trust == 0.0))
        self.assertEqual(self.listener.context.scene, "CHILL")

    def test_listener_delayed_flags_reset(self):
        """Verify delayed novelty flags reset to False when no queued event matches."""
        self.listener._delayed_is_song_change = True
        self.listener._delayed_is_verse_chorus_change = True
        self.listener.update()
        self.assertFalse(self.listener.is_song_change)
        self.assertFalse(self.listener.is_verse_chorus_change)

    def test_listener_standalone_phase(self):
        """Verify listener exposes standalone_phase alias matching beat_phase."""
        self.assertEqual(self.listener.standalone_phase, self.listener.beat_phase)


if __name__ == '__main__':
    unittest.main()
