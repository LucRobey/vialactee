"""The owner's inbox: one page with everything the two labs are waiting on the owner for.

    python -m research.inbox

Writes research/INBOX.md. It only reads small committed files, so it needs no lab environment:

- music lab: every run under research/scoreboard/runs/ whose proposal has no answer (run.json, state "proposed");
- choreography lab: every clip of research/choreography/queue.json that no line of verdicts.jsonl names yet;
- standing questions: research/OWNER_QUESTIONS.md, kept by hand (decisions only the owner can take).

The labs rebuild it when something is proposed, nominated or decided. It belongs to neither lab and imports neither.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).resolve().parent
RUNS = HERE / "scoreboard" / "runs"
QUEUE = HERE / "choreography" / "queue.json"
VERDICTS = HERE / "choreography" / "verdicts.jsonl"
QUESTIONS = HERE / "OWNER_QUESTIONS.md"
INBOX = HERE / "INBOX.md"


def music_runs(runs_dir: Path = RUNS) -> List[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(runs_dir.glob("*/run.json"))]


def waiting_clips(queue_path: Path = QUEUE, verdicts_path: Path = VERDICTS) -> List[dict]:
    queue = json.loads(queue_path.read_text(encoding="utf-8")) if queue_path.exists() else []
    judged = set()
    if verdicts_path.exists():
        for line in verdicts_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                judged.add(json.loads(line).get("clip"))
    return [e for e in queue if e["clip"] not in judged]


def _p(x: Optional[float]) -> str:
    return "-" if x is None else f"{100 * x:.0f}"


def build(runs: List[dict], clips: List[dict], questions: str, today: str) -> str:
    proposed = [r for r in runs if r["state"] == "proposed"]
    lines = ["# Waiting for you", "",
             f"Built {today} by `python -m research.inbox`. Do not edit by hand.", "",
             f"**{len(proposed)} proposal(s) to answer, {len(clips)} clip(s) to watch.**", "",
             "## Music lab: proposals waiting for your yes or no", ""]
    if not proposed:
        lines.append("Nothing is waiting.")
    for r in proposed:
        chk = (r.get("check") or {}).get("signals", {})
        scores = ", ".join(f"{name} {_p(v.get('candidate'))} "
                           + ("(a new signal)" if v.get("production") is None else f"(today {_p(v.get('production'))})") for name, v in chk.items())
        lines += [f"- **{', '.join(r['signals'])}** (run `{r['run']}`, {r['verdict']['date']}): {r['verdict']['summary']}",
                  f"  - On the tracks nobody tuned on: {scores}.",
                  f"  - Read [`PROPOSAL.md`](scoreboard/runs/{r['run']}/PROPOSAL.md), then answer yes or no."]
    lines += ["", "## Choreography lab: clips waiting for your choice", ""]
    if not clips:
        lines.append("Nothing is waiting.")
    else:
        lines += ["Start the clip page (`choreography-clips`, http://127.0.0.1:8768): the waiting clips come first.", ""]
        for e in clips:
            what = f"`{e['mode']}` against `{e['against']}`" if e.get("against") else f"`{e['mode']}`, its versions"
            note = f": {e['note']}" if e.get("note") else ""
            lines.append(f"- {what}, track {e['track']} from {int(e['start_s'])} s (nominated {e['nominated']}){note}")
    lines += ["", "## Standing questions", ""]
    lines.append(questions.strip() if questions.strip() else "None.")
    done = [r for r in runs if r["state"] in ("decided", "archived")][-5:]
    lines += ["", "## Recently closed", ""]
    if not done:
        lines.append("Nothing yet.")
    for r in reversed(done):
        if r.get("decision"):
            end = f"{r['decision']['decision']} by you on {r['decision']['date']}"
        else:
            end = f"dropped by the lab: {r['verdict']['summary']}"
        lines.append(f"- `{r['run']}` ({', '.join(r['signals'])}): {end}")
    lines += ["", "Where everything stands: [`scoreboard/STATUS.md`](scoreboard/STATUS.md) (signals) and "
              "[`choreography/STATUS.md`](choreography/STATUS.md) (modes).", ""]
    return "\n".join(lines)


def write(path: Path = INBOX) -> Path:
    questions = QUESTIONS.read_text(encoding="utf-8") if QUESTIONS.exists() else ""
    questions = "\n".join(l for l in questions.splitlines() if l.startswith(("- ", "  ")))     # the questions, not the file's own notes
    path.write_text(build(music_runs(), waiting_clips(), questions, datetime.date.today().isoformat()), encoding="utf-8")
    return path


if __name__ == "__main__":
    print(f"wrote {write()}")
