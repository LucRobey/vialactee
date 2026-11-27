"""Before and after: a research candidate against the model it wants to replace, and the gate.

Reads the scores.json of one scoreboard run that contains both models and writes COMPARISON.md next to it:

1. The gate: no signal the baseline already produces may get worse by more than the margin.
2. The new signals the candidate fills, scored apart on the open tracks (which the researcher may tune on) and
   on the check tracks (which the researcher did not look at).
3. The cost: time per tick of the whole listener step, baseline against candidate.

Run from the repository root:
    python -m research.scoreboard.compare research/scoreboard/runs/<run> --baseline NAME --candidate NAME
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

GATE_MARGIN: float = 0.01      # one point out of 100: proposal, to be replaced by a measured noise margin
TRACK_DROP: float = 0.05       # a single track losing more than five points is listed even when the average holds


SPLIT = json.loads((Path(__file__).resolve().parent / "split.json").read_text(encoding="utf-8"))


def is_open(track_id: str) -> bool:
    """Open tracks may be tuned on; the others are the check set. The list is split.json (provisional, the owner's to fix)."""
    return track_id in SPLIT["open"]


def _score(cell: dict) -> Optional[float]:
    """The score that counts for a signal on a track: checked truth when there is some, all truth otherwise."""
    if not cell.get("produced"):
        return None
    return cell["checked"] if cell.get("checked") is not None else cell.get("all")


def _mean(values: List[Optional[float]]) -> Optional[float]:
    v = [x for x in values if x is not None]
    return sum(v) / len(v) if v else None


def signal_means(per_track: Dict[str, dict], name: str, ids: Optional[List[str]] = None) -> Tuple[Optional[float], int, bool]:
    """Average score of one signal over tracks. Returns (mean, tracks counted, graded on checked truth)."""
    cells = [per_track[t]["signals"][name] for t in (ids or list(per_track))]
    scores = [_score(c) for c in cells]
    checked = any(c.get("produced") and c.get("checked") is not None for c in cells)
    return _mean(scores), sum(1 for s in scores if s is not None), checked


def gate(result: dict, baseline: str, candidate: str, margin: float = GATE_MARGIN) -> List[dict]:
    """One row per signal the baseline produces: did the candidate keep it?"""
    base, cand = result["models"][baseline], result["models"][candidate]
    rows = []
    for name in next(iter(base.values()))["signals"]:
        b, n, checked = signal_means(base, name)
        if b is None:
            continue
        c, _, _ = signal_means(cand, name)
        drops = []
        for tid in base:
            sb, sc = _score(base[tid]["signals"][name]), _score(cand[tid]["signals"][name])
            if sb is not None and (sc is None or sb - sc > TRACK_DROP):
                drops.append(tid)
        rows.append({"signal": name, "baseline": b, "candidate": c, "tracks": n, "checked": checked,
                     "passed": c is not None and c >= b - margin, "track_drops": drops})
    return rows


def new_signals(result: dict, baseline: str, candidate: str) -> List[dict]:
    """One row per signal the candidate produces and the baseline does not."""
    base, cand = result["models"][baseline], result["models"][candidate]
    open_ids = [t for t in cand if is_open(t)]
    check_ids = [t for t in cand if not is_open(t)]
    rows = []
    for name in next(iter(cand.values()))["signals"]:
        if signal_means(base, name)[0] is not None or signal_means(cand, name)[0] is None:
            continue
        every, n, checked = signal_means(cand, name)
        per = sorted(((_score(cand[t]["signals"][name]), t) for t in cand if _score(cand[t]["signals"][name]) is not None))
        rows.append({"signal": name, "open": signal_means(cand, name, open_ids)[0], "check": signal_means(cand, name, check_ids)[0],
                     "all": every, "tracks": n, "checked": checked, "weakest": per[:3]})
    return rows


def frame_cost(result: dict, baseline: str, candidate: str) -> Tuple[Optional[float], Optional[float]]:
    def avg(model: str) -> Optional[float]:
        return _mean([t.get("frame_ms") for t in result["models"][model].values()])

    return avg(baseline), avg(candidate)


def _p(x: Optional[float]) -> str:
    return "-" if x is None else f"{100 * x:.1f}"


def write_comparison(result: dict, baseline: str, candidate: str, out_path: Path) -> bool:
    g, new = gate(result, baseline, candidate), new_signals(result, baseline, candidate)
    b_ms, c_ms = frame_cost(result, baseline, candidate)
    passed = all(r["passed"] for r in g)
    names = {t: info["file"].rsplit(".", 1)[0][:24] for t, info in result["tracks"].items()}
    lines = [
        f"# Comparison: `{candidate}` against `{baseline}`", "",
        f"Scoreboard run of {result['built']}, {len(result['tracks'])} tracks, production `Listener`, "
        f"{result['lookahead_s']:.0f} s look-ahead. Scores from 0 to 100.", "",
        f"## 1. The gate: {'PASSED' if passed else 'FAILED'}", "",
        f"No signal the baseline produces may lose more than {100 * GATE_MARGIN:.0f} point on average.", "",
        "| Signal | Baseline | Candidate | Change | Truth | Verdict | Tracks losing more than 5 points |", "|---|---|---|---|---|---|---|",
    ]
    for r in g:
        change = "-" if r["candidate"] is None else f"{100 * (r['candidate'] - r['baseline']):+.1f}"
        lines.append(f"| {r['signal']} | {_p(r['baseline'])} | {_p(r['candidate'])} | {change} | "
                     f"{'checked' if r['checked'] else 'one tool only'} | {'kept' if r['passed'] else '**worse**'} | "
                     f"{', '.join(r['track_drops']) or 'none'} |")
    lines += ["", "## 2. New signals", "",
              "Open tracks (odd numbers) could be used for tuning. Check tracks (even numbers) were not looked at: "
              "a score that holds there is not an accident of the tuning.", "",
              "| Signal | Open tracks | Check tracks | All | Truth | Weakest tracks |", "|---|---|---|---|---|---|"]
    for r in new:
        weak = ", ".join(f"{names[t]} ({100 * s:.0f})" for s, t in r["weakest"])
        lines.append(f"| {r['signal']} | {_p(r['open'])} | {_p(r['check'])} | {_p(r['all'])} | "
                     f"{'checked' if r['checked'] else 'one tool only'} | {weak} |")
    lines += ["", "## 3. Cost", ""]
    if b_ms is not None and c_ms is not None:
        lines.append(f"Time per tick of the whole listener step (audio front end, analyzer, context) on this PC: "
                     f"baseline {b_ms:.3f} ms, candidate {c_ms:.3f} ms, difference {c_ms - b_ms:+.3f} ms "
                     f"({100 * (c_ms / b_ms - 1):+.0f}%). Not measured on the Raspberry Pi.")
    else:
        lines.append("Not measured in this run.")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return passed


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("run_dir")
    p.add_argument("--baseline", default="DyadicMetricalAudioAnalyzer")
    p.add_argument("--candidate", required=True)
    args = p.parse_args()
    run = Path(args.run_dir)
    result = json.loads((run / "scores.json").read_text(encoding="utf-8"))
    passed = write_comparison(result, args.baseline, args.candidate, run / "COMPARISON.md")
    print(f"gate {'PASSED' if passed else 'FAILED'}; wrote {run / 'COMPARISON.md'}")


if __name__ == "__main__":
    main()
