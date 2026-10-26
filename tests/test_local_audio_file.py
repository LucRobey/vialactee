"""
tests/test_local_audio_file.py - Tests for Local_AudioFile streamer and Main.py CLI parity
"""

import os
import unittest
import numpy as np
import tempfile
import soundfile as sf

from music.Listener import Listener
from connectors.Local_AudioFile import Local_AudioFile
from Main import parse_arguments


class TestLocalAudioFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.assets_mp3_dir = os.path.join(cls.repo_root, "assets", "musics", "mp3_files")

        # Create a small temporary test audio file (2 seconds of 440 Hz sine wave at 48000 Hz to test resampling)
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_wav_path = os.path.join(cls.temp_dir.name, "test_tone.wav")
        sr = 48000
        t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False, dtype=np.float32)
        sine_wave = 0.5 * np.sin(2 * np.pi * 440.0 * t).astype(np.float32)
        stereo_wave = np.column_stack((sine_wave, sine_wave))
        sf.write(cls.test_wav_path, stereo_wave, sr)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def setUp(self):
        self.infos = {
            "useMicrophone": False,
            "fakeDelay": 5.0,
            "onRaspberry": False,
            "HARDWARE_MODE": "simulation",
            "sample_rate": 44100,
            "buffer_size": 4096,
        }
        self.listener = Listener(self.infos)

    def test_audio_file_loading_and_resampling(self):
        player = Local_AudioFile(self.listener, self.infos, song_path=self.test_wav_path)
        self.assertEqual(player.sample_rate, 44100)
        # Should be resampled to exactly 44100 * 2.0 = 88200 samples
        expected_samples = 44100 * 2
        self.assertAlmostEqual(player.total_samples, expected_samples, delta=10)
        self.assertAlmostEqual(player.total_duration, 2.0, delta=0.01)
        self.assertEqual(player.stereo_data.ndim, 2)
        self.assertEqual(player.stereo_data.shape[1], 2)
        self.assertEqual(player.mono_data.ndim, 1)

    def test_resolve_song_path_variants(self):
        player = Local_AudioFile(self.listener, self.infos, song_path=self.test_wav_path)

        # 1. Direct path
        self.assertEqual(os.path.normpath(player.resolve_song_path(self.test_wav_path)), os.path.normpath(self.test_wav_path))

        # 2. Assets directory resolution by filename
        resolved_nightcall = player.resolve_song_path("Nightcall.mp3")
        expected_nightcall = os.path.join(self.assets_mp3_dir, "Nightcall.mp3")
        self.assertEqual(os.path.normpath(resolved_nightcall), os.path.normpath(expected_nightcall))

        # 3. Without .mp3 extension
        resolved_no_ext = player.resolve_song_path("Nightcall")
        self.assertEqual(os.path.normpath(resolved_no_ext), os.path.normpath(expected_nightcall))

        # 4. Fuzzy match
        resolved_fuzzy = player.resolve_song_path("palladium")
        self.assertTrue(resolved_fuzzy.lower().endswith("palladium.mp3"))

    def test_anticipation_and_lookahead_priming(self):
        player = Local_AudioFile(self.listener, self.infos, song_path=self.test_wav_path)
        self.assertTrue(getattr(self.listener, "is_externally_clocked", False))
        self.assertEqual(self.listener.dynamic_audio_latency, 0.0)

        # Prime analyzer (should fill ring buffer with lookahead frames)
        player.prime_analyzer(0.0)
        self.assertGreater(self.listener._ring_count, 0)
        self.assertEqual(player.ingest_sample_pos, 300 * player.hop_samples)

    def test_advance_ingest_frame(self):
        player = Local_AudioFile(self.listener, self.infos, song_path=self.test_wav_path)
        player.prime_analyzer(0.0)
        initial_ingest = player.ingest_sample_pos

        # Simulate speaker position moving forward by 2 hops
        player.speaker_sample_pos = 2 * player.hop_samples
        stepped = player.advance_ingest_frame(0.0)
        self.assertGreaterEqual(stepped, 1)
        self.assertGreater(player.ingest_sample_pos, initial_ingest)

    def test_transport_controls(self):
        player = Local_AudioFile(self.listener, self.infos, song_path=self.test_wav_path)
        player.is_playing = True

        # Pause / Resume
        new_state = player.toggle_pause()
        self.assertFalse(new_state)
        self.assertFalse(player.is_playing)

        new_state = player.toggle_pause()
        self.assertTrue(new_state)
        self.assertTrue(player.is_playing)

        # Seek
        player.seek(1.0)
        self.assertAlmostEqual(player.get_current_time(), 1.0, delta=0.05)

        player.seek_relative(-0.5)
        self.assertAlmostEqual(player.get_current_time(), 0.5, delta=0.05)

    def test_cli_parser_options(self):
        # 1. Song with explicit flag
        args = parse_arguments(["--song", "Nightcall.mp3"])
        self.assertEqual(args.song, "Nightcall.mp3")
        self.assertFalse(args.use_microphone)

        # 2. Song with short flag -s
        args = parse_arguments(["-s", "assets/musics/mp3_files/Nightcall.mp3"])
        self.assertEqual(args.song, "assets/musics/mp3_files/Nightcall.mp3")

        # 3. Flag --song without value (defaults to const="")
        args = parse_arguments(["--song"])
        self.assertEqual(args.song, "")

        # 4. Positional song
        args = parse_arguments(["Palladium.mp3"])
        self.assertEqual(args.song_pos, "Palladium.mp3")
        self.assertIsNone(args.song)

        # 5. Microphone override
        args = parse_arguments(["--mic"])
        self.assertTrue(args.use_microphone)

        # 6. Additional options
        args = parse_arguments([
            "--song", "Nightcall.mp3",
            "--loop",
            "--mode", "Rainbow",
            "--profile", "small",
            "--model", "AudioAnalyzer",
            "--server",
            "--panel"
        ])
        self.assertEqual(args.song, "Nightcall.mp3")
        self.assertTrue(args.loop)
        self.assertEqual(args.mode, "Rainbow")
        self.assertEqual(args.profile, "small")
        self.assertEqual(args.model, "AudioAnalyzer")
        self.assertTrue(args.server)
        self.assertTrue(args.panel)

    def test_fake_leds_audio_player_delegation(self):
        from hardware.Fake_leds import FakeLedsVisualizer, Fake_leds
        vis = FakeLedsVisualizer()
        strip = Fake_leds(100)

        player = Local_AudioFile(self.listener, self.infos, song_path=self.test_wav_path)
        strip.set_audio_player(player)
        self.assertIs(vis.audio_player, player)

    def test_startup_transition_stability_and_ring_buffer_cleanliness(self):
        """Verifies that prime_analyzer leaves zero false triggers and Transition_Director experiences zero startup transitions."""
        from transitions.director import Transition_Director
        from core.TransitionBridge import build_music_snapshot

        infos = dict(self.infos)
        infos["startup_grace_period"] = 3.0
        listener = Listener(infos)
        director = Transition_Director(infos)

        player = Local_AudioFile(listener, infos, song_path=self.test_wav_path)
        player.prime_analyzer()

        # 1. Verify ring buffers and delayed triggers are pristine after pre-roll
        self.assertFalse(np.any(listener._ring_is_song_change))
        self.assertFalse(np.any(listener._ring_is_verse_chorus_change))
        self.assertFalse(listener._delayed_is_song_change)
        self.assertFalse(listener._delayed_is_verse_chorus_change)

        # 2. Simulate 180 frames (3.0 seconds) of speaker playback
        dt = 1.0 / 60.0
        transitions_fired = 0

        for f in range(180):
            # Step the audio player ingestion
            player.speaker_sample_pos = f * player.hop_samples
            player.advance_ingest_frame()

            # Create snapshot for Transition_Director
            music = build_music_snapshot(listener)
            if director.update(dt, music):
                transitions_fired += 1

        self.assertEqual(transitions_fired, 0, f"No transitions should fire during the 3.0s startup grace window, got reason={director.last_trigger_reason}")
        self.assertFalse(director._song_change_armed)
        self.assertFalse(director._structural_change_armed)
        self.assertFalse(director._drop_buildup_armed)


if __name__ == "__main__":
    unittest.main()
