"""Review tool: local web page where the owner checks the truth draft by eye and ear, and corrects it.

Run from the repository root:
    research/analyzer_trials/.venv/Scripts/python.exe -m research.truth.review_server
then open http://127.0.0.1:8766

It serves review.html, each track's truth draft (tracks/<id>.json), its curves, and the audio as WAV. Corrections
are saved to labels/<id>.json, one file per track. Those files are the owner's word: build_truth.py lays them
over the machine draft and never changes them.
"""
from __future__ import annotations

import datetime
import io
import json
import os
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TRIALS = REPO / "research" / "analyzer_trials"
TRACKS_DIR = HERE / "tracks"
LABELS_DIR = HERE / "labels"
PORT = 8766
MAX_BODY = 8 << 20

_SPEC = json.loads((TRIALS / "tracks.json").read_text(encoding="utf-8"))
TRACKS = {t["id"]: {**t, "path": str(REPO / _SPEC["audio_dir"] / t["file"])} for t in _SPEC["tracks"]}
CURVE_DECIMALS = {"fullness": 2, "bright_oct": 2}


def load_labels(tid: str) -> Optional[dict]:
    p = LABELS_DIR / f"{tid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_labels(tid: str, body: dict) -> dict:
    """Write the owner's corrections for one track (whole file replaced, through a temporary file)."""
    layers = body.get("layers")
    if not isinstance(layers, dict):
        raise ValueError("layers missing")
    doc = {
        "track": tid,
        "file": TRACKS[tid]["file"],
        "saved": datetime.datetime.now().isoformat(timespec="seconds"),
        "about": "Corrections made by ear in the review tool. An item with by='owner' was placed or moved by "
                 "the owner; a layer with reviewed=true was checked whole.",
        "layers": layers,
    }
    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LABELS_DIR / f"{tid}.json.tmp"
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, LABELS_DIR / f"{tid}.json")
    return {"saved": doc["saved"], "layers": sorted(layers)}


def track_payload(tid: str) -> Optional[dict]:
    p = TRACKS_DIR / f"{tid}.json"
    if not p.exists():
        return None
    truth = json.loads(p.read_text(encoding="utf-8"))
    curves = {}
    npz = TRACKS_DIR / f"{tid}.curves.npz"
    if npz.exists():
        with np.load(npz) as z:
            for name in z.files:
                arr = np.nan_to_num(z[name].astype(np.float64), nan=0.0, neginf=-120.0, posinf=0.0)
                curves[name] = np.round(arr, CURVE_DECIMALS.get(name, 1)).tolist()
    return {"truth": truth, "curves": curves, "labels": load_labels(tid)}


def track_list() -> list:
    rows = []
    for tid, t in TRACKS.items():
        lab = load_labels(tid)
        layers = (lab or {}).get("layers", {})
        rows.append({
            "id": tid, "file": t["file"], "group": t.get("group"),
            "built": (TRACKS_DIR / f"{tid}.json").exists(),
            "edited": len(layers),
            "reviewed": sum(1 for v in layers.values() if v.get("reviewed")),
        })
    return rows


@lru_cache(maxsize=2)
def wav_bytes(tid: str) -> bytes:
    import soundfile as sf

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

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]
        tid = path.rsplit("/", 1)[-1].removesuffix(".wav")
        if path == "/":
            self._send(200, (HERE / "review.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/tracks":
            self._json(track_list())
        elif path.startswith("/api/track/") and tid in TRACKS:
            payload = track_payload(tid)
            self._json(payload) if payload else self._json({"error": "no truth file; run build_truth.py"}, 404)
        elif path.startswith("/audio/") and tid in TRACKS:
            self._send(200, wav_bytes(tid), "audio/wav")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]
        tid = path.rsplit("/", 1)[-1]
        length = int(self.headers.get("Content-Length") or 0)
        if not path.startswith("/api/labels/") or tid not in TRACKS or not 0 < length <= MAX_BODY:
            self._send(400, b"bad request", "text/plain")
            return
        try:
            self._json(save_labels(tid, json.loads(self.rfile.read(length).decode("utf-8"))))
        except (ValueError, UnicodeDecodeError) as exc:
            self._json({"error": str(exc)}, 400)

    def log_message(self, *args) -> None:  # keep the console quiet
        pass


if __name__ == "__main__":
    print(f"Truth review on http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
