"""Profile the clips already built: numbers, words and pictures for every version of every clip.

For each clip in research/choreography/output/clips/ this writes, in research/choreography/output/profiles/<clip>/:

    PROFILE.md               the description in words of each version, and the versions side by side in numbers
    profile.json             every number
    <version>_strip.png      time strip
    <version>_sheet.png      contact sheet
    <version>_reactions.png  reaction curves

Run from the repository root:
    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.profile_clip [clip ids...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from research.choreography import pictures
from research.choreography.layout import load_layout
from research.choreography.profile import describe, passage_truth, profile

HERE = Path(__file__).resolve().parent
CLIPS = HERE / "output" / "clips"
PROFILES = HERE / "output" / "profiles"
SIDE_BY_SIDE = (                                     # (label, path into the profile, format)
    ("Average brightness", ("light", "mean"), "pct"),
    ("Jump on a kick", ("reactions", "kick", "jump"), "pct"),
    ("Jump between two kicks", ("reactions", "between_kicks", "jump"), "pct"),
    ("Kick peak after the sound", ("reactions", "kick", "delay_ms"), "ms"),
    ("Jump on a snare", ("reactions", "snare", "jump"), "pct"),
    ("Jump on a drop", ("reactions", "drop", "jump"), "pct"),
    ("Movement in a break, against normal", ("stretches", "breakdown", "movement_ratio"), "pct"),
    ("Follows loudness", ("loudness", "corr"), "corr"),
    ("Bottom follows bass", ("space", "low_follows_bass"), "corr"),
    ("Top follows treble", ("space", "top_follows_treble"), "corr"),
    ("Fast flicker", ("comfort", "flicker"), "pct"),
    ("Bar-to-bar likeness", ("variety", "bar_to_bar_likeness"), "corr"),
)


def _get(d: Any, path: tuple) -> Any:
    for key in path:
        if not isinstance(d, dict) or d.get(key) is None:
            return None
        d = d[key]
    return d


def _fmt(v: Any, kind: str) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "-"
    return f"{100 * v:.0f}%" if kind == "pct" else f"{v:.0f} ms" if kind == "ms" else f"{v:.2f}"


def _clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (float, np.floating)):
        return None if obj != obj else round(float(obj), 4)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    return obj


def profile_clip(clip_id: str) -> Path:
    meta = json.loads((CLIPS / clip_id / "meta.json").read_text(encoding="utf-8"))
    layout = load_layout()
    fps = float(meta["fps"])
    truth = passage_truth(meta["track"]["id"], meta["start_s"], meta["duration_s"], fps)
    dest = PROFILES / clip_id
    dest.mkdir(parents=True, exist_ok=True)
    song = meta["track"]["file"].rsplit(".", 1)[0]
    profiles: Dict[str, dict] = {}
    for feed in meta["feeds"]:
        frames = np.fromfile(CLIPS / clip_id / feed["file"], dtype=np.uint8).reshape(feed["frames"], meta["leds"], 3)
        p = profile(frames, fps, layout, truth)
        p["words"] = describe(p)
        profiles[feed["key"]] = p
        title = f"{meta['mode']} · {song[:40]} from {meta['start_s']:.0f} s · {feed['label']}"
        pictures.time_strip(frames, layout, truth, fps, dest / f"{feed['key']}_strip.png", title)
        pictures.contact_sheet(frames, layout, pictures.choose_instants(frames, truth, fps), dest / f"{feed['key']}_sheet.png", title)
        pictures.reaction_plot(p["reactions"], fps, dest / f"{feed['key']}_reactions.png", title)

    lines: List[str] = [
        f"# Profile: `{meta['mode']}` on {song}, from {meta['start_s']:.0f} s for {meta['duration_s']:.0f} s", "",
        "What the light does on this passage, from the rendered frames and the truth of the passage. It says what the show",
        "does, not whether it is good. Percentages are shares of full brightness.", "",
        "## Side by side", "",
        "| | " + " | ".join(f["label"] for f in meta["feeds"]) + " |", "|---|" + "---|" * len(meta["feeds"]),
    ]
    for label, path, kind in SIDE_BY_SIDE:
        lines.append(f"| {label} | " + " | ".join(_fmt(_get(profiles[f["key"]], path), kind) for f in meta["feeds"]) + " |")
    for feed in meta["feeds"]:
        key = feed["key"]
        lines += ["", f"## {feed['label']}", "", f"*{feed['text']}.*", "", " ".join(profiles[key]["words"]), "",
                  f"![time strip]({key}_strip.png)", "", f"![reactions]({key}_reactions.png)", "", f"![contact sheet]({key}_sheet.png)"]
    (dest / "PROFILE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (dest / "profile.json").write_text(json.dumps(_clean({"clip": meta["id"], "profiles": profiles}), indent=1), encoding="utf-8")
    return dest


def main() -> None:
    ids = [a for a in sys.argv[1:] if not a.startswith("-")] or sorted(p.parent.name for p in CLIPS.glob("*/meta.json"))
    for clip_id in ids:
        print(f"wrote {profile_clip(clip_id)}", flush=True)


if __name__ == "__main__":
    main()
