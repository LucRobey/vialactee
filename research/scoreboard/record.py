"""Play one song through the production Listener, as the installation would, and record what it says.

The Listener is stepped offline at 60 frames per second with the real 5 s look-ahead (same stepping as
tools/choreography_probe.py). Frame k describes the music heard at speaker time k / 60 - look-ahead, so every
recorded value is laid on the song's own clock and can be compared with the truth file of that song.

Recorded per frame:
- every slot of listener.signals (config/music_signals.json); a slot that answers None is stored as NaN;
- a few existing signals that are close to an empty slot, to test them as candidates (see CANDIDATE_NOTES).
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import numpy as np

FPS: float = 60.0
TAG_CODES: Dict[str, int] = {"Bass/Kick": 0, "Snare/Mid": 1, "Hi-hat/Cymbal": 2}
CANDIDATE_NOTES: Dict[str, str] = {
    "beat_tag": "the drum that dominates each beat (one label per beat), tested as kick / snare / hat hits",
    "is_locked": "the analyzer's own confidence that it follows the beat; its opposite is tested as no_beat",
    "bands": "the 16-band spectrum at speaker time, grouped into bass / mid / high",
    "flux_low": "sudden rises of the lowest band, tested as kick hits",
    "song_change": "the analyzer's 'a new song starts' flag, which in practice also fires inside songs; tested as section_change",
}


def record_track(mono: np.ndarray, analyzer_class: Optional[Any] = None, lookahead: float = 5.0) -> Dict[str, np.ndarray]:
    """Run the Listener over a 44.1 kHz mono song. Returns arrays with one row per frame, at speaker time."""
    from music.api import Listener
    from music.MusicSignals import FIELDS
    from tools.choreography_probe import HOP, OfflineClock, step_listener
    from tools.listener_config import build_listener_infos

    infos = build_listener_infos()
    infos["fakeDelay"] = lookahead
    lead = int(round(lookahead * FPS))
    n = len(mono) // HOP                      # frames of music at speaker time
    numeric = [f for f in FIELDS if f != "chord"]
    out: Dict[str, np.ndarray] = {f: np.full(n, np.nan, dtype=np.float32) for f in numeric}
    chord = np.full(n, "", dtype=object)
    tag = np.full(n, -1, dtype=np.int8)
    locked = np.zeros(n, dtype=bool)
    trust = np.zeros(n, dtype=np.float32)
    flux_low = np.zeros(n, dtype=np.float32)
    song_change = np.zeros(n, dtype=bool)
    bands: Optional[np.ndarray] = None

    with OfflineClock() as clock:
        listener = Listener(infos, analyzer_class=analyzer_class)
        listener.dynamic_audio_latency = 0.0
        sig, ctx = listener.signals, listener.context
        last_count = listener.beat_count
        spent = 0.0
        for k in range(n + lead):
            t0 = time.perf_counter()
            step_listener(listener, mono, k * HOP, clock)
            spent += time.perf_counter() - t0
            i = k - lead                      # index of the speaker-time frame this tick describes
            beat_now = bool(listener.is_beat) or listener.beat_count > last_count
            last_count = listener.beat_count
            if i < 0:
                continue
            for f in numeric:
                v = getattr(sig, f)
                if v is not None:
                    out[f][i] = float(v)
            if beat_now:                       # a beat counted between two frames is still a beat
                out["beat"][i] = 1.0
                tag[i] = TAG_CODES.get(listener.beat_tag, -1)
            if sig.chord is not None:
                chord[i] = str(sig.chord)
            locked[i] = bool(ctx.is_locked)
            trust[i] = float(listener.beat_trust)
            raw = listener.smoothed_fft_band_values
            if bands is None:
                bands = np.zeros((n, len(raw)), dtype=np.float32)
            bands[i] = raw
            flux_low[i] = float(listener.band_flux[0])
            song_change[i] = bool(listener.is_song_change)

    out.update({
        "chord": chord.astype(str), "cand_beat_tag": tag, "cand_is_locked": locked, "cand_beat_trust": trust,
        "cand_bands": bands if bands is not None else np.zeros((n, 16), dtype=np.float32), "cand_flux_low": flux_low,
        "cand_song_change": song_change,
        "fps": np.array(FPS), "lookahead": np.array(lookahead),
        "frame_ms": np.array(1000.0 * spent / max(1, n + lead)),      # audio front end + analyzer + context, per tick
    })
    return out


def band_centres_hz(n_bands: int = 16) -> np.ndarray:
    """Centre frequency of each Mel band of AudioIngestion (20 Hz to 20 kHz), to group them like the truth bands."""
    def hz_to_mel(f: float) -> float:
        return 2595.0 * np.log10(1.0 + f / 700.0)

    mel = np.linspace(hz_to_mel(20.0), hz_to_mel(20000.0), n_bands + 2)
    return (700.0 * (10.0 ** (mel / 2595.0) - 1.0))[1:-1]
