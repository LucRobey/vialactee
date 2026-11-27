"""Tests for the unattended cycle of the choreography lab: the gate (check_mode.py), mode against mode
(build_clips.py), the owner's queue (nominate.py, records.py), the clip page's verdict line (clip_server.py) and
the status record (status.py). Everything runs on made-up inputs in temporary folders: nothing here touches
the real queue, the real gates or the owner's verdicts.
"""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from research.choreography import build_clips, check_mode, clip_server, nominate, records, status
from research.choreography.layout import load_layout
from research.choreography.profile import profile

OWNER_FIRST_LINE = '{"at": "2026-11-27T01:19:49", "clip": "13_0030_Kick_bands_mode", "choice": "A"'


# -- made-up inputs --------------------------------------------------------------------------------------
def _prof(flash_max=2.0, dark=0.0, low=0.2, high=0.6, led_swing=0.3, mean=0.4, flashes=40, hits=50, on_hit=0.9):
    """The few numbers of a profile the gate reads."""
    return {"light": {"mean": mean, "low": low, "high": high, "dark_share": dark, "led_swing": led_swing},
            "safety": {"flashes_per_second_max": flash_max, "where": "whole installation"},
            "flashes": {"flashes": flashes, "hits": hits, "flashes_with_a_hit": on_hit}}


def _passage(song="Made-up song", start=30.0, truth=None, today=None, control=None, errors=None, draw_ms=1.0, same=False):
    profiles = {"truth": truth or _prof(), "today": today or _prof(on_hit=0.7), "control": control or _prof(on_hit=0.3)}
    errors = errors or {}
    for feed in errors:
        profiles.pop(feed, None)
    return {"clip": f"t_{int(start):04d}_X", "song": song, "start_s": start, "duration_s": 20.0, "feeds": ["truth", "today", "control"],
            "errors": errors, "draw_ms": {f: draw_ms for f in profiles}, "profiles": profiles, "control_same_as_truth": same}


def _status(rules):
    return {r["rule"]: r["status"] for r in rules}


class _Glow:
    """A throwaway mode: every LED at a steady level. Never registered, never drawn on the installation."""
    LEVEL = 60

    def __init__(self, name, segment_name, listener, leds, indexes, rgb_list, infos):
        self.rgb_list = rgb_list

    def render(self, buffer=None):
        buffer[:] = self.LEVEL


class _Bright(_Glow):
    LEVEL = 200


class _Broken(_Glow):
    def render(self, buffer=None):
        raise RuntimeError("boom in the mode")


def _made_up_passage():
    rng = np.random.default_rng(0)
    mono = (0.05 * rng.standard_normal(8 * 44100)).astype(np.float32)
    return build_clips.Passage({"id": "t1", "file": "made-up.wav", "group": None}, mono, load_layout(), 5.5, 1.0, [], np.zeros(60, dtype=bool), 0.25, None)


# -- the gate ---------------------------------------------------------------------------------------------
class TestGateRules(unittest.TestCase):
    def test_a_sound_mode_passes_the_five_rules(self):
        rules = check_mode.judge([_passage(), _passage(song="Other song")])
        self.assertEqual(_status(rules), {1: "pass", 2: "pass", 3: "pass", 4: "pass", 5: "pass"})
        self.assertTrue(check_mode.passed(rules))
        self.assertIn("6 of 6", rules[0]["measured"])

    def test_too_many_flashes_fail_rule_3_with_the_number_and_the_passage(self):
        rules = check_mode.judge([_passage(), _passage(song="Strobe song", truth=_prof(flash_max=7.0))])
        flash = rules[2]
        self.assertEqual(flash["status"], "fail")
        self.assertEqual(flash["failed_on"], ["Strobe song from 0:30"])
        self.assertIn("7.0", flash["measured"])
        self.assertEqual(flash["numbers"]["flashes_per_second_max"], 7.0)
        self.assertFalse(check_mode.passed(rules))
        self.assertEqual([r["rule"] for r in rules if r["status"] == "fail"], [3])          # the other rules still pass
        exactly = check_mode.judge([_passage(truth=_prof(flash_max=3.0))])
        self.assertEqual(exactly[2]["status"], "pass")                                       # three in a second is allowed
        on_today = check_mode.judge([_passage(today=_prof(flash_max=3.5))])
        self.assertEqual(on_today[2]["status"], "fail")                                      # judged on today's analyzer too
        on_control = check_mode.judge([_passage(control=_prof(flash_max=9.0, on_hit=0.2))])
        self.assertEqual(on_control[2]["status"], "pass")                                    # the control is not shown: not judged

    def test_a_light_stuck_dark_or_frozen_on_todays_analyzer_fails_rule_2(self):
        dark = check_mode.judge([_passage(today=_prof(dark=0.9, low=0.0, high=0.3))])[1]
        self.assertEqual(dark["status"], "fail")
        self.assertIn("stuck dark", dark["rows"][0]["measured"])
        frozen = check_mode.judge([_passage(today=_prof(low=0.5, high=0.51, led_swing=0.0, mean=0.5))])[1]
        self.assertEqual(frozen["status"], "fail")
        self.assertIn("frozen", frozen["rows"][0]["measured"])
        black = check_mode.judge([_passage(today=_prof(low=0.0, high=0.0, led_swing=0.0, mean=0.0))])[1]
        self.assertIn("stuck dark", black["rows"][0]["measured"])
        # a show that moves in space at a constant total light is not frozen
        travels = check_mode.judge([_passage(today=_prof(low=0.5, high=0.5, led_swing=0.4, mean=0.5))])[1]
        self.assertEqual(travels["status"], "pass")

    def test_a_mode_that_flashes_as_well_on_the_control_is_not_tied_to_the_music(self):
        rules = check_mode.judge([_passage(control=_prof(on_hit=0.85))])
        self.assertEqual(rules[3]["status"], "fail")
        self.assertIn("90%", rules[3]["measured"])
        self.assertIn("85%", rules[3]["measured"])
        self.assertFalse(check_mode.passed(rules))

    def test_a_mode_that_does_not_flash_is_not_applicable_and_still_passes(self):
        quiet = _passage(truth=_prof(flashes=0, on_hit=None), control=_prof(flashes=0, on_hit=None))
        rules = check_mode.judge([quiet])
        self.assertEqual(rules[3]["status"], "not applicable")
        self.assertIn("neither a pass nor a fail", rules[3]["note"])
        self.assertTrue(check_mode.passed(rules))
        deaf = check_mode.judge([_passage(same=True)])                    # same frames on the truth and on the control
        self.assertEqual(deaf[3]["status"], "not applicable")
        self.assertIn("does not read the hits", deaf[3]["rows"][0]["measured"])
        mixed = check_mode.judge([quiet, _passage(song="Other song")])    # one passage can say: the rule is judged on it
        self.assertEqual(mixed[3]["status"], "pass")

    def test_a_crash_fails_rule_1_with_the_error_text(self):
        rules = check_mode.judge([_passage(errors={"today": "ZeroDivisionError: division by zero (X.py, line 12)"})])
        self.assertEqual(rules[0]["status"], "fail")
        self.assertTrue(any("ZeroDivisionError" in row["measured"] for row in rules[0]["rows"]))
        self.assertIn("2 of 3", rules[0]["measured"])
        self.assertEqual(rules[1]["status"], "not measured")              # nothing to measure on the feed that crashed
        self.assertFalse(check_mode.passed(rules))
        unloadable = check_mode.judge([], load_error="SyntaxError: invalid syntax (X.py, line 3)")
        self.assertEqual(_status(unloadable), {1: "fail", 2: "not measured", 3: "not measured", 4: "not measured", 5: "not measured"})

    def test_cost_fails_only_above_the_generous_limit(self):
        self.assertEqual(check_mode.judge([_passage(draw_ms=4.0)])[4]["status"], "pass")
        slowish = check_mode.judge([_passage(draw_ms=12.0)])[4]
        self.assertEqual(slowish["status"], "pass")
        self.assertIn("time this mode on the Pi", slowish["note"])
        slow = check_mode.judge([_passage(draw_ms=check_mode.DRAW_MS_LIMIT + 5.0)])[4]
        self.assertEqual(slow["status"], "fail")
        self.assertIn("only an indication", slow["note"])


class TestGateOnRealProfiles(unittest.TestCase):
    """The rules read the profile as profile.py really writes it: a made-up show, profiled, then judged."""

    FPS = 30.0

    def _show(self, layout, flash_times, truth_kicks, seconds=12.0):
        n = int(seconds * self.FPS)
        t = np.arange(n) / self.FPS
        pulse = np.zeros(n)
        for k in flash_times:
            pulse += np.exp(-np.clip(t - k, 0, None) / 0.06) * (t >= k)
        frames = np.zeros((n, layout.total, 3), dtype=np.uint8)
        frames[:, :, 1] = (30 + 200 * np.clip(pulse, 0, 1))[:, None].astype(np.uint8)
        kicks = np.array(truth_kicks)
        truth = {"events": {"kick": kicks, "snare": np.array([]), "beat": kicks, "drop": np.array([]), "section_change": np.array([])},
                 "bars": kicks[::4],
                 "masks": {name: np.zeros(n, dtype=bool) for name in ("no_beat", "breakdown", "silence", "kick_present", "buildup")},
                 "levels": {name: np.full(n, 0.5) for name in ("loudness", "band_bass", "band_mid", "band_high")}}
        return profile(frames, self.FPS, layout, truth)

    def _record(self, layout, kicks, flash_times):
        late = [f + 0.25 for f in flash_times]                             # the control: the light reacts half a beat late
        profiles = {"truth": self._show(layout, flash_times, kicks), "today": self._show(layout, flash_times, kicks),
                    "control": self._show(layout, late, kicks)}
        return {"clip": "t_0000_X", "song": "Made-up show", "start_s": 0.0, "duration_s": 12.0, "feeds": list(profiles),
                "errors": {}, "draw_ms": {f: 0.5 for f in profiles}, "profiles": profiles, "control_same_as_truth": False}

    def test_a_show_that_flashes_on_the_kicks_passes_and_a_strobe_fails_flash_safety(self):
        layout = load_layout()
        kicks = list(np.arange(1.0, 11.5, 0.5))                            # two kicks a second: within the limit
        rules = check_mode.judge([self._record(layout, kicks, kicks)])
        self.assertEqual(_status(rules), {1: "pass", 2: "pass", 3: "pass", 4: "pass", 5: "pass"}, rules)
        self.assertGreater(rules[3]["numbers"]["tied_gap_min"], 0.5)
        strobe = list(np.arange(1.0, 11.5, 0.2))                           # five flashes a second
        rules = check_mode.judge([self._record(layout, kicks, strobe)])
        self.assertEqual(rules[2]["status"], "fail")
        self.assertGreater(rules[2]["numbers"]["flashes_per_second_max"], 3.0)


class TestGateRecords(unittest.TestCase):
    def test_check_writes_the_report_and_the_committed_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            def measure(mode, track, start, duration, reuse, candidate):
                return _passage(song=f"Track {track}", start=start, truth=_prof(flash_max=5.0) if track == "13" else None)

            result = check_mode.check("Throwaway_mode", passages=(("19", 208.0, 24.0), ("13", 30.0, 20.0)), gates_dir=tmp / "gates",
                                      gates_path=tmp / "gates.json", measure=measure, load_error=lambda mode: None)
            self.assertFalse(result["passed"])
            self.assertEqual(result["failed_rules"], [3])
            text = (tmp / "gates" / "Throwaway_mode" / "GATE.md").read_text(encoding="utf-8")
            self.assertIn("FAILED", text)
            self.assertIn("provisional proposals, not decisions of the owner", text)
            self.assertIn("Track 13 from 0:30", text)
            self.assertIn("Reported, not judged", text)
            self.assertIn("only an indication", text)
            saved = json.loads((tmp / "gates" / "Throwaway_mode" / "gate.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["thresholds"]["FLASH_LIMIT"], 3)
            record = records.read_gates(tmp / "gates.json")["Throwaway_mode"]
            self.assertEqual((record["passed"], record["failed_rules"], record["rules"]["3"]), (False, [3], "fail"))
            self.assertEqual(record["numbers"]["flashes_per_second_max"], 5.0)
            self.assertEqual(record["date"], records.today())

            check_mode.check("Other_mode", passages=(("19", 208.0, 24.0),), gates_dir=tmp / "gates", gates_path=tmp / "gates.json",
                             measure=lambda *a: _passage(), load_error=lambda mode: None)
            gates = records.read_gates(tmp / "gates.json")
            self.assertTrue(gates["Other_mode"]["passed"])
            self.assertFalse(gates["Throwaway_mode"]["passed"])            # the other mode's record is left alone

    def test_a_mode_that_cannot_be_loaded_is_a_failed_gate_not_a_crash_of_the_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            result = check_mode.check("Throwaway_mode", gates_dir=tmp / "gates", gates_path=tmp / "gates.json",
                                      measure=lambda *a: self.fail("nothing to measure"), load_error=lambda mode: "SyntaxError: bad (X.py, line 3)")
            self.assertFalse(result["passed"])
            self.assertEqual(result["failed_rules"], [1, 2, 3, 4, 5])
            self.assertIn("SyntaxError", (tmp / "gates" / "Throwaway_mode" / "GATE.md").read_text(encoding="utf-8"))

    def test_the_committed_gate_record_and_thresholds_are_in_place(self):
        self.assertEqual(check_mode.THRESHOLDS["FLASH_LIMIT"], 3)          # WCAG 2.3.1: not ours to loosen
        for name, record in records.read_gates().items():
            self.assertIsInstance(record["passed"], bool, name)
            self.assertIsInstance(record["failed_rules"], list, name)


# -- mode against mode, and the clip page ---------------------------------------------------------------------
class TestModeAgainstMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.clips = Path(cls.tmp.name) / "clips"
        cls.passage = _made_up_passage()
        cls.versus = build_clips.modes_clip(cls.passage, {"Glow": _Glow, "Bright": _Bright}, "today", None, cls.clips)
        cls.errors = {}
        cls.feeds = build_clips.feeds_clip(cls.passage, "Glow", _Glow, {"truth": None, "today": None, "control": None}, cls.clips,
                                           errors=cls.errors)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_a_modes_clip_holds_the_two_modes_on_the_same_feed(self):
        meta = json.loads((self.versus / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["id"], "t1_0005_Glow_vs_Bright_today")
        self.assertEqual((meta["kind"], meta["mode"], meta["against"], meta["feed"]), ("modes", "Glow", "Bright", "today"))
        self.assertEqual([(v["key"], v["mode"], v["feed"], v["hidden"]) for v in meta["feeds"]],
                         [("Glow", "Glow", "today", False), ("Bright", "Bright", "today", False)])
        for v in meta["feeds"]:
            frames = np.fromfile(self.versus / v["file"], dtype=np.uint8).reshape(v["frames"], meta["leds"], 3)
            self.assertEqual(frames.shape, (60, 1304, 3))
            self.assertEqual(int(frames.max()), {"Glow": 60, "Bright": 200}[v["mode"]])
            self.assertGreater(v["draw_ms"], 0.0)                          # the cost of drawing is measured
        with self.assertRaises(ValueError):
            build_clips.modes_clip(self.passage, {"Glow": _Glow}, "today", None, self.clips)

    def test_a_feeds_clip_is_unchanged_and_says_what_it_is(self):
        meta = json.loads((self.feeds / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["id"], "t1_0005_Glow")
        self.assertEqual((meta["kind"], meta["mode"], meta["against"], meta["feed"], meta["errors"]), ("feeds", "Glow", None, None, {}))
        self.assertEqual([(v["key"], v["hidden"]) for v in meta["feeds"]], [("truth", False), ("today", False), ("control", True)])
        self.assertEqual(self.errors, {})

    def test_a_crash_is_noted_for_the_gate_or_raised_for_everyone_else(self):
        errors = {}
        clip = build_clips.feeds_clip(self.passage, "Broken", _Broken, {"today": None}, self.clips, errors=errors)
        self.assertIn("RuntimeError: boom in the mode", errors["today"])
        meta = json.loads((clip / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual((meta["feeds"], list(meta["errors"])), ([], ["today"]))
        with self.assertRaises(RuntimeError):
            build_clips.feeds_clip(self.passage, "Broken", _Broken, {"today": None}, self.clips)

    def test_the_verdict_line_says_which_mode_was_chosen(self):
        verdicts = Path(self.tmp.name) / "verdicts.jsonl"
        row = clip_server.save_verdict({"clip": self.versus.name, "choice": "B", "order": ["Bright", "Glow"], "chosen_version": "Glow",
                                        "labels_hidden": True}, verdicts, self.clips)
        self.assertEqual((row["kind"], row["mode"], row["against"], row["feed"], row["chosen_mode"]), ("modes", "Glow", "Bright", "today", "Glow"))
        self.assertEqual(row["chosen_feed"], "today")
        for old_field in ("at", "clip", "choice", "order", "chosen_feed", "labels_hidden", "note"):
            self.assertIn(old_field, row)                                  # the fields of the first verdict lines are kept
        none = clip_server.save_verdict({"clip": self.versus.name, "choice": "none", "order": ["Bright", "Glow"]}, verdicts, self.clips)
        self.assertEqual((none["chosen_mode"], none["chosen_feed"]), (None, None))
        feeds = clip_server.save_verdict({"clip": self.feeds.name, "choice": "A", "order": ["today", "truth"], "chosen_feed": "today"},
                                         verdicts, self.clips)                # the page as it was before: chosen_feed only
        self.assertEqual((feeds["kind"], feeds["chosen_feed"], feeds["chosen_mode"], feeds["mode"]), ("feeds", "today", None, "Glow"))
        with self.assertRaises(ValueError):                                # the hidden control cannot be chosen
            clip_server.save_verdict({"clip": self.feeds.name, "choice": "A", "chosen_version": "control"}, verdicts, self.clips)
        with self.assertRaises(ValueError):
            clip_server.save_verdict({"clip": "../outside", "choice": "A", "chosen_version": "Glow"}, verdicts, self.clips)
        self.assertEqual(len(records.read_verdicts(verdicts)), 3)

    def test_the_page_lists_the_waiting_clips_first(self):
        tmp = Path(self.tmp.name)
        queue, verdicts = tmp / "queue_page.json", tmp / "verdicts_page.jsonl"
        records.write_queue([{"clip": self.versus.name, "mode": "Glow", "against": "Bright", "feed": "today"},
                             {"clip": "t1_0005_Glow_n1", "mode": "Glow", "against": None, "feed": None}], queue)
        listed = clip_server.list_clips(self.clips, queue, verdicts)
        self.assertEqual(listed[0]["id"], self.versus.name)                # alphabetically it would come last
        self.assertEqual([c["waiting"] for c in listed], [True] + [False] * (len(listed) - 1))
        self.assertEqual(listed[0]["queue"]["against"], "Bright")
        waiting = clip_server.waiting_queue(self.clips, queue, verdicts)["waiting"]
        self.assertEqual([(e["clip"], e["built"]) for e in waiting], [(self.versus.name, True), ("t1_0005_Glow_n1", False)])
        clip_server.save_verdict({"clip": self.versus.name, "choice": "A", "chosen_version": "Glow"}, verdicts, self.clips)
        self.assertFalse(any(c["waiting"] for c in clip_server.list_clips(self.clips, queue, verdicts)))


# -- the queue ----------------------------------------------------------------------------------------------
class _Lab:
    """A throwaway lab in a temporary folder: candidates, registered modes, gates, queue, verdicts, and fake builders."""

    def __init__(self, tmp: Path) -> None:
        self.candidates, self.production, self.clips = tmp / "candidates", tmp / "modes", tmp / "clips"
        self.queue, self.verdicts, self.gates = tmp / "queue.json", tmp / "verdicts.jsonl", tmp / "gates.json"
        for folder in (self.candidates, self.production, self.clips):
            folder.mkdir()
        self.queue.write_text("[]", encoding="utf-8")
        self.built = []
        self.add_mode("Throwaway_mode")
        self.add_mode("Rival_mode")
        (self.production / "Old_mode.py").write_text("class Old_mode: pass\n", encoding="utf-8")

    def add_mode(self, name: str, body: str = "pass") -> Path:
        path = self.candidates / f"{name}.py"
        path.write_text(f"class {name}:\n    {body}\n", encoding="utf-8")
        return path

    def gate(self, name: str, passed: bool, failed=()) -> None:
        records.write_gate(name, {"date": "2026-11-27", "passed": passed, "failed_rules": list(failed),
                                  "source_sha": records.source_sha(records.mode_file(name, self.candidates, self.production))}, self.gates)

    def _write(self, clip_id: str, clips_dir: Path) -> Path:
        (clips_dir / clip_id).mkdir(parents=True)
        (clips_dir / clip_id / "meta.json").write_text(json.dumps({"id": clip_id}), encoding="utf-8")
        self.built.append(clip_id)
        return clips_dir / clip_id

    def build_feeds(self, mode, track, start, duration, clip_id=None, clips_dir=None):
        return self._write(clip_id, clips_dir)

    def build_versus(self, mode, against, track, start, duration, feed="truth", clip_id=None, clips_dir=None):
        return self._write(clip_id, clips_dir)

    def nominate(self, mode, against=None, **kw):
        return nominate.nominate(mode, against, passages=(("19", 208.0, 24.0), ("13", 30.0, 20.0)), queue_path=self.queue,
                                 verdicts_path=self.verdicts, gates_path=self.gates, candidates=self.candidates, production=self.production,
                                 clips_dir=self.clips, build_feeds=self.build_feeds, build_versus=self.build_versus, **kw)

    def judge(self, clip_id: str, **fields) -> None:
        with open(self.verdicts, "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": "2026-11-28T10:00:00", "clip": clip_id, "choice": "A", **fields}) + "\n")


class TestQueue(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.lab = _Lab(Path(self._tmp.name))

    def test_an_entry_waits_exactly_until_a_verdict_names_its_clip(self):
        queue = [{"clip": "a"}, {"clip": "b"}, {"clip": "c"}]
        self.assertEqual(records.waiting(queue, []), queue)
        verdicts = [{"clip": "b", "choice": "none"}, {"clip": "zzz", "choice": "A"}]
        self.assertEqual([e["clip"] for e in records.waiting(queue, verdicts)], ["a", "c"])       # any verdict line counts, even "none"
        self.assertEqual(records.waiting(queue, verdicts + [{"clip": "a"}, {"clip": "c"}, {"clip": "c"}]), [])

    def test_a_mode_that_was_never_gated_or_failed_its_gate_is_refused(self):
        with self.assertRaisesRegex(nominate.Refused, "never been through the gate"):
            self.lab.nominate("Throwaway_mode")
        self.lab.gate("Throwaway_mode", False, failed=[3])
        with self.assertRaisesRegex(nominate.Refused, r"failed its latest gate .*3 \(flash safety\)"):
            self.lab.nominate("Throwaway_mode")
        with self.assertRaisesRegex(nominate.Refused, "no mode 'Nowhere_mode'"):
            self.lab.nominate("Nowhere_mode")
        self.assertEqual(records.read_queue(self.lab.queue), [])
        self.assertEqual(self.lab.built, [])                               # refused before anything is drawn

    def test_a_gate_only_counts_for_the_code_it_was_measured_on(self):
        self.lab.gate("Throwaway_mode", True)
        self.lab.add_mode("Throwaway_mode", body="changed = True")
        with self.assertRaisesRegex(nominate.Refused, "has changed since its gate"):
            self.lab.nominate("Throwaway_mode")

    def test_the_other_mode_needs_a_passed_gate_only_if_it_is_a_lab_mode(self):
        self.lab.gate("Throwaway_mode", True)
        with self.assertRaisesRegex(nominate.Refused, "Rival_mode has never been through the gate"):
            self.lab.nominate("Throwaway_mode", "Rival_mode")
        with self.assertRaisesRegex(nominate.Refused, "against itself"):
            self.lab.nominate("Throwaway_mode", "Throwaway_mode")
        entries = self.lab.nominate("Throwaway_mode", "Old_mode", feed="today", note="look at the break")     # a registered mode: no gate asked
        self.assertEqual([e["clip"] for e in entries], ["19_0208_Throwaway_mode_vs_Old_mode_today_n1", "13_0030_Throwaway_mode_vs_Old_mode_today_n1"])
        self.lab.gate("Rival_mode", True)
        self.assertEqual(len(self.lab.nominate("Throwaway_mode", "Rival_mode")), 2)

    def test_nominating_builds_the_clips_and_queues_one_entry_per_clip(self):
        self.lab.gate("Throwaway_mode", True)
        entries = self.lab.nominate("Throwaway_mode", note="first try")
        self.assertEqual(records.read_queue(self.lab.queue), entries)
        self.assertEqual(entries[0], {"clip": "19_0208_Throwaway_mode_n1", "mode": "Throwaway_mode", "against": None, "feed": None, "track": "19",
                                      "start_s": 208.0, "duration_s": 24.0, "nominated": records.today(), "note": "first try"})
        self.assertEqual(tuple(entries[0]), records.QUEUE_KEYS)
        self.assertEqual(self.lab.built, [e["clip"] for e in entries])
        self.assertEqual(len(records.waiting(entries, records.read_verdicts(self.lab.verdicts))), 2)

        self.lab.judge(entries[0]["clip"])
        still = records.waiting(records.read_queue(self.lab.queue), records.read_verdicts(self.lab.verdicts))
        self.assertEqual([e["clip"] for e in still], ["13_0030_Throwaway_mode_n1"])

        again = self.lab.nominate("Throwaway_mode")                        # a later version: fresh ids, so it waits again
        self.assertEqual([e["clip"] for e in again], ["19_0208_Throwaway_mode_n2", "13_0030_Throwaway_mode_n2"])
        still = records.waiting(records.read_queue(self.lab.queue), records.read_verdicts(self.lab.verdicts))
        self.assertEqual(len(still), 3)

    def test_a_build_that_fails_queues_nothing(self):
        self.lab.gate("Throwaway_mode", True)

        def broken(*args, **kwargs):
            raise RuntimeError("no such song")

        with self.assertRaises(RuntimeError):
            nominate.nominate("Throwaway_mode", passages=(("19", 208.0, 24.0),), queue_path=self.lab.queue, verdicts_path=self.lab.verdicts,
                              gates_path=self.lab.gates, candidates=self.lab.candidates, production=self.lab.production,
                              clips_dir=self.lab.clips, build_feeds=broken, build_versus=broken)
        self.assertEqual(records.read_queue(self.lab.queue), [])

    def test_rebuild_draws_only_the_waiting_clips_that_are_missing(self):
        self.lab.gate("Throwaway_mode", True)
        entries = self.lab.nominate("Throwaway_mode") + self.lab.nominate("Throwaway_mode", "Old_mode")
        self.lab.judge(entries[0]["clip"])
        for e in entries:                                                  # a fresh checkout: no clip on disk
            (self.lab.clips / e["clip"] / "meta.json").unlink()
            (self.lab.clips / e["clip"]).rmdir()
        self.lab.built.clear()
        paths = dict(queue_path=self.lab.queue, verdicts_path=self.lab.verdicts, gates_path=self.lab.gates, clips_dir=self.lab.clips,
                     build_feeds=self.lab.build_feeds, build_versus=self.lab.build_versus)
        self.assertEqual(nominate.rebuild(**paths), [e["clip"] for e in entries[1:]])
        self.assertEqual(nominate.rebuild(**paths), [])                    # nothing left to do
        self.assertEqual(nominate.rebuild(everything=True, **paths), [entries[0]["clip"]])       # the judged one, on request
        self.assertEqual(len(records.read_queue(self.lab.queue)), 4)       # rebuilding never changes the queue

    def test_the_real_queue_and_the_owners_verdicts_are_well_formed(self):
        for entry in records.read_queue():
            self.assertEqual(tuple(entry), records.QUEUE_KEYS)
        lines = records.VERDICTS.read_text(encoding="utf-8").splitlines()
        self.assertTrue(lines[0].startswith(OWNER_FIRST_LINE))             # the owner's word is never rewritten
        self.assertEqual(records.verdict_mode(json.loads(lines[0])), "Kick_bands_mode")       # old lines still read


# -- the status record ---------------------------------------------------------------------------------------
class TestStatus(unittest.TestCase):
    def test_the_status_says_where_every_lab_mode_stands_and_what_waits(self):
        with tempfile.TemporaryDirectory() as tmp:
            lab = _Lab(Path(tmp))
            lab.add_mode("Unchecked_mode")
            lab.gate("Throwaway_mode", True)
            lab.gate("Rival_mode", False, failed=[3, 5])
            lab.gate("Old_mode", True)
            entries = lab.nominate("Throwaway_mode", "Old_mode", note="a | b") + lab.nominate("Throwaway_mode")
            lab.judge(entries[0]["clip"], kind="modes", mode="Throwaway_mode", against="Old_mode", chosen_mode="Old_mode")
            lab.judge(entries[2]["clip"], kind="feeds", mode="Throwaway_mode", chosen_feed="truth")
            lab.judge("13_0030_Throwaway_mode", chosen_feed="today")       # a line from before the new fields
            text = status.build(records.read_gates(lab.gates), records.read_queue(lab.queue), records.read_verdicts(lab.verdicts),
                                records.candidate_names(lab.candidates), lab.candidates, lab.production)
            rows = {line.split("|")[1].strip(): [c.strip() for c in line.split("|")[2:-1]] for line in text.splitlines() if line.startswith("| `")}
            self.assertEqual(rows["`Throwaway_mode`"], ["passed 2026-11-27", "-", "4", "2", "0 / 1 / 0", "today 1, truth 1"])
            self.assertEqual(rows["`Rival_mode`"][:2], ["FAILED 2026-11-27", "3 (flash safety), 5 (cost)"])
            self.assertEqual(rows["`Unchecked_mode`"][:3], ["never checked", "-", "0"])
            self.assertEqual(rows["`Old_mode`"], ["passed 2026-11-27", "-"])     # a registered mode that went through the gate
            self.assertIn("## Waiting for the owner: 2", text)
            self.assertIn("`13_0030_Throwaway_mode_vs_Old_mode_today_n1`", text)
            self.assertIn("a / b", text)                                   # a note cannot break the table
            self.assertNotIn(f"`{entries[0]['clip']}` |", text)              # judged: no longer listed as waiting

            lab.add_mode("Throwaway_mode", body="changed = True")
            text = status.build(records.read_gates(lab.gates), [], [], ["Throwaway_mode"], lab.candidates, lab.production)
            self.assertIn("the mode has changed since", text)
            self.assertIn("Nothing is waiting.", text)


if __name__ == "__main__":
    unittest.main()
