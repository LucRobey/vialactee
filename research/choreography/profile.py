"""Profile of a mode on a passage: what the light does, in numbers and in words.

An agent cannot watch a clip. This turns the rendered frames of a passage, together with the truth of that
passage, into numbers an agent can read: how much light, how it reacts to a kick, a snare, a drop, what it does
in a break, where the light sits, which colours, how much flicker, how much it repeats. `describe` then says
the same in plain sentences.

It says what a show does, not whether it is beautiful: that stays the owner's choice between clips.

Brightness is always the brightness the eye sees (render.perceived), except for flash safety, which the
standard defines on the light itself.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from research.choreography.feeds import FPS as FEED_FPS, truth_feed
from research.choreography.layout import Layout
from research.choreography.render import perceived

HUES = ("red", "orange", "yellow", "lime", "green", "teal", "cyan", "azure", "blue", "violet", "magenta", "rose")
DARK: float = 0.02
EVENTS = ("kick", "snare", "beat", "drop", "section_change")
WIDE = {"drop": (1.0, 2.0), "section_change": (1.0, 2.0)}      # (seconds before, after); others: 0.3 and 0.6
ROOM_HEIGHT: float = 245.0
FLASH_SWING: float = 0.10          # W3C WCAG 2.3.1: a flash is a pair of opposing changes of 10% or more of full light
FLASH_DARK_BELOW: float = 0.80     # ...where the darker state is under 80% of full light
FLASH_LIMIT: int = 3               # no more than three flashes within any one second
SEEN_RISE: float = 0.05            # a rise of perceived brightness this large within 0.1 s is a flash the eye notices
MATCH_EARLY_S, MATCH_LATE_S = 0.08, 0.12     # a flash belongs to a hit if it starts this close before or after it


def passage_truth(track_id: str, start_s: float, duration_s: float, fps: float) -> Dict[str, Any]:
    """The truth of one passage, on the clip's own clock: event times, yes/no masks and levels per frame."""
    feed = truth_feed(track_id)
    a, n = int(round(start_s * FEED_FPS)), int(round(duration_s * FEED_FPS))
    step = int(round(FEED_FPS / fps))
    cut = {k: v[a : a + n] for k, v in feed.columns.items()}
    events = {name: np.flatnonzero(cut[name] > 0) / FEED_FPS for name in EVENTS}
    bars = np.flatnonzero((cut["beat"] > 0) & (cut["bar_position"] == 1)) / FEED_FPS
    masks = {name: cut[name][::step] > 0 for name in ("no_beat", "breakdown", "silence", "kick_present", "buildup")}
    levels = {name: cut[name][::step].astype(float) for name in ("loudness", "band_bass", "band_mid", "band_high")}
    return {"events": events, "bars": bars, "masks": masks, "levels": levels}


def luminance(frames: np.ndarray) -> np.ndarray:
    """How bright every LED looks on every frame, 0..1 (perceived brightness of its strongest colour channel)."""
    lut = perceived(np.arange(256) / 255.0).astype(np.float32)
    return lut[frames.max(axis=2)]


def light(frames: np.ndarray) -> np.ndarray:
    """Light given off by every LED on every frame, 0..1 (relative luminance of the drive values, not perception)."""
    f = frames.astype(np.float32)
    return (0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]) / 255.0


def flashes_per_second(curve: np.ndarray, fps: float) -> float:
    """Largest number of flashes in any one second: opposing swings of FLASH_SWING or more, counted in pairs."""
    turns: List[int] = []
    lo = hi = float(curve[0])
    direction = 0
    for i, v in enumerate(curve):
        v = float(v)
        if direction >= 0 and v <= hi - FLASH_SWING and v < FLASH_DARK_BELOW:        # was rising or flat, now fell
            turns.append(i)
            direction, lo = -1, v
        elif direction <= 0 and v >= lo + FLASH_SWING and lo < FLASH_DARK_BELOW:     # was falling or flat, now rose
            turns.append(i)
            direction, hi = 1, v
        if direction >= 0:
            hi = max(hi, v)
        if direction <= 0:
            lo = min(lo, v)
    if not turns:
        return 0.0
    t = np.array(turns) / fps
    most = max(int(np.searchsorted(t, x + 1.0, side="left") - k) for k, x in enumerate(t))
    return most / 2.0


def seen_flashes(bright: np.ndarray, fps: float) -> np.ndarray:
    """Instants where the installation visibly jumps brighter: starts of rises of SEEN_RISE or more within 0.1 s."""
    w = max(1, int(round(0.1 * fps)))
    rise = np.zeros(len(bright))
    rise[:-w] = bright[w:] - bright[:-w]
    out: List[float] = []
    i = 0
    while i < len(rise):
        if rise[i] >= SEEN_RISE:
            j = i
            while j + 1 < len(rise) and rise[j + 1] >= SEEN_RISE:
                j += 1
            out.append((i + int(np.argmax(np.diff(bright[i : j + w + 1])) if j + w + 1 - i > 1 else 0)) / fps)
            i = j + w
        else:
            i += 1
    return np.array(out)


def match_flashes(flashes: np.ndarray, hits: np.ndarray) -> Dict[str, float]:
    """How the flashes line up with the true hits: hits that get a flash, flashes that have a hit."""
    hits = np.sort(np.asarray(hits, dtype=float))
    used = np.zeros(len(flashes), dtype=bool)
    served = 0
    for h in hits:
        cand = np.flatnonzero((flashes >= h - MATCH_EARLY_S) & (flashes <= h + MATCH_LATE_S) & ~used)
        if len(cand):
            used[cand[np.argmin(np.abs(flashes[cand] - h))]] = True
            served += 1
    return {"flashes": int(len(flashes)), "hits": int(len(hits)),
            "hits_with_a_flash": served / len(hits) if len(hits) else float("nan"),
            "flashes_with_a_hit": float(used.mean()) if len(flashes) else float("nan"),
            "false_flashes": int((~used).sum())}


def reaction(bright: np.ndarray, fps: float, times: Sequence[float], before: float = 0.3, after: float = 0.6,
             min_events: int = 3) -> Optional[Dict[str, Any]]:
    """Average brightness around a kind of event: how high the light jumps, how late, how fast it fades."""
    pre, post = int(round(before * fps)), int(round(after * fps))
    rows = []
    for t in times:
        i = int(round(t * fps))
        if i - pre >= 0 and i + post < len(bright):
            rows.append(bright[i - pre : i + post + 1])
    if len(rows) < min_events:
        return None
    curve = np.mean(rows, axis=0)
    base = float(curve[max(0, pre - max(1, int(0.2 * fps))) : pre].mean())
    win = curve[pre : pre + int(round(0.2 * fps)) + 1]
    k = int(np.argmax(win))
    peak = float(win[k])
    jump = peak - base
    half = None
    if jump > 0.01:
        below = np.flatnonzero(curve[pre + k :] < base + jump / 2.0)
        half = float(below[0] / fps * 1000.0) if len(below) else None
    rise = None
    if jump > 0.01:                      # when the light is halfway up: read between two frames, may be before the sound
        level = base + jump / 2.0
        for i in range(pre + k, 0, -1):
            if curve[i - 1] < level <= curve[i]:
                rise = float(((i - 1) + (level - curve[i - 1]) / (curve[i] - curve[i - 1]) - pre) / fps * 1000.0)
                break
    return {"events": len(rows), "jump": jump, "base": base, "peak": peak, "delay_ms": 1000.0 * k / fps, "half_rise_ms": rise,
            "half_life_ms": half, "before_s": before, "curve": [round(float(x), 4) for x in curve]}


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    if n < 10 or np.std(a) < 1e-6 or np.std(b) < 1e-6:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def _best_corr(a: np.ndarray, b: np.ndarray, fps: float, max_lag: float = 0.5) -> Dict[str, float]:
    best, lag_at = float("nan"), 0
    n = min(len(a), len(b))
    for lag in range(-int(max_lag * fps), int(max_lag * fps) + 1):
        c = _corr(a[max(0, lag) : n + min(0, lag)], b[max(0, -lag) : n - max(0, lag)])
        if c == c and (best != best or c > best):
            best, lag_at = c, lag
    return {"corr": best, "lag_ms": 1000.0 * lag_at / fps}


def _smooth(x: np.ndarray, frames: int) -> np.ndarray:
    k = max(1, frames | 1)
    return np.convolve(np.pad(x, k // 2, mode="edge"), np.ones(k) / k, mode="valid")


def _stretch(bright: np.ndarray, pulse: np.ndarray, mask: np.ndarray) -> Optional[Dict[str, float]]:
    """Brightness and movement inside a kind of stretch, against outside it."""
    m = mask[: len(bright)]
    if m.mean() < 0.08 or m.mean() > 0.92:
        return None
    return {"share_of_passage": float(m.mean()), "brightness_in": float(bright[m].mean()), "brightness_out": float(bright[~m].mean()),
            "movement_in": float(pulse[m].mean()), "movement_out": float(pulse[~m].mean()),
            "movement_ratio": float(pulse[m].mean() / max(1e-6, pulse[~m].mean()))}


def _colours(frames: np.ndarray, lum: np.ndarray) -> Dict[str, Any]:
    sub = frames[::3].astype(np.float32) / 255.0
    w = lum[::3]
    mx, mn = sub.max(axis=2), sub.min(axis=2)
    lit = w > 0.08
    if not lit.any():
        return {"hues": {}, "dominant": [], "saturation": float("nan"), "white_share": float("nan")}
    d = mx - mn
    r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
    safe = np.where(d > 1e-6, d, 1.0)
    hue = np.where(mx == r, ((g - b) / safe) % 6.0, np.where(mx == g, (b - r) / safe + 2.0, (r - g) / safe + 4.0)) / 6.0
    sat = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    coloured = lit & (sat >= 0.15)
    total = float(w[lit].sum())
    bins = np.floor(((hue + 1.0 / 24.0) % 1.0) * 12.0).astype(int) % 12
    shares = np.bincount(bins[coloured], weights=w[coloured], minlength=12) / max(1e-9, total)
    order = np.argsort(-shares)
    return {"hues": {HUES[i]: round(float(shares[i]), 3) for i in order if shares[i] >= 0.02},
            "dominant": [HUES[i] for i in order if shares[i] >= 0.12],
            "saturation": float((sat[lit] * w[lit]).sum() / total),
            "white_share": float(w[lit & (sat < 0.15)].sum() / total)}


def profile(frames: np.ndarray, fps: float, layout: Layout, truth: Dict[str, Any]) -> Dict[str, Any]:
    """Every number of the profile for one rendered passage."""
    lum = luminance(frames)
    bright = lum.mean(axis=1)
    n = len(bright)
    silence = truth["masks"]["silence"][:n] if len(truth["masks"]["silence"]) >= n else np.zeros(n, dtype=bool)
    heard = ~silence
    pulse = np.abs(bright - _smooth(bright, int(0.5 * fps)))

    out: Dict[str, Any] = {"seconds": n / fps}
    led_low, led_high = np.percentile(lum[::2], (5, 95), axis=0)        # each LED's own dim and bright moments
    out["light"] = {
        # how far a typical LED travels: a show that moves in space at a constant total light still counts as moving
        "led_swing": float(np.mean(led_high - led_low)),
        "mean": float(bright.mean()), "low": float(np.percentile(bright, 5)), "high": float(np.percentile(bright, 95)),
        "dark_share": float(np.mean(bright[heard] < DARK)) if heard.any() else float("nan"),
        "full_share": float(np.mean(bright > 0.85)),
    }
    out["loudness"] = _best_corr(bright, truth["levels"]["loudness"], fps)

    reactions: Dict[str, Any] = {}
    for name in EVENTS:
        before, after = WIDE.get(name, (0.3, 0.6))
        reactions[name] = reaction(bright, fps, truth["events"][name], before, after, min_events=1 if name in WIDE else 3)
    kicks = np.sort(truth["events"]["kick"])
    between = [(a + b) / 2.0 for a, b in zip(kicks[:-1], kicks[1:]) if 0.25 < b - a < 2.0]
    off = reaction(bright, fps, between)
    reactions["between_kicks"] = off
    out["reactions"] = reactions
    out["kick_contrast"] = (reactions["kick"]["jump"] - off["jump"]) if reactions["kick"] and off else float("nan")

    flashes = seen_flashes(bright, fps)
    hits = np.concatenate([truth["events"][k] for k in ("kick", "snare", "drop")])
    out["flashes"] = match_flashes(flashes, hits)
    quiet = truth["masks"]["breakdown"][:n] | truth["masks"]["no_beat"][:n]
    in_quiet = quiet[np.clip(np.round(flashes * fps).astype(int), 0, n - 1)] if len(flashes) else np.zeros(0, dtype=bool)
    out["flashes"]["per_second_in_breaks"] = float(in_quiet.sum() / (quiet.sum() / fps)) if quiet.sum() > fps else None

    emitted = light(frames)
    zones_light = {"whole installation": emitted.mean(axis=1)}
    out["stretches"] = {name: _stretch(bright, pulse, truth["masks"][name]) for name in ("breakdown", "no_beat")}
    out["in_silence"] = float(bright[silence].mean()) if silence.any() else None

    alt = 1.0 - layout.xy[:, 1] / ROOM_HEIGHT
    low, top = alt < 1.0 / 3.0, alt > 2.0 / 3.0
    mid = ~low & ~top
    zone = {"low": lum[:, low].mean(axis=1), "mid": lum[:, mid].mean(axis=1), "top": lum[:, top].mean(axis=1)}
    zones_light.update({"the bottom third": emitted[:, low].mean(axis=1), "the middle third": emitted[:, mid].mean(axis=1),
                        "the top third": emitted[:, top].mean(axis=1)})
    worst = max(zones_light, key=lambda k: flashes_per_second(zones_light[k], fps))
    most = flashes_per_second(zones_light[worst], fps)
    out["safety"] = {"flashes_per_second_max": most, "where": worst, "limit": FLASH_LIMIT, "passes": bool(most <= FLASH_LIMIT),
                     "note": "general flashes only (WCAG 2.3.1); saturated red flashes are not checked"}
    total = max(1e-9, float(lum.sum()))
    roles = {"pillars": [s for s in layout.segments if s.seg_id.startswith("v")],
             "canopy": [s for s in layout.segments if "tier:canopy" in s.tags],
             "bridges": [s for s in layout.segments if not s.seg_id.startswith("v") and "tier:canopy" not in s.tags]}
    seg_curves = np.stack([lum[:, s.offset : s.offset + s.size].mean(axis=1) for s in layout.segments])
    pair = [_corr(seg_curves[i], seg_curves[j]) for i in range(len(seg_curves)) for j in range(i + 1, len(seg_curves))]
    pair = [c for c in pair if c == c]
    out["space"] = {
        "share_by_height": {k: float(lum[:, m].sum() / total) for k, m in (("low", low), ("mid", mid), ("top", top))},
        "share_by_role": {k: float(sum(lum[:, s.offset : s.offset + s.size].sum() for s in segs) / total) for k, segs in roles.items()},
        "low_follows_bass": _corr(zone["low"], truth["levels"]["band_bass"]),
        "top_follows_treble": _corr(zone["top"], truth["levels"]["band_high"]),
        "low_follows_treble": _corr(zone["low"], truth["levels"]["band_high"]),
        "top_follows_bass": _corr(zone["top"], truth["levels"]["band_bass"]),
        "segments_together": float(np.mean(pair)) if pair else float("nan"),
    }
    out["colour"] = _colours(frames, lum)

    spec = np.abs(np.fft.rfft(bright - bright.mean())) ** 2
    freqs = np.fft.rfftfreq(n, 1.0 / fps)
    out["comfort"] = {"flicker": float(spec[freqs >= 8.0].sum() / max(1e-12, spec[1:].sum())),
                      "biggest_jump": float(np.max(np.abs(np.diff(bright)))) if n > 1 else 0.0}

    bars = [b for b in truth["bars"] if b >= 0]
    shapes = []
    for a, b in zip(bars[:-1], bars[1:]):
        i0, i1 = int(a * fps), int(b * fps)
        if i1 - i0 >= 8 and i1 <= n:
            shapes.append(np.interp(np.linspace(0, 1, 16, endpoint=False), np.linspace(0, 1, i1 - i0, endpoint=False), bright[i0:i1]))
    same = [_corr(x, y) for x, y in zip(shapes[:-1], shapes[1:])]
    same = [c for c in same if c == c]
    out["variety"] = {"bars": len(shapes), "bar_to_bar_likeness": float(np.mean(same)) if len(same) >= 3 else float("nan")}
    return out


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def _hit_sentence(name: str, r: Optional[Dict[str, Any]]) -> str:
    if r is None:
        return f"Too few {name}s in this passage to say how it reacts to them."
    if r["jump"] < 0.03:
        return f"Does not react to the {name} (brightness moves {_pct(max(0.0, r['jump']))} of full)."
    how = "Punches on" if r["jump"] >= 0.08 else "Reacts weakly to"
    fade = f", half gone after {r['half_life_ms']:.0f} ms" if r["half_life_ms"] is not None else ", and stays up"
    rise = r.get("half_rise_ms")
    when = (f"halfway up {abs(rise):.0f} ms {'after' if rise >= 0 else 'before'} the sound" if rise is not None
            else f"peak {r['delay_ms']:.0f} ms after the sound")
    return f"{how} the {name}: +{_pct(r['jump'])} of full brightness, {when}{fade}."


def describe(p: Dict[str, Any]) -> List[str]:
    """The profile as plain sentences."""
    s: List[str] = []
    light = p["light"]
    word = "Dim" if light["mean"] < 0.08 else "Medium bright" if light["mean"] < 0.25 else "Bright"
    s.append(f"{word}: {_pct(light['mean'])} of full on average, moving between {_pct(light['low'])} and {_pct(light['high'])}.")
    if light["dark_share"] == light["dark_share"] and light["dark_share"] > 0.15:
        s.append(f"Dark {_pct(light['dark_share'])} of the time while music plays.")
    c = p["loudness"]["corr"]
    if c == c:
        s.append("Follows the loudness of the music closely." if c > 0.6 else "Follows the loudness loosely." if c > 0.3
                 else "Does not follow the loudness of the music.")
    r = p["reactions"]
    s.append(_hit_sentence("kick", r["kick"]))
    if r["kick"] and r["between_kicks"] and r["kick"]["jump"] >= 0.03 and r["between_kicks"]["jump"] > 0.6 * r["kick"]["jump"]:
        s.append(f"But it jumps almost as much between two kicks (+{_pct(r['between_kicks']['jump'])}): the punch is not tied to the kick.")
    s.append(_hit_sentence("snare", r["snare"]))
    fl = p["flashes"]
    if fl["flashes"] and fl["hits"]:
        s.append(f"Of its {fl['flashes']} visible flashes, {_pct(fl['flashes_with_a_hit'])} fall on a real kick, snare or drop "
                 f"({fl['false_flashes']} do not); {_pct(fl['hits_with_a_flash'])} of the real hits get a flash.")
    if fl.get("per_second_in_breaks"):
        s.append(f"Flashes {fl['per_second_in_breaks']:.1f} times a second during breaks, where nothing hits.")
    if r["drop"]:
        s.append(f"On a drop: {'+' if r['drop']['jump'] >= 0 else ''}{_pct(r['drop']['jump'])} of full brightness." if abs(r["drop"]["jump"]) >= 0.03
                 else "Does nothing special on a drop.")
    for name, label in (("breakdown", "a break (kick gone)"), ("no_beat", "a stretch with no beat")):
        st = p["stretches"][name]
        if st is None:
            continue
        ratio = st["movement_ratio"]
        move = "keeps pulsing as before" if ratio > 0.7 else "calms down" if ratio > 0.3 else "goes almost still"
        s.append(f"In {label} it {move} (movement {_pct(ratio)} of normal) at {_pct(st['brightness_in'])} brightness "
                 f"against {_pct(st['brightness_out'])} outside.")
    if p["in_silence"] is not None:
        s.append("Goes dark in silence." if p["in_silence"] < 0.03 else f"Still lit in silence ({_pct(p['in_silence'])}).")
    sp = p["space"]
    h = sp["share_by_height"]
    where = max(h, key=h.get)
    s.append(f"Light by height: {_pct(h['low'])} low, {_pct(h['mid'])} middle, {_pct(h['top'])} top"
             + (f" (mostly {where})." if h[where] > 0.5 else "."))
    lb, tt = sp["low_follows_bass"], sp["top_follows_treble"]
    if lb == lb and tt == tt:
        parts = [f"the bottom {'follows' if lb > 0.5 else 'does not follow'} the bass", f"the top {'follows' if tt > 0.5 else 'does not follow'} the treble"]
        s.append((parts[0] + ", " + parts[1] + ".").capitalize())
    tg = sp["segments_together"]
    if tg == tg:
        s.append("The 11 segments act as one." if tg > 0.8 else "The segments act partly together." if tg > 0.4 else "The segments act independently.")
    col = p["colour"]
    if col["dominant"]:
        s.append(f"Colours: {', '.join(col['dominant'])}" + (f"; washed out to white {_pct(col['white_share'])} of the light." if col["white_share"] > 0.25 else "."))
    elif col["white_share"] == col["white_share"]:
        s.append("Mostly white or grey: no clear colour.")
    sf = p["safety"]
    s.append(f"Flash safety: at most {sf['flashes_per_second_max']:.1f} large flashes in any second ({sf['where']}); "
             + ("within the limit of 3." if sf["passes"] else "OVER THE LIMIT OF 3."))
    f = p["comfort"]["flicker"]
    s.append("Flickers fast (uncomfortable)." if f > 0.3 else "Some fast flicker." if f > 0.12 else "No fast flicker.")
    v = p["variety"]["bar_to_bar_likeness"]
    if v == v:
        s.append("Looks the same every bar." if v > 0.85 else "Changes a little from bar to bar." if v > 0.5 else "Changes a lot from bar to bar.")
    return s
