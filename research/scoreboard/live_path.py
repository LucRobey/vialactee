"""Does the analyzer behave on live sound (Spotify, aux) as it does on an audio file?

The scoreboard, the old benchmark and the choreography lab all step the Listener exactly 60 times a second,
which is what the audio-file player does (connectors/Local_AudioFile.py, advance_ingest_frame). Live sound
takes another road (connectors/Local_Microphone.py + core/Mode_master.py):

    the sound card delivers 1024 samples at a time into a 4096-sample window;
    a task recomputes the spectrum from that window about 60 times a second (listen + sleep(1/60));
    the display loop calls listener.update() once per loop, `target_fps` (30) times a second, on the real clock.

This script replays that road offline, on a made-up clock, and grades the beats and the tempo against the truth
exactly as the scoreboard does. It also counts how many one-frame beat flags a 30-per-second display loop
actually sees, since a flag raised and cleared between two reads is lost.

Paths:
    file          60 ticks a second on the audio position (audio file, and every lab tool)
    live          the live road as it was written until 2026-11-27, display loop at 30
    connector     the live road through the real connectors/Local_Microphone.py as it is now (fix A applied)
    live_60       the live road if the display loop ran at 60
    audio_clock   proposed: the live road, with the analyzer ticked by the audio received (735 samples per tick)
    audio_clock_held   the same, and a beat flag stays up until the display loop has read it once

The replay has no jitter: the sound card, the task and the loop are perfectly regular, which the real ones are not.

Run from the repository root:
    research/analyzer_trials/.venv/Scripts/python.exe -m research.scoreboard.live_path [track ids...]
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TRUTH = REPO / "research" / "truth" / "tracks"
TRACKS = json.loads((REPO / "research" / "analyzer_trials" / "tracks.json").read_text(encoding="utf-8"))
SR, CHUNK, WINDOW, HOP = 44100, 1024, 4096, 735
LOOKAHEAD = 5.0
PATHS = ("file", "live", "connector", "live_60", "audio_clock", "audio_clock_held")
DISPLAY_FPS = 30.0


class _Clock:
    """Replaces time.time with a clock the replay sets by hand."""

    def __init__(self) -> None:
        self.t = 1000.0
        self._orig = time.time

    def __enter__(self) -> "_Clock":
        self._orig = time.time
        time.time = lambda: self.t
        return self

    def __exit__(self, *exc) -> None:
        time.time = self._orig


def _window(mono: np.ndarray, end: int) -> np.ndarray:
    """The 4096 samples ending at `end` (zeros before the song starts and after it ends)."""
    out = np.zeros(WINDOW, dtype=np.float32)
    a, b = max(0, end - WINDOW), min(len(mono), end)
    if b > a:
        out[WINDOW - (end - a) : WINDOW - (end - b)] = mono[a:b]
    return out


def replay(mono: np.ndarray, path: str) -> Dict[str, np.ndarray]:
    """Play a song down one path. Returns the beats emitted, the beats a 30 fps display loop saw, and the tempo."""
    from music.api import Listener
    from tools.listener_config import build_listener_infos

    infos = build_listener_infos()
    infos["fakeDelay"] = LOOKAHEAD
    total = len(mono) / SR + LOOKAHEAD + 1.0
    loop_fps = 60.0 if path == "live_60" else 30.0
    by_audio = path.startswith("audio_clock")
    held = [False]
    emitted: List[float] = []
    seen: List[float] = []
    bpm_t: List[float] = []
    bpm_v: List[float] = []

    with _Clock() as clock:
        t0 = clock.t
        listener = Listener(infos)
        last = [listener.beat_count]

        def tick_done(now: float) -> None:
            beat = bool(listener.is_beat) or listener.beat_count > last[0]
            last[0] = listener.beat_count
            if beat:
                emitted.append(now - LOOKAHEAD)
                held[0] = True
            bpm_t.append(now - LOOKAHEAD)
            bpm_v.append(float(listener.bpm))

        if path == "connector":
            import types

            from connectors.Local_Microphone import Local_Microphone

            mic = Local_Microphone(listener, {"useMicrophone": True, "fakeDelay": 0.0})
            info = types.SimpleNamespace(currentTime=0.0, inputBufferAdcTime=0.0)
            sent = 0
            for j in range(1, int(total * 60)):                                     # the task comes back 60 times a second
                now = j / 60.0
                clock.t = t0 + now
                while sent + CHUNK <= int(now * SR):                                # chunks the sound card has delivered
                    chunk = np.zeros(CHUNK, dtype=np.float32)
                    a, b = sent, min(len(mono), sent + CHUNK)
                    if b > a:
                        chunk[: b - a] = mono[a:b]
                    mic.audio_callback(chunk.reshape(-1, 1), CHUNK, info, None)
                    sent += CHUNK
                before = listener.beat_count
                mic.step_analyzer()
                if listener.beat_count > before:
                    emitted.append(now - LOOKAHEAD)
                bpm_t.append(now - LOOKAHEAD)
                bpm_v.append(float(listener.bpm))
                if j % 2 == 0 and listener.is_beat:                                 # the display loop reads at 30
                    seen.append(now - LOOKAHEAD)
        elif path == "file":
            listener.dynamic_audio_latency = 0.0
            n = int(total * 60)
            for k in range(n):
                now = k / 60.0
                clock.t = t0 + now
                listener.process_raw_audio(_window(mono, k * HOP + WINDOW // 2))     # window centred on the tick
                listener.update(fixed_dt=1.0 / 60.0)
                tick_done(now)
                if k % 2 == 1 and listener.is_beat:                                  # the display loop reads every other tick
                    seen.append(now - LOOKAHEAD)
        else:
            listen_dt, loop_dt = 1.0 / 60.0, 1.0 / loop_fps
            events = sorted([(j * listen_dt, 0) for j in range(1, int(total / listen_dt))]
                            + [(m * loop_dt, 1) for m in range(1, int(total / loop_dt))]
                            + ([(m / DISPLAY_FPS + 1e-9, 2) for m in range(1, int(total * DISPLAY_FPS))] if by_audio else []))
            processed = 0
            for now, kind in events:
                clock.t = t0 + now
                received = int(now * SR) // CHUNK * CHUNK                          # samples the sound card has delivered
                if kind == 0 and not by_audio:                                      # the task: spectrum of the newest window
                    listener.dynamic_audio_latency = (now - received / SR) + (WINDOW / 2.0) / SR
                    listener.process_raw_audio(_window(mono, received))
                elif kind == 0:                                                     # proposed: one tick per 735 samples received
                    while processed + HOP <= received:
                        processed += HOP
                        listener.dynamic_audio_latency = (now - processed / SR) + (WINDOW / 2.0) / SR
                        listener.process_raw_audio(_window(mono, processed))
                        listener.update(fixed_dt=1.0 / 60.0)
                        tick_done(now)
                elif kind == 1 and not by_audio:                                    # the display loop ticks the analyzer
                    listener.update()
                    tick_done(now)
                    if listener.is_beat:
                        seen.append(now - LOOKAHEAD)
                elif kind == 2:                                                     # the display loop only reads
                    if (held[0] if path == "audio_clock_held" else listener.is_beat):
                        seen.append(now - LOOKAHEAD)
                    held[0] = False
    return {"emitted": np.array(emitted), "seen": np.array(seen), "bpm_t": np.array(bpm_t), "bpm_v": np.array(bpm_v)}


def _grade(track_id: str, res: Dict[str, np.ndarray]) -> Dict[str, float]:
    """Grade beats and tempo with the scoreboard's own functions, on the checked truth."""
    from research.scoreboard.scoreboard import SPEC, grade_signal

    truth = json.loads((TRUTH / f"{track_id}.json").read_text(encoding="utf-8"))
    with np.load(TRUTH / f"{track_id}.curves.npz") as z:
        curves = {k: z[k] for k in z.files}
    n = int(truth["track"]["duration"] * 60)
    by_name = {s["name"]: s for s in SPEC["signals"]}

    def beat_array(times: np.ndarray) -> np.ndarray:
        arr = np.zeros(n, dtype=np.float32)
        idx = np.round(times[(times >= 0) & (times < n / 60.0)] * 60).astype(int)
        arr[np.clip(idx, 0, n - 1)] = 1.0
        return arr

    bpm = np.full(n, np.nan, dtype=np.float32)
    if len(res["bpm_t"]):
        idx = np.clip(np.searchsorted(res["bpm_t"], np.arange(n) / 60.0, side="right") - 1, 0, len(res["bpm_t"]) - 1)
        bpm = res["bpm_v"][idx].astype(np.float32)
    beat = grade_signal(by_name["beat"], beat_array(res["emitted"]), truth, curves, 60.0)
    seen = grade_signal(by_name["beat"], beat_array(res["seen"]), truth, curves, 60.0)
    tempo = grade_signal(by_name["bpm"], bpm, truth, curves, 60.0)
    return {"beat": beat["checked"], "beat_offset_ms": beat["detail"].get("offset_ms"), "tempo": tempo["checked"],
            "beat_seen_by_display": seen["checked"],
            "share_seen": len(res["seen"]) / len(res["emitted"]) if len(res["emitted"]) else float("nan")}


def _job(job: Tuple[str, str, str]) -> Tuple[str, str, Dict[str, float]]:
    track_id, file, path = job
    from tools.choreography_probe import load_audio_mono

    return track_id, path, _grade(track_id, replay(load_audio_mono(str(REPO / TRACKS["audio_dir"] / file)), path))


def main() -> None:
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    tracks = [t for t in TRACKS["tracks"] if not only or t["id"] in only]
    jobs = [(t["id"], t["file"], p) for t in tracks for p in PATHS]
    results: Dict[str, Dict[str, Dict[str, float]]] = {p: {} for p in PATHS}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=5) as pool:
        for i, (track_id, path, scores) in enumerate(pool.map(_job, jobs), 1):
            results[path][track_id] = scores
            if i % 10 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} runs, {time.time() - t0:.0f}s", flush=True)

    def mean(path: str, key: str) -> float:
        vals = [v[key] for v in results[path].values() if v[key] is not None and v[key] == v[key]]
        return float(np.mean(vals)) if vals else float("nan")

    dest = HERE / "runs" / "live_path"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "scores.json").write_text(json.dumps(results, indent=1, default=lambda o: None), encoding="utf-8")
    print(f"\n{len(tracks)} tracks, production analyzer, averages (0 to 100):")
    print(f"{'path':17s} {'beats':>6s} {'tempo':>6s} {'offset ms':>10s} {'flags seen at 30 fps':>21s} {'beats as seen':>14s}")
    for p in PATHS:
        print(f"{p:17s} {100 * mean(p, 'beat'):6.0f} {100 * mean(p, 'tempo'):6.0f} {mean(p, 'beat_offset_ms'):10.0f} "
              f"{100 * mean(p, 'share_seen'):20.0f}% {100 * mean(p, 'beat_seen_by_display'):14.0f}")
    print(f"per-track numbers: {dest / 'scores.json'}")


if __name__ == "__main__":
    main()
