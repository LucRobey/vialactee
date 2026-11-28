"""The lab candidate MultiBandSixSignalsAudioAnalyzer (run 2026-11-27_best_beat) inside the production Listener:
the parent model's beats and tempo, plus the six slots production writes itself. Promoted on 2026-11-27: the
candidate is now an alias of the main analyzer, and these tests hold for both."""
import unittest

from music.api import Listener
from music.MultiBandOnsetAudioAnalyzer import MultiBandOnsetAudioAnalyzer
from music.MusicSignals import BRIDGED, FIELDS, PRODUCED
from research.experiments.models.MultiBandSixSignalsAudioAnalyzer import MultiBandSixSignalsAudioAnalyzer


class TestMultiBandSixSignals(unittest.TestCase):
    def test_it_is_the_parent_model_with_no_sub_pulse(self):
        listener = Listener({"useMicrophone": False}, analyzer_class=MultiBandSixSignalsAudioAnalyzer)
        self.assertIsInstance(listener.analyzer, MultiBandOnsetAudioAnalyzer)
        self.assertFalse(hasattr(listener.analyzer, "subpulse_active"))      # the half-beat arbiter belongs to production only

    def test_the_six_slots_wait_for_the_speakers(self):
        listener = Listener({"useMicrophone": False}, analyzer_class=MultiBandSixSignalsAudioAnalyzer)      # 5 s look-ahead
        for _ in range(8):
            listener.update(1.0 / 60.0)
        values = listener.signals.as_dict()
        for name in PRODUCED:
            self.assertIsNone(values[name], name)

    def test_it_fills_the_six_slots_and_only_those(self):
        listener = Listener({"useMicrophone": False, "fakeDelay": 0.0}, analyzer_class=MultiBandSixSignalsAudioAnalyzer)
        for _ in range(8):
            listener.update(1.0 / 60.0)
        values = listener.signals.as_dict()
        for name in FIELDS:
            if name in BRIDGED or name in PRODUCED:
                self.assertIsNotNone(values[name], name)
            else:
                self.assertIsNone(values[name], name)
        for name in ("kick", "band_bass", "band_mid", "band_high"):
            self.assertTrue(0.0 <= values[name] <= 1.0, name)
        self.assertIsInstance(values["no_beat"], bool)
        listener.reset()
        self.assertTrue(all(v is None for v in listener.signals.as_dict().values()))


if __name__ == "__main__":
    unittest.main()
