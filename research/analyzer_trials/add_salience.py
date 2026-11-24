"""Add beat salience and "no beat" regions to the combined grid (updates output/grid/<id>.json in place).

In a spoken passage, an intro or a breakdown the trackers keep producing beats, but nothing in the music may mark
them. Regions are decided beat by beat (no averaging window, so the edges are as sharp as the beats):

  agreement  = a run of consecutive beats of one neural tracker (Beat This / BeatNet) that each land within TOL of a
               beat of the other (RUN_ON in a row), or each land midway between two of them (RUN_MID in a row: one
               tracker is on the offbeat, the beat still exists). Checked in both directions, so double tempo counts.
               The tolerance grows to TOL_FRAC of the beat in slow music, where expressive timing is wider.
  no_beat    = a gap between agreement runs of at least MIN_NO_BEAT s and MIN_NO_BEAT_BEATS beats (one tracker
               glitching for a few beats is not a break). Because trackers coast for a few beats after
               the drums stop, the start is then pulled back over beats that have no drum hit on them.
               Beats inside stay in the file but are flagged `no_beat`, so a benchmark can ignore the stretch.
  implied    =(needs stems) drum stem silent for MIN_QUIET s or more while the trackers agree: the beat is carried
               by other instruments. Beats stay, with a low salience.

  salience   = per grid beat, the drum-stem level within 60 ms of the beat, in dB under the track's loud hits,
               mapped to 0..1 (FLOOR_DB -> 0, FULL_DB -> 1). Drum loudness is NOT used to find no-beat regions:
               out-of-time percussion is loud.
  drums      = (needs output/drums/<id>.json from derive_from_stems.py) every kick / snare / hat hit is copied into
               the file as `drum_hits` [time, kind, strength], and each grid beat lists the kinds that hit within
               DRUM_ON_BEAT of it. The kinds come from a simple band-energy rule, one label per hit: the hit TIMES
               are more trustworthy than the kick/snare/hat split.

Removed: a "check" test that listed stretches where the instruments' onsets were no stronger on the grid than off
it. The one stretch checked by ear (Plastic People 5:33-5:44) had a clear beat, and it flagged 90 s of Roadgame.

hand_labels.json holds timings judged by ear; when a track has some, the detected edges are printed next to them.

Usage: python add_salience.py [track ids...]
"""
from __future__ import annotations

import json
import sys

import librosa
import numpy as np
from scipy.ndimage import maximum_filter1d

from build_grid import load_trackers
from common import HERE, OUT, load_audio, load_tracks, parse_only

SR, HOP = 22050, 256
FPS = SR / HOP
TOL, RUN_ON, RUN_MID = 0.05, 4, 6   # agreement: tolerance (s) and run lengths (beats)
TOL_FRAC = 0.10                     # ...or this share of the local beat, whichever is larger
MIN_NO_BEAT, MIN_NO_BEAT_BEATS = 5.0, 6   # a no-beat region lasts at least this many s AND this many beats
DRUM_ON_BEAT = 0.06                 # s: a drum hit this close to a grid beat belongs to that beat
COAST_MAX = 5.0                     # start pull-back: at most this many s, over beats with no drum hit
FLOOR_DB, FULL_DB = -28.0, -6.0     # drum level relative to the track's loud hits
MIN_QUIET = 3.0                     # s of silent drums for "implied"
IMPLIED_SALIENCE = 0.25
CURVE_HZ = 20


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    edges = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(int), [0]))))
    return list(zip(edges[::2], edges[1::2]))


def agreement_runs(x: np.ndarray, y: np.ndarray) -> list[tuple[float, float]]:
    """Stretches where consecutive beats of x each land on a y beat, or each land midway between two y beats."""
    idx = np.clip(np.searchsorted(y, x), 1, len(y) - 1)
    prev, nxt = y[idx - 1], y[idx]
    tol = np.maximum(TOL, TOL_FRAC * np.minimum(nxt - prev, 1.2))  # slow, expressive music gets more room
    inside = (x >= y[0] - TOL) & (x <= y[-1] + TOL)
    on = inside & (np.minimum(np.abs(x - prev), np.abs(x - nxt)) <= tol)
    mid = inside & (np.abs(x - (prev + nxt) / 2) <= tol) & (nxt - prev < 2.5 * np.median(np.diff(y)))
    out = []
    for match, need in ((on, RUN_ON), (mid, RUN_MID)):
        out += [(float(x[a]), float(x[b - 1])) for a, b in runs(match) if b - a >= need]
    return out


def gaps(spans: list[tuple[float, float]], dur: float, period_at) -> list[list[float]]:
    """Stretches not covered by any span that last at least MIN_NO_BEAT s and MIN_NO_BEAT_BEATS local beats."""
    out, cursor = [], 0.0
    for a, b in sorted(spans) + [(dur, dur)]:
        if a - cursor >= max(MIN_NO_BEAT, MIN_NO_BEAT_BEATS * period_at((a + cursor) / 2)):
            out.append([cursor, a])
        cursor = max(cursor, b)
    return out


def analyse(tid: str, grid: dict) -> dict:
    beats = grid["beats"]
    bt = np.array([b["t"] for b in beats])
    trackers = load_trackers(tid)
    stem_dir = OUT / "stems" / tid
    has_stems = (stem_dir / "drums.wav").exists()
    dur = max(v[-1] for v in trackers.values())

    drum_rel = held_rel = None
    if has_stems:
        drums = load_audio(str(stem_dir / "drums.wav"), sr=SR, mono=True)[0][0]
        dur = len(drums) / SR
        db = 20 * np.log10(librosa.feature.rms(y=drums, frame_length=1024, hop_length=HOP)[0] + 1e-7)
        held = maximum_filter1d(db, size=int(0.5 * FPS))  # hold each hit 0.5 s so gaps between hits do not count
        ref = float(np.percentile(held, 95))
        drum_rel, held_rel = db - ref, held - ref

    def drum_at(t: float) -> float:
        """Drum-stem level (dB under the track's loud hits) within 60 ms of time t."""
        f, h = int(round(t * FPS)), int(0.06 * FPS)
        return float(drum_rel[max(0, f - h) : f + h + 1].max()) if f < len(drum_rel) else -120.0

    # --- no_beat: gaps between stretches where the two neural trackers agree
    no_beat: list[list[float]] = []
    if "beat_this" in trackers and "beatnet" in trackers:
        a, b = trackers["beat_this"], trackers["beatnet"]

        def period_at(t: float) -> float:  # local beat period from Beat This, +-10 s
            near = a[(a >= t - 10) & (a <= t + 10)]
            return float(np.median(np.diff(near if len(near) > 3 else a)))

        no_beat = gaps(agreement_runs(a, b) + agreement_runs(b, a), dur, period_at)
        if has_stems:
            # Trackers coast for a few beats after the drums stop: pull the start back over beats with no drum hit.
            # (Drums, not all instruments: a loud sustained synth hides the cut in the mixed onset strength.)
            for reg in no_beat:
                for t in bt[(bt < reg[0] + 1e-6) & (bt >= reg[0] - COAST_MAX)][::-1]:
                    if drum_at(float(t)) >= FLOOR_DB:
                        break
                    reg[0] = float(t)
    regions = [{"start": round(max(0.0, a), 2), "end": round(min(dur, b), 2), "kind": "no_beat", "why": ["trackers disagree"]} for a, b in no_beat]
    covered = lambda s, e: sum(max(0.0, min(e, b) - max(s, a)) for a, b in no_beat) / max(e - s, 1e-6)

    if has_stems:
        # --- implied: silent drums although the trackers agree
        for i, j in runs(held_rel < FLOOR_DB):
            s, e = i / FPS, j / FPS
            if e - s >= MIN_QUIET and covered(s, e) < 0.5:
                regions.append({"start": round(s, 2), "end": round(e, 2), "kind": "implied", "why": ["no drums"]})
    regions.sort(key=lambda r: r["start"])

    im = [(r["start"], r["end"]) for r in regions if r["kind"] == "implied"]
    inside = lambda t, spans: any(a <= t < b for a, b in spans)
    for beat in beats:
        beat["no_beat"] = inside(beat["t"], no_beat)
        if has_stems:
            peak = drum_at(beat["t"])
            sal = float(np.clip((peak - FLOOR_DB) / (FULL_DB - FLOOR_DB), 0, 1))
            if beat["votes"] >= 2 and inside(beat["t"], im):
                sal = max(sal, IMPLIED_SALIENCE)
            beat["drum_db"], beat["salience"] = round(peak, 1), round(sal, 2)

    # --- drums: copy the hits in, and attach to each grid beat the kinds that land on it
    dp = OUT / "drums" / f"{tid}.json"
    n_on = n_hits = 0
    if has_stems and dp.exists():
        hits = json.loads(dp.read_text(encoding="utf-8"))["hits"]
        ht = np.array([h[0] for h in hits])
        taken = np.zeros(len(hits), dtype=bool)
        for beat in beats:
            near = np.flatnonzero(np.abs(ht - beat["t"]) <= DRUM_ON_BEAT)
            taken[near] = True
            beat["drums"] = sorted({hits[k][1] for k in near})
        grid["drum_hits"] = hits
        n_on, n_hits = int(taken.sum()), len(hits)

    for key in ("no_beat_regions", "normal_agree_rate"):
        grid.pop(key, None)
    grid["quiet_regions"] = regions
    if has_stems:
        step = int(round(FPS / CURVE_HZ))
        curve = np.clip((held_rel[::step] - FLOOR_DB) / (FULL_DB - FLOOR_DB), 0, 1)
        grid["drum_level"] = {"hz": round(FPS / step, 3), "values": [round(float(v), 2) for v in curve]}
    grid["salience_params"] = {"tol_s": TOL, "tol_frac": TOL_FRAC, "run_on": RUN_ON, "run_mid": RUN_MID,
                               "min_no_beat_s": MIN_NO_BEAT, "min_no_beat_beats": MIN_NO_BEAT_BEATS, "drum_on_beat_s": DRUM_ON_BEAT,
                               "coast_max_s": COAST_MAX, "floor_db": FLOOR_DB, "full_db": FULL_DB,
                               "min_quiet_s": MIN_QUIET, "implied_salience": IMPLIED_SALIENCE,
                               "stems": has_stems}
    kinds = {k: sum(1 for b in beats if k in b.get("drums", [])) for k in ("kick", "snare", "hat")}
    return {"regions": regions, "dur": dur, "stems": has_stems, "hits": n_hits, "hits_on_beat": n_on, "beats_with": kinds}


def fmt(t: float) -> str:
    t = round(t, 1)
    return f"{int(t // 60)}:{t % 60:04.1f}"


def main() -> None:
    hand = json.loads((HERE / "hand_labels.json").read_text(encoding="utf-8"))
    for t in load_tracks(parse_only(sys.argv[1:])):
        gp = OUT / "grid" / f"{t['id']}.json"
        if not gp.exists():
            print(f"[{t['id']}] no grid, skipping")
            continue
        grid = json.loads(gp.read_text(encoding="utf-8"))
        s = analyse(t["id"], grid)
        gp.write_text(json.dumps(grid), encoding="utf-8")
        by = lambda kind: [r for r in s["regions"] if r["kind"] == kind]
        span = lambda rs: sum(r["end"] - r["start"] for r in rs)
        show = lambda rs, n: (" ".join(f"{fmt(r['start'])}-{fmt(r['end'])}" for r in rs[:n]) or "none") + (" ..." if len(rs) > n else "")
        nb = by("no_beat")
        print(
            f"[{t['id']}] {t['file'][:22]:22s} NO BEAT {span(nb):4.0f}s ({span(nb) / s['dur']:3.0%}): {show(nb, 7)}"
            f" | implied {span(by('implied')):3.0f}s"
            f" | drums: {s['hits']} hits, {s['hits_on_beat'] / max(1, s['hits']):.0%} on a grid beat; beats with kick/snare/hat: "
            f"{s['beats_with']['kick']}/{s['beats_with']['snare']}/{s['beats_with']['hat']} of {len(grid['beats'])}",
            flush=True,
        )
        for lab in hand.get(t["id"], {}).get("no_beat", []):
            ref = lab["end"] if lab["end"] is not None else lab["start"]
            best = min(nb, key=lambda r: abs(r["end"] - ref) if lab["end"] is not None else abs(r["start"] - ref), default=None)
            if best is None:
                print(f"       by ear {lab}: no detected region")
                continue
            d = lambda key: "not given" if lab[key] is None else f"{fmt(lab[key])} by ear, {fmt(best[key])} detected ({best[key] - lab[key]:+.1f}s)"
            print(f"       start: {d('start')} | end: {d('end')}")


if __name__ == "__main__":
    main()
