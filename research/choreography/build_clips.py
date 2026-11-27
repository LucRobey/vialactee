"""Build clips: one mode, one passage of one song, rendered once per feed, ready for the owner to compare.

A clip is a folder in research/choreography/output/clips/ holding the passage's audio, one file of frames per
feed, and meta.json (what is what, and the measures). The page served by clip_server.py plays them side by side.

Run from the repository root with the trial environment (it can decode every song):
    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.build_clips --defaults
    research/analyzer_trials/.venv/Scripts/python.exe -m research.choreography.build_clips --mode Kick_bands_mode --track 19 --start 208 --duration 24
"""
from __future__ import annotations

import argparse
import datetime
import importlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from research.choreography import measures
from research.choreography.feeds import FPS, RECORDINGS_DIR, TRUTH_DIR, Feed, recording_feed, truth_feed
from research.choreography.layout import load_layout
from research.choreography.render import CLIP_FPS, brightness, render_clip

REPO = Path(__file__).resolve().parents[2]
CLIPS = Path(__file__).resolve().parent / "output" / "clips"
TRACKS = json.loads((REPO / "research" / "analyzer_trials" / "tracks.json").read_text(encoding="utf-8"))
DEFAULT_CANDIDATE = "BandKickSlotsAudioAnalyzer"
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


def load_mode(name: str) -> Any:
    """A lab candidate from research/choreography/candidates/, or a registered mode from modes/."""
    for package in ("research.choreography.candidates", "modes"):
        try:
            return getattr(importlib.import_module(f"{package}.{name}"), name)
        except ModuleNotFoundError:
            continue
    raise ValueError(f"mode '{name}' not found in research/choreography/candidates/ or modes/")


def build_clip(mode_name: str, track_id: str, start_s: float, duration_s: float, candidate: str = DEFAULT_CANDIDATE) -> Path:
    import soundfile as sf
    from tools.choreography_probe import load_audio_mono

    track = next(t for t in TRACKS["tracks"] if t["id"] == track_id)
    audio_path = REPO / TRACKS["audio_dir"] / track["file"]
    mono = load_audio_mono(str(audio_path))
    layout = load_layout()
    mode_cls = load_mode(mode_name)
    truth = json.loads((TRUTH_DIR / f"{track_id}.json").read_text(encoding="utf-8"))

    feeds: Dict[str, Optional[Feed]] = {"truth": truth_feed(track_id)}
    if (RECORDINGS_DIR / candidate / f"{track_id}.npz").exists():
        feeds["candidate"] = recording_feed(candidate, track_id)
    feeds["today"] = None
    in_passage = [b["bpm"] for b in truth["beats"] if b["main"] and b["bpm"] > 0 and start_s <= b["t"] < start_s + duration_s]
    half_beat = 30.0 / float(np.median(in_passage)) if in_passage else 0.25
    feeds["control"] = feeds["truth"].shifted(half_beat)

    clip_id = f"{track_id}_{int(start_s):04d}_{mode_name}"
    dest = CLIPS / clip_id
    dest.mkdir(parents=True, exist_ok=True)
    kicks = [r[0] - start_s for r in truth["drums"]["pieces"].get("kick", []) if r[2] != "W" and start_s <= r[0] < start_s + duration_s]
    silent = np.zeros(int(duration_s * CLIP_FPS), dtype=bool)
    for r in truth["regions"].get("silence", []):
        silent[max(0, int((r["start"] - start_s) * CLIP_FPS)) : max(0, int((r["end"] - start_s) * CLIP_FPS))] = True

    feed_meta: List[dict] = []
    for key, feed in feeds.items():
        frames = render_clip(mode_cls, mono, layout, feed, start_s, duration_s)
        frames.tofile(dest / f"{key}.bin")
        bright = brightness(frames)
        label, text = FEED_TEXT[key]
        feed_meta.append({
            "key": key, "label": label, "text": text, "file": f"{key}.bin", "frames": int(frames.shape[0]),
            "hidden": key == "control",
            "source": candidate if key == "candidate" else key,
            "provides": [] if feed is None else feed.provides(),
            "measures": {"kick_punch": measures.kick_punch(bright, CLIP_FPS, kicks), "alive": measures.alive(bright, silent)},
        })
        print(f"  {clip_id}  {key:9s}  kick punch contrast {feed_meta[-1]['measures']['kick_punch']['contrast']:.3f}", flush=True)

    data, sr = sf.read(str(audio_path), dtype="float32", always_2d=True)
    sf.write(str(dest / "audio.wav"), data[int(start_s * sr) : int((start_s + duration_s) * sr)], sr, subtype="PCM_16")
    meta = {
        "id": clip_id, "built": datetime.date.today().isoformat(), "mode": mode_name,
        "track": {"id": track_id, "file": track["file"], "group": track.get("group")},
        "start_s": start_s, "duration_s": duration_s, "fps": CLIP_FPS, "leds": layout.total, "feeds": feed_meta,
        "kicks": [round(k, 3) for k in kicks], "control_shift_s": round(half_beat, 3),
        "note": "Simulated on screen from the segment layout. Not the real installation: brightness, colour and the room differ.",
    }
    (dest / "meta.json").write_text(json.dumps(_clean(meta), indent=1), encoding="utf-8")
    return dest


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
    p = argparse.ArgumentParser()
    p.add_argument("--mode", default="Kick_bands_mode")
    p.add_argument("--track")
    p.add_argument("--start", type=float, default=30.0)
    p.add_argument("--duration", type=float, default=20.0)
    p.add_argument("--candidate", default=DEFAULT_CANDIDATE, help="analyzer whose recording feeds the 'candidate' version")
    p.add_argument("--defaults", action="store_true", help="build the three standard passages")
    args = p.parse_args()
    jobs = DEFAULT_CLIPS if args.defaults or not args.track else ((args.track, args.start, args.duration),)
    for track_id, start, duration in jobs:
        print(f"wrote {build_clip(args.mode, track_id, start, duration, args.candidate)}")


if __name__ == "__main__":
    main()
