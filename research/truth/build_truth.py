"""Build the automatic draft of the source of truth, one file per track.

This is the machine pass that comes BEFORE the owner's review by ear. It gathers what the offline tools in
research/analyzer_trials/ already produced (merged beats, no-beat stretches, drum hits, chords, stems), adds
direct measurements (research/truth/measures.py) and bar positions (research/truth/meter.py), lays the
owner's existing timings on top, and writes:

    research/truth/tracks/<id>.json         events and stretches, each with its level of evidence
    research/truth/tracks/<id>.curves.npz   curves, 20 values per second
    research/truth/REPORT.md                what was built and what most needs a human ear

The owner's corrections from the review tool (research/truth/labels/<id>.json) are laid over the draft at the
end (research/truth/labels.py). They are read, never written, here.

Levels of evidence (papers/P1): H timed by ear, A accepted by ear, M2 two tools agree, M1 one tool,
W known weak, X exact by construction (a direct measurement of the mix).

Run from the repository root with the trial environment:
    research/analyzer_trials/.venv/Scripts/python.exe -m research.truth.build_truth [track ids...]
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from research.truth import buildups, measures, meter
from research.truth.labels import apply_labels, finalize
from research.truth.report import write_report
from research.truth.sections import section_changes

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TRIALS = REPO / "research" / "analyzer_trials"
OUT = TRIALS / "output"
TRACKS_DIR = HERE / "tracks"
LABELS_DIR = HERE / "labels"
DROP_MIN_JUMP_DB = 3.0   # a kick return with at least this jump in loudness is proposed as a drop
FORMAT = 1
PIPELINE = "auto-draft 0.1"
STEMS = ("drums", "bass", "vocals", "other")
KICK_AGREE = 0.8   # share of a kick stretch that the second method must cover to call it agreed
KICK_MATCH_S = 0.07   # a trained-model kick and a measured low-band peak this close are the same kick
HIT_MATCH_S = 0.05
ON_BEAT_S = 0.06


def _load(path: Path) -> Optional[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _overlaps(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def no_beat_regions(grid: dict, hand: Optional[dict]) -> List[dict]:
    """Machine no-beat stretches, replaced by the owner's wherever the owner has spoken."""
    machine = [
        {"start": r["start"], "end": r["end"], "level": "M1", "source": "trackers disagree"}
        for r in grid.get("quiet_regions", [])
        if r.get("kind") == "no_beat"
    ]
    if not hand:
        return machine
    human = []
    for r in hand.get("no_beat", []):
        timed = set(r.get("timed", []))
        human.append({
            "start": r["start"], "end": r["end"],
            "level": "H" if timed == {"start", "end"} else "A",
            "edges": {e: ("H" if e in timed else "A") for e in ("start", "end")},
            "source": "owner", "note": r.get("note", ""),
        })
    beat_ok = hand.get("beat_present", [])
    kept = [m for m in machine if not any(_overlaps(m, h) for h in human) and not any(_overlaps(m, b) for b in beat_ok)]
    return sorted(human + kept, key=lambda r: r["start"])


def _near(times: np.ndarray, t: float, tol: float) -> bool:
    if len(times) == 0:
        return False
    i = int(np.searchsorted(times, t))
    return any(0 <= j < len(times) and abs(times[j] - t) <= tol for j in (i - 1, i))


def trained_drum_hits(adtof: Optional[dict], measured_kicks: List[float]) -> Optional[dict]:
    """Hits of the trained drum model, each as [time, strength, level].

    kick: M2 when a low-band peak of the drum stem (a direct measurement) sits at the same instant, else M1.
    other pieces: M1 when the model finds the hit both in the mix and in the drum stem, W when in the mix only.
    (Mix and stem are two runs of the same model: that is a consistency check, not a second tool.)
    """
    if not adtof:
        return None
    kicks = np.array(sorted(measured_kicks))
    out: Dict[str, list] = {}
    for name, hits in adtof["mix"].items():
        stem = np.array(sorted(h[0] for h in adtof.get("stem", {}).get(name, [])))
        rows = []
        for t, strength in hits:
            if name == "kick":
                level = "M2" if _near(kicks, t, KICK_MATCH_S) else "M1"
            else:
                level = "M1" if _near(stem, t, HIT_MATCH_S) else "W"
            rows.append([t, strength, level])
        out[name] = rows
    return out


def build_track(track: dict, hand_all: dict) -> Optional[dict]:
    tid = track["id"]
    grid = _load(OUT / "grid" / f"{tid}.json")
    if grid is None:
        print(f"[{tid}] no beat grid, skipped")
        return None
    audio = REPO / "assets" / "musics" / "mp3_files" / track["file"]
    stem_dir = OUT / "stems" / tid
    stem_paths = {s: str(stem_dir / f"{s}.wav") for s in STEMS if (stem_dir / f"{s}.wav").exists()}
    curves, regs, info = measures.measure_track(str(audio), stem_paths)
    hand = hand_all.get(tid)

    # --- beats, no-beat stretches, tempo, bars ---------------------------------------------------------
    nb_regs = no_beat_regions(grid, hand)
    t = np.array([b["t"] for b in grid["beats"]])
    no_beat = np.array([any(r["start"] <= x < r["end"] for r in nb_regs) for x in t], dtype=bool)
    bt = (_load(OUT / "beats" / f"{tid}.json") or {}).get("beat_this", {})
    bn = _load(OUT / "beatnet" / f"{tid}.json") or {}
    confirmed = np.array([b.get("votes", 0) >= 2 for b in grid["beats"]], dtype=bool)
    main = meter.main_beat_mask(t, no_beat, confirmed)
    mi = np.flatnonzero(main)
    tm, nbm = t[mi], no_beat[mi]
    f_bt = meter.flag_downbeats(tm, bt.get("downbeats", []))
    f_bn = meter.flag_downbeats(tm, bn.get("downbeats", []))
    m_bt, m_bn = meter.beats_per_bar(f_bt), meter.beats_per_bar(f_bn)
    bar_len = m_bt if m_bt == m_bn and m_bt else (4 if 4 in (m_bt, m_bn) else (m_bt or m_bn or 4))
    lead, other = (f_bt, f_bn) if m_bt == bar_len else (f_bn, f_bt)
    bars_m = meter.bar_positions(tm, nbm, lead, other, bar_len)
    bars = {"pos": np.zeros(len(t), dtype=int), "agreed": np.zeros(len(t), dtype=bool)}
    bars["pos"][mi], bars["agreed"][mi] = bars_m["pos"], bars_m["agreed"]
    bpm = np.zeros(len(t))
    bpm[mi] = meter.local_bpm(tm, nbm)
    for i in range(1, len(bpm)):          # a half-beat carries the tempo of the main beat before it
        if not main[i]:
            bpm[i] = bpm[i - 1]

    beats = []
    for i, b in enumerate(grid["beats"]):
        beats.append({
            "t": b["t"],
            "main": bool(main[i]),
            "level": "M2" if b.get("votes", 0) >= 2 else "M1",
            "votes": b.get("votes", 0),
            "no_beat": bool(no_beat[i]),
            "bpm": round(float(bpm[i]), 1),
            "bar_pos": int(bars["pos"][i]),
            "bar_pos_level": "M2" if bars["agreed"][i] else ("M1" if bars["pos"][i] else None),
            "strength": b.get("salience"),
            "drums": b.get("drums", []),
        })
    trained = trained_drum_hits(_load(OUT / "adtof" / f"{tid}.json"), info.get("kick_times", []))
    if trained:
        by_piece = {k: np.array([h[0] for h in v if h[2] != "W"]) for k, v in trained.items()}
        for b in beats:
            b["drums"] = [k for k, ts in by_piece.items() if _near(ts, b["t"], ON_BEAT_S)]

    # --- kick stretches: measurement, checked against the drum model (or the old rule without it) -------
    drums = _load(OUT / "drums" / f"{tid}.json") or {}
    hit_kicks = [h[0] for h in trained["kick"]] if trained else [h[0] for h in drums.get("hits", []) if h[1] == "kick"]
    second = measures.cluster_events(hit_kicks)
    kick_regs = []
    for a, e in regs.pop("kick_present", []):
        cov = measures.coverage([a, e], second)
        kick_regs.append({"start": a, "end": e, "level": "M2" if cov >= KICK_AGREE else "M1", "second_method": round(cov, 2)})

    def plain(name: str, level: str, source: str) -> List[dict]:
        return [{"start": a, "end": e, "level": level, "source": source} for a, e in regs.get(name, [])]

    vocal_old = _load(OUT / "vocals" / f"{tid}.json") or {}
    truth = {
        "format": FORMAT,
        "status": "auto draft, not reviewed by ear",
        "pipeline": PIPELINE,
        "built": datetime.date.today().isoformat(),
        "track": {
            "id": tid, "file": track["file"], "group": track.get("group"),
            "duration": info["duration"], "audio_sha1": _sha1(audio),
        },
        "sources": {
            "beats": grid.get("trackers", []), "downbeats": ["beat_this", "beatnet"], "stems": "demucs htdemucs",
            "chords": "BTC", "drums": "ADTOF (trained) on the mix" if trained else "band rule on the drum stem", "human": "hand_labels.json" if hand else None,
        },
        "meter": {
            "beats_per_bar": bar_len, "beat_this_says": m_bt, "beatnet_says": m_bn,
            "conflict": bool(m_bt and m_bn and m_bt != m_bn),
        },
        "beats": beats,
        "regions": {
            "no_beat": nb_regs,
            "beat_confirmed": [{**b, "level": "A", "source": "owner"} for b in (hand or {}).get("beat_present", [])],
            "silence": plain("silence", "X", "mix level"),
            "kick_present": kick_regs,
            "breakdown": [{**r, "level": "M1", "source": "kick leaves and returns"} for r in regs.get("breakdown", [])],
            "bass_present": plain("bass_present", "M1", "bass stem level"),
            "drums_present": plain("drums_present", "M1", "drum stem level"),
            "vocal_present": plain("vocals_present", "M1", "vocal stem level against the mix"),
            "vocal_present_old_rule": [
                {"start": a, "end": e, "level": "W", "source": "vocal stem against itself"}
                for a, e in vocal_old.get("segments", [])
            ],
            "other_present": plain("other_present", "M1", "other stem level"),
            "riser": [{**r, "level": "W", "source": "brightness rising"} for r in regs.get("riser", [])],
        },
        "moments": [{**m, "level": "M1"} for m in info.get("moments", [])],
        "drops": [
            {"t": m["t"], "level": "M1", "loudness_jump_db": m["loudness_jump_db"]}
            for m in info.get("moments", [])
            if m["kind"] == "kick_return" and m["loudness_jump_db"] >= DROP_MIN_JUMP_DB
        ],
        "drums": {
            "note": "each hit is [time, strength 0..1 from the model, level]; see trained_drum_hits() for the levels",
            "pieces": trained or {},
        },
        "drum_hits_old_rule": {"level": "W", "note": "times usable, kick / snare / hat split is not", "hits": drums.get("hits", [])},
        "kick_times_measured": {"level": "M1", "ref_db": info.get("kick_ref_db"), "times": info.get("kick_times", [])},
        "chords": {"level": "M1", "items": (_load(OUT / "chords" / f"{tid}.json") or {}).get("chords", [])},
        "sections": {"level": "M1", "boundaries": [], "items": []},     # filled just below, from the measurements
        "sections_old_rule": {"level": "W", "boundaries": (_load(OUT / "sections" / f"{tid}.json") or {}).get("boundaries", [])},
        "curves": {"file": f"{tid}.curves.npz", "hz": measures.CURVE_HZ, "names": sorted(curves), "level": "X for mix curves, M1 for stem curves"},
    }
    changes = section_changes(beats, curves, measures.CURVE_HZ, info["duration"])
    truth["sections"]["items"] = [{**c, "level": "M1"} for c in changes]
    truth["sections"]["boundaries"] = [c["t"] for c in changes]
    # No tool finds build-ups or drops. A weak first guess (level W, never used to grade) saves the owner's time
    # in the review tool: research/truth/buildups.py.
    releases = buildups.release_points(truth["moments"], truth["sections"]["items"], curves["loud_db"], measures.CURVE_HZ)
    truth["regions"]["buildup"] = buildups.buildups(releases, beats, curves, truth["drums"]["pieces"], kick_regs, measures.CURVE_HZ)
    truth["drops"] = sorted(truth["drops"] + buildups.possible_drops(releases, truth["drops"]), key=lambda d: d["t"])
    finalize(apply_labels(truth, _load(LABELS_DIR / f"{tid}.json")))
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    (TRACKS_DIR / f"{tid}.json").write_text(json.dumps(truth, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    np.savez_compressed(TRACKS_DIR / f"{tid}.curves.npz", **{k: v.astype(np.float32) for k, v in curves.items()})
    return truth


def main() -> None:
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    spec = json.loads((TRIALS / "tracks.json").read_text(encoding="utf-8"))
    hand_all = json.loads((TRIALS / "hand_labels.json").read_text(encoding="utf-8"))
    for track in spec["tracks"]:
        if only and track["id"] not in only:
            continue
        truth = build_track(track, hand_all)
        if truth:
            r = truth["regions"]
            print(f"[{track['id']}] {track['file'][:40]:40s} beats {len(truth['beats'])}, "
                  f"no-beat {len(r['no_beat'])}, kick stretches {len(r['kick_present'])}, "
                  f"breakdowns {len(r['breakdown'])}, risers {len(r['riser'])}", flush=True)
    write_report(TRACKS_DIR, HERE / "REPORT.md")


if __name__ == "__main__":
    main()
