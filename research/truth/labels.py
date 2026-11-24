"""Lay the owner's corrections (labels/<id>.json, written by the review tool) over the machine draft.

A layer the owner touched replaces the machine's layer whole. Inside it:
    an item with by == "owner" (placed or moved by ear)   -> level H
    any other item, when the layer is ticked "checked whole" -> level A
    any other item otherwise                               -> keeps the level the machine gave it
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from research.truth import meter

PIECES = ("kick", "snare", "hat", "tom", "cymbal")
ON_BEAT_S = 0.06


def _level(item: dict, reviewed: bool, default: str = "M1") -> str:
    if item.get("by") == "owner":
        return "H"
    return "A" if reviewed else item.get("lvl") or default


def apply_labels(truth: dict, labels: Optional[dict]) -> dict:
    """Replace every layer the owner touched. Returns the same truth dict, changed in place."""
    layers: Dict[str, dict] = (labels or {}).get("layers") or {}
    summary = {}
    for key, layer in layers.items():
        items: List[dict] = layer.get("items", [])
        reviewed = bool(layer.get("reviewed"))
        summary[key] = {"reviewed": reviewed, "by_owner": sum(1 for i in items if i.get("by") == "owner"), "items": len(items)}
        if key == "beats":
            truth["beats"] = [{
                "t": i["t"], "main": bool(i.get("main", True)), "level": _level(i, reviewed),
                "bar_pos": int(i.get("pos") or 0),
                "bar_pos_level": ("H" if i.get("posBy") == "owner" else "A" if reviewed else i.get("plvl")) if i.get("pos") else None,
                "strength": i.get("s"),
            } for i in sorted(items, key=lambda i: i["t"])]
        elif key in PIECES:
            truth.setdefault("drums", {}).setdefault("pieces", {})[key] = [
                [i["t"], i.get("s", 1.0), _level(i, reviewed)] for i in sorted(items, key=lambda i: i["t"])]
        elif key == "drop":
            truth["drops"] = [{"t": i["t"], "level": _level(i, reviewed)} for i in sorted(items, key=lambda i: i["t"])]
        elif key == "section":
            marks = sorted(items, key=lambda i: i["t"])
            truth["sections"] = {
                "level": "A" if reviewed else "W",
                "boundaries": [i["t"] for i in marks],
                "items": [{"t": i["t"], "level": _level(i, reviewed, "W")} for i in marks],
            }
        else:   # a kind of stretch: no_beat, kick_present, breakdown, buildup, riser, ..._present, silence
            truth["regions"][key] = [
                {"start": i["start"], "end": i["end"], "level": _level(i, reviewed),
                 "source": "owner" if i.get("by") == "owner" else "draft"}
                for i in sorted(items, key=lambda i: i["start"])]
    if summary:
        truth["status"] = "draft with the owner's corrections"
        truth["owner"] = {"saved": labels.get("saved"), "layers": summary}
    return truth


def finalize(truth: dict) -> dict:
    """Recompute what depends on several layers: beats inside no-beat stretches, tempo, drum pieces on each beat."""
    beats = truth["beats"]
    if not beats:
        return truth
    t = np.array([b["t"] for b in beats])
    spans = truth["regions"].get("no_beat", [])
    no_beat = np.array([any(r["start"] <= x < r["end"] for r in spans) for x in t], dtype=bool)
    main = np.array([b.get("main", True) for b in beats], dtype=bool)
    mi = np.flatnonzero(main)
    bpm = np.zeros(len(t))
    if len(mi):
        bpm[mi] = meter.local_bpm(t[mi], no_beat[mi])
    for i in range(1, len(bpm)):
        if not main[i]:
            bpm[i] = bpm[i - 1]
    pieces = {k: np.array([h[0] for h in v if h[2] != "W"]) for k, v in truth.get("drums", {}).get("pieces", {}).items()}
    for i, b in enumerate(beats):
        b["no_beat"] = bool(no_beat[i])
        b["bpm"] = round(float(bpm[i]), 1)
        if pieces:
            b["drums"] = [k for k, ts in pieces.items() if len(ts) and np.min(np.abs(ts - b["t"])) <= ON_BEAT_S]
        else:
            b.setdefault("drums", [])
    return truth
