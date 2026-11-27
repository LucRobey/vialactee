"""Clip page of the choreography lab: the owner watches versions of a clip side by side and says which is best.

Run from the repository root:
    python -m research.choreography.clip_server
then open http://127.0.0.1:8768

Serves clips.html, the clips built by build_clips.py (output/clips/), and the LED layout. Each choice the owner
makes is appended to verdicts.jsonl: that file is the owner's word and is committed.
"""
from __future__ import annotations

import datetime
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from research.choreography.layout import load_layout

HERE = Path(__file__).resolve().parent
CLIPS = HERE / "output" / "clips"
VERDICTS = HERE / "verdicts.jsonl"
PORT = 8768
TYPES = {".bin": "application/octet-stream", ".wav": "audio/wav", ".json": "application/json; charset=utf-8"}


def list_clips() -> list:
    out = []
    for meta in sorted(CLIPS.glob("*/meta.json")):
        out.append(json.loads(meta.read_text(encoding="utf-8")))
    return out


def save_verdict(body: dict) -> dict:
    """Append one choice of the owner. Nothing is ever rewritten."""
    if not isinstance(body.get("clip"), str) or body.get("choice") not in ("A", "B", "C", "none"):
        raise ValueError("clip and choice are required")
    row = {
        "at": datetime.datetime.now().isoformat(timespec="seconds"),
        "clip": body["clip"], "choice": body["choice"],
        "order": body.get("order"),                    # which feed was shown as A, B, C
        "chosen_feed": body.get("chosen_feed"),
        "labels_hidden": bool(body.get("labels_hidden", True)),
        "note": str(body.get("note", ""))[:500],
    }
    with open(VERDICTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


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
        if path == "/":
            self._send(200, (HERE / "clips.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/clips":
            self._json(list_clips())
        elif path == "/api/layout":
            layout = load_layout()
            self._json({"xy": layout.xy.round(1).tolist(), "segments": [[s.seg_id, s.offset, s.size] for s in layout.segments]})
        elif path.startswith("/clips/"):
            parts = path.split("/")[2:]
            target = (CLIPS / "/".join(parts)).resolve()
            if len(parts) == 2 and CLIPS.resolve() in target.parents and target.is_file() and target.suffix in TYPES:
                self._send(200, target.read_bytes(), TYPES[target.suffix])
            else:
                self._send(404, b"not found", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        if self.path.split("?")[0] != "/api/verdict" or not 0 < length < 100000:
            self._send(400, b"bad request", "text/plain")
            return
        try:
            self._json(save_verdict(json.loads(self.rfile.read(length).decode("utf-8"))))
        except (ValueError, UnicodeDecodeError) as exc:
            self._json({"error": str(exc)}, 400)

    def log_message(self, *args) -> None:
        pass


if __name__ == "__main__":
    print(f"Choreography clips on http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
