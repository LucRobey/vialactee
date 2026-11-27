"""
tests/test_mode_master_display_frame.py
The display loop collects the analyzer's one-frame signals once per frame, before the modes draw
(docs/contracts/music_analyzer_contract.md, section 1.1), and ticks the listener itself only when no audio
connector does.
"""
import asyncio
import unittest
from unittest.mock import MagicMock

import numpy as np

from core.Mode_master import Mode_master


def _mode_master(externally_clocked: bool):
    listener = MagicMock()
    listener.luminosite = 0.8
    listener.sensi = 0.5
    listener.smoothed_fft_band_values = np.zeros(16)
    listener.asserved_fft_band = np.zeros(16)
    listener._delayed_asserved_fft_band = np.zeros(16)
    listener.nb_of_fft_band = 16
    listener.asserved_total_power = 0.0
    listener.is_externally_clocked = externally_clocked
    infos = {"onRaspberry": False, "HARDWARE_MODE": "simulation", "printCpuFpsInfo": False, "auto_transition_time": 25.0}
    mm = Mode_master(listener, infos, np.zeros((785, 3), dtype=np.int32), np.zeros((519, 3), dtype=np.int32))
    order = []
    listener.update.side_effect = lambda *a, **k: order.append("tick")
    listener.begin_display_frame.side_effect = lambda: order.append("collect")
    for seg in mm.segments_list:
        seg.update = MagicMock(side_effect=lambda *a, **k: order.append("draw"))
    mm.leds_list = []
    return mm, listener, order


class TestDisplayFrame(unittest.TestCase):
    def test_signals_are_collected_once_before_the_modes_draw(self):
        mm, listener, order = _mode_master(externally_clocked=True)
        asyncio.run(mm.update())
        self.assertEqual(listener.begin_display_frame.call_count, 1)
        self.assertEqual(order[0], "collect")
        self.assertIn("draw", order)
        self.assertNotIn("tick", order)          # the audio connector ticks the analyzer, not the display loop
        asyncio.run(mm.update())
        self.assertEqual(listener.begin_display_frame.call_count, 2)

    def test_without_an_audio_clock_the_loop_ticks_then_collects(self):
        mm, listener, order = _mode_master(externally_clocked=False)
        asyncio.run(mm.update())
        self.assertEqual(order[:2], ["tick", "collect"])


if __name__ == "__main__":
    unittest.main()
