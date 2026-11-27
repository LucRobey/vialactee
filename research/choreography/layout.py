"""The installation as the lab draws it: the 11 segments, their LEDs and where each LED sits in the room.

Read from config/segments_full.json (the same file the installation uses). Room coordinates are in the
configuration's own units: x from 0 (left) to 431, y from 0 (top) to 245.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, NamedTuple

import numpy as np

REPO = Path(__file__).resolve().parents[2]
SEGMENTS_FILE = REPO / "config" / "segments_full.json"


class SegmentLayout(NamedTuple):
    seg_id: str
    name: str          # the name a mode receives ("Segment v1")
    size: int          # number of LEDs
    offset: int        # index of its first LED in the whole-installation frame
    orientation: str
    tags: tuple


class Layout(NamedTuple):
    segments: List[SegmentLayout]
    xy: np.ndarray     # (total LEDs, 2) room coordinates
    total: int


def load_layout(path: Path = SEGMENTS_FILE) -> Layout:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    raw = sorted((s for key, group in cfg.items() if key.startswith("segs_") for s in group), key=lambda s: s.get("order", 0))
    segments: List[SegmentLayout] = []
    coords = []
    offset = 0
    for s in raw:
        n = int(s["size"])
        idx = np.arange(n, dtype=np.float64)
        coords.append(np.stack([s["start"]["x"] + idx * s["step"]["x"], s["start"]["y"] + idx * s["step"]["y"]], axis=1))
        segments.append(SegmentLayout(s["id"], s.get("name", f"Segment {s['id']}"), n, offset, s.get("orientation", ""), tuple(s.get("tags", ()))))
        offset += n
    return Layout(segments, np.concatenate(coords, axis=0), offset)
