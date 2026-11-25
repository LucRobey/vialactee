"""The signal contract looks exactly like the source of truth, in both directions.

Every slot of config/music_signals.json points at a value that exists in every truth file, and every value of
a truth file that describes the music is mirrored by a slot. What the truth holds for bookkeeping only is
listed in NOT_MIRRORED with the reason.
"""
import glob
import json
import os
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SPEC_PATH = os.path.join(REPO_ROOT, "config", "music_signals.json")
TRACKS_GLOB = os.path.join(REPO_ROOT, "research", "truth", "tracks", "*.json")

NOT_MIRRORED = {
    "beats.main": "tells main beats from half-beats; the live `beat` is the main beat only",
    "beats.level": "level of evidence, not music",
    "beats.votes": "level of evidence, not music",
    "beats.bar_pos_level": "level of evidence, not music",
    "beats.no_beat": "copy of regions.no_beat on each beat",
    "beats.drums": "copy of drums.pieces on each beat",
    "regions.beat_confirmed": "the owner's note that a doubted stretch has a beat",
    "regions.vocal_present_old_rule": "first vocal rule, kept for comparison",
}


def music_values(truth: dict) -> set:
    """Every value of a truth file that describes the music, as the dotted names the contract uses."""
    out = {f"beats.{k}" for k in truth["beats"][0]}
    out |= {f"regions.{k}" for k in truth["regions"]}
    out |= {f"drums.pieces.{k}" for k in truth["drums"]["pieces"]}
    out |= {f"curves.{k}" for k in truth["curves"]["names"]}
    out |= {"meter.beats_per_bar", "drops", "sections.items", "chords.items"}
    return out


class TestTruthContractParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SPEC_PATH, "r", encoding="utf-8") as f:
            cls.refs = {s["truth"]: s["name"] for s in json.load(f)["signals"]}
        cls.paths = sorted(glob.glob(TRACKS_GLOB))

    def test_truth_files_exist(self):
        self.assertGreaterEqual(len(self.paths), 20, "the truth drafts are missing: run research/truth/build_truth.py")

    def test_contract_and_truth_hold_the_same_values(self):
        for path in self.paths:
            with open(path, "r", encoding="utf-8") as f:
                truth = json.load(f)
            with self.subTest(track=os.path.basename(path)):
                for key in ("meter", "drops", "sections", "chords"):
                    self.assertIn(key, truth)
                self.assertIn("items", truth["sections"])
                self.assertIn("items", truth["chords"])
                in_truth = music_values(truth) - set(NOT_MIRRORED)
                in_contract = set(self.refs)
                self.assertEqual(in_contract - in_truth, set(), "the contract names values the truth does not hold")
                self.assertEqual(in_truth - in_contract, set(), "the truth holds values the contract does not mirror")

    def test_exclusions_are_real(self):
        with open(self.paths[0], "r", encoding="utf-8") as f:
            values = music_values(json.load(f))
        for name in NOT_MIRRORED:
            self.assertIn(name, values, f"'{name}' is excluded but no longer exists in the truth")


if __name__ == "__main__":
    unittest.main()
