"""One research cycle of the music lab, one command per step.

    start   NAME --signal S [--signal S2] [--idea M03]    open a run folder with a plan to fill in
    grade   RUN --candidate C                             score the candidate on the OPEN tracks (as often as needed)
    check   RUN --candidate C                             score it once on the CHECK tracks: one number per signal
    close   RUN --verdict propose|archive --summary "..."  end the run; a proposal goes to the owner's inbox
    decide  RUN --decision approved|refused --note "..."   the owner's answer (only on the owner's word)

RUN is the folder name under research/scoreboard/runs/. Run from the repository root with the trial environment:

    research/analyzer_trials/.venv/Scripts/python.exe -m research.scoreboard.cycle start no_beat --signal no_beat

Why a tool and not a habit: the check tracks are only worth something if nobody tunes on them. `grade` never
plays them, `check` gives one number per signal and no track detail, and after a check the run is frozen: a new
idea is a new run. Every step is written to run.json so the status record and the owner's inbox can be built.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from research.scoreboard import compare

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUNS = HERE / "runs"
HIDDEN = HERE / "output" / "check"            # track detail of the check set: not committed, not for researchers
BASELINE = "MultiBandOnsetAudioAnalyzer"        # the main analyzer of the installation
SPLIT = json.loads((HERE / "split.json").read_text(encoding="utf-8"))
SPEC = json.loads((REPO / "config" / "music_signals.json").read_text(encoding="utf-8"))
SIGNAL_NAMES = [s["name"] for s in SPEC["signals"]]
TODO = "TODO"

PLAN = """# Plan of run `{run}`

Target: {signals}. Idea from the work list: {idea}.

Fill this in BEFORE writing code. Keep it short.

## What will change
{todo}: which candidate file, what it adds or changes, in two or three sentences.

## What result is expected
{todo}: the score you expect on the open tracks, and why you believe it.

## How I will know it failed
{todo}: the number under which the idea is dropped.

## What it could break
{todo}: the existing signals this could touch (the gate checks all of them).
"""

PROPOSAL = """# Proposal to the owner: {signals} (run `{run}`, {date})

## What is proposed
{todo}: in plain words, what the installation would gain. One short paragraph.

## Results (0 to 100)

{table}

{gate_line}

## What I ask you
{todo}: the decision, as one question.

## What this result does not tell you
{todo}: weak truth, weak tracks, cost on the Raspberry Pi not measured, anything not verified.
"""


def _today() -> str:
    return datetime.date.today().isoformat()


def _run_dir(name: str) -> Path:
    d = RUNS / name
    if not (d / "run.json").exists():
        sys.exit(f"no run '{name}' (no run.json in {d}). Runs: {', '.join(sorted(p.parent.name for p in RUNS.glob('*/run.json')))}")
    return d


def load(d: Path) -> dict:
    return json.loads((d / "run.json").read_text(encoding="utf-8"))


def save(d: Path, state: dict) -> None:
    (d / "run.json").write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def production_fingerprint() -> str:
    """Changes whenever the production analyzer or the bench changes: old baseline recordings are then stale."""
    h = hashlib.sha256()
    for folder in ("music", "research/scoreboard"):
        for p in sorted((REPO / folder).glob("*.py")):
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _scores(models: List[str], ids: List[str], workers: int) -> dict:
    """Play the tracks through the baseline (reused while production is unchanged) and the candidate (always)."""
    from research.scoreboard import scoreboard

    mark = scoreboard.OUT / BASELINE / "fingerprint.json"
    seen: Dict[str, str] = json.loads(mark.read_text(encoding="utf-8")) if mark.exists() else {}
    fp = production_fingerprint()
    fresh = [t for t in ids if seen.get(t) == fp and (scoreboard.OUT / BASELINE / f"{t}.npz").exists()]
    stale = [t for t in ids if t not in fresh]
    result = scoreboard.run([m for m in models if m != BASELINE], ids, workers, False) if len(models) > 1 else None
    base = scoreboard.run([BASELINE], stale, workers, False) if stale else None
    if fresh:
        kept = scoreboard.run([BASELINE], fresh, workers, True)
        if base is None:
            base = kept
        else:
            base["models"][BASELINE].update(kept["models"][BASELINE])
            base["tracks"].update(kept["tracks"])
    seen.update({t: fp for t in ids})
    mark.parent.mkdir(parents=True, exist_ok=True)
    mark.write_text(json.dumps(seen), encoding="utf-8")
    if result is None:
        return scoreboard._clean(base)
    result["models"][BASELINE] = base["models"][BASELINE]
    return scoreboard._clean(result)


def _p(x: Optional[float]) -> str:
    return "-" if x is None else f"{100 * x:.1f}"


def truth_note(per_track: dict, name: str) -> str:
    """On how many tracks the signal is graded, and on how many of those the truth is one that may grade."""
    cells = [t["signals"][name] for t in per_track.values() if t["signals"][name].get("produced")]
    graded = [c for c in cells if compare._score(c) is not None]
    checked = sum(1 for c in graded if c.get("checked") is not None)
    return f"{len(graded)} of {len(per_track)} tracks graded, {checked} of them on checked truth"


def _stand_ins(result: dict, signals: List[str]) -> List[str]:
    """The existing signals the scoreboard grades as if they filled the slot: the score to beat for an empty slot."""
    base = result["models"][BASELINE]
    keys = [k for k in next(iter(base.values()))["candidates"] if k.split(" <- ")[0] in signals]
    rows = []
    for k in keys:
        scores = [compare._score(dict(t["candidates"][k], produced=True)) for t in base.values()]
        scores = [s for s in scores if s is not None]
        rows.append(f"| {k} | {_p(sum(scores) / len(scores)) if scores else '-'} | {len(scores)} |")
    if not rows:
        return []
    return ["", "Existing signals graded as if they filled the slot (the score to beat):", "",
            "| Stand-in | Score | Tracks graded |", "|---|---|---|"] + rows


def _targets_table(result: dict, candidate: str, signals: List[str], with_tracks: bool) -> List[str]:
    base, cand = result["models"][BASELINE], result["models"][candidate]
    lines = ["| Signal | Production today | Candidate | Change | Truth |", "|---|---|---|---|---|"]
    for name in signals:
        b, _, _ = compare.signal_means(base, name)
        c, _, _ = compare.signal_means(cand, name)
        change = "-" if b is None or c is None else f"{100 * (c - b):+.1f}"
        lines.append(f"| {name} | {_p(b)} | {_p(c)} | {change} | {truth_note(cand, name)} |")
    lines += _stand_ins(result, signals)
    if with_tracks:
        names = {t: info["file"].rsplit(".", 1)[0][:28] for t, info in result["tracks"].items()}
        for name in signals:
            lines += ["", f"`{name}`, track by track (open tracks only):", "", "| Track | Production today | Candidate |", "|---|---|---|"]
            for t in sorted(cand):
                lines.append(f"| {t} {names[t]} | {_p(compare._score(base[t]['signals'][name]))} | {_p(compare._score(cand[t]['signals'][name]))} |")
        lines += ["", "A dash means the truth has nothing to grade on that track (for a stretch signal: no such stretch in the song). "
                  "A wrong answer there costs nothing in the score: measure it yourself and say it in the proposal."]
    return lines


def _gate_rows(result: dict, candidate: str, targets: List[str]) -> List[dict]:
    return [r for r in compare.gate(result, BASELINE, candidate) if r["signal"] not in targets]


def cmd_start(args: argparse.Namespace) -> None:
    for s in args.signal:
        if s not in SIGNAL_NAMES:
            sys.exit(f"'{s}' is not a signal of config/music_signals.json")
    run = f"{_today()}_{args.name}"
    d = RUNS / run
    if d.exists():
        sys.exit(f"{d} already exists: pick another name")
    d.mkdir(parents=True)
    state = {"run": run, "started": _today(), "signals": args.signal, "idea": args.idea or None, "candidate": None,
             "baseline": BASELINE, "state": "open", "grades": [], "check": None, "verdict": None, "decision": None}
    save(d, state)
    (d / "PLAN.md").write_text(PLAN.format(run=run, signals=", ".join(f"`{s}`" for s in args.signal), idea=args.idea or "none", todo=TODO), encoding="utf-8")
    print(f"run {run} opened. Fill in {d / 'PLAN.md'}, then write the candidate in research/experiments/models/ and run:\n"
          f"  cycle grade {run} --candidate <ClassName>")


def cmd_grade(args: argparse.Namespace) -> None:
    d = _run_dir(args.run)
    state = load(d)
    if state["state"] != "open":
        sys.exit(f"run {args.run} is '{state['state']}': it was already checked or closed. Tuning after a check turns the check "
                 f"tracks into tuning tracks. A new idea is a new run: cycle start <name> ...")
    if TODO in (d / "PLAN.md").read_text(encoding="utf-8"):
        sys.exit(f"fill in {d / 'PLAN.md'} first (it still contains {TODO}): the plan comes before the code")
    result = _scores([BASELINE, args.candidate], SPLIT["open"], args.workers)
    (d / "open_scores.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    targets = state["signals"]
    gate = _gate_rows(result, args.candidate, targets)
    passed = all(r["passed"] for r in gate)
    b_ms, c_ms = compare.frame_cost(result, BASELINE, args.candidate)
    lines = [f"# Open tracks: `{args.candidate}` against production (run `{args.run}`, grade {len(state['grades']) + 1})", "",
             f"{len(SPLIT['open'])} open tracks, production `Listener`, 5 s look-ahead. Scores from 0 to 100. "
             "You may tune on these tracks and grade again as often as you need.", "",
             "## Target", ""] + _targets_table(result, args.candidate, targets, True)
    lines += ["", f"## Gate on the other signals: {'PASSED' if passed else 'FAILED'}", "",
              f"No signal production already has may lose more than {100 * compare.GATE_MARGIN:.0f} point on average.", "",
              "| Signal | Production today | Candidate | Verdict | Tracks losing more than 5 points |", "|---|---|---|---|---|"]
    lines += [f"| {r['signal']} | {_p(r['baseline'])} | {_p(r['candidate'])} | {'kept' if r['passed'] else '**worse**'} | "
              f"{', '.join(r['track_drops']) or 'none'} |" for r in gate]
    if b_ms and c_ms:
        lines += ["", "## Cost", "", f"Whole listener step on this PC: production {b_ms:.3f} ms, candidate {c_ms:.3f} ms "
                  f"({100 * (c_ms / b_ms - 1):+.0f}%). Not measured on the Raspberry Pi."]
    (d / "OPEN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    means = {s: compare.signal_means(result["models"][args.candidate], s)[0] for s in targets}
    state["candidate"] = args.candidate
    state["grades"].append({"date": _today(), "candidate": args.candidate, "open": means, "gate_passed": passed})
    save(d, state)
    print(f"open tracks: " + ", ".join(f"{s} {_p(v)}" for s, v in means.items()) + f"; gate {'PASSED' if passed else 'FAILED'}; read {d / 'OPEN.md'}")


def cmd_check(args: argparse.Namespace) -> None:
    d = _run_dir(args.run)
    state = load(d)
    if state["state"] != "open":
        sys.exit(f"run {args.run} is '{state['state']}': a run is checked once")
    if not state["grades"] or state["grades"][-1]["candidate"] != args.candidate:
        sys.exit("grade this candidate on the open tracks first (cycle grade)")
    result = _scores([BASELINE, args.candidate], SPLIT["check"], args.workers)
    HIDDEN.mkdir(parents=True, exist_ok=True)
    (HIDDEN / f"{args.run}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    targets = state["signals"]
    base, cand = result["models"][BASELINE], result["models"][args.candidate]
    gate = _gate_rows(result, args.candidate, targets)
    worse = [r["signal"] for r in gate if not r["passed"]]
    open_means = state["grades"][-1]["open"]
    rows, record = [], {}
    for s in targets:
        b, c = compare.signal_means(base, s)[0], compare.signal_means(cand, s)[0]
        record[s] = {"production": b, "candidate": c, "open": open_means.get(s)}
        rows.append(f"| {s} | {_p(open_means.get(s))} | {_p(c)} | {_p(b)} | {truth_note(cand, s)} |")
    target_ok = all(v["candidate"] is not None and (v["production"] is None or v["candidate"] >= v["production"] - compare.GATE_MARGIN)
                    for v in record.values())
    lines = [f"# Check tracks: `{args.candidate}` (run `{args.run}`)", "",
             f"{len(SPLIT['check'])} tracks nobody tuned on. One number per signal, no track detail: that is on purpose. "
             "This run is now frozen; a new idea is a new run.", "",
             "| Signal | Candidate on the open tracks | Candidate on the check tracks | Production on the check tracks | Truth on the check tracks |",
             "|---|---|---|---|---|"] + rows
    lines += ["", f"Gate on the other signals, check tracks: {'PASSED' if not worse else 'FAILED (worse: ' + ', '.join(worse) + ')'}.",
              f"Target not worse than production on the check tracks: {'yes' if target_ok else 'NO'}.", "",
              "A score that holds on the check tracks is not an accident of the tuning. A score that falls there by much "
              "more than between two open tracks was fitted to the open tracks."]
    (d / "CHECK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    state["check"] = {"date": _today(), "candidate": args.candidate, "signals": record, "gate_passed": not worse, "target_ok": target_ok}
    state["state"] = "checked"
    save(d, state)
    print("\n".join(lines[4:]))


def cmd_close(args: argparse.Namespace) -> None:
    d = _run_dir(args.run)
    state = load(d)
    if state["state"] in ("proposed", "archived", "decided"):
        sys.exit(f"run {args.run} is already '{state['state']}'")
    if args.verdict == "propose":
        chk = state["check"]
        if not chk or not chk["gate_passed"] or not chk["target_ok"]:
            sys.exit("a proposal needs a check that passed (cycle check). Archive the run, or start a new one.")
        prop = d / "PROPOSAL.md"
        if not prop.exists():
            table = ["| Signal | Production, tracks not looked at | Candidate, tracks tuned on | Candidate, tracks not looked at |", "|---|---|---|---|"]
            table += [f"| `{s}` | {_p(v['production'])} | {_p(v['open'])} | {_p(v['candidate'])} |" for s, v in chk["signals"].items()]
            prop.write_text(PROPOSAL.format(signals=", ".join(f"`{s}`" for s in state["signals"]), run=args.run, date=_today(), todo=TODO,
                                            table="\n".join(table),
                                            gate_line="Gate: no other signal got worse, on the open tracks and on the check tracks."), encoding="utf-8")
            print(f"wrote the skeleton of {prop}. Replace every {TODO} in plain words, then run close again.")
            return
        if TODO in prop.read_text(encoding="utf-8"):
            sys.exit(f"{prop} still contains {TODO}")
    state["verdict"] = {"date": _today(), "verdict": args.verdict, "summary": args.summary}
    state["state"] = "proposed" if args.verdict == "propose" else "archived"
    save(d, state)
    _refresh()
    print(f"run {args.run} closed: {state['state']}")


def cmd_decide(args: argparse.Namespace) -> None:
    d = _run_dir(args.run)
    state = load(d)
    if state["state"] != "proposed":
        sys.exit(f"run {args.run} is '{state['state']}': only a proposed run waits for a decision")
    state["decision"] = {"date": _today(), "decision": args.decision, "note": args.note}
    state["state"] = "decided"
    save(d, state)
    _refresh()
    print(f"run {args.run}: {args.decision}")


def _refresh() -> None:
    from research import inbox
    from research.scoreboard import status

    status.write()
    inbox.write()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("name")
    s.add_argument("--signal", action="append", required=True)
    s.add_argument("--idea", default="")
    for name in ("grade", "check"):
        s = sub.add_parser(name)
        s.add_argument("run")
        s.add_argument("--candidate", required=True)
        s.add_argument("--workers", type=int, default=5)
    s = sub.add_parser("close")
    s.add_argument("run")
    s.add_argument("--verdict", choices=("propose", "archive"), required=True)
    s.add_argument("--summary", required=True)
    s = sub.add_parser("decide")
    s.add_argument("run")
    s.add_argument("--decision", choices=("approved", "refused"), required=True)
    s.add_argument("--note", default="")
    args = p.parse_args()
    {"start": cmd_start, "grade": cmd_grade, "check": cmd_check, "close": cmd_close, "decide": cmd_decide}[args.cmd](args)


if __name__ == "__main__":
    main()
