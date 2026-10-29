"""
tools/choreography_probe.py
Offline real-audio choreography probe running modes through the production Listener and Mood service.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple
import math
import random
import time
import numpy as np

from music.Listener import Listener
from music.DyadicMetricalAudioAnalyzer import DyadicMetricalAudioAnalyzer
from mood.api import create_mood_service
from modes.Mode import Mode
from utils.driver_mute import DriverMuteProxy
from tools.listener_config import PRODUCTION_VISUAL_FFT_BANDS, build_listener_infos
from tools.choreography_matrix import (
    MATRIX_CONFIG,
    compute_response_metrics,
    format_measurement_report,
    load_registered_mode_classes,
    measure_with_runner,
)

HOP: int = 735                      # samples per 60 Hz frame at 44.1 kHz
WINDOW: int = 4096
DEFAULT_WARMUP_FRAMES: int = 600    # Listener ring drains after 300 frames; the rest lets beat trust settle
DEFAULT_START_S: float = 25.0
DEFAULT_DURATION_S: float = 45.0


class OfflineClock:
    """Patches the global time.time with a simulated clock advancing 1/60 s per tick (see fact F5)."""

    def __init__(self, start: float = 1000.0, step: float = 1.0 / 60.0) -> None:
        self._t: float = float(start)
        self._step: float = float(step)
        self._orig = time.time

    def __enter__(self) -> "OfflineClock":
        self._orig = time.time
        time.time = self.now
        return self

    def __exit__(self, *exc: Any) -> None:
        time.time = self._orig

    def now(self) -> float:
        return self._t

    def tick(self) -> None:
        self._t += self._step


def load_audio_mono(path: str) -> np.ndarray:
    """Load an audio file as a 44.1 kHz mono float32 array."""
    import soundfile as sf

    raw_data, sr = sf.read(path, dtype="float32")
    if raw_data.ndim > 1:
        mono = np.mean(raw_data, axis=1).astype(np.float32)
    else:
        mono = raw_data.astype(np.float32)

    if int(sr) != 44100:
        try:
            import scipy.signal as signal
        except ImportError as exc:
            raise ImportError(
                f"Resampling {path!r} from {sr} Hz to 44100 Hz requires scipy (pip install scipy)."
            ) from exc
        gcd = math.gcd(int(sr), 44100)
        up = 44100 // gcd
        down = int(sr) // gcd
        mono = signal.resample_poly(mono, up, down).astype(np.float32)

    return mono


def make_listener(
    nb_bands: int = PRODUCTION_VISUAL_FFT_BANDS,
    analyzer_class: Any = DyadicMetricalAudioAnalyzer,
) -> Listener:
    """Create a production Listener with zero artificial ADC buffer delay."""
    listener = Listener(build_listener_infos(nb_bands), analyzer_class=analyzer_class)
    listener.dynamic_audio_latency = 0.0
    return listener


def step_listener(listener: Listener, mono: np.ndarray, center_sample: int, clock: OfflineClock) -> None:
    """Step the Listener by one 60 Hz frame centered at `center_sample`."""
    chunk = np.zeros(WINDOW, dtype=np.float32)
    s, e = max(0, center_sample - 2048), min(len(mono), center_sample + 2048)
    if e > s:
        chunk[: e - s] = mono[s:e]
    clock.tick()
    listener.process_raw_audio(chunk)
    listener.update(fixed_dt=1.0 / 60.0)


def compute_rhythm_lock(listener: Any) -> float:
    """Mirrors Mode.rhythm_lock (modes/Mode.py L467)."""
    ctx = getattr(listener, "context", None)
    if ctx is not None:
        trust = float(getattr(ctx, "beat_trust", 0.0))
        salience = float(getattr(ctx, "salience", 0.0))
        if salience <= 0.0 and not bool(getattr(ctx, "is_silent", False)):
            salience = float(getattr(listener, "rhythm_salience", 1.0))
    else:
        trust = float(getattr(listener, "beat_confidence", getattr(listener, "beat_trust", 0.0)))
        salience = float(getattr(listener, "rhythm_salience", 1.0))
    return max(0.0, min(1.0, max(0.0, min(1.0, trust)) * (0.4 + 0.6 * max(0.0, min(1.0, salience)))))


def _resolve_window(mono_len: int, start_s: float, duration_s: float) -> Tuple[int, int]:
    eval_frames = max(2, int(round(duration_s * 60.0)))
    pos0 = int(start_s * 44100)
    if pos0 + eval_frames * HOP > mono_len:
        pos0 = max(0, mono_len - eval_frames * HOP)
    return pos0, eval_frames


@dataclass
class TrackTelemetry:
    lock: np.ndarray            # (frames,)
    trust: np.ndarray           # (frames,)
    salience: np.ndarray        # (frames,)
    flux: np.ndarray            # (frames, nb_bands) listener.band_flux (the delayed signal modes see)
    bands: np.ndarray           # (frames, nb_bands) listener.asserved_fft_band

    def summary(self) -> Dict[str, float]:
        return {
            "seconds": float(len(self.lock)) / 60.0,
            "lock_mean": float(np.mean(self.lock)),
            "lock_p10": float(np.percentile(self.lock, 10)),
            "lock_p50": float(np.percentile(self.lock, 50)),
            "lock_p90": float(np.percentile(self.lock, 90)),
            "flux_p50": float(np.percentile(self.flux, 50)),
            "flux_p99": float(np.percentile(self.flux, 99)),
            "flux_max": float(np.max(self.flux)),
            "frac_flux_gt_10": float(np.mean(self.flux > 10.0)),
        }


def capture_telemetry(
    mono: np.ndarray,
    *,
    start_s: float = DEFAULT_START_S,
    duration_s: float = DEFAULT_DURATION_S,
    warmup_frames: int = DEFAULT_WARMUP_FRAMES,
    nb_bands: int = PRODUCTION_VISUAL_FFT_BANDS,
) -> TrackTelemetry:
    """Step a fresh Listener over the warm-up + evaluation window and record delayed telemetry."""
    pos0, eval_frames = _resolve_window(len(mono), start_s, duration_s)
    lock = np.zeros(eval_frames, dtype=np.float64)
    trust = np.zeros(eval_frames, dtype=np.float64)
    salience = np.zeros(eval_frames, dtype=np.float64)
    flux = np.zeros((eval_frames, nb_bands), dtype=np.float64)
    bands = np.zeros((eval_frames, nb_bands), dtype=np.float64)

    with OfflineClock() as clock:
        listener = make_listener(nb_bands=nb_bands)
        total_frames = warmup_frames + eval_frames
        for i in range(total_frames):
            center_sample = pos0 + (i - warmup_frames) * HOP
            step_listener(listener, mono, center_sample, clock)
            if i >= warmup_frames:
                idx = i - warmup_frames
                ctx = listener.context
                lock[idx] = compute_rhythm_lock(listener)
                trust[idx] = float(getattr(ctx, "beat_trust", listener.beat_trust))
                salience[idx] = float(getattr(ctx, "salience", listener.rhythm_salience))
                flux[idx, :] = listener.band_flux[:nb_bands]
                bands[idx, :] = listener.asserved_fft_band[:nb_bands]

    return TrackTelemetry(lock=lock, trust=trust, salience=salience, flux=flux, bands=bands)


def run_mode_on_audio(
    mode_cls: Any,
    mono: np.ndarray,
    muted_channels: Sequence[str] = (),
    *,
    start_s: float = DEFAULT_START_S,
    duration_s: float = DEFAULT_DURATION_S,
    warmup_frames: int = DEFAULT_WARMUP_FRAMES,
    nb_bands: int = PRODUCTION_VISUAL_FFT_BANDS,
    num_leds: int = MATRIX_CONFIG["num_leds"],
) -> Tuple[float, float]:
    """Run `mode_cls` on real audio `mono` under `muted_channels` and return `(R_std, R_diff)`."""
    random.seed(42)
    np.random.seed(42)
    pos0, eval_frames = _resolve_window(len(mono), start_s, duration_s)
    recorded = np.zeros((eval_frames, num_leds, 3), dtype=np.int32)

    with OfflineClock() as clock:
        listener = make_listener(nb_bands=nb_bands)
        proxy = DriverMuteProxy(listener)
        mood = create_mood_service(auto_scene=True)
        Mode.bind_mood_colors(mood.colors())
        Mode.bind_mood_modifiers(mood.modifiers())
        try:
            rgb = np.zeros((num_leds, 3), dtype=np.int32)
            mode = mode_cls(
                mode_cls.__name__,
                "probe_segment",
                proxy,
                None,
                list(range(num_leds)),
                rgb,
                {},
            )
            total_frames = warmup_frames + eval_frames
            for i in range(total_frames):
                if i == warmup_frames:
                    for ch in muted_channels:
                        proxy.set_muted(ch, True)
                center_sample = pos0 + (i - warmup_frames) * HOP
                step_listener(listener, mono, center_sample, clock)
                ctx = getattr(listener, "context", None)
                raw_scene = getattr(ctx, "scene", None) if ctx is not None else None
                scene_str = (
                    str(raw_scene.value if hasattr(raw_scene, "value") else raw_scene)
                    if raw_scene is not None
                    else None
                )
                mood.update(1.0 / 60.0, scene_str)
                proxy.observe()
                proxy.sync_macro_modifiers(Mode, mood.modifiers())
                mode.render(buffer=rgb)
                if i >= warmup_frames:
                    recorded[i - warmup_frames] = rgb
        finally:
            Mode.reset_mood_colors()
            Mode.reset_mood_modifiers()

    return compute_response_metrics(recorded)


def measure_mode_on_audio(mode_cls: Any, mono: np.ndarray, **kw: Any) -> Dict[str, Any]:
    """Evaluate a single mode across all choreography mute conditions on `mono`."""
    return measure_with_runner(mode_cls, lambda cls, muted: run_mode_on_audio(cls, mono, muted, **kw))


def measure_all_modes_on_audio(mono: np.ndarray, **kw: Any) -> List[Dict[str, Any]]:
    """Evaluate all registered modes across all choreography mute conditions on `mono`."""
    return [measure_mode_on_audio(cls, mono, **kw) for cls in load_registered_mode_classes()]


def format_telemetry_summary(track_label: str, summary: Dict[str, float]) -> str:
    """Format a one-line telemetry summary for CLI output."""
    return (
        f"Track: {track_label} ({summary['seconds']:.1f}s) | "
        f"lock mean={summary['lock_mean']:.3f} (p10={summary['lock_p10']:.3f}, p50={summary['lock_p50']:.3f}, p90={summary['lock_p90']:.3f}) | "
        f"flux p50={summary['flux_p50']:.1f}, p99={summary['flux_p99']:.1f}, max={summary['flux_max']:.0f}, frac>10={summary['frac_flux_gt_10']:.3f}"
    )
