"""
Contract tests for the tools/mode_studio.py ingest loop.

is_beat / is_real_beat are ONE-FRAME flags cleared by the next Listener.update(). The studio catches up with
up to 6 analyzer steps per screen frame, so it must hand control to the mode after EVERY step
(`advance_ingest_frame(on_frame_step=...)`); rendering once after the batch silently drops beat ticks.
"""
import unittest

import numpy as np

from tools.mode_studio import AudioStreamer


class _StubListener:
    def __init__(self):
        self.updates = 0
        self.is_beat = False

    def process_raw_audio(self, chunk):
        pass

    def update(self, fixed_dt=None):
        self.updates += 1
        # a tick lands on every 3rd analyzer step; the next update clears it
        self.is_beat = (self.updates % 3 == 0)


def _make_streamer(listener, steps_behind):
    """AudioStreamer wired to a stub listener, `steps_behind` analyzer hops behind the speaker."""
    s = object.__new__(AudioStreamer)
    s.listener = listener
    s.sample_rate = 44100
    s.hop_samples = 735
    s.lookahead_samples = 0
    s.mono_data = np.zeros(44100 * 5, dtype=np.float32)
    s.total_samples = len(s.mono_data)
    s.ingest_sample_pos = 0
    s.get_actual_speaker_sample = lambda: steps_behind * s.hop_samples
    return s


class TestStudioIngestContract(unittest.TestCase):
    def test_callback_runs_once_per_analyzer_step(self):
        listener = _StubListener()
        streamer = _make_streamer(listener, steps_behind=5)
        calls = []
        stepped = streamer.advance_ingest_frame(0.0, on_frame_step=lambda: calls.append(listener.is_beat))
        self.assertEqual(stepped, 5)
        self.assertEqual(len(calls), 5)
        self.assertEqual(listener.updates, 5)

    def test_per_step_callback_sees_every_tick_that_a_batch_render_would_miss(self):
        listener = _StubListener()
        streamer = _make_streamer(listener, steps_behind=6)
        seen = []
        streamer.advance_ingest_frame(0.0, on_frame_step=lambda: seen.append(listener.is_beat))
        self.assertEqual(sum(seen), 2, "ticks on steps 3 and 6 must both be observed")

        # What the old loop observed: only the state after the whole batch.
        listener2 = _StubListener()
        streamer2 = _make_streamer(listener2, steps_behind=6)
        streamer2.advance_ingest_frame(0.0)
        self.assertEqual(int(listener2.is_beat), 1)  # 1 of the 2 ticks survives; with 5 steps it would be 0


if __name__ == "__main__":
    unittest.main()
