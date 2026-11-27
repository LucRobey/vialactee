"""The tools that let an agent work alone in the music lab, and the two shared ones.

- research/scoreboard/cycle.py: the steps of a run and the rules that keep the check tracks honest
- research/scoreboard/status.py: the status record
- research/guard.py: what a lab may change
- research/inbox.py: the owner's page

No song is played: the scoring is replaced by made-up scores.
"""
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

from research import guard, inbox
from research.scoreboard import compare, cycle, status

BASE = cycle.BASELINE
CAND = "MadeUpAnalyzer"


def _result(ids, target_score, other_score=0.8, base_other=0.8):
    """A scoreboard result where production has `beat` and the candidate adds `no_beat`."""
    def cell(v):
        return {"produced": v is not None, "checked": v, "all": v}

    def model(beat, no_beat):
        return {t: {"signals": {"beat": cell(beat), "no_beat": cell(no_beat)}, "candidates": {}, "frame_ms": 0.5} for t in ids}

    return {"built": "2026-01-01", "lookahead_s": 5.0, "tracks": {t: {"file": f"song {t}.mp3", "group": "rock"} for t in ids},
            "models": {BASE: model(base_other, None), CAND: model(other_score, target_score)}}


class TestCycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.patches = [mock.patch.object(cycle, "RUNS", root / "runs"), mock.patch.object(cycle, "HIDDEN", root / "hidden"),
                        mock.patch.object(cycle, "_refresh", lambda: None), mock.patch.object(cycle, "_today", lambda: "2026-01-01")]
        for p in self.patches:
            p.start()
        self.scores = {"open": 0.9, "check": 0.88, "other": 0.8}
        self.played = []

        def fake_scores(models, ids, workers):
            self.played.append(list(ids))
            which = "open" if ids == cycle.SPLIT["open"] else "check"
            return _result(ids, self.scores[which], self.scores["other"])

        self.patches.append(mock.patch.object(cycle, "_scores", fake_scores))
        self.patches[-1].start()
        self.run_name = "2026-01-01_trial"
        self.dir = root / "runs" / self.run_name

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _start(self):
        cycle.cmd_start(Namespace(name="trial", signal=["no_beat"], idea="M01"))

    def _plan(self):
        (self.dir / "PLAN.md").write_text("# Plan\nAll four answers written.", encoding="utf-8")

    def _grade(self):
        cycle.cmd_grade(Namespace(run=self.run_name, candidate=CAND, workers=1))

    def _check(self):
        cycle.cmd_check(Namespace(run=self.run_name, candidate=CAND, workers=1))

    def _close(self, verdict):
        cycle.cmd_close(Namespace(run=self.run_name, verdict=verdict, summary="made up"))

    def test_start_opens_a_run_with_a_plan_to_fill_in(self):
        self._start()
        state = cycle.load(self.dir)
        self.assertEqual((state["state"], state["signals"], state["idea"]), ("open", ["no_beat"], "M01"))
        self.assertIn(cycle.TODO, (self.dir / "PLAN.md").read_text(encoding="utf-8"))
        with self.assertRaises(SystemExit):
            cycle.cmd_start(Namespace(name="other", signal=["not_a_signal"], idea=""))

    def test_the_plan_comes_before_the_code(self):
        self._start()
        with self.assertRaises(SystemExit):
            self._grade()
        self.assertEqual(self.played, [])

    def test_grade_plays_only_the_open_tracks_and_can_be_repeated(self):
        self._start()
        self._plan()
        self._grade()
        self._grade()
        self.assertEqual(self.played, [cycle.SPLIT["open"], cycle.SPLIT["open"]])
        state = cycle.load(self.dir)
        self.assertEqual(len(state["grades"]), 2)
        self.assertAlmostEqual(state["grades"][-1]["open"]["no_beat"], 0.9)
        text = (self.dir / "OPEN.md").read_text(encoding="utf-8")
        self.assertIn("PASSED", text)
        self.assertIn("song 01", text)                       # track detail is allowed on the open tracks
        self.assertIn("10 of 10 tracks graded, 10 of them on checked truth", text)

    def test_check_needs_a_grade_gives_no_track_detail_and_freezes_the_run(self):
        self._start()
        self._plan()
        with self.assertRaises(SystemExit):
            self._check()
        self._grade()
        self._check()
        self.assertEqual(self.played[-1], cycle.SPLIT["check"])
        text = (self.dir / "CHECK.md").read_text(encoding="utf-8")
        for tid in cycle.SPLIT["check"]:
            self.assertNotIn(f"song {tid}", text)
        self.assertFalse((self.dir / "check_scores.json").exists())
        self.assertEqual(cycle.load(self.dir)["state"], "checked")
        with self.assertRaises(SystemExit):
            self._grade()                                    # no tuning after the check
        with self.assertRaises(SystemExit):
            self._check()                                    # and the check is run once

    def test_the_open_and_check_tracks_do_not_overlap(self):
        self.assertFalse(set(cycle.SPLIT["open"]) & set(cycle.SPLIT["check"]))
        self.assertTrue(all(compare.is_open(t) for t in cycle.SPLIT["open"]))
        self.assertFalse(any(compare.is_open(t) for t in cycle.SPLIT["check"]))

    def test_a_proposal_needs_a_passed_check_and_finished_words(self):
        self._start()
        self._plan()
        self._grade()
        with self.assertRaises(SystemExit):
            self._close("propose")                           # not checked
        self._check()
        self._close("propose")                               # writes the skeleton and stops: not a failure
        self.assertEqual(cycle.load(self.dir)["state"], "checked")
        prop = self.dir / "PROPOSAL.md"
        self.assertIn("88", prop.read_text(encoding="utf-8"))
        with self.assertRaises(SystemExit):
            self._close("propose")                           # still TODO
        prop.write_text(prop.read_text(encoding="utf-8").replace(cycle.TODO, "done"), encoding="utf-8")
        self._close("propose")
        self.assertEqual(cycle.load(self.dir)["state"], "proposed")
        cycle.cmd_decide(Namespace(run=self.run_name, decision="approved", note="yes"))
        self.assertEqual(cycle.load(self.dir)["state"], "decided")

    def test_a_candidate_that_hurts_another_signal_cannot_be_proposed(self):
        self.scores["other"] = 0.6                           # beat falls from 80 to 60
        self._start()
        self._plan()
        self._grade()
        self.assertFalse(cycle.load(self.dir)["grades"][-1]["gate_passed"])
        self._check()
        with self.assertRaises(SystemExit):
            self._close("propose")
        self._close("archive")
        self.assertEqual(cycle.load(self.dir)["state"], "archived")
        with self.assertRaises(SystemExit):
            cycle.cmd_decide(Namespace(run=self.run_name, decision="approved", note=""))


class TestStatusAndInbox(unittest.TestCase):
    RUN = {"run": "2026-01-01_trial", "signals": ["no_beat"], "candidate": CAND, "state": "proposed",
           "grades": [{"open": {"no_beat": 0.9}}],
           "check": {"signals": {"no_beat": {"production": None, "candidate": 0.88, "open": 0.9}}},
           "verdict": {"date": "2026-01-01", "verdict": "propose", "summary": "says when there is no beat"}, "decision": None}

    def test_status_lists_every_signal_and_every_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runs" / "2026-01-01_trial").mkdir(parents=True)
            (root / "runs" / "2026-01-01_trial" / "run.json").write_text(json.dumps(self.RUN), encoding="utf-8")
            with mock.patch.object(status, "RUNS", root / "runs"):
                text = status.write(root / "STATUS.md").read_text(encoding="utf-8")
                self.assertEqual([r["run"] for r in status.waiting_for_owner()], ["2026-01-01_trial"])
        for name in cycle.SIGNAL_NAMES:
            self.assertIn(f"| `{name}` |", text)
        self.assertIn("88 (`2026-01-01_trial`)", text)
        self.assertIn("waiting for the owner", text)

    def test_inbox_shows_what_waits_and_nothing_else(self):
        queue = [{"clip": "a", "mode": "New_mode", "against": "Old_mode", "feed": "today", "track": "13", "start_s": 30.0,
                  "duration_s": 20.0, "nominated": "2026-01-01", "note": "look at the kick"},
                 {"clip": "b", "mode": "New_mode", "against": None, "feed": None, "track": "19", "start_s": 208.0,
                  "duration_s": 24.0, "nominated": "2026-01-01", "note": ""}]
        with tempfile.TemporaryDirectory() as tmp:
            q, v = Path(tmp) / "queue.json", Path(tmp) / "verdicts.jsonl"
            q.write_text(json.dumps(queue), encoding="utf-8")
            v.write_text(json.dumps({"clip": "b", "choice": "A"}) + "\n", encoding="utf-8")
            waiting = inbox.waiting_clips(q, v)
        self.assertEqual([e["clip"] for e in waiting], ["a"])
        closed = dict(self.RUN, run="2025-12-01_old", state="decided", decision={"date": "2025-12-02", "decision": "refused", "note": ""})
        text = inbox.build([self.RUN, closed], waiting, "- **A question?** Details.", "2026-01-02")
        self.assertIn("**1 proposal(s) to answer, 1 clip(s) to watch.**", text)
        self.assertIn("scoreboard/runs/2026-01-01_trial/PROPOSAL.md", text)
        self.assertIn("`New_mode` against `Old_mode`", text)
        self.assertIn("A question?", text)
        self.assertIn("`2025-12-01_old` (no_beat): refused by you", text)
        self.assertNotIn("PROPOSAL.md](scoreboard/runs/2025-12-01_old", text)


class TestGuard(unittest.TestCase):
    def test_a_music_agent_stays_in_the_music_lab(self):
        ok = ["research/experiments/models/NewAnalyzer.py", "research/scoreboard/runs/2026-01-01_x/PLAN.md",
              "research/scoreboard/runs/2026-01-01_x/tune.py", "research/scoreboard/BACKLOG.md", "research/scoreboard/STATUS.md",
              "research/tests/test_candidate_new.py", "work_history/2026-01-01_x.md", "research/INBOX.md", "research/OWNER_QUESTIONS.md"]
        self.assertEqual(guard.judge(ok, "music"), [])
        locked = ["music/Listener.py", "modes/Rainbow_mode.py", "core/Mode_master.py", "config/music_signals.json",
                  "research/truth/tracks/01.json", "research/scoreboard/split.json", "research/scoreboard/grade.py",
                  "tests/governance/test_lab_isolation.py", "docs/contracts/music_analyzer_contract.md",
                  ".agents/skills/vialactee-researcher/SKILL.md", "research/tests/test_scoreboard_grading.py", "README.md"]
        bad = guard.judge(locked, "music")
        self.assertEqual([p for p, _ in bad], locked)
        self.assertIn("source of truth", dict(bad)["research/truth/tracks/01.json"])
        self.assertIn("graded", dict(bad)["research/scoreboard/grade.py"])

    def test_a_choreography_agent_stays_in_the_choreography_lab(self):
        ok = ["research/choreography/candidates/New_mode.py", "research/choreography/BACKLOG.md", "research/choreography/STATUS.md",
              "research/choreography/gates.json", "research/choreography/queue.json", "research/tests/test_choreography_candidate_new.py",
              "research/choreography/runs/New_mode/stress.py"]
        self.assertEqual(guard.judge(ok, "choreography"), [])
        locked = ["research/choreography/verdicts.jsonl", "research/choreography/check_mode.py", "research/choreography/profile.py",
                  "modes/Rainbow_mode.py", "music/api.py"]
        self.assertEqual([p for p, _ in guard.judge(locked, "choreography")], locked)

    def test_the_other_lab_and_earlier_changes_are_told_apart(self):
        found = guard.judge(["research/choreography/candidates/New_mode.py", "config/app_config.json"], "music", already=["config/app_config.json"])
        self.assertEqual(found, [("research/choreography/candidates/New_mode.py", guard.OTHER_LAB)])

    def test_no_role_may_change_a_locked_place(self):
        for pattern, _ in guard.LOCKED_REASON:
            sample = pattern.replace("*", "x")
            for role in guard.ALLOWED:
                self.assertTrue(guard.judge([sample], role), f"{role} may change {sample}")


if __name__ == "__main__":
    unittest.main()
