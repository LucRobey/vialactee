"""Signal feeds: what a mode under test hears through listener.signals.

A feed is a table with one row per frame (60 per second, at speaker time) and one column per slot of the
signal contract (config/music_signals.json). NaN means "this feed does not provide the slot": the slot is then
left as the production Listener set it. The lab knows three kinds of feed:

    truth        every slot, read from a truth file (research/truth/tracks/<id>.json): the best a mode can get
    recording    the slots a given analyzer produced on that song, as recorded by the music lab's scoreboard
    today        no table at all: the mode hears the production analyzer as it is

The choreography lab never imports the music lab's code. A recording is a data file whose columns are the
contract's slot names; that file and the contract are all the two labs share.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

FPS: float = 60.0
REPO = Path(__file__).resolve().parents[2]
TRUTH_DIR = REPO / "research" / "truth" / "tracks"
RECORDINGS_DIR = REPO / "research" / "scoreboard" / "output"     # <model>/<track id>.npz, written by the music lab
SIGNALS = json.loads((REPO / "config" / "music_signals.json").read_text(encoding="utf-8"))["signals"]
SLOTS: List[str] = [s["name"] for s in SIGNALS]
TYPES: Dict[str, str] = {s["name"]: s["type"] for s in SIGNALS}
KINDS: Dict[str, str] = {s["name"]: s["kind"] for s in SIGNALS}
LEVEL_RANGE_DB: float = 50.0       # a truth level of 0 is this far under the track's loud level
BRIGHT_LOW_OCT, BRIGHT_HIGH_OCT = 7.0, 12.5


class Feed:
    """One table of slot values per frame. `apply` writes row i into a MusicSignals record."""

    def __init__(self, name: str, columns: Dict[str, np.ndarray], chords: Optional[np.ndarray] = None) -> None:
        self.name = name
        self.columns = columns
        self.chords = chords
        self.n = min(len(c) for c in columns.values()) if columns else 0
        self._names = [n for n in SLOTS if n in columns]

    def shifted(self, seconds: float, name: str = "control") -> "Feed":
        """The same feed with every moment (hits, beats, drops) moved later by `seconds`: a deliberately wrong feed.

        A mode that really follows its signals looks clearly worse on it; a mode whose numbers barely change was
        never tied to the music.
        """
        k = int(round(seconds * FPS))
        cols = dict(self.columns)
        for slot in SLOTS:
            if KINDS.get(slot) == "event" and slot in cols:
                moved = np.zeros_like(cols[slot])
                if 0 < k < len(moved):
                    moved[k:] = cols[slot][:-k]
                cols[slot] = moved
        return Feed(name, cols, self.chords)

    def provides(self) -> List[str]:
        return [n for n in self._names if np.isfinite(self.columns[n]).any()] + (["chord"] if self.chords is not None else [])

    def apply(self, i: int, signals: Any) -> None:
        if i < 0 or i >= self.n:
            return
        for name in self._names:
            v = self.columns[name][i]
            if v != v:                       # NaN: this feed leaves the slot alone
                continue
            kind = TYPES[name]
            setattr(signals, name, bool(v) if kind == "bool" else int(v) if kind == "int" else float(v))
        if self.chords is not None:
            signals.chord = str(self.chords[i])


def _mask(regions: List[dict], n: int) -> np.ndarray:
    m = np.zeros(n, dtype=np.float32)
    for r in regions:
        m[max(0, int(round(r["start"] * FPS))) : max(0, int(round(r["end"] * FPS)))] = 1.0
    return m


def _events(times: List[float], strengths: List[float], n: int) -> np.ndarray:
    col = np.zeros(n, dtype=np.float32)
    for t, s in zip(times, strengths):
        i = int(round(t * FPS))
        if 0 <= i < n:
            col[i] = max(col[i], s)
    return col


def _held(times: np.ndarray, values: np.ndarray, n: int) -> np.ndarray:
    """A value that holds from one beat to the next."""
    col = np.zeros(n, dtype=np.float32)
    if len(times):
        # read half a frame late, so the frame a beat falls on already carries that beat's value
        idx = np.clip(np.searchsorted(times, (np.arange(n) + 0.5) / FPS, side="right") - 1, 0, len(times) - 1)
        col[:] = values[idx]
        col[: max(0, int(round(times[0] * FPS)))] = 0.0
    return col


def _level(db: np.ndarray, n: int) -> np.ndarray:
    """A truth curve in dB (20 values per second) as a 0..1 level at 60 frames per second."""
    top = float(np.percentile(db[db > -80.0], 99)) if (db > -80.0).any() else 0.0
    lvl = np.clip(1.0 + (db - top) / LEVEL_RANGE_DB, 0.0, 1.0)
    return np.repeat(lvl, 3)[:n] if len(lvl) * 3 >= n else np.pad(np.repeat(lvl, 3), (0, n - len(lvl) * 3))


def truth_feed(track_id: str, truth_dir: Path = TRUTH_DIR) -> Feed:
    """Every slot of the contract, from the truth file of one track."""
    truth = json.loads((truth_dir / f"{track_id}.json").read_text(encoding="utf-8"))
    with np.load(truth_dir / f"{track_id}.curves.npz") as z:
        curves = {k: z[k].astype(np.float64) for k in z.files}
    n = int(truth["track"]["duration"] * FPS)
    regions = truth["regions"]
    beats = [b for b in truth["beats"] if b["main"] and not b["no_beat"]]
    bt = np.array([b["t"] for b in beats])
    pieces = truth["drums"]["pieces"]
    cols: Dict[str, np.ndarray] = {
        "beat": _events(list(bt), [1.0] * len(bt), n),
        "bpm": _held(bt, np.array([b["bpm"] for b in beats], dtype=np.float32), n),
        "no_beat": _mask(regions.get("no_beat", []), n),
        "bar_position": _held(bt, np.array([b["bar_pos"] for b in beats], dtype=np.float32), n),
        "beats_per_bar": np.full(n, truth["meter"]["beats_per_bar"], dtype=np.float32),
        "beat_strength": _held(bt, np.array([b["strength"] or 0.0 for b in beats], dtype=np.float32), n),
        "drop": _events([d["t"] for d in truth.get("drops", [])], [1.0] * len(truth.get("drops", [])), n),
        "section_change": _events([s["t"] for s in truth["sections"]["items"]], [1.0] * len(truth["sections"]["items"]), n),
        "layers": np.repeat(curves["layers"], 3)[:n],
        "brightness": np.repeat(np.clip((np.nan_to_num(curves["bright_oct"], nan=BRIGHT_LOW_OCT) - BRIGHT_LOW_OCT)
                                        / (BRIGHT_HIGH_OCT - BRIGHT_LOW_OCT), 0.0, 1.0), 3)[:n],
        "fullness": np.repeat(curves["fullness"], 3)[:n],
    }
    for piece in ("kick", "snare", "hat", "tom", "cymbal"):
        rows = [r for r in pieces.get(piece, []) if r[2] != "W"]
        cols[piece] = _events([r[0] for r in rows], [max(0.05, float(r[1])) for r in rows], n)
    for name in ("kick_present", "breakdown", "buildup", "riser", "silence", "bass_present", "drums_present", "vocal_present", "other_present"):
        cols[name] = _mask(regions.get(name, []), n)
    for slot, curve in (("kick_level", "kick_db"), ("bass_level", "stem_bass_db"), ("drums_level", "stem_drums_db"),
                        ("vocal_level", "stem_vocals_db"), ("other_level", "stem_other_db"), ("loudness", "loud_db"),
                        ("band_sub", "sub_db"), ("band_bass", "bass_db"), ("band_mid", "mid_db"), ("band_high", "high_db")):
        cols[slot] = _level(curves[curve], n)
    cols = {k: np.pad(v, (0, max(0, n - len(v))))[:n].astype(np.float32) for k, v in cols.items()}
    chords = np.full(n, "N", dtype=object)
    for a, b, label in truth["chords"]["items"]:
        chords[int(a * FPS) : int(b * FPS)] = label
    return Feed("truth", cols, chords.astype(str))


def recording_feed(model: str, track_id: str, recordings_dir: Path = RECORDINGS_DIR) -> Feed:
    """The slots one analyzer produced on one track, from the music lab's recording of it."""
    path = recordings_dir / model / f"{track_id}.npz"
    with np.load(path) as z:
        cols = {name: z[name].astype(np.float32) for name in SLOTS if name in z.files and name != "chord"}
        chords = z["chord"] if "chord" in z.files and (z["chord"] != "").any() else None
    return Feed(model, cols, chords)
