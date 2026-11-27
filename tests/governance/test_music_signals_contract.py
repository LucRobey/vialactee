"""
tests/governance/test_music_signals_contract.py
The truth-mirrored signal contract: one list, kept identical in three places.

1. music/MusicSignals.py            the slots of the record exposed at listener.signals
2. config/music_signals.json        the machine-readable definition of every slot
3. docs/contracts/music_analyzer_contract.md section 6, the human-readable contract

(The fourth place, the truth files themselves, is checked in research/tests/test_truth_contract_parity.py.)
Also checks the behaviour the contract promises: empty slots are None, Listener fills only the bridged slots,
the production analyzer fills the produced slots once the music reaches the speakers, and an analyzer that
writes a slot is seen through the Listener.
"""
import json
import os
import re
import unittest

from music.api import ANALYZER_REGISTRY, Listener, MusicalContextEngine, MusicSignals
from music.BandKickSignals import BandKickSignals
from music.MusicSignals import BRIDGED, FIELDS, PRODUCED

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SPEC_PATH = os.path.join(REPO_ROOT, "config", "music_signals.json")
DOC_PATH = os.path.join(REPO_ROOT, "docs", "contracts", "music_analyzer_contract.md")
KINDS = {"event", "state", "value"}
TYPES = {"bool", "int", "float", "str"}
STATUS_MARK = {"bridged": "BRIDGED", "produced": "PRODUCED", "empty": "EMPTY"}
OWNERS = {"Listener": Listener, "MusicalContextEngine": MusicalContextEngine, "BandKickSignals": BandKickSignals}
PRODUCING_MODEL = "DyadicMetricalAudioAnalyzer"


class TestMusicSignalsContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SPEC_PATH, "r", encoding="utf-8") as f:
            cls.spec = json.load(f)
        cls.signals = cls.spec["signals"]
        with open(DOC_PATH, "r", encoding="utf-8") as f:
            cls.doc = f.read()

    def test_record_slots_equal_the_signal_list(self):
        self.assertEqual(tuple(s["name"] for s in self.signals), FIELDS,
                         "music/MusicSignals.FIELDS and config/music_signals.json must list the same slots in the same order")
        self.assertEqual(len(set(FIELDS)), len(FIELDS), "duplicate slot name")
        self.assertEqual(tuple(MusicSignals.__slots__), FIELDS)

    def test_every_definition_is_complete(self):
        truth_refs = [s["truth"] for s in self.signals]
        self.assertEqual(len(set(truth_refs)), len(truth_refs), "two slots point at the same truth value")
        for s in self.signals:
            with self.subTest(signal=s["name"]):
                self.assertIn(s["kind"], KINDS)
                self.assertIn(s["type"], TYPES)
                self.assertIn(s["status"], STATUS_MARK)
                for key in ("group", "range", "meaning", "truth", "graded"):
                    self.assertTrue(s.get(key), f"'{key}' is missing")

    def test_bridged_slots_match_code_and_point_at_real_signals(self):
        bridged = tuple(s["name"] for s in self.signals if s["status"] == "bridged")
        self.assertEqual(bridged, tuple(f for f in FIELDS if f in BRIDGED),
                         "the bridged slots of config/music_signals.json must equal MusicSignals.BRIDGED")
        produced = tuple(s["name"] for s in self.signals if s["status"] == "produced")
        self.assertEqual(produced, tuple(f for f in FIELDS if f in PRODUCED),
                         "the produced slots of config/music_signals.json must equal MusicSignals.PRODUCED")
        self.assertFalse(set(BRIDGED) & set(PRODUCED), "a slot is bridged or produced, not both")
        for s in self.signals:
            with self.subTest(signal=s["name"]):
                if s["status"] == "empty":
                    self.assertIsNone(s["source"], "an empty slot has no source")
                    continue
                owner, _, attr = s["source"].partition(".")
                self.assertIn(owner, OWNERS, f"unknown owner in source '{s['source']}'")
                self.assertTrue(hasattr(OWNERS[owner], attr), f"'{s['source']}' does not exist")

    def test_contract_document_has_one_row_per_slot(self):
        documented = re.findall(r"^\| `signals\.([a-z_]+)` \|(.*)$", self.doc, flags=re.MULTILINE)
        self.assertEqual([name for name, _ in documented], list(FIELDS),
                         "section 6 of music_analyzer_contract.md must have exactly one row per slot, in order")
        rows = dict(documented)
        for s in self.signals:
            with self.subTest(signal=s["name"]):
                row = rows[s["name"]]
                self.assertTrue(row.startswith(f" {s['kind']} |"), f"kind column should read '{s['kind']}'")
                self.assertIn(f"`{s['truth']}`", row)
                self.assertIn(STATUS_MARK[s["status"]], row)
                if s["source"]:
                    self.assertIn(f"`{s['source']}`", row)

    def test_empty_record_answers_none_everywhere(self):
        rec = MusicSignals()
        self.assertTrue(all(v is None for v in rec.as_dict().values()))
        rec.kick = 0.8
        rec.clear()
        self.assertIsNone(rec.kick)
        with self.assertRaises(AttributeError):
            rec.not_a_signal = 1          # the record cannot grow outside the contract

    def test_listener_fills_only_the_bridged_slots(self):
        for model in sorted(ANALYZER_REGISTRY):
            with self.subTest(model=model):
                listener = Listener({"useMicrophone": False, "analyzer_model": model})
                self.assertIs(listener.signals, listener.analyzer.signals)
                self.assertTrue(all(v is None for v in listener.signals.as_dict().values()))
                for _ in range(8):
                    listener.update(1.0 / 60.0)
                values = listener.signals.as_dict()
                for name in FIELDS:
                    if name in BRIDGED:
                        self.assertIsNotNone(values[name], f"bridged slot '{name}' is still empty")
                    elif name in PRODUCED and model == PRODUCING_MODEL:
                        self.assertIsNone(values[name], f"'{name}' must wait until the music reaches the speakers")
                    else:
                        self.assertIsNone(values[name], f"slot '{name}' should be empty: nothing produces it yet")
                listener.reset()
                self.assertTrue(all(v is None for v in listener.signals.as_dict().values()))

    def test_the_production_analyzer_fills_the_produced_slots_at_speaker_time(self):
        self.assertIs(ANALYZER_REGISTRY[PRODUCING_MODEL], Listener({"useMicrophone": False}).analyzer.__class__,
                      "the model that produces these slots must be the default one")
        for model in sorted(ANALYZER_REGISTRY):
            with self.subTest(model=model):
                listener = Listener({"useMicrophone": False, "analyzer_model": model, "fakeDelay": 0.0})
                for _ in range(8):                        # no look-ahead: the audio reaches the speakers at once
                    listener.update(1.0 / 60.0)
                values = listener.signals.as_dict()
                for name in FIELDS:
                    if name in BRIDGED or (name in PRODUCED and model == PRODUCING_MODEL):
                        self.assertIsNotNone(values[name], f"slot '{name}' is still empty")
                    else:
                        self.assertIsNone(values[name], f"slot '{name}' should be empty: nothing produces it yet")
                if model == PRODUCING_MODEL:
                    self.assertIsInstance(values["kick_present"], bool)
                    for name in ("kick", "band_bass", "band_mid", "band_high"):
                        self.assertTrue(0.0 <= values[name] <= 1.0, name)
                listener.reset()
                self.assertTrue(all(v is None for v in listener.signals.as_dict().values()))

    def test_a_slot_written_by_the_analyzer_is_seen_through_the_listener(self):
        listener = Listener({"useMicrophone": False})
        listener.analyzer.signals.snare = 0.7              # two slots that nothing produces yet
        listener.analyzer.signals.vocal_present = True
        listener.update(1.0 / 60.0)
        self.assertEqual(listener.signals.snare, 0.7)
        self.assertIs(listener.signals.vocal_present, True)

    def test_a_model_can_claim_a_bridged_slot(self):
        base = ANALYZER_REGISTRY[PRODUCING_MODEL]
        self.assertEqual(Listener({"useMicrophone": False}).analyzer.claimed_slots, (), "no production model claims a slot")

        class Claims(base):
            claimed_slots = ("brightness", "kick")           # kick is not bridged: naming it changes nothing

            def detect_band_peaks(self, current_time, dt, fps_ratio):
                super().detect_band_peaks(current_time, dt, fps_ratio)
                self.signals.brightness = 0.123

        listener = Listener({"useMicrophone": False}, analyzer_class=Claims)
        for _ in range(4):
            listener.update(1.0 / 60.0)
        self.assertEqual(listener.signals.brightness, 0.123)             # the model's value, not the copied one
        self.assertIsNotNone(listener.signals.loudness)                  # the other bridged slots are still copied


if __name__ == "__main__":
    unittest.main()
