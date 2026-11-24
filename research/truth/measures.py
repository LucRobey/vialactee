"""Direct measurements on the mix and on its stems: no trained model here, only levels and spectra.

Everything is sampled on one clock, CURVE_HZ values per second, frame i centred on i / CURVE_HZ seconds.
Levels are in dB relative to full scale (a full-scale sine reads about -3 dB).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

CURVE_HZ: int = 20
N_FFT: int = 4096
EPS: float = 1e-12

SILENCE_DB: float = -50.0          # mix under this level is silence
SILENCE_MIN_S: float = 0.5
STEM_FLOOR_DB: float = -45.0       # a stem under this level is never "present"
STEM_REL_DB: Dict[str, float] = {"drums": 18.0, "bass": 18.0, "vocals": 15.0, "other": 18.0}
STEM_HYST_DB: float = 3.0
STEM_MIN_S: float = 1.0
STEM_BRIDGE_S: float = 0.6
KICK_BAND: Tuple[float, float] = (30.0, 150.0)
KICK_DROP_DB: float = 12.0         # a kick is a low-band peak within this many dB of the track's loud kicks
KICK_MIN_REF_DB: float = -50.0     # under this, the track has no kick to speak of
KICK_GAP_S: float = 2.0            # kicks further apart than this are two separate stretches
KICK_MIN_EVENTS: int = 4
BREAKDOWN_MIN_S: float = 6.0
RISER_WINDOW_S: float = 4.0
RISER_MIN_OCT: float = 0.7
FULLNESS_BANDS: Tuple[float, ...] = (40, 80, 160, 320, 640, 1280, 2560, 5120, 16000)
FULLNESS_DROP_DB: float = 15.0


def load_mono(path: str) -> Tuple[np.ndarray, int]:
    import soundfile as sf

    data, sr = sf.read(path, dtype="float32", always_2d=True)
    return data.mean(axis=1), int(sr)


def spectra(y: np.ndarray, sr: int, hz: int = CURVE_HZ, n_fft: int = N_FFT) -> Tuple[np.ndarray, np.ndarray]:
    """Power spectra, scaled so that summing bins gives the mean square of the signal in that band."""
    hop = int(round(sr / hz))
    n = max(1, 1 + (len(y) - 1) // hop)
    pad = n_fft // 2
    yp = np.concatenate([np.zeros(pad, np.float32), y.astype(np.float32), np.zeros(pad + hop, np.float32)])
    win = np.hanning(n_fft).astype(np.float32)
    scale = 2.0 / (n_fft * float(np.sum(win**2)))
    power = np.empty((n, n_fft // 2 + 1), np.float32)
    offsets = np.arange(n_fft)[None, :]
    for a in range(0, n, 256):
        idx = np.arange(a, min(n, a + 256))[:, None] * hop + offsets
        power[a : a + idx.shape[0]] = (np.abs(np.fft.rfft(yp[idx] * win, axis=1)) ** 2) * scale
    return power, np.fft.rfftfreq(n_fft, 1.0 / sr)


def band_db(power: np.ndarray, freqs: np.ndarray, lo: float, hi: float) -> np.ndarray:
    m = (freqs >= lo) & (freqs < hi)
    return 10.0 * np.log10(power[:, m].sum(axis=1) + EPS)


def centroid_oct(power: np.ndarray, freqs: np.ndarray, lo: float = 50.0, hi: float = 16000.0) -> np.ndarray:
    """Brightness: centre of mass of the spectrum, in octaves (log2 of Hz). NaN where there is no sound."""
    m = (freqs >= lo) & (freqs < hi)
    w = power[:, m]
    tot = w.sum(axis=1)
    c = (w * np.log2(freqs[m])[None, :]).sum(axis=1) / (tot + EPS)
    c[10.0 * np.log10(tot + EPS) < -70.0] = np.nan
    return c


def smooth(x: np.ndarray, seconds: float, hz: int = CURVE_HZ) -> np.ndarray:
    """Centred moving average that ignores NaN."""
    k = max(1, int(round(seconds * hz)) | 1)
    ok = np.isfinite(x).astype(np.float64)
    kern = np.ones(k)
    num = np.convolve(np.nan_to_num(x) * ok, kern, mode="same")
    den = np.convolve(ok, kern, mode="same")
    out = np.full(len(x), np.nan)
    np.divide(num, den, out=out, where=den > 0)
    return out


def hysteresis(x: np.ndarray, on: float, off: float) -> np.ndarray:
    out = np.zeros(len(x), dtype=bool)
    state = False
    for i, v in enumerate(x):
        state = (v > off) if state else (v > on)
        out[i] = state
    return out


def regions(mask: np.ndarray, hz: int = CURVE_HZ, min_s: float = 0.0, bridge_s: float = 0.0) -> List[List[float]]:
    """Turn a yes/no curve into [start, end] stretches; close short gaps first, then drop short stretches."""
    edges = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(np.int8), [0]))))
    segs = [[a / hz, b / hz] for a, b in zip(edges[::2], edges[1::2])]
    merged: List[List[float]] = []
    for s in segs:
        if merged and s[0] - merged[-1][1] <= bridge_s:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [[round(a, 2), round(b, 2)] for a, b in merged if b - a >= min_s]


def regions_to_mask(regs: Sequence[Sequence[float]], n: int, hz: int = CURVE_HZ) -> np.ndarray:
    m = np.zeros(n, dtype=bool)
    for a, b in regs:
        m[max(0, int(round(a * hz))) : max(0, int(round(b * hz)))] = True
    return m


def coverage(reg: Sequence[float], others: Sequence[Sequence[float]]) -> float:
    """Share of one stretch that is covered by a list of stretches."""
    a, b = reg[0], reg[1]
    if b <= a:
        return 0.0
    return float(sum(max(0.0, min(b, y) - max(a, x)) for x, y in others) / (b - a))


def stem_presence(stem_db: np.ndarray, mix_db: np.ndarray, rel_db: float) -> np.ndarray:
    """A stem is present when it is loud in itself and not far under the mix."""
    d = smooth(stem_db, 0.5) - smooth(mix_db, 0.5)
    mask = hysteresis(d, -rel_db, -rel_db - STEM_HYST_DB)
    return mask & (smooth(stem_db, 0.5) > STEM_FLOOR_DB)


def peak_times(x: np.ndarray, threshold: float, min_sep_s: float = 0.15, hz: int = CURVE_HZ) -> np.ndarray:
    """Times of local maxima of x at or above threshold, at least min_sep_s apart (strongest wins)."""
    idx = np.flatnonzero((x[1:-1] >= threshold) & (x[1:-1] >= x[:-2]) & (x[1:-1] > x[2:])) + 1
    keep: List[int] = []
    sep = max(1, int(round(min_sep_s * hz)))
    for i in idx[np.argsort(-x[idx], kind="stable")]:
        if all(abs(i - j) >= sep for j in keep):
            keep.append(int(i))
    return np.sort(np.array(keep, dtype=float)) / hz


def cluster_events(times: Sequence[float], gap_s: float = KICK_GAP_S, min_events: int = KICK_MIN_EVENTS) -> List[List[float]]:
    """Stretches where events keep coming: consecutive events at most gap_s apart, at least min_events of them."""
    out: List[List[float]] = []
    run: List[float] = []
    for t in list(times) + [float("inf")]:
        if run and t - run[-1] > gap_s:
            if len(run) >= min_events:
                out.append([round(run[0], 2), round(run[-1] + 0.3, 2)])
            run = []
        run.append(t)
    return out


def kick_regions(kick_db: np.ndarray, mix_db: np.ndarray) -> Tuple[List[List[float]], np.ndarray, Optional[float]]:
    """Stretches where a kick keeps coming, from the low band of the drum stem. Returns (regions, kick times, ref)."""
    audible = kick_db[mix_db > SILENCE_DB]
    if len(audible) == 0:
        return [], np.array([]), None
    ref = float(np.percentile(audible, 95))
    if ref < KICK_MIN_REF_DB:
        return [], np.array([]), ref
    times = peak_times(kick_db, ref - KICK_DROP_DB)
    return cluster_events(times), times, ref


def breakdowns(kick_regs: List[List[float]], mix_db: np.ndarray) -> Tuple[List[Dict], List[Dict]]:
    """Gaps between two kick stretches (the kick leaves and comes back), with the size of the return."""
    regs: List[Dict] = []
    moments: List[Dict] = []
    two = 2 * CURVE_HZ
    for (_, end), (start, _) in zip(kick_regs[:-1], kick_regs[1:]):
        if start - end < BREAKDOWN_MIN_S:
            continue
        i = int(round(start * CURVE_HZ))
        before, after = mix_db[max(0, i - two) : i], mix_db[i : i + two]
        jump = float(np.mean(after) - np.mean(before)) if len(before) and len(after) else 0.0
        regs.append({"start": end, "end": start})
        moments.append({"t": end, "kind": "kick_out"})
        moments.append({"t": start, "kind": "kick_return", "loudness_jump_db": round(jump, 1)})
    return regs, moments


def riser_regions(bright_oct: np.ndarray, mix_db: np.ndarray) -> List[Dict]:
    """Stretches where the sound keeps getting brighter (filter opening, riser)."""
    w = int(round(RISER_WINDOW_S * CURVE_HZ))
    b = smooth(bright_oct, 1.0)
    if len(b) <= w:
        return []
    rise = np.concatenate([b[w:] - b[:-w], np.full(w, np.nan)])
    mask = np.nan_to_num(rise, nan=-1.0) >= RISER_MIN_OCT
    mask &= mix_db > SILENCE_DB + 5.0
    out: List[Dict] = []
    for a, e in regions(mask, min_s=2.0, bridge_s=1.0):
        end = min(len(b) - 1, int(round(e * CURVE_HZ)) + w)
        i0 = int(round(a * CURVE_HZ))
        if not (np.isfinite(b[i0]) and np.isfinite(b[end])):
            continue
        out.append({"start": a, "end": round(end / CURVE_HZ, 2), "rise_oct": round(float(b[end] - b[i0]), 2)})
    return out


def fullness(power: np.ndarray, freqs: np.ndarray) -> np.ndarray:
    """Share of the octave bands that are active (each compared with its own loud level in this track)."""
    active = np.zeros(power.shape[0])
    edges = FULLNESS_BANDS
    for lo, hi in zip(edges[:-1], edges[1:]):
        db = smooth(band_db(power, freqs, lo, hi), 0.5)
        active += db >= np.percentile(db, 90) - FULLNESS_DROP_DB
    return active / (len(edges) - 1)


def measure_track(mix_path: str, stem_paths: Dict[str, str]) -> Tuple[Dict[str, np.ndarray], Dict[str, list], Dict]:
    """All direct measurements for one track. Returns (curves, regions, info)."""
    y, sr = load_mono(mix_path)
    power, freqs = spectra(y, sr)
    n = power.shape[0]
    mix_db = band_db(power, freqs, 0.0, sr)
    curves: Dict[str, np.ndarray] = {
        "loud_db": mix_db,
        "sub_db": band_db(power, freqs, 20.0, 60.0),
        "bass_db": band_db(power, freqs, 60.0, 250.0),
        "mid_db": band_db(power, freqs, 250.0, 4000.0),
        "high_db": band_db(power, freqs, 4000.0, sr),
        "bright_oct": centroid_oct(power, freqs),
        "fullness": fullness(power, freqs),
    }
    regs: Dict[str, list] = {"silence": regions(mix_db < SILENCE_DB, min_s=SILENCE_MIN_S)}
    info: Dict = {"duration": round(len(y) / sr, 2), "sr": sr}
    del power

    layers = np.zeros(n)
    for name, path in stem_paths.items():
        ys, srs = load_mono(path)
        ps, fs = spectra(ys, srs)
        ps = ps[:n] if ps.shape[0] >= n else np.pad(ps, ((0, n - ps.shape[0]), (0, 0)))
        db = band_db(ps, fs, 0.0, srs)
        curves[f"stem_{name}_db"] = db
        present = stem_presence(db, mix_db, STEM_REL_DB.get(name, 18.0))
        layers += present
        regs[f"{name}_present"] = regions(present, min_s=STEM_MIN_S, bridge_s=STEM_BRIDGE_S)
        if name == "drums":
            kick = band_db(ps, fs, *KICK_BAND)
            curves["kick_db"] = kick
            kregs, ktimes, ref = kick_regions(kick, mix_db)
            regs["kick_present"] = kregs
            info["kick_times"] = [round(float(t), 2) for t in ktimes]
            info["kick_ref_db"] = None if ref is None else round(ref, 1)
            regs["breakdown"], info["moments"] = breakdowns(kregs, mix_db)
        del ps
    curves["layers"] = layers
    regs["riser"] = riser_regions(curves["bright_oct"], mix_db)
    return curves, regs, info
