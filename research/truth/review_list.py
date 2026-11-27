"""Where the owner's ear is most useful: a short list for the review tool.

    python -m research.truth.review_list

Writes research/truth/REVIEW_LIST.md from the truth files: for each song, the proposals of the four lanes that
no tool can settle (drop, build-up, no beat, section change), with their times, and whether the owner has
already checked the lane. Songs with the most to check come first.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

HERE = Path(__file__).resolve().parent
TRACKS = HERE / "tracks"
OWNER_LEVELS = ("H", "A")


def _mmss(t: float) -> str:
    return f"{int(t) // 60}:{int(t % 60):02d}"


LAYER = {"Drop": "drop", "Build-up": "buildup", "No beat": "no_beat", "sections": "section"}


def song(truth: dict) -> dict:
    r = truth["regions"]
    ticked = {k for k, v in ((truth.get("owner") or {}).get("layers") or {}).items() if v.get("reviewed")}

    def _done(items: List[dict], name: str = "") -> bool:
        """Checked: the owner ticked the lane (even an empty one), or every mark carries the owner's level."""
        return LAYER.get(name) in ticked or (bool(items) and all(i.get("level") in OWNER_LEVELS for i in items))

    lanes = {
        "Drop": [(_mmss(d["t"]) + ("?" if d.get("level") == "W" else ""), d) for d in truth.get("drops", [])],
        "Build-up": [(f"{_mmss(b['start'])}-{_mmss(b['end'])}", b) for b in r.get("buildup", [])],
        "No beat": [(f"{_mmss(b['start'])}-{_mmss(b['end'])}", b) for b in r.get("no_beat", [])],
    }
    sections = truth["sections"]["items"]
    todo = sum(len(v) for k, v in lanes.items() if not _done([i for _, i in v], k))
    return {"id": truth["track"]["id"], "name": truth["track"]["file"].rsplit(".", 1)[0][:34], "group": truth["track"].get("group") or "",
            "lanes": {k: ([label for label, _ in v], _done([i for _, i in v], k)) for k, v in lanes.items()},
            "sections": (len(sections), _done(sections, "sections")), "todo": todo}


def build(truths: List[dict]) -> str:
    songs = sorted((song(t) for t in truths), key=lambda s: -s["todo"])
    lines = ["# Review list: where your ear is most useful", "",
             "Built by `python -m research.truth.review_list`. Open the review tool (`truth-review`, http://127.0.0.1:8766), pick the song, "
             "and go through the lanes below. A time followed by `?` is only a possible drop. \"checked\" means every mark of the lane "
             "is yours or was accepted by you.", "",
             "For each lane: delete what is wrong, move what is late or early, add what is missing, then tick \"checked whole\" for the lane. "
             "A lane with nothing in it and nothing to add needs no tick.", "",
             "| # | Song | Drop | Build-up | No beat | Section changes |", "|---|---|---|---|---|---|"]
    for s in songs:
        cells = []
        for name in ("Drop", "Build-up", "No beat"):
            labels, done = s["lanes"][name]
            cells.append("checked" if done else (", ".join(labels) if labels else "none proposed"))
        n, done = s["sections"]
        cells.append("checked" if done else f"{n} proposed")
        lines.append(f"| {s['id']} | {s['name']} ({s['group']}) | " + " | ".join(cells) + " |")
    lines += ["", "The build-ups and the drops marked `?` are weak guesses (`research/truth/buildups.py`): expect many to be wrong. "
              "Nothing in these four lanes is used to grade the analyzer reliably until you have checked it.", ""]
    return "\n".join(lines)


def write(path: Path = HERE / "REVIEW_LIST.md") -> Path:
    truths = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(TRACKS.glob("*.json"))]
    path.write_text(build(truths), encoding="utf-8")
    return path


if __name__ == "__main__":
    print(f"wrote {write()}")
