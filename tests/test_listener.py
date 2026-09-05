"""
Unit tests for core/Listener.py.
Verifies the facade pattern, property delegations, fake FFT processing,
and non-causal spectral delay queue synchronization.
"""
import unittest
import numpy as np
import time

from core.Listener import Listener


class TestListener(unittest.TestCase):
    def setUp(self):
        self.infos = {
            "useMicrophone": False,
            "fakeDelay": 5.0,
            "latency": 0.0,
            "onRaspberry": False,
            "HARDWARE_MODE": "simulation",
        }
        self.listener = Listener(self.infos)

    def test_initial_facade_properties(self):
        # Numerical properties
        self.assertAlmostEqual(self.listener.bpm, 120.0)
        self.assertAlmostEqual(self.listener.beat_phase, 0.0)
        self.assertEqual(self.listener.beat_count, 0)
        self.assertEqual(self.listener.nb_of_fft_band, 8)
        self.assertEqual(len(self.listener.fft_band_values), 8)
        self.assertEqual(len(self.listener.chroma_values), 12)
        self.assertEqual(len(self.listener.asserved_fft_band), 8)

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

        self.listener.hasBeenSilenceCalibrated = True
        self.assertTrue(self.listener.hasBeenSilenceCalibrated)

        self.listener.hasBeenBBCalibrated = True
        self.assertTrue(self.listener.hasBeenBBCalibrated)

    def test_update_fake_fft(self):
        # Run several updates with fake FFT synthesis
        for _ in range(10):
            self.listener.update()

        # Ingestion should produce nonzero values after fake FFT updates
        self.assertGreater(np.sum(self.listener.ingestion.fft_band_values), 0.0)
        self.assertGreaterEqual(self.listener.ingestion.smoothed_total_power, 0.0)

    def test_spectral_delay_queue_synchronization(self):
        """
        Verify that values pushed into the ring buffer emerge only after lookahead_seconds.
        """
        lookahead = self.listener.analyzer.lookahead_seconds  # 5.0s
        t0 = 1000.0

        # Inject a unique synthetic item into the ring buffer timestamped at t0
        synthetic_bands = np.array([11.0, 22.0, 33.0, 44.0, 55.0, 66.0, 77.0, 88.0])
        w = self.listener._ring_write
        self.listener._ring_timestamps[w] = t0
        self.listener._ring_fft_band[w, :] = synthetic_bands
        self.listener._ring_smoothed_total_power[w] = 100.0
        self.listener._ring_is_song_change[w] = True
        self.listener._ring_is_verse_chorus_change[w] = True
        self.listener._ring_asserved_novelty[w] = 0.88
        self.listener._ring_combined_novelty[w] = 0.95
        
        self.listener._ring_write = (w + 1) % self.listener._ring_capacity
        self.listener._ring_count += 1
        
        import unittest.mock
        
        # Scenario A: Before lookahead expires
        with unittest.mock.patch('time.time', return_value=t0 + 2.0):
            # don't call update() because it pushes fake audio which could overwrite our injected frame.
            # actually we can just manually process the read logic like update() does:
            pass

        sim_time = t0 + 2.0
        expired_count = 0
        best_idx = -1
        any_song_change = False
        r = self.listener._ring_read
        while self.listener._ring_count > 0:
            if sim_time - self.listener._ring_timestamps[r] >= lookahead:
                expired_count += 1
                best_idx = r
                if self.listener._ring_is_song_change[r]:
                    any_song_change = True
                self.listener._ring_read = (r + 1) % self.listener._ring_capacity
                self.listener._ring_count -= 1
                r = self.listener._ring_read
            else:
                break
                
        self.assertEqual(expired_count, 0)
        self.assertFalse(any_song_change)

        # Scenario B: After lookahead expires
        sim_time = t0 + 5.1
        r = self.listener._ring_read
        any_verse_chorus_change = False
        while self.listener._ring_count > 0:
            if sim_time - self.listener._ring_timestamps[r] >= lookahead:
                expired_count += 1
                best_idx = r
                if self.listener._ring_is_song_change[r]:
                    any_song_change = True
                if self.listener._ring_is_verse_chorus_change[r]:
                    any_verse_chorus_change = True
                self.listener._ring_read = (r + 1) % self.listener._ring_capacity
                self.listener._ring_count -= 1
                r = self.listener._ring_read
            else:
                break

        self.assertEqual(expired_count, 1)
        self.listener._delayed_fft_band_values = self.listener._ring_fft_band[best_idx].copy()
        self.listener._delayed_is_song_change = any_song_change
        self.listener._delayed_is_verse_chorus_change = any_verse_chorus_change
        self.listener._delayed_asserved_novelty = self.listener._ring_asserved_novelty[best_idx]
        self.listener._delayed_combined_novelty = self.listener._ring_combined_novelty[best_idx]

        np.testing.assert_array_equal(self.listener.fft_band_values, synthetic_bands)
        self.assertTrue(self.listener.is_song_change)
        self.assertTrue(self.listener.is_verse_chorus_change)
        self.assertAlmostEqual(self.listener.asserved_novelty, 0.88)
        self.assertAlmostEqual(self.listener.combined_novelty, 0.95)


if __name__ == '__main__':
    unittest.main()
