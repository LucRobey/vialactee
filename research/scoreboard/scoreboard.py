"""The scoreboard: every slot of listener.signals graded against the source of truth, on the 20 truth tracks.

For each analyzer model it plays each song through the production Listener with the 5 s look-ahead
(record.py), grades every signal of config/music_signals.json against the truth value it mirrors (grade.py),
and writes research/scoreboard/SCOREBOARD.md and scores.json.

Two scores per signal:
    checked   only against truth allowed to grade (timed or accepted by ear, two tools agreeing, or exact)
    all       against all the truth we have, weak values left out; indicative only

Run from the repository root with the trial environment (it can decode every song):
    research/analyzer_trials/.venv/Scripts/python.exe -m research.scoreboard.scoreboard [--model NAME] [track ids]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from research.scoreboard import grade
from research.scoreboard.report import write_report

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TRUTH = REPO / "research" / "truth" / "tracks"
OUT = HERE / "output"
SPEC = json.loads((REPO / "config" / "music_signals.json").read_text(encoding="utf-8"))
TRACKS = json.loads((REPO / "research" / "analyzer_trials" / "tracks.json").read_text(encoding="utf-8"))
DEFAULT_MODELS = ("MultiBandOnsetAudioAnalyzer", "DyadicMetricalAudioAnalyzer")
EVENT_TOL = {"drops": 0.5, "sections.items": 2.0}      # seconds; every other event: 50 ms
HIT_TOL = 0.05
EXACT_CURVES = {"loud_db", "sub_db", "bass_db", "mid_db", "high_db", "bright_oct", "fullness"}
SILENT_DB = -50.0
NAN = float("nan")


def _record_job(job: Tuple[str, str, str, str]) -> Tuple[str, str, float]:
    model, tid, audio, dest = job
    from research.benchmarks.run_benchmark import load_model_class
    from research.scoreboard.record import record_track
    from tools.choreography_probe import load_audio_mono

    t0 = time.time()
    # a production model by its registry name, or a research candidate from research/experiments/models/
    rec = record_track(load_audio_mono(audio), analyzer_class=load_model_class(model, str(REPO)))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    np.savez_compressed(dest, **rec)
    return model, tid, time.time() - t0


def _levels_ok(levels: List[str]) -> np.ndarray:
    return np.array([lv in grade.MAY_GRADE for lv in levels], dtype=bool)


def _span_grade(regions: List[dict], name: str) -> bool:
    """May this lane of stretches grade? Silence is exact; otherwise most of its time must carry a strong level."""
    if name == "silence":
        return True
    total = sum(r["end"] - r["start"] for r in regions)
    strong = sum(r["end"] - r["start"] for r in regions if r.get("level") in grade.MAY_GRADE)
    return total > 0 and strong / total >= 0.8


def grade_signal(sig: dict, est: np.ndarray, truth: dict, curves: Dict[str, np.ndarray], fps: float, chord: Optional[np.ndarray] = None) -> Dict[str, Any]:
    """Grade one signal of one track. `est` is the recorded value per frame (NaN where the slot was empty)."""
    ref = sig["truth"]
    produced = bool(np.isfinite(est).any()) if ref != "chords.items" else bool(chord is not None and (chord != "").any())
    out: Dict[str, Any] = {"produced": produced, "checked": NAN, "all": NAN, "detail": {}}
    if not produced:
        return out
    n = len(est)
    beats = [b for b in truth["beats"] if b["main"] and not b["no_beat"]]
    bt = np.array([b["t"] for b in beats])
    loud = curves["loud_db"]
    audible = loud > SILENT_DB

    if ref == "beats.t":
        hits = grade.rising_edges(est, fps)
        # a beat reported inside a no-beat stretch is not graded: the truth has no beats there to compare with
        nb = grade.regions_to_mask([(r["start"], r["end"]) for r in truth["regions"].get("no_beat", [])], n, fps)
        hits = hits[~nb[np.clip(np.round(hits * fps).astype(int), 0, n - 1)]]
        strong = grade.event_score(hits, bt, HIT_TOL, _levels_ok([b["level"] for b in beats]))
        every = grade.event_score(hits, bt, HIT_TOL)
        out.update(checked=strong["f1"], all=every["f1"], detail={"found": every["found"], "right": every["right"],
                                                                 "offset_ms": every["offset_ms"], "n_truth": every["n_truth"], "n_est": every["n_est"]})
    elif ref == "beats.bpm":
        ok = _levels_ok([b["level"] for b in beats])
        strong = grade.tempo_score(est, fps, bt[ok], [b["bpm"] for b, k in zip(beats, ok) if k])
        every = grade.tempo_score(est, fps, bt, [b["bpm"] for b in beats])
        out.update(checked=strong["right"], all=every["right"], detail={"double": every["double"], "half": every["half"]})
    elif ref in ("beats.bar_pos", "beats.strength"):
        idx = np.clip(np.round(bt * fps).astype(int), 0, n - 1)
        key = ref.split(".")[1]
        vals = np.array([b[key] if b[key] is not None else np.nan for b in beats], dtype=float)
        if key == "bar_pos":
            known = vals > 0
            ok = np.array([b["bar_pos_level"] in grade.MAY_GRADE for b in beats], dtype=bool)
            out.update(checked=grade.equal_score(est[idx], vals, known & ok), all=grade.equal_score(est[idx], vals, known))
        else:
            k = np.isfinite(vals) & np.isfinite(est[idx])
            out.update(all=float(np.corrcoef(est[idx][k], vals[k])[0, 1]) if k.sum() > 20 and np.std(est[idx][k]) > 0 else NAN)
    elif ref == "meter.beats_per_bar":
        score = grade.equal_score(est, np.full(n, truth["meter"]["beats_per_bar"], dtype=float))
        out.update(checked=NAN if truth["meter"]["conflict"] else score, all=score)
    elif ref.startswith("drums.pieces.") or ref in EVENT_TOL:
        if ref.startswith("drums.pieces."):
            rows = truth["drums"]["pieces"].get(ref.rsplit(".", 1)[1], [])
            times, levels, tol = [r[0] for r in rows], [r[2] for r in rows], HIT_TOL
        else:
            rows = truth["drops"] if ref == "drops" else truth["sections"]["items"]
            times, levels, tol = [r["t"] for r in rows], [r["level"] for r in rows], EVENT_TOL[ref]
        hits = grade.rising_edges(est, fps)
        strong = grade.event_score(hits, times, tol, _levels_ok(levels))
        every = grade.event_score(hits, times, tol, [lv != "W" for lv in levels])
        out.update(checked=strong["f1"] if strong["n_truth"] else NAN, all=every["f1"] if every["n_truth"] else NAN,
                   detail={"found": every["found"], "right": every["right"], "offset_ms": every["offset_ms"],
                           "n_truth": every["n_truth"], "n_est": every["n_est"]})
    elif ref.startswith("regions."):
        name = ref.split(".", 1)[1]
        regions = [r for r in truth["regions"].get(name, []) if r.get("level") != "W"]      # weak truth never grades
        mask = grade.regions_to_mask([(r["start"], r["end"]) for r in regions], n, fps)
        res = grade.state_score(np.nan_to_num(est) > 0, mask, fps)
        out.update(checked=res["balanced"] if _span_grade(regions, name) else NAN, all=res["balanced"], detail=res)
    elif ref.startswith("curves."):
        name = ref.split(".", 1)[1]
        curve = curves[name]
        if name == "layers":
            step = int(round(fps / 20))
            m = min(n // step, len(curve))
            out.update(all=grade.equal_score(np.round(np.nanmean(est[: m * step].reshape(m, step), axis=1)), curve[:m]))
        else:
            res = grade.follow_score(est, fps, curve, 20.0, audible)
            out.update(checked=res["corr"] if name in EXACT_CURVES else NAN, all=res["corr"], detail=res)
    elif ref == "chords.items" and chord is not None:
        want = np.full(n, "N", dtype=object)
        for a, b, label in truth["chords"]["items"]:
            want[int(a * fps) : int(b * fps)] = label
        said = chord[:n] != ""
        out.update(all=float(np.mean(chord[:n][said] == want[said])) if said.any() else NAN)
    return out


def grade_candidates(rec: Dict[str, np.ndarray], truth: dict, curves: Dict[str, np.ndarray], fps: float) -> Dict[str, Dict[str, Any]]:
    """Existing signals that are close to an empty slot, graded as if they filled it."""
    from research.scoreboard.record import TAG_CODES, band_centres_hz

    out: Dict[str, Dict[str, Any]] = {}
    by_name = {s["name"]: s for s in SPEC["signals"]}

    def as_slot(slot: str, values: np.ndarray) -> Dict[str, Any]:
        return grade_signal(by_name[slot], values.astype(np.float32), truth, curves, fps)

    tag = rec["cand_beat_tag"]
    for slot, code in (("kick", TAG_CODES["Bass/Kick"]), ("snare", TAG_CODES["Snare/Mid"]), ("hat", TAG_CODES["Hi-hat/Cymbal"])):
        out[f"{slot} <- beat tag"] = as_slot(slot, (tag == code).astype(float))
    flux = np.zeros(len(tag))
    flux[np.clip(np.round(grade.peak_times(rec["cand_flux_low"], fps) * fps).astype(int), 0, len(tag) - 1)] = 1.0
    out["kick <- sudden rise of the lowest band"] = as_slot("kick", flux)
    out["section_change <- the 'song change' flag"] = as_slot("section_change", rec["cand_song_change"].astype(float))
    out["no_beat <- not locked"] = as_slot("no_beat", (~rec["cand_is_locked"]).astype(float))
    out["no_beat <- beat trust under 0.35"] = as_slot("no_beat", (rec["cand_beat_trust"] < 0.35).astype(float))
    bands = rec["cand_bands"].astype(float)
    centres = band_centres_hz(bands.shape[1])
    groups = {"band_bass": centres < 250.0, "band_mid": (centres >= 250.0) & (centres < 4000.0), "band_high": centres >= 4000.0}
    for slot, pick in groups.items():
        if pick.any():
            out[f"{slot} <- {int(pick.sum())} of the 16 bands"] = as_slot(slot, 10.0 * np.log10(bands[:, pick].sum(axis=1) + 1e-6))
    out["kick_level <- lowest band"] = as_slot("kick_level", 10.0 * np.log10(bands[:, 0] + 1e-6))
    return out


def run(models: List[str], only: List[str], workers: int, reuse: bool) -> dict:
    """Play the tracks through each model (unless reused) and grade everything. Returns the full result."""
    tracks = [t for t in TRACKS["tracks"] if (not only or t["id"] in only) and (TRUTH / f"{t['id']}.json").exists()]
    jobs = []
    for model in models:
        for t in tracks:
            dest = OUT / model / f"{t['id']}.npz"
            if not (reuse and dest.exists()):
                jobs.append((model, t["id"], str(REPO / TRACKS["audio_dir"] / t["file"]), str(dest)))
    if jobs:
        print(f"recording {len(jobs)} runs ({len(models)} model(s) x {len(tracks)} tracks) on {workers} workers", flush=True)
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for i, (model, tid, sec) in enumerate(pool.map(_record_job, jobs), 1):
                print(f"  {i}/{len(jobs)}  {model[:24]:24s} {tid}  {sec:5.0f}s  (elapsed {time.time() - t0:.0f}s)", flush=True)

    result: dict = {"built": datetime.date.today().isoformat(), "lookahead_s": 5.0, "models": {},
                    "tracks": {t["id"]: {"file": t["file"], "group": t.get("group")} for t in tracks}}
    for model in models:
        per_track: Dict[str, dict] = {}
        for t in tracks:
            truth = json.loads((TRUTH / f"{t['id']}.json").read_text(encoding="utf-8"))
            with np.load(TRUTH / f"{t['id']}.curves.npz") as z:
                curves = {k: z[k] for k in z.files}
            with np.load(OUT / model / f"{t['id']}.npz") as z:
                rec = {k: z[k] for k in z.files}
            fps = float(rec["fps"])
            frame_ms = float(rec["frame_ms"]) if "frame_ms" in rec else NAN
            signals = {s["name"]: grade_signal(s, rec[s["name"]] if s["name"] != "chord" else np.zeros(1), truth, curves, fps,
                                               chord=rec["chord"]) for s in SPEC["signals"]}
            per_track[t["id"]] = {"signals": signals, "candidates": grade_candidates(rec, truth, curves, fps), "frame_ms": frame_ms}
        result["models"][model] = per_track
    return result


def _clean(obj: Any) -> Any:
    """Plain JSON: numpy numbers become Python numbers, NaN becomes null."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return None if obj != obj else round(float(obj), 4)
    return obj


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("ids", nargs="*")
    p.add_argument("--model", action="append", default=[])
    p.add_argument("--workers", type=int, default=5)
    p.add_argument("--reuse", action="store_true", help="grade the recordings already on disk instead of playing the songs again")
    p.add_argument("--out", default="", help="folder for SCOREBOARD.md and scores.json (default: research/scoreboard/); use one folder per research run")
    args = p.parse_args()
    dest = Path(args.out) if args.out else HERE
    dest.mkdir(parents=True, exist_ok=True)
    result = run(args.model or list(DEFAULT_MODELS), args.ids, args.workers, args.reuse)
    (dest / "scores.json").write_text(json.dumps(_clean(result), indent=1), encoding="utf-8")
    write_report(result, SPEC, dest / "SCOREBOARD.md")
    print(f"wrote {dest / 'SCOREBOARD.md'}")


if __name__ == "__main__":
    sys.exit(main())
