"""
tests/test_local_microphone_clock.py
Live sound (Spotify, aux) must advance the analyzer by the audio received, 60 ticks per second of music.

Before 2026-11-27 the live connector only refreshed the spectrum and left the ticking to the display loop
(30 per second), which put the beats in the wrong place (research/scoreboard/runs/live_path/LIVE_PATH.md).
"""
import time
import types
import unittest

import numpy as np

from connectors.Local_Microphone import Local_Microphone

SR, CHUNK, HOP, WINDOW = 44100, 1024, 735, 4096


class _FakeListener:
    """Records what the connector asks of the listener."""

    def __init__(self) -> None:
        self.windows, self.dts, self.latencies = [], [], []
        self.dynamic_audio_latency = 0.0
        self.fft_band_values = np.zeros(16)

    def process_raw_audio(self, audio: np.ndarray) -> None:
        self.windows.append(audio.copy())
        self.latencies.append(self.dynamic_audio_latency)

    def update(self, fixed_dt=None) -> None:
        self.dts.append(fixed_dt)


def _feed(mic: Local_Microphone, samples: np.ndarray) -> None:
    info = types.SimpleNamespace(currentTime=0.0, inputBufferAdcTime=0.0)
    for a in range(0, len(samples) - CHUNK + 1, CHUNK):
        mic.audio_callback(samples[a : a + CHUNK].reshape(-1, 1), CHUNK, info, None)


class TestAnalyzerIsTickedByTheAudio(unittest.TestCase):
    def setUp(self):
        self.listener = _FakeListener()
        self.mic = Local_Microphone(self.listener, {"useMicrophone": True, "fakeDelay": 0.0})
        self.ramp = np.arange(SR, dtype=np.float64)          # sample n has value n: a window says where it ends

    def test_no_audio_no_tick(self):
        self.assertEqual(self.mic.step_analyzer(), 0)
        self.assertEqual(self.listener.dts, [])

    def test_one_tick_per_735_samples_with_the_right_window(self):
        _feed(self.mic, self.ramp[: 4 * CHUNK])              # 4096 samples received: five ticks of 735 fit
        ticks = self.mic.step_analyzer()
        self.assertEqual(ticks, 4096 // HOP)
        self.assertEqual(self.listener.dts, [1.0 / 60.0] * ticks)
        for k, w in enumerate(self.listener.windows):
            end = (k + 1) * HOP
            self.assertEqual(len(w), WINDOW)
            self.assertEqual(w[-1], end - 1)                 # the window ends on the tick's sample
            self.assertEqual(w[0], 0.0)                      # before the stream started: silence
        self.assertEqual(self.mic.step_analyzer(), 0)        # nothing new: no tick

    def test_ticks_follow_the_audio_not_the_number_of_calls(self):
        calls = 0
        for a in range(0, 40 * CHUNK, CHUNK):                # 40960 samples, a call after each chunk and two idle calls
            _feed(self.mic, self.ramp[a : a + CHUNK])
            for _ in range(3):
                self.mic.step_analyzer()
                calls += 1
        self.assertEqual(len(self.listener.dts), (40 * CHUNK) // HOP)
        self.assertEqual(calls, 120)
        last = self.listener.windows[-1]
        self.assertEqual(last[-1], ((40 * CHUNK) // HOP) * HOP - 1)
        np.testing.assert_array_equal(np.diff(last), np.ones(WINDOW - 1))     # a clean cut across the ring's edge

    def test_a_late_call_catches_up_then_skips_what_is_too_old(self):
        _feed(self.mic, self.ramp[: 8 * CHUNK])              # 11 ticks behind: replayed, six per call
        self.assertEqual(self.mic.step_analyzer(), Local_Microphone.MAX_TICKS_PER_CALL)
        self.assertEqual(self.mic.step_analyzer(), (8 * CHUNK) // HOP - Local_Microphone.MAX_TICKS_PER_CALL)
        _feed(self.mic, self.ramp[8 * CHUNK : 30 * CHUNK])   # 30 ticks behind: the oldest audio is skipped
        self.assertEqual(self.mic.step_analyzer(), 2)
        self.assertGreater(self.listener.windows[-1][-1], 30 * CHUNK - 2 * HOP - 1)

    def test_latency_counts_the_audio_received_after_the_window(self):
        _feed(self.mic, self.ramp[: 4 * CHUNK])
        self.mic._newest_sample_time = time.time()           # the newest sample is "now"
        self.mic.step_analyzer()
        half = (WINDOW / 2.0) / SR
        behind_first = (4 * CHUNK - HOP) / SR
        self.assertAlmostEqual(self.listener.latencies[0], behind_first + half, delta=0.01)
        self.assertLess(self.listener.latencies[-1], self.listener.latencies[0])


class TestBeatsOnTheLiveRoad(unittest.TestCase):
    """The real connector and a real Listener on a made-up song: the beats must be where the kicks are."""

    def test_beats_are_found_at_the_display_loops_pace(self):
        from music.api import Listener
        from tools.listener_config import build_listener_infos

        rng = np.random.default_rng(0)
        mono = (0.02 * rng.standard_normal(30 * SR)).astype(np.float32)
        burst_t = np.arange(int(0.12 * SR)) / SR
        burst = (0.8 * np.sin(2 * np.pi * 60.0 * burst_t) * np.exp(-burst_t / 0.04)).astype(np.float32)
        kicks = np.arange(1.0, 29.0, 0.4917)
        for t in kicks:
            i = int(t * SR)
            mono[i : i + len(burst)] += burst

        clock = [1000.0]
        real_time = time.time
        time.time = lambda: clock[0]
        try:
            infos = build_listener_infos()
            infos["fakeDelay"] = 5.0
            listener = Listener(infos)
            mic = Local_Microphone(listener, {"useMicrophone": True, "fakeDelay": 0.0})
            info = types.SimpleNamespace(currentTime=0.0, inputBufferAdcTime=0.0)
            beats, last, sent = [], listener.beat_count, 0
            for j in range(1, int(34 * 60)):                 # the task comes back 60 times a second
                now = j / 60.0
                clock[0] = 1000.0 + now
                while sent + CHUNK <= int(now * SR):         # the sound card has delivered these chunks
                    chunk = np.zeros(CHUNK, dtype=np.float32)
                    a, b = sent, min(len(mono), sent + CHUNK)
                    if b > a:
                        chunk[: b - a] = mono[a:b]
                    mic.audio_callback(chunk.reshape(-1, 1), CHUNK, info, None)
                    sent += CHUNK
                before = listener.beat_count
                mic.step_analyzer()
                if listener.beat_count > before or listener.beat_count > last:
                    beats.append(now - 5.0)
                last = listener.beat_count
        finally:
            time.time = real_time
        beats = np.array(beats)
        late = kicks[kicks >= 12.0]
        on_time = np.mean([np.min(np.abs(beats - k)) <= 0.05 for k in late])
        self.assertGreater(on_time, 0.9)


if __name__ == "__main__":
    unittest.main()
