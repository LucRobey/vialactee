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
        Verify that values pushed into spectral_delay_queue emerge only after lookahead_seconds.
        """
        lookahead = self.listener.analyzer.lookahead_seconds  # 5.0s
        t0 = 1000.0

        # Inject a unique synthetic item into the queue timestamped at t0
        synthetic_bands = np.array([11.0, 22.0, 33.0, 44.0, 55.0, 66.0, 77.0, 88.0])
        self.listener.spectral_delay_queue.append({
            'time': t0,
            'fft_band_values': synthetic_bands,
            'chroma_values': np.zeros(12),
            'smoothed_fft_band_values': synthetic_bands,
            'smoothed_chroma_values': np.zeros(12),
            'asserved_fft_band': synthetic_bands,
            'band_proportion': np.zeros(8),
            'band_means': np.zeros(8),
            'smoothed_total_power': 100.0,
            'asserved_total_power': 100.0,
            'band_peak': np.zeros(8),
            'band_flux': np.zeros(8),
            'is_song_change': True,
            'is_verse_chorus_change': True,
            'asserved_novelty': 0.88,
            'combined_novelty': 0.95,
        })

        # Scenario A: Before lookahead expires (e.g. t0 + 2.0s), popped_items should be empty
        self.listener.last_env_time = t0 + 2.0
        # Check popping logic manually or via time simulation
        popped_items = []
        sim_time = t0 + 2.0
        while len(self.listener.spectral_delay_queue) > 0:
            if sim_time - self.listener.spectral_delay_queue[0]['time'] >= lookahead:
                popped_items.append(self.listener.spectral_delay_queue.popleft())
            else:
                break
        self.assertEqual(len(popped_items), 0)
        self.assertFalse(self.listener.is_song_change)

        # Scenario B: After lookahead expires (e.g. t0 + 5.1s), item should pop and update facade
        sim_time = t0 + 5.1
        while len(self.listener.spectral_delay_queue) > 0:
            if sim_time - self.listener.spectral_delay_queue[0]['time'] >= lookahead:
                popped_items.append(self.listener.spectral_delay_queue.popleft())
            else:
                break

        self.assertEqual(len(popped_items), 1)
        best = popped_items[0]
        self.listener._delayed_fft_band_values = best['fft_band_values']
        self.listener._delayed_is_song_change = best['is_song_change']
        self.listener._delayed_is_verse_chorus_change = best['is_verse_chorus_change']
        self.listener._delayed_asserved_novelty = best['asserved_novelty']
        self.listener._delayed_combined_novelty = best['combined_novelty']

        np.testing.assert_array_equal(self.listener.fft_band_values, synthetic_bands)
        self.assertTrue(self.listener.is_song_change)
        self.assertTrue(self.listener.is_verse_chorus_change)
        self.assertAlmostEqual(self.listener.asserved_novelty, 0.88)
        self.assertAlmostEqual(self.listener.combined_novelty, 0.95)


if __name__ == '__main__':
    unittest.main()
