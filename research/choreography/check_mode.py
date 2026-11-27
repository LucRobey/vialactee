"""The gate: may this mode be shown to the owner at all?

It draws the mode on the three standard passages (build_clips.DEFAULT_CLIPS), on every feed, profiles the result,
and answers five questions with pass or fail. A mode that fails cannot be nominated (nominate.py). The gate
filters out what clearly does not work. It never says a show is good: that stays the owner's choice.

    1. it runs                      every feed of every passage is drawn without an error
    2. works on today's analyzer    hearing what the installation hears today, the light is not stuck dark or frozen
    3. flash safety                 no more than 3 general flashes in any one second, on the truth and today feeds
    4. tied to the music            on the control (every hit half a beat late) fewer flashes land on a real hit
    5. cost                         mean time to draw one frame, on this computer

Run from the repository root with the trial environment:
    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.check_mode Kick_bands_mode [--reuse]

Writes output/gates/<mode>/GATE.md and gate.json, and the mode's line of gates.json (committed).
Exit code: 0 the mode passes, 1 it fails, 2 the gate could not run (no such mode, a missing song or truth file).
"""
from __future__ import annotations

import argparse
import filecmp
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from research.choreography import records
from research.choreography.profile import FLASH_LIMIT

# Every limit of the gate. PROVISIONAL: proposed by the agent who wrote the gate, not decided by the owner.
TODAY_DARK_SHARE_MAX: float = 0.50    # rule 2: dark for more than half of the time music plays = stuck dark
TODAY_MOVE_MIN: float = 0.03          # rule 2: the light must travel at least 3% of full brightness (as the eye sees it),
                                      #         either the whole installation or a typical LED; under that it is frozen
SAFETY_FEEDS = ("truth", "today")     # rule 3: the feeds flash safety is judged on (FLASH_LIMIT comes from profile.py: 3)
TIED_MIN_FLASHES: int = 8             # rule 4: with fewer visible flashes on the truth feed the rule cannot say anything
TIED_MIN_HITS: int = 8                # rule 4: nor with fewer real kicks, snares and drops in the passage
TIED_GAP_MIN: float = 0.20            # rule 4: the share of flashes on a real hit must be 20 points lower on the control
DRAW_MS_LIMIT: float = 33.0           # rule 5: a whole frame at 30 frames per second, measured on a PC. Generous on
                                      #         purpose: the Raspberry Pi is several times slower than a PC
DRAW_MS_WATCH: float = 5.0            # rule 5: above this the report asks for a timing on the Pi (still a pass)

GATES_DIR = Path(__file__).resolve().parent / "output" / "gates"
PASS, FAIL, NOT_APPLICABLE, NOT_MEASURED = "pass", "fail", "not applicable", "not measured"
THRESHOLDS = {"TODAY_DARK_SHARE_MAX": TODAY_DARK_SHARE_MAX, "TODAY_MOVE_MIN": TODAY_MOVE_MIN, "FLASH_LIMIT": FLASH_LIMIT,
              "TIED_MIN_FLASHES": TIED_MIN_FLASHES, "TIED_MIN_HITS": TIED_MIN_HITS, "TIED_GAP_MIN": TIED_GAP_MIN,
              "DRAW_MS_LIMIT": DRAW_MS_LIMIT, "DRAW_MS_WATCH": DRAW_MS_WATCH}


def _num(x: Any) -> Optional[float]:
    return None if x is None or x != x else float(x)


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def label(passage: dict) -> str:
    m = int(passage["start_s"] // 60)
    return f"{passage['song']} from {m}:{int(passage['start_s'] - 60 * m):02d}"


def _rule(number: int, title: str, rows: List[dict], measured: str, limit: str, numbers: Dict[str, Any], note: str = "",
          status: Optional[str] = None) -> dict:
    """One rule's answer. Without an explicit status: fail if any row fails; else not measured if any row could
    not be measured (or there is none); else pass if at least one row passes; else not applicable."""
    states = [r["status"] for r in rows]
    if status is None:
        status = (FAIL if FAIL in states else NOT_MEASURED if NOT_MEASURED in states or not states
                  else PASS if PASS in states else NOT_APPLICABLE)
    failed_on = sorted({r["passage"] for r in rows if r["status"] == FAIL})
    return {"rule": number, "title": title, "status": status, "measured": measured, "limit": limit, "failed_on": failed_on,
            "rows": rows, "numbers": numbers, "note": note}


# -- the five rules. Each reads the passage records built by measure_passage ----------------------------
def rule_runs(passages: Sequence[dict], load_error: Optional[str]) -> dict:
    if load_error:
        rows = [{"passage": "all passages", "feed": "all feeds", "measured": load_error, "status": FAIL}]
        return _rule(1, "It runs", rows, "the mode could not be loaded", "no error", {"renders_ok": 0, "renders": 0})
    rows = []
    for p in passages:
        for feed in p["feeds"]:
            err = p["errors"].get(feed)
            rows.append({"passage": label(p), "feed": feed, "measured": err or "drawn", "status": FAIL if err else PASS})
    ok = sum(r["status"] == PASS for r in rows)
    return _rule(1, "It runs", rows, f"{ok} of {len(rows)} versions drawn without an error", "all of them",
                 {"renders_ok": ok, "renders": len(rows)})


def rule_today(passages: Sequence[dict]) -> dict:
    rows, darks, moves = [], [], []
    for p in passages:
        light = (p["profiles"].get("today") or {}).get("light")
        if light is None:
            rows.append({"passage": label(p), "feed": "today", "measured": "no frames to measure", "status": NOT_MEASURED})
            continue
        dark = _num(light.get("dark_share")) or 0.0
        move = max((_num(light.get("high")) or 0.0) - (_num(light.get("low")) or 0.0), _num(light.get("led_swing")) or 0.0)
        darks.append(dark)
        moves.append(move)
        if dark > TODAY_DARK_SHARE_MAX:
            verdict, status = "stuck dark", FAIL
        elif move < TODAY_MOVE_MIN:
            verdict, status = ("stuck dark" if (_num(light.get("mean")) or 0.0) < 0.02 else "frozen: lit but nothing moves"), FAIL
        else:
            verdict, status = "lit and moving", PASS
        rows.append({"passage": label(p), "feed": "today", "status": status,
                     "measured": f"dark {_pct(dark)} of the time music plays; the light travels {_pct(move)} of full brightness: {verdict}"})
    measured = (f"dark at most {_pct(max(darks))} of the time; the light travels at least {_pct(min(moves))} of full brightness"
                if darks else "nothing measured")
    return _rule(2, "It works on today's analyzer", rows, measured,
                 f"dark no more than {_pct(TODAY_DARK_SHARE_MAX)} of the time; travels at least {_pct(TODAY_MOVE_MIN)}",
                 {"today_dark_share_max": max(darks) if darks else None, "today_movement_min": min(moves) if moves else None})


def rule_flash(passages: Sequence[dict]) -> dict:
    rows, worst = [], None
    for p in passages:
        for feed in SAFETY_FEEDS:
            safety = (p["profiles"].get(feed) or {}).get("safety")
            if safety is None:
                rows.append({"passage": label(p), "feed": feed, "measured": "no frames to measure", "status": NOT_MEASURED})
                continue
            most = float(safety["flashes_per_second_max"])
            rows.append({"passage": label(p), "feed": feed, "status": PASS if most <= FLASH_LIMIT else FAIL,
                         "measured": f"at most {most:.1f} flashes in one second ({safety.get('where', 'whole installation')})"})
            if worst is None or most > worst[0]:
                worst = (most, label(p), feed)
    measured = f"at most {worst[0]:.1f} flashes in one second ({worst[1]}, {worst[2]} feed)" if worst else "nothing measured"
    return _rule(3, "Flash safety", rows, measured, f"no more than {FLASH_LIMIT} in any one second",
                 {"flashes_per_second_max": worst[0] if worst else None},
                 "General flashes only, counted by the profile (WCAG 2.3.1). Saturated red flashes are not checked.")


def rule_tied(passages: Sequence[dict]) -> dict:
    rows, gaps = [], []
    for p in passages:
        truth, control = (p["profiles"].get("truth") or {}).get("flashes"), (p["profiles"].get("control") or {}).get("flashes")
        row = {"passage": label(p), "feed": "truth against control"}
        if truth is None or control is None:
            rows.append({**row, "measured": "no frames to measure", "status": NOT_MEASURED})
        elif p.get("control_same_as_truth"):
            rows.append({**row, "status": NOT_APPLICABLE,
                         "measured": "the frames are the same on the truth and on the control: the mode does not read the hits the lab feeds it"})
        elif truth["flashes"] < TIED_MIN_FLASHES or truth["hits"] < TIED_MIN_HITS:
            rows.append({**row, "status": NOT_APPLICABLE,
                         "measured": f"{truth['flashes']} visible flashes and {truth['hits']} real hits: too few to say"})
        else:
            on_truth, on_control = _num(truth.get("flashes_with_a_hit")) or 0.0, _num(control.get("flashes_with_a_hit")) or 0.0
            gap = on_truth - on_control
            gaps.append((gap, on_truth, on_control, label(p)))
            rows.append({**row, "status": PASS if gap >= TIED_GAP_MIN else FAIL,
                         "measured": f"flashes on a real hit: {_pct(on_truth)} on the truth, {_pct(on_control)} on the control ({100 * gap:.0f} points apart)"})
    note = ""
    if gaps:
        gap, on_truth, on_control, where = min(gaps)
        measured = f"flashes on a real hit: {_pct(on_truth)} on the truth, {_pct(on_control)} on the control (smallest gap, {where})"
    else:
        measured = "this rule cannot test this mode" if rows and all(r["status"] == NOT_APPLICABLE for r in rows) else "nothing measured"
        if any(r["status"] == NOT_APPLICABLE for r in rows):
            note = ("Not applicable is neither a pass nor a fail. This rule works by counting visible flashes that land on a real "
                    "kick, snare or drop. A mode that does not flash, or does not read the hits the lab feeds, gives it nothing to "
                    "count. Whether such a mode follows the music is then left to the owner's eye.")
    return _rule(4, "Tied to the music", rows, measured, f"at least {100 * TIED_GAP_MIN:.0f} points lower on the control",
                 {"tied_gap_min": min(gaps)[0] if gaps else None}, note)


def rule_cost(passages: Sequence[dict]) -> dict:
    rows, all_ms = [], []
    for p in passages:
        values = [v for v in p["draw_ms"].values() if v is not None]
        if not values:
            rows.append({"passage": label(p), "feed": "all feeds", "measured": "not timed", "status": NOT_MEASURED})
            continue
        all_ms += values
        mean = sum(values) / len(values)
        rows.append({"passage": label(p), "feed": "all feeds", "measured": f"{mean:.2f} ms a frame (slowest feed {max(values):.2f} ms)",
                     "status": PASS if mean <= DRAW_MS_LIMIT else FAIL})
    mean = sum(all_ms) / len(all_ms) if all_ms else None
    note = ("Measured on this computer, not on the installation. The installation draws 30 frames a second (33 ms each) on a "
            "Raspberry Pi, which is several times slower than a PC: this number is only an indication.")
    if mean is not None and DRAW_MS_WATCH < mean <= DRAW_MS_LIMIT:
        note += f" Above {DRAW_MS_WATCH:.0f} ms on a PC: time this mode on the Pi before trusting it."
    status = None if mean is None else PASS if mean <= DRAW_MS_LIMIT else FAIL
    return _rule(5, "Cost", rows, f"{mean:.2f} ms to draw one frame, on this computer" if mean is not None else "not timed",
                 f"no more than {DRAW_MS_LIMIT:.0f} ms on a PC", {"draw_ms": round(mean, 3) if mean is not None else None}, note, status)


def judge(passages: Sequence[dict], load_error: Optional[str] = None) -> List[dict]:
    """The five rules on the passage records of one mode."""
    return [rule_runs(passages, load_error), rule_today(passages), rule_flash(passages), rule_tied(passages), rule_cost(passages)]


def passed(rules: Sequence[dict]) -> bool:
    """A mode passes when no rule fails and none is left unmeasured. "Not applicable" (rule 4 only) does not block."""
    return all(r["status"] in (PASS, NOT_APPLICABLE) for r in rules)


# -- measuring a mode on a passage ----------------------------------------------------------------------
def load_error_of(mode: str) -> Optional[str]:
    """None when the mode's file can be loaded, else the error in one line."""
    from research.choreography.build_clips import error_text

    path = records.mode_file(mode)
    package = "research.choreography.candidates" if records.is_candidate(mode) else "modes"
    try:
        getattr(importlib.import_module(f"{package}.{path.stem}"), mode)
    except Exception as exc:  # noqa: BLE001 - whatever stops the file from loading is the mode's failure
        return error_text(exc)
    return None


def _reusable(clip: Path, mode: str, start_s: float, duration_s: float, sha: Optional[str]) -> bool:
    """A clip built earlier can stand in for a new one only if it is this mode's current code on this passage, timed."""
    if not (clip / "meta.json").is_file():
        return False
    meta = json.loads((clip / "meta.json").read_text(encoding="utf-8"))
    return (meta.get("kind") == "feeds" and meta.get("mode") == mode and meta.get("start_s") == start_s
            and meta.get("duration_s") == duration_s and sha is not None and (meta.get("sources") or {}).get(mode) == sha
            and all(f.get("draw_ms") is not None and (clip / f["file"]).is_file() for f in meta.get("feeds", [])))


def measure_passage(mode: str, track_id: str, start_s: float, duration_s: float, reuse: bool, candidate: str) -> dict:
    """Draw (or reuse) the feeds clip of one passage, profile it, and return the record the rules read."""
    from research.choreography import build_clips, profile_clip

    clip_id = build_clips.clip_name(track_id, start_s, mode)
    clip = build_clips.CLIPS / clip_id
    if reuse and _reusable(clip, mode, start_s, duration_s, records.source_sha(records.mode_file(mode))):
        print(f"reusing {clip}", flush=True)
    else:
        build_clips.build_clip(mode, track_id, start_s, duration_s, candidate, errors={})
    meta = json.loads((clip / "meta.json").read_text(encoding="utf-8"))
    profiles: Dict[str, dict] = {}
    if meta["feeds"]:
        dest = profile_clip.profile_clip(clip_id)
        profiles = json.loads((dest / "profile.json").read_text(encoding="utf-8"))["profiles"]
    drawn = [f["key"] for f in meta["feeds"]]
    same = ("truth" in drawn and "control" in drawn and filecmp.cmp(clip / "truth.bin", clip / "control.bin", shallow=False))
    return {"clip": clip_id, "song": meta["track"]["file"].rsplit(".", 1)[0], "start_s": start_s, "duration_s": duration_s,
            "feeds": drawn + [k for k in meta.get("errors", {}) if k not in drawn], "errors": meta.get("errors", {}),
            "draw_ms": {f["key"]: f.get("draw_ms") for f in meta["feeds"]}, "profiles": profiles, "control_same_as_truth": bool(same)}


# -- the report -----------------------------------------------------------------------------------------
def report(result: dict) -> str:
    """GATE.md: the result first, then each rule with its numbers, then what is reported without being judged."""
    from research.choreography.profile_clip import SIDE_BY_SIDE, _fmt

    rules = result["rules"]
    failed = [r for r in rules if r["status"] == FAIL]
    verdict = "PASSED" if result["passed"] else "FAILED"
    lines = [f"# Gate of `{result['mode']}`: {verdict}", "", f"Checked on {result['date']}, on {len(result['passages'])} passages."]
    if result["passed"]:
        lines.append("No rule failed: this mode may be nominated for the owner. The gate does not say the show is good.")
    else:
        why = "; ".join(f"rule {r['rule']} ({records.RULE_NAMES[r['rule']]})" for r in rules if r["status"] in (FAIL, NOT_MEASURED))
        lines.append(f"Not passed because of: {why}. This mode may not be nominated for the owner until it passes.")
    lines += ["", "**The limits below are provisional proposals, not decisions of the owner.** They are named constants at the top of",
              "`research/choreography/check_mode.py`. The gate filters out what clearly does not work; only the owner judges a show.", "",
              "| Rule | Result | Measured | Limit | Failed on |", "|---|---|---|---|---|"]
    for r in rules:
        lines.append(f"| {r['rule']}. {r['title']} | **{r['status']}** | {r['measured']} | {r['limit']} | {', '.join(r['failed_on']) or '-'} |")
    lines += ["", "## Rule by rule"]
    for r in rules:
        lines += ["", f"### {r['rule']}. {r['title']}: {r['status']}", ""]
        if r["note"]:
            lines += [r["note"], ""]
        lines += ["| Passage | Feed | Measured | Result |", "|---|---|---|---|"]
        lines += [f"| {row['passage']} | {row['feed']} | {row['measured']} | {row['status']} |" for row in r["rows"]]
    lines += ["", "## Reported, not judged", "",
              "Everything else the profile measures. These numbers describe the show; no limit is set on them.",
              "\"Wrong on purpose\" is the control: the truth with every hit moved half a beat late."]
    for p in result["passages"]:
        feeds = [f for f in p["feeds"] if f in p.get("reported", {})]
        lines += ["", f"### {label(p)} ({p['duration_s']:.0f} s)", "",
                  f"Full profile with pictures: `research/choreography/output/profiles/{p['clip']}/PROFILE.md`", ""]
        if not feeds:
            lines.append("Nothing was drawn on this passage.")
            continue
        lines += ["| | " + " | ".join(feeds) + " |", "|---|" + "---|" * len(feeds)]
        for name, _, kind in SIDE_BY_SIDE:
            lines.append(f"| {name} | " + " | ".join(_fmt(p["reported"][f].get(name), kind) for f in feeds) + " |")
        lines.append("| Time to draw one frame, on this computer | " + " | ".join(
            "-" if p["draw_ms"].get(f) is None else f"{p['draw_ms'][f]:.2f} ms" for f in feeds) + " |")
    return "\n".join(lines) + "\n"


def _slim(passage: dict) -> dict:
    """A passage record without the full profiles: only the numbers the report lists."""
    from research.choreography.profile_clip import SIDE_BY_SIDE, _get

    reported = {feed: {name: _get(prof, path) for name, path, _ in SIDE_BY_SIDE} for feed, prof in passage["profiles"].items()}
    return {**{k: v for k, v in passage.items() if k != "profiles"}, "reported": reported}


def check(mode: str, reuse: bool = False, candidate: Optional[str] = None, passages: Optional[Sequence[tuple]] = None,
          gates_dir: Path = GATES_DIR, gates_path: Path = records.GATES,
          measure: Callable[..., dict] = measure_passage, load_error: Optional[Callable[[str], Optional[str]]] = None) -> dict:
    """Run the gate on one mode, write GATE.md, gate.json and the mode's line of gates.json, and return the result."""
    from research.choreography import build_clips

    error = (load_error or load_error_of)(mode)
    measured = [] if error else [measure(mode, track, start, duration, reuse, candidate or build_clips.DEFAULT_CANDIDATE)
                                 for track, start, duration in (passages or build_clips.DEFAULT_CLIPS)]
    rules = judge(measured, error)
    numbers: Dict[str, Any] = {}
    for r in rules:
        numbers.update(r["numbers"])
    result = {"mode": mode, "date": records.today(), "passed": passed(rules),
              "failed_rules": [r["rule"] for r in rules if r["status"] in (FAIL, NOT_MEASURED)],
              "rules": rules, "numbers": numbers, "thresholds": THRESHOLDS, "provisional": True,
              "source_sha": records.source_sha(records.mode_file(mode)), "passages": [_slim(p) for p in measured]}
    dest = gates_dir / mode
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "GATE.md").write_text(report(result), encoding="utf-8")
    (dest / "gate.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    records.write_gate(mode, {"date": result["date"], "passed": result["passed"], "failed_rules": result["failed_rules"],
                              "rules": {str(r["rule"]): r["status"] for r in rules}, "numbers": numbers,
                              "source": "candidates" if records.is_candidate(mode) else "modes", "source_sha": result["source_sha"],
                              "thresholds_provisional": True}, gates_path)
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="The gate of a lab mode: five pass/fail rules on the three standard passages.")
    p.add_argument("mode")
    p.add_argument("--reuse", action="store_true", help="reuse clips already built from this mode's current code")
    p.add_argument("--candidate", help="analyzer whose recording feeds the 'candidate' version")
    args = p.parse_args()
    if records.mode_file(args.mode) is None:
        print(f"No mode '{args.mode}' in research/choreography/candidates/ or modes/. Nothing was checked.")
        return 2
    try:
        result = check(args.mode, args.reuse, args.candidate)
    except Exception as exc:  # noqa: BLE001 - a missing song or truth file is the lab's problem, not the mode's
        from research.choreography.build_clips import error_text

        print(f"The gate could not run (this is not a verdict on the mode): {error_text(exc)}")
        return 2
    print(f"\nGate of {args.mode}: {'PASSED' if result['passed'] else 'FAILED'}")
    for r in result["rules"]:
        print(f"  {r['rule']}. {r['title']:30s} {r['status']:15s} {r['measured']}" + (f"  [failed on: {', '.join(r['failed_on'])}]" if r["failed_on"] else ""))
    print(f"Report: {GATES_DIR / args.mode / 'GATE.md'}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
