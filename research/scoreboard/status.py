"""The status record of the music lab: where every signal stands, and every research run.

    research/analyzer_trials/.venv/Scripts/python.exe -m research.scoreboard.status

Writes research/scoreboard/STATUS.md from three sources: the signal list (config/music_signals.json), the latest
scoreboard of the production model (scores.json), and the run.json of every run under runs/. `cycle close` and
`cycle decide` rebuild it. Read it before picking work: it says what is empty, what is weak, and what was tried.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from research.scoreboard import compare

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUNS = HERE / "runs"
BASELINE = "DyadicMetricalAudioAnalyzer"
STATE_TEXT = {"open": "in progress", "checked": "checked, not closed", "proposed": "**waiting for the owner**",
              "archived": "dropped", "decided": "decided"}


def runs() -> List[dict]:
    out = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RUNS.glob("*/run.json"))]
    return sorted(out, key=lambda r: r["run"])


def waiting_for_owner() -> List[dict]:
    """Runs whose proposal has no answer yet."""
    return [r for r in runs() if r["state"] == "proposed"]


def _p(x: Optional[float]) -> str:
    return "-" if x is None else f"{100 * x:.0f}"


def write(out_path: Optional[Path] = None) -> Path:
    spec = json.loads((REPO / "config" / "music_signals.json").read_text(encoding="utf-8"))
    board = json.loads((HERE / "scores.json").read_text(encoding="utf-8"))
    prod = board["models"][BASELINE]
    all_runs = runs()
    tried: Dict[str, List[dict]] = {}
    for r in all_runs:
        for s in r["signals"]:
            tried.setdefault(s, []).append(r)

    lines = ["# Music lab: status", "",
             f"Built by `research/scoreboard/status.py`. Production scores from the scoreboard of {board['built']} "
             f"({len(board['tracks'])} tracks, 0 to 100). Do not edit by hand.", "",
             "## Signals", "",
             "| Signal | In the contract | Production today | Truth | Runs on it | Best candidate on the check tracks |", "|---|---|---|---|---|---|"]
    for s in spec["signals"]:
        name = s["name"]
        mean, n, checked = compare.signal_means(prod, name)
        truth = "-" if mean is None else ("checked" if checked else "one tool only")
        rs = tried.get(name, [])
        best, best_run = None, ""
        for r in rs:
            v = ((r.get("check") or {}).get("signals") or {}).get(name, {}).get("candidate")
            if v is not None and (best is None or v > best):
                best, best_run = v, r["run"]
        lines.append(f"| `{name}` | {s['status']} | {_p(mean)} | {truth} | {len(rs) or '-'} | "
                     f"{_p(best) + ' (`' + best_run + '`)' if best is not None else '-'} |")

    lines += ["", "## Runs", "", "| Run | Target | Candidate | Open tracks | Check tracks | State | Outcome |", "|---|---|---|---|---|---|---|"]
    for r in reversed(all_runs):
        grade = r["grades"][-1] if r.get("grades") else None
        opens = ", ".join(f"{k} {_p(v)}" for k, v in (grade["open"] if grade else {}).items()) or "-"
        chk = r.get("check")
        checks = ", ".join(f"{k} {_p(v.get('candidate'))}" for k, v in chk["signals"].items()) if chk else "-"
        outcome = ""
        if r.get("decision"):
            outcome = f"{r['decision']['decision']} by the owner {r['decision']['date']}. {r['decision'].get('note', '')}".strip()
        elif r.get("verdict"):
            outcome = r["verdict"]["summary"]
        lines.append(f"| `{r['run']}` | {', '.join(r['signals'])} | {r.get('candidate') or '-'} | {opens} | {checks} | "
                     f"{STATE_TEXT.get(r['state'], r['state'])} | {outcome} |")
    lines += ["", "The work list is `BACKLOG.md`. A run that is \"waiting for the owner\" also appears in `research/INBOX.md`.", ""]
    dest = out_path or HERE / "STATUS.md"
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest


if __name__ == "__main__":
    print(f"wrote {write()}")
