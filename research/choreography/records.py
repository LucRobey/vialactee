"""The lab's small committed records, and the rules that read them.

    queue.json       clips nominated for the owner to judge (nominate.py appends an entry per clip)
    verdicts.jsonl   every choice the owner made (clip_server.py appends a line; nothing is ever rewritten)
    gates.json       the latest gate result of each mode (check_mode.py writes it)

Two rules live here, so every tool applies them the same way:

- An entry of the queue is "waiting" exactly when no line of verdicts.jsonl has the same "clip" value.
- A gate result counts only for the code it was measured on: if the mode's file has changed since, the gate is
  stale and has to be run again.

Nothing here imports the heavy parts of the lab, so the clip page and the status record load fast.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
QUEUE = HERE / "queue.json"
VERDICTS = HERE / "verdicts.jsonl"
GATES = HERE / "gates.json"
CANDIDATES = HERE / "candidates"          # lab modes
PRODUCTION_MODES = REPO / "modes"         # registered modes of the installation
CLIPS = HERE / "output" / "clips"
MODE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
RULE_NAMES: Dict[int, str] = {1: "it runs", 2: "works on today's analyzer", 3: "flash safety", 4: "tied to the music", 5: "cost"}
QUEUE_KEYS = ("clip", "mode", "against", "feed", "track", "start_s", "duration_s", "nominated", "note")


def today() -> str:
    return datetime.date.today().isoformat()


def clip_name(track_id: str, start_s: float, mode: str, against: Optional[str] = None, feed: Optional[str] = None, tag: str = "") -> str:
    """The id of a clip, which is also its folder name. `tag` tells two builds of the same comparison apart."""
    base = f"{track_id}_{int(start_s):04d}_{mode}" + (f"_vs_{against}_{feed}" if against else "")
    return base + (f"_{tag}" if tag else "")


# -- the queue and the verdicts ------------------------------------------------------------------------
def read_queue(path: Path = QUEUE) -> List[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8") or "[]")
    if not isinstance(data, list):
        raise ValueError(f"{path} must hold a list")
    return data


def write_queue(entries: List[dict], path: Path = QUEUE) -> None:
    path.write_text(json.dumps(entries, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def read_verdicts(path: Path = VERDICTS) -> List[dict]:
    """Every line of verdicts.jsonl, oldest first. Read only: this file is the owner's word."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def judged_clips(verdicts: Iterable[dict]) -> Set[str]:
    return {v["clip"] for v in verdicts if isinstance(v.get("clip"), str)}


def waiting(queue: Iterable[dict], verdicts: Iterable[dict]) -> List[dict]:
    """The queue entries no verdict line names yet, in the order they were nominated."""
    seen = judged_clips(verdicts)
    return [e for e in queue if e.get("clip") not in seen]


def verdict_mode(verdict: dict) -> Optional[str]:
    """The mode a verdict line is about. Lines written before the "mode" field existed carry it in the clip id."""
    if verdict.get("mode"):
        return verdict["mode"]
    m = re.match(r"^[^_]+_\d{4}_(.+)$", str(verdict.get("clip", "")))
    return m.group(1) if m else None


# -- the modes and their gates -------------------------------------------------------------------------
def mode_file(name: str, candidates: Path = CANDIDATES, production: Path = PRODUCTION_MODES) -> Optional[Path]:
    """The file of a mode: a lab candidate first, else a registered mode. None when there is no such mode."""
    if not MODE_NAME.match(name or ""):
        return None
    for folder in (candidates, production):
        path = folder / f"{name}.py"
        if path.is_file():
            return path
    return None


def is_candidate(name: str, candidates: Path = CANDIDATES) -> bool:
    return bool(MODE_NAME.match(name or "")) and (candidates / f"{name}.py").is_file()


def candidate_names(candidates: Path = CANDIDATES) -> List[str]:
    return sorted(p.stem for p in candidates.glob("*.py") if not p.stem.startswith("_"))


def source_sha(path: Optional[Path]) -> Optional[str]:
    """A short fingerprint of a mode's file (line endings ignored), to know whether it changed since its gate."""
    if path is None or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]


def read_gates(path: Path = GATES) -> Dict[str, dict]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8") or "{}")


def write_gate(mode: str, record: Dict[str, Any], path: Path = GATES) -> None:
    """Keep the latest gate result of one mode. The other modes' results are left as they are."""
    gates = read_gates(path)
    gates[mode] = record
    path.write_text(json.dumps(dict(sorted(gates.items())), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def gate_problem(name: str, gates: Dict[str, dict], candidates: Path = CANDIDATES, production: Path = PRODUCTION_MODES) -> Optional[str]:
    """Why this mode may not go to the owner yet, in words. None when its latest gate passed on its current code."""
    record = gates.get(name)
    if record is None:
        return f"{name} has never been through the gate: run check_mode on it first"
    if not record.get("passed"):
        failed = ", ".join(f"{n} ({RULE_NAMES.get(n, '?')})" for n in record.get("failed_rules", [])) or "see its GATE.md"
        return f"{name} failed its latest gate ({record.get('date')}): rule {failed}"
    now = source_sha(mode_file(name, candidates, production))
    if record.get("source_sha") and now and record["source_sha"] != now:
        return f"{name} has changed since its gate of {record.get('date')}: run check_mode on it again"
    return None
