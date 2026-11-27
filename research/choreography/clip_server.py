"""Clip page of the choreography lab: the owner watches versions of a clip side by side and says which is best.

Run from the repository root:
    python -m research.choreography.clip_server
then open http://127.0.0.1:8768

Serves clips.html, the clips built by build_clips.py (output/clips/), and the LED layout. The clips of the queue
that still wait for the owner (queue.json entries no verdict names yet) are listed first. Each choice the owner
makes is appended to verdicts.jsonl: that file is the owner's word and is committed.
"""
from __future__ import annotations

import datetime
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from research.choreography import records
from research.choreography.layout import load_layout

HERE = Path(__file__).resolve().parent
CLIPS = HERE / "output" / "clips"
VERDICTS = HERE / "verdicts.jsonl"
PORT = 8768
TYPES = {".bin": "application/octet-stream", ".wav": "audio/wav", ".json": "application/json; charset=utf-8"}


def list_clips(clips_dir: Optional[Path] = None, queue_path: Path = records.QUEUE, verdicts_path: Optional[Path] = None) -> list:
    """Every clip built here. The ones waiting for the owner come first, in the order they were nominated."""
    clips_dir, verdicts_path = clips_dir or CLIPS, verdicts_path or VERDICTS
    still = {e["clip"]: (i, e) for i, e in enumerate(records.waiting(records.read_queue(queue_path), records.read_verdicts(verdicts_path)))}
    out = []
    for meta in sorted(clips_dir.glob("*/meta.json")):
        clip = json.loads(meta.read_text(encoding="utf-8"))
        clip["waiting"] = clip["id"] in still
        clip["queue"] = still[clip["id"]][1] if clip["waiting"] else None
        out.append(clip)
    out.sort(key=lambda c: (0, still[c["id"]][0]) if c["waiting"] else (1, 0))        # stable: the rest stay in name order
    return out


def waiting_queue(clips_dir: Optional[Path] = None, queue_path: Path = records.QUEUE, verdicts_path: Optional[Path] = None) -> dict:
    """The queue entries still waiting, each with whether its clip is built on this computer."""
    clips_dir, verdicts_path = clips_dir or CLIPS, verdicts_path or VERDICTS
    still = records.waiting(records.read_queue(queue_path), records.read_verdicts(verdicts_path))
    return {"waiting": [{**e, "built": (clips_dir / str(e.get("clip")) / "meta.json").is_file()} for e in still]}


def _clip_meta(clip_id: str, clips_dir: Path) -> dict:
    target = (clips_dir / clip_id / "meta.json").resolve()
    if clips_dir.resolve() != target.parent.parent or not target.is_file():
        raise ValueError("unknown clip")
    return json.loads(target.read_text(encoding="utf-8"))


def save_verdict(body: dict, verdicts_path: Optional[Path] = None, clips_dir: Optional[Path] = None) -> dict:
    """Append one choice of the owner. Nothing is ever rewritten.

    What was chosen is read from the clip's own meta.json, not taken from the page: the feed and, for a
    mode-against-mode clip, the mode of the chosen version.
    """
    if not isinstance(body.get("clip"), str) or body.get("choice") not in ("A", "B", "C", "none"):
        raise ValueError("clip and choice are required")
    meta = _clip_meta(body["clip"], clips_dir or CLIPS)
    versus = meta.get("kind") == "modes"
    key = body.get("chosen_version", body.get("chosen_feed"))
    version = None if body["choice"] == "none" else next((f for f in meta["feeds"] if f["key"] == key and not f.get("hidden")), None)
    if body["choice"] != "none" and version is None:
        raise ValueError("the chosen version is not one of this clip's versions")
    row = {
        "at": datetime.datetime.now().isoformat(timespec="seconds"),
        "clip": body["clip"], "choice": body["choice"],
        "order": body.get("order"),                    # which version was shown as A, B, C (feeds, or modes in a modes clip)
        "chosen_feed": None if version is None else version.get("feed", version["key"]),
        "labels_hidden": bool(body.get("labels_hidden", True)),
        "note": str(body.get("note", ""))[:500],
        "kind": "modes" if versus else "feeds",        # what the versions of this clip were
        "mode": meta.get("mode"),                      # the mode of the clip (the first of the two in a modes clip)
        "against": meta.get("against"),                # the other mode of a modes clip, else null
        "feed": meta.get("feed"),                      # what both modes heard in a modes clip, else null
        "chosen_mode": version.get("mode") if versus and version is not None else None,     # the mode the owner preferred
    }
    with open(verdicts_path or VERDICTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _refresh_records() -> None:
    """After a choice: rewrite the lab's status and the owner's inbox. Never lets a verdict fail."""
    try:
        from research import inbox
        from research.choreography import status

        status.write()
        inbox.write()
    except Exception as exc:  # noqa: BLE001
        print(f"could not refresh STATUS.md / INBOX.md: {exc}", flush=True)


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
        elif path == "/api/queue":
            self._json(waiting_queue())
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
            _refresh_records()
        except (ValueError, UnicodeDecodeError) as exc:
            self._json({"error": str(exc)}, 400)

    def log_message(self, *args) -> None:
        pass


if __name__ == "__main__":
    print(f"Choreography clips on http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
