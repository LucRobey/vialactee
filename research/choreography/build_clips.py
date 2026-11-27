"""Build clips: a passage of one song drawn in several versions, ready for the owner to compare.

Two kinds of clip:

    feeds   one mode, drawn once per feed (truth, candidate analyzer, today's analyzer, and a hidden control)
    modes   two modes, both hearing the same feed: mode against mode

A clip is a folder in research/choreography/output/clips/ holding the passage's audio, one file of frames per
version, and meta.json (what is what, and the measures). The page served by clip_server.py plays the versions
side by side without saying which is which.

Run from the repository root with the trial environment (it can decode every song):
    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.build_clips --defaults
    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.build_clips --mode Kick_bands_mode --track 19 --start 208 --duration 24
    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.build_clips --mode Kick_bands_mode --against Rainbow_mode --feed today --track 19 --start 208 --duration 24
"""
from __future__ import annotations

import argparse
import importlib
import json
import traceback
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

import numpy as np

from research.choreography import measures, records
from research.choreography.feeds import RECORDINGS_DIR, TRUTH_DIR, Feed, recording_feed, truth_feed
from research.choreography.layout import Layout, load_layout
from research.choreography.render import CLIP_FPS, brightness, render_clip

REPO = Path(__file__).resolve().parents[2]
CLIPS = Path(__file__).resolve().parent / "output" / "clips"
TRACKS = json.loads((REPO / "research" / "analyzer_trials" / "tracks.json").read_text(encoding="utf-8"))
# No candidate analyzer by default: the signals of the first one were promoted to the installation on 2026-11-27,
# so its version would be the same as "today". Pass --candidate NAME to add the feed of a research analyzer.
DEFAULT_CANDIDATE = ""
DEFAULT_CLIPS = (                      # (track, start in seconds, duration)
    ("19", 208.0, 24.0),               # Plastic People: end of the second break, the kick returns at 3:38.7
    ("13", 30.0, 20.0),                # Another One Bites The Dust: steady kick and snare
    ("20", 160.0, 24.0),               # Nobody Rules the Streets: a break, the kick returns at 2:53
)
FEED_TEXT = {
    "truth": ("Truth", "the mode hears the source of truth: the best this idea can look"),
    "candidate": ("Candidate analyzer", "the mode hears the research candidate: what the installation could do"),
    "today": ("Today's analyzer", "the mode hears the production analyzer as it is, through its fallbacks"),
    "control": ("Wrong on purpose", "the mode hears the truth with every hit moved half a beat late: a control, not shown to the owner"),
}
# What two modes can both be made to hear. The default is "today": a registered mode does not read the lab's
# signals, so on "truth" a lab mode would hear perfect hits while the registered mode still hears today's analyzer.
VERSUS_FEEDS = ("truth", "today", "candidate")
NOTE = "Simulated on screen from the segment layout. Not the real installation: brightness, colour and the room differ."


class Passage(NamedTuple):
    """A stretch of one song, with what the lab needs to draw a mode on it."""
    track: dict                        # {"id", "file", "group"}
    mono: np.ndarray                   # the whole song, 44.1 kHz mono
    layout: Layout
    start_s: float
    duration_s: float
    kicks: List[float]                 # the true kicks, on the clip's own clock
    silent: np.ndarray                 # one yes/no per clip frame
    half_beat_s: float                 # how far the control moves every hit
    audio_path: Optional[Path]         # the song's file; None writes no audio (tests)


def load_mode(name: str) -> Any:
    """A lab candidate from research/choreography/candidates/, or a registered mode from modes/."""
    for package in ("research.choreography.candidates", "modes"):
        try:
            return getattr(importlib.import_module(f"{package}.{name}"), name)
        except ModuleNotFoundError:
            continue
    raise ValueError(f"mode '{name}' not found in research/choreography/candidates/ or modes/")


clip_name = records.clip_name


def error_text(exc: BaseException) -> str:
    """One line saying what went wrong and where, instead of a traceback."""
    frames = traceback.extract_tb(exc.__traceback__)
    where = f" ({Path(frames[-1].filename).name}, line {frames[-1].lineno})" if frames else ""
    return f"{type(exc).__name__}: {exc}{where}"


def load_passage(track_id: str, start_s: float, duration_s: float) -> Passage:
    from tools.choreography_probe import load_audio_mono

    track = next((t for t in TRACKS["tracks"] if t["id"] == track_id), None)
    if track is None:
        raise ValueError(f"track '{track_id}' is not in research/analyzer_trials/tracks.json")
    audio_path = REPO / TRACKS["audio_dir"] / track["file"]
    truth = json.loads((TRUTH_DIR / f"{track_id}.json").read_text(encoding="utf-8"))
    in_passage = [b["bpm"] for b in truth["beats"] if b["main"] and b["bpm"] > 0 and start_s <= b["t"] < start_s + duration_s]
    kicks = [r[0] - start_s for r in truth["drums"]["pieces"].get("kick", []) if r[2] != "W" and start_s <= r[0] < start_s + duration_s]
    silent = np.zeros(int(duration_s * CLIP_FPS), dtype=bool)
    for r in truth["regions"].get("silence", []):
        silent[max(0, int((r["start"] - start_s) * CLIP_FPS)) : max(0, int((r["end"] - start_s) * CLIP_FPS))] = True
    return Passage({"id": track_id, "file": track["file"], "group": track.get("group")}, load_audio_mono(str(audio_path)), load_layout(),
                   start_s, duration_s, kicks, silent, 30.0 / float(np.median(in_passage)) if in_passage else 0.25, audio_path)


def standard_feeds(passage: Passage, candidate: str = DEFAULT_CANDIDATE) -> Dict[str, Optional[Feed]]:
    """The feeds a mode is drawn on: truth, the candidate analyzer when it was recorded, today, and the control."""
    track_id = passage.track["id"]
    feeds: Dict[str, Optional[Feed]] = {"truth": truth_feed(track_id)}
    if candidate and (RECORDINGS_DIR / candidate / f"{track_id}.npz").exists():
        feeds["candidate"] = recording_feed(candidate, track_id)
    feeds["today"] = None
    feeds["control"] = feeds["truth"].shifted(passage.half_beat_s)
    return feeds


def _version(passage: Passage, mode_cls: Any, heard: Optional[Feed], dest: Path, key: str, label: str, text: str, **extra: Any) -> dict:
    """Draw one version of the clip (a mode hearing a feed), write its frames, and return its entry for meta.json."""
    timing: Dict[str, float] = {}
    frames = render_clip(mode_cls, passage.mono, passage.layout, heard, passage.start_s, passage.duration_s, timing=timing)
    frames.tofile(dest / f"{key}.bin")
    bright = brightness(frames)
    entry = {"key": key, "label": label, "text": text, "file": f"{key}.bin", "frames": int(frames.shape[0]), "hidden": False, **extra,
             "provides": [] if heard is None else heard.provides(), "draw_ms": timing.get("draw_ms"), "draw_ms_max": timing.get("draw_ms_max"),
             "measures": {"kick_punch": measures.kick_punch(bright, CLIP_FPS, passage.kicks), "alive": measures.alive(bright, passage.silent)}}
    print(f"  {dest.name}  {key:9s}  kick punch contrast {entry['measures']['kick_punch']['contrast']:.3f}", flush=True)
    return entry


def _finish(dest: Path, passage: Passage, versions: List[dict], **fields: Any) -> Path:
    """Write the passage's audio and meta.json next to the frames."""
    if passage.audio_path is not None:
        import soundfile as sf

        data, sr = sf.read(str(passage.audio_path), dtype="float32", always_2d=True)
        sf.write(str(dest / "audio.wav"), data[int(passage.start_s * sr) : int((passage.start_s + passage.duration_s) * sr)], sr, subtype="PCM_16")
    meta = {"id": dest.name, "built": records.today(), **fields, "track": passage.track, "start_s": passage.start_s,
            "duration_s": passage.duration_s, "fps": CLIP_FPS, "leds": passage.layout.total, "feeds": versions,
            "kicks": [round(k, 3) for k in passage.kicks], "control_shift_s": round(passage.half_beat_s, 3), "note": NOTE}
    (dest / "meta.json").write_text(json.dumps(_clean(meta), indent=1), encoding="utf-8")
    return dest


def feeds_clip(passage: Passage, mode_name: str, mode_cls: Any, feeds: Dict[str, Optional[Feed]], clips_dir: Optional[Path] = None,
               clip_id: Optional[str] = None, candidate: str = DEFAULT_CANDIDATE, errors: Optional[Dict[str, str]] = None) -> Path:
    """One mode drawn once per feed. With `errors`, a feed the mode crashes on is noted there instead of stopping the build."""
    dest = (clips_dir or CLIPS) / (clip_id or clip_name(passage.track["id"], passage.start_s, mode_name))
    dest.mkdir(parents=True, exist_ok=True)
    versions: List[dict] = []
    for key, feed in feeds.items():
        label, text = FEED_TEXT[key]
        try:
            versions.append(_version(passage, mode_cls, feed, dest, key, label, text, hidden=key == "control", mode=mode_name, feed=key,
                                     source=candidate if key == "candidate" else key))
        except Exception as exc:  # noqa: BLE001 - a mode under test may fail in any way; the gate reports it
            if errors is None:
                raise
            errors[key] = error_text(exc)
            print(f"  {dest.name}  {key:9s}  CRASHED: {errors[key]}", flush=True)
    return _finish(dest, passage, versions, kind="feeds", mode=mode_name, against=None, feed=None, errors=dict(errors or {}),
                   sources={mode_name: records.source_sha(records.mode_file(mode_name))})


def modes_clip(passage: Passage, modes: Dict[str, Any], feed_name: str, feed: Optional[Feed], clips_dir: Optional[Path] = None,
               clip_id: Optional[str] = None, candidate: str = DEFAULT_CANDIDATE) -> Path:
    """Two modes (name -> class, the first is "the mode", the second "against") drawn on the same passage and the same feed."""
    names = list(modes)
    if len(names) != 2:
        raise ValueError("a mode-against-mode clip compares exactly two different modes")
    dest = (clips_dir or CLIPS) / (clip_id or clip_name(passage.track["id"], passage.start_s, names[0], names[1], feed_name))
    dest.mkdir(parents=True, exist_ok=True)
    heard = FEED_TEXT[feed_name][0].lower()
    versions = [_version(passage, cls, feed, dest, name, name, f"mode {name}, hearing: {heard}", mode=name, feed=feed_name,
                         source=candidate if feed_name == "candidate" else feed_name) for name, cls in modes.items()]
    return _finish(dest, passage, versions, kind="modes", mode=names[0], against=names[1], feed=feed_name, errors={},
                   sources={name: records.source_sha(records.mode_file(name)) for name in names})


def build_clip(mode_name: str, track_id: str, start_s: float, duration_s: float, candidate: str = DEFAULT_CANDIDATE,
               clip_id: Optional[str] = None, errors: Optional[Dict[str, str]] = None, clips_dir: Optional[Path] = None) -> Path:
    """A feeds clip of a real passage: `mode_name` on every feed."""
    passage = load_passage(track_id, start_s, duration_s)
    return feeds_clip(passage, mode_name, load_mode(mode_name), standard_feeds(passage, candidate), clips_dir, clip_id, candidate, errors)


def build_versus_clip(mode_name: str, against: str, track_id: str, start_s: float, duration_s: float, feed: str = "today",
                      candidate: str = DEFAULT_CANDIDATE, clip_id: Optional[str] = None, clips_dir: Optional[Path] = None) -> Path:
    """A modes clip of a real passage: `mode_name` and `against`, both hearing `feed`."""
    if feed not in VERSUS_FEEDS:
        raise ValueError(f"feed must be one of {', '.join(VERSUS_FEEDS)}")
    if mode_name == against:
        raise ValueError("a mode cannot be compared against itself")
    modes = {mode_name: load_mode(mode_name), against: load_mode(against)}
    passage = load_passage(track_id, start_s, duration_s)
    feeds = standard_feeds(passage, candidate)
    if feed not in feeds:
        raise ValueError(f"no recording of {candidate} on track {track_id}: the 'candidate' feed is not available")
    return modes_clip(passage, modes, feed, feeds[feed], clips_dir, clip_id, candidate)


def _clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (float, np.floating)):
        return None if obj != obj else round(float(obj), 4)
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def main() -> None:
    p = argparse.ArgumentParser(description="Build clips for the owner to compare.")
    p.add_argument("--mode", default="Kick_bands_mode")
    p.add_argument("--against", help="a second mode: the clip then compares the two modes instead of the feeds of one")
    p.add_argument("--feed", default="today", choices=VERSUS_FEEDS, help="with --against: what both modes hear (default: today)")
    p.add_argument("--track")
    p.add_argument("--start", type=float, default=30.0)
    p.add_argument("--duration", type=float, default=20.0)
    p.add_argument("--candidate", default=DEFAULT_CANDIDATE, help="analyzer whose recording feeds the 'candidate' version")
    p.add_argument("--defaults", action="store_true", help="build the three standard passages")
    args = p.parse_args()
    jobs = DEFAULT_CLIPS if args.defaults or not args.track else ((args.track, args.start, args.duration),)
    for track_id, start, duration in jobs:
        if args.against:
            print(f"wrote {build_versus_clip(args.mode, args.against, track_id, start, duration, args.feed, args.candidate)}")
        else:
            print(f"wrote {build_clip(args.mode, track_id, start, duration, args.candidate)}")


if __name__ == "__main__":
    main()
