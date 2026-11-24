"""Beat viewer: local web page to check the trackers by eye and ear.

Run:  .venv/Scripts/python.exe beat_viewer.py     then open http://127.0.0.1:8765

Serves viewer.html plus, per track, the tool outputs from output/ and the audio as WAV. The WAV is decoded
here with libsndfile (the decoder the trial scripts used), so the browser plays the same samples the tools saw.
"""
from __future__ import annotations

import io
import json
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import soundfile as sf

from common import HERE, OUT, load_tracks

PORT = 8765
TRACKS = {t["id"]: t for t in load_tracks()}


def read_json(kind: str, tid: str):
    p = OUT / kind / f"{tid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def compare(a: list[float], b: list[float], duration: float) -> dict | None:
    """How tracker `a` relates to tracker `b`: share of a's beats within 70 ms of a b beat, the median distance,
    and whether a's beats run past the end of the song (a broken time base, not a musical disagreement)."""
    if len(a) < 3 or len(b) < 3:
        return None
    x, y = np.asarray(a), np.asarray(b)
    idx = np.clip(np.searchsorted(y, x), 1, len(y) - 1)
    d = np.minimum(np.abs(x - y[idx - 1]), np.abs(x - y[idx]))
    period = float(np.median(np.diff(y)))
    return {
        "agree": round(float(np.mean(d < 0.07)), 2),
        "median_ms": round(float(np.median(d)) * 1000),
        "median_fraction": round(float(np.median(d)) / period, 2),
        "overrun": round(float(x[-1]) / duration, 2) if x[-1] > duration + 3 else None,
    }


def duration(tid: str) -> float:
    info = sf.info(TRACKS[tid]["path"])
    return info.frames / info.samplerate


def bpm(beats: list[float]) -> float | None:
    return round(60.0 / float(np.median(np.diff(beats))), 1) if len(beats) > 2 else None


def track_payload(tid: str) -> dict:
    t = TRACKS[tid]
    beats = read_json("beats", tid) or {}
    trackers = {}
    beats["beatnet_rerun"] = read_json("beatnet", tid)  # run_beatnet.py: BeatNet on correctly decoded audio
    for key in ("beat_this", "beatnet_rerun", "beatnet_existing", "librosa"):
        r = beats.get(key) or {}
        trackers[key] = {"beats": r.get("beats", []), "downbeats": r.get("downbeats", []), "bpm": bpm(r.get("beats", []))}
    grid = read_json("grid", tid)  # build_grid.py: the trackers combined (average time, votes per beat)
    gb = [b["t"] for b in grid["beats"]] if grid else []
    trackers["combined"] = {"beats": gb, "downbeats": [], "bpm": bpm(gb), "votes": [b["votes"] for b in grid["beats"]] if grid else []}
    if grid and "quiet_regions" in grid:  # add_salience.py has run for this track
        trackers["combined"]["salience"] = [b["salience"] for b in grid["beats"]]
        trackers["combined"]["no_beat"] = [b["no_beat"] for b in grid["beats"]]
    ref = trackers["beat_this"]["beats"]
    return {
        "id": tid,
        "file": t["file"],
        "trackers": trackers,
        "duration": round(duration(tid), 2),
        "vs_beat_this": {k: compare(trackers[k]["beats"], ref, duration(tid)) for k in ("beatnet_rerun", "beatnet_existing", "librosa")},
        "quiet_regions": (grid or {}).get("quiet_regions", []),
        "drum_level": (grid or {}).get("drum_level"),
        "chords": (read_json("chords", tid) or {}).get("chords", []),
        "sections": (read_json("sections", tid) or {}).get("boundaries", []),
        "vocals": (read_json("vocals", tid) or {}).get("segments"),
        "drums": (read_json("drums", tid) or {}).get("hits"),
    }


def track_list() -> list[dict]:
    rows = []
    for tid, t in TRACKS.items():
        b = read_json("beats", tid) or {}
        c = compare((b.get("beatnet_existing") or {}).get("beats", []), (b.get("beat_this") or {}).get("beats", []), duration(tid))
        rows.append({"id": tid, "file": t["file"], "group": t["group"], "cmp": c})
    return rows


@lru_cache(maxsize=2)
def wav_bytes(tid: str) -> bytes:
    data, sr = sf.read(TRACKS[tid]["path"], dtype="float32", always_2d=True)
    buf = io.BytesIO()
    sf.write(buf, data, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj) -> None:
        self._send(200, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]
        tid = path.rsplit("/", 1)[-1].removesuffix(".wav")
        if path == "/":
            self._send(200, (HERE / "viewer.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/tracks":
            self._json(track_list())
        elif path.startswith("/api/track/") and tid in TRACKS:
            self._json(track_payload(tid))
        elif path.startswith("/audio/") and tid in TRACKS:
            self._send(200, wav_bytes(tid), "audio/wav")
        else:
            self._send(404, b"not found", "text/plain")

    def log_message(self, *args) -> None:  # keep the console quiet
        pass


if __name__ == "__main__":
    print(f"Beat viewer on http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
