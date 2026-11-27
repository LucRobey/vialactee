"""research/truth/buildups.py: the weak first guess of build-ups and possible drops, and the review list."""
import unittest

import numpy as np

from research.truth import buildups, review_list

HZ = 20


def _curves(seconds, loud, bright):
    n = int(seconds * HZ)
    t = np.arange(n) / HZ
    return {"loud_db": np.array([loud(x) for x in t], dtype=float), "bright_oct": np.array([bright(x) for x in t], dtype=float)}


BEATS = [{"t": 0.5 * i, "main": True} for i in range(240)]


class TestReleasePointsAndDrops(unittest.TestCase):
    def test_kick_returns_and_loud_section_changes_are_release_points(self):
        loud = _curves(120, lambda x: -10.0 if x >= 60 else -20.0, lambda x: 0.0)["loud_db"]
        moments = [{"t": 30.0, "kind": "kick_out"}, {"t": 40.0, "kind": "kick_return", "loudness_jump_db": 2.0}]
        sections = [{"t": 60.0}, {"t": 61.0}, {"t": 90.0}]            # 60 s: +10 dB; 61 s: the same jump again, dropped; 90 s: no jump
        rel = buildups.release_points(moments, sections, loud, HZ)
        self.assertEqual([(r["t"], r["kind"]) for r in rel], [(40.0, "kick returns"), (60.0, "section change, much louder")])

    def test_possible_drops_are_weak_and_skip_what_is_already_a_drop_and_the_start_of_the_file(self):
        rel = [{"t": 2.0, "kind": "section change, much louder", "jump_db": 9.0}, {"t": 40.0, "kind": "kick returns", "jump_db": 2.0},
               {"t": 80.0, "kind": "kick returns", "jump_db": 6.0}]
        out = buildups.possible_drops(rel, [{"t": 80.5, "level": "M1"}])
        self.assertEqual([(d["t"], d["level"]) for d in out], [(40.0, "W")])


class TestBuildups(unittest.TestCase):
    RELEASE = [{"t": 60.0, "kind": "kick returns", "jump_db": 6.0}]
    KICK = [{"start": 0.0, "end": 40.0}, {"start": 60.0, "end": 120.0}]      # the kick is out from 40 s to 60 s

    def test_a_climb_before_the_kick_returns_is_proposed_from_where_it_starts(self):
        # flat, then loudness and brightness climb from 50 s to 60 s
        c = _curves(120, lambda x: -20.0 + max(0.0, min(10.0, x - 50.0)), lambda x: max(0.0, min(1.0, (x - 50.0) / 10.0)))
        out = buildups.buildups(self.RELEASE, BEATS, c, {}, self.KICK, HZ)
        self.assertEqual(len(out), 1)
        b = out[0]
        self.assertEqual((b["end"], b["level"]), (60.0, "W"))
        self.assertTrue(47.0 <= b["start"] <= 53.0, b["start"])
        self.assertEqual(b["start"] % 0.5, 0.0)                              # on a beat
        self.assertIn("getting louder", b["why"])
        self.assertIn("getting brighter", b["why"])

    def test_a_song_that_was_only_quieter_long_before_is_not_a_build_up(self):
        # quiet until 42 s, a step up, then flat until the kick returns: no climb that ends at the release point
        c = _curves(120, lambda x: -30.0 if x < 42.0 else -20.0, lambda x: 0.0)
        self.assertEqual(buildups.buildups(self.RELEASE, BEATS, c, {}, self.KICK, HZ), [])

    def test_one_sign_is_enough_in_a_break_and_two_are_needed_elsewhere(self):
        c = _curves(120, lambda x: -20.0 + max(0.0, min(10.0, x - 50.0)), lambda x: 0.0)      # louder only
        self.assertEqual(len(buildups.buildups(self.RELEASE, BEATS, c, {}, self.KICK, HZ)), 1)
        no_break = [{"start": 0.0, "end": 120.0}]
        section = [{"t": 60.0, "kind": "section change, much louder", "jump_db": 6.0}]
        self.assertEqual(buildups.buildups(section, BEATS, c, {}, no_break, HZ), [])

    def test_a_drum_roll_is_a_sign(self):
        c = _curves(120, lambda x: -20.0 + max(0.0, min(10.0, x - 50.0)), lambda x: 0.0)
        roll = [[t, 1.0, "M1"] for t in np.arange(56.0, 60.0, 0.15)] + [[t, 1.0, "M1"] for t in np.arange(40.0, 56.0, 2.0)]
        section = [{"t": 60.0, "kind": "section change, much louder", "jump_db": 6.0}]
        out = buildups.buildups(section, BEATS, c, {"snare": roll}, [{"start": 0.0, "end": 120.0}], HZ)
        self.assertEqual(len(out), 1)
        self.assertIn("drum roll", out[0]["why"])


class TestReviewList(unittest.TestCase):
    def test_the_song_with_the_most_to_check_comes_first_and_checked_lanes_say_so(self):
        def truth(tid, drops, buildup):
            return {"track": {"id": tid, "file": f"song {tid}.mp3", "group": "rock"}, "drops": drops,
                    "regions": {"buildup": buildup, "no_beat": []}, "sections": {"items": [{"t": 10.0, "level": "M1"}]}}

        a = truth("01", [{"t": 65.0, "level": "A"}], [])
        b = truth("02", [{"t": 65.0, "level": "M1"}, {"t": 130.0, "level": "W"}], [{"start": 50.0, "end": 65.0, "level": "W"}])
        text = review_list.build([a, b])
        rows = [l for l in text.splitlines() if l.startswith("| 0")]
        self.assertTrue(rows[0].startswith("| 02 "))
        self.assertIn("1:05, 2:10?", rows[0])
        self.assertIn("0:50-1:05", rows[0])
        self.assertIn("| checked | none proposed | none proposed | 1 proposed |", rows[1])


if __name__ == "__main__":
    unittest.main()
