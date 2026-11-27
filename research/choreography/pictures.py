"""Still pictures of a clip, so that an agent (or a person in a hurry) can see what a show does without playing it.

    time strip      time runs left to right, the LEDs top to bottom, segment by segment. A kick is a vertical
                    bright line, a front climbing a pillar is a diagonal, a break is a dim band. Truth marks on
                    top, overall brightness underneath.
    contact sheet   the installation drawn at chosen instants: on a kick, between two kicks, on the drop...
    reactions       the average brightness around a kick, a snare, a drop.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw

from research.choreography.layout import Layout
from research.choreography.render import brightness, screen_values

GUTTER, PX_PER_FRAME, LANE = 70, 2, 9
LANES = (("kick", (229, 72, 77)), ("snare", (245, 217, 10)), ("drop", (255, 255, 255)), ("section_change", (179, 136, 255)))
BANDS = (("breakdown", (76, 201, 240)), ("no_beat", (229, 72, 77)), ("silence", (107, 114, 128)))
PLOT_COLOURS = {"kick": (229, 72, 77), "between_kicks": (120, 128, 140), "snare": (245, 217, 10), "beat": (255, 209, 102),
                "drop": (255, 255, 255), "section_change": (179, 136, 255)}
TEXT, DIM, BG, PANEL = (230, 233, 238), (139, 148, 163), (11, 13, 17), (21, 25, 32)


def _display_order(layout: Layout) -> List[Tuple[str, np.ndarray]]:
    """Segments grouped as pillars, canopy, bridges; each pillar listed from its top LED down."""
    def group(seg) -> int:
        return 0 if seg.seg_id.startswith("v") else 1 if "tier:canopy" in seg.tags else 2

    rows = []
    for seg in sorted(layout.segments, key=lambda s: (group(s), s.seg_id)):
        idx = np.arange(seg.offset, seg.offset + seg.size)
        rows.append((seg.seg_id, idx[::-1] if seg.seg_id.startswith("v") else idx))
    return rows


def time_strip(frames: np.ndarray, layout: Layout, truth: Dict[str, Any], fps: float, path: Path, title: str = "") -> None:
    n_all = frames.shape[0]
    step = max(1, int(round(fps / 30.0)))                           # the strip is drawn at about 30 columns per second
    shown = screen_values(frames[::step])
    n, col_fps = shown.shape[0], fps / step
    width = GUTTER + n * PX_PER_FRAME + 6
    blocks, labels, y = [], [], 0
    for seg_id, idx in _display_order(layout):
        rows = shown[:, idx[::2]].transpose(1, 0, 2)                # (LED rows, columns, 3)
        blocks.append(rows)
        labels.append((seg_id, y + rows.shape[0] // 2))
        y += rows.shape[0] + 2
    top = 22 + (len(LANES) + len(BANDS)) * LANE + 4
    curve_h = 64
    height = top + y + curve_h + 22
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = BG
    yy = top
    for rows in blocks:
        img[yy : yy + rows.shape[0], GUTTER : GUTTER + n * PX_PER_FRAME] = np.repeat(rows, PX_PER_FRAME, axis=1)
        yy += rows.shape[0] + 2
    lane_y = 22
    lane_labels = []
    for name, colour in LANES:
        for t in truth["events"][name]:
            x = GUTTER + int(round(t * col_fps)) * PX_PER_FRAME
            if GUTTER <= x < width - 2:
                img[lane_y : lane_y + LANE - 2, x : x + 2] = colour
        lane_labels.append((name.replace("_", " "), lane_y, colour))
        lane_y += LANE
    for name, colour in BANDS:
        mask = truth["masks"][name][:n_all][::step][:n]
        on = np.repeat(mask, PX_PER_FRAME)
        img[lane_y + 1 : lane_y + LANE - 2, GUTTER : GUTTER + len(on)][:, on] = colour
        lane_labels.append((name.replace("_", " "), lane_y, colour))
        lane_y += LANE
    bright = brightness(frames)[::step][:n]
    base = top + y + curve_h
    for i, b in enumerate(bright):
        h = int(round(b * (curve_h - 4)))
        x = GUTTER + i * PX_PER_FRAME
        img[base - h : base, x : x + PX_PER_FRAME] = (200, 205, 215)

    pic = Image.fromarray(img)
    d = ImageDraw.Draw(pic)
    d.text((4, 4), title or "time strip", fill=TEXT)
    for name, ly, colour in lane_labels:
        d.text((2, ly - 2), name[:11], fill=colour)
    for seg_id, ly in labels:
        d.text((GUTTER - 30, top + ly - 5), seg_id, fill=DIM)
    d.text((2, base - curve_h + 2), "brightness", fill=DIM)
    for sec in range(0, int(n / col_fps) + 1):
        x = GUTTER + int(sec * col_fps) * PX_PER_FRAME
        d.line([(x, base + 2), (x, base + (7 if sec % 2 == 0 else 4))], fill=DIM)
        if sec % 2 == 0:
            d.text((x - 3, base + 8), str(sec), fill=DIM)
    d.text((width - 20, base + 8), "s", fill=DIM)
    pic.save(path)


def _draw_installation(frame: np.ndarray, layout: Layout, w: int = 446, h: int = 256) -> np.ndarray:
    tile = np.zeros((h, w, 3), dtype=np.uint8)
    frame = screen_values(frame)
    xs = (4 + layout.xy[:, 0] * (w - 10) / 431.0).astype(int)
    ys = (4 + layout.xy[:, 1] * (h - 10) / 245.0).astype(int)
    for dx in range(3):
        for dy in range(3):
            np.maximum.at(tile, (np.clip(ys + dy - 1, 0, h - 1), np.clip(xs + dx - 1, 0, w - 1)), frame)
    return tile


def choose_instants(frames: np.ndarray, truth: Dict[str, Any], fps: float) -> List[Tuple[str, int]]:
    """Frames worth looking at: a kick, the gap after it, a snare, the drop, the break, the brightest and dimmest moments."""
    n = frames.shape[0]
    bright = brightness(frames)
    out: List[Tuple[str, int]] = []
    drops = list(truth["events"]["drop"])
    kicks = [k for k in truth["events"]["kick"] if 0.3 <= k < n / fps - 0.6 and all(abs(k - d) > 2.0 for d in drops)]
    if kicks:
        k = kicks[(2 * len(kicks)) // 3]          # a kick well inside a kick stretch, away from any drop
        later = [x for x in truth["events"]["kick"] if x > k + 0.2]
        out.append((f"on a kick ({k:.2f} s)", int(round((k + 0.04) * fps))))
        if later:
            out.append((f"between two kicks ({(k + later[0]) / 2:.2f} s)", int(round((k + later[0]) / 2 * fps))))
    for name, label in (("snare", "on a snare"), ("drop", "on the drop")):
        ev = [t for t in truth["events"][name] if 0.2 <= t < n / fps - 0.3]
        if ev:
            out.append((f"{label} ({ev[len(ev) // 2 if name == 'snare' else 0]:.2f} s)", int(round((ev[len(ev) // 2 if name == "snare" else 0] + 0.04) * fps))))
    brk = np.flatnonzero(truth["masks"]["breakdown"][:n])
    if len(brk):
        out.append((f"in the break ({brk[len(brk) // 2] / fps:.2f} s)", int(brk[len(brk) // 2])))
    out.append((f"brightest moment ({int(np.argmax(bright)) / fps:.2f} s)", int(np.argmax(bright))))
    out.append((f"dimmest moment ({int(np.argmin(bright)) / fps:.2f} s)", int(np.argmin(bright))))
    return [(label, min(n - 1, max(0, i))) for label, i in out]


def contact_sheet(frames: np.ndarray, layout: Layout, instants: Sequence[Tuple[str, int]], path: Path, title: str = "") -> None:
    cols = 3
    rows = (len(instants) + cols - 1) // cols
    tw, th, pad, head = 446, 256, 8, 18
    sheet = np.zeros((24 + rows * (th + head + pad), pad + cols * (tw + pad), 3), dtype=np.uint8)
    sheet[:] = BG
    places = []
    for k, (label, i) in enumerate(instants):
        x, y = pad + (k % cols) * (tw + pad), 24 + (k // cols) * (th + head + pad)
        sheet[y + head : y + head + th, x : x + tw] = _draw_installation(frames[i], layout, tw, th)
        places.append((label, x, y))
    pic = Image.fromarray(sheet)
    d = ImageDraw.Draw(pic)
    d.text((pad, 5), title or "contact sheet", fill=TEXT)
    for label, x, y in places:
        d.text((x + 2, y + 3), label, fill=DIM)
    pic.save(path)


def _plot(d: ImageDraw.ImageDraw, box: Tuple[int, int, int, int], curves: Dict[str, Dict[str, Any]], fps: float, heading: str) -> None:
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=PANEL)
    d.text((x0 + 6, y0 + 4), heading, fill=TEXT)
    if not curves:
        d.text((x0 + 6, y0 + 24), "no such event in this passage", fill=DIM)
        return
    top = max(0.05, max(max(c["curve"]) for c in curves.values()) * 1.1)
    before = next(iter(curves.values()))["before_s"]
    length = max(len(c["curve"]) for c in curves.values())
    px0, px1, py0, py1 = x0 + 40, x1 - 10, y0 + 24, y1 - 22

    def pt(i: int, v: float) -> Tuple[float, float]:
        return px0 + (px1 - px0) * i / max(1, length - 1), py1 - (py1 - py0) * min(1.0, v / top)

    zero = px0 + (px1 - px0) * (before * fps) / max(1, length - 1)
    d.line([(zero, py0), (zero, py1)], fill=DIM)
    d.text((zero - 14, py1 + 4), "sound", fill=DIM)
    d.text((px0, py1 + 4), f"-{before:.1f} s", fill=DIM)
    d.text((px1 - 34, py1 + 4), f"+{(length - 1) / fps - before:.1f} s", fill=DIM)
    d.text((x0 + 4, py0 - 2), f"{100 * top:.0f}%", fill=DIM)
    d.text((x0 + 4, py1 - 10), "0%", fill=DIM)
    d.line([(px0, py1), (px1, py1)], fill=DIM)
    lx = x0 + 18 + int(6.4 * len(heading))
    for name, c in curves.items():
        colour = PLOT_COLOURS.get(name, TEXT)
        d.line([pt(i, v) for i, v in enumerate(c["curve"])], fill=colour, width=2)
        label = f"{name.replace('_', ' ')} ({c['events']})"
        d.text((lx, y0 + 4), label, fill=colour)
        lx += 12 + 7 * len(label)


def reaction_plot(reactions: Dict[str, Any], fps: float, path: Path, title: str = "") -> None:
    pic = Image.new("RGB", (1000, 330), BG)
    d = ImageDraw.Draw(pic)
    d.text((8, 5), title or "reactions", fill=TEXT)
    short = {k: reactions[k] for k in ("kick", "between_kicks", "snare", "beat") if reactions.get(k)}
    wide = {k: reactions[k] for k in ("drop", "section_change") if reactions.get(k)}
    _plot(d, (8, 24, 496, 322), short, fps, "brightness around a hit")
    _plot(d, (504, 24, 992, 322), wide, fps, "around a drop or a section change")
    pic.save(path)
