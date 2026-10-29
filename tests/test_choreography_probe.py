"""
tests/test_choreography_probe.py - Unit tests for tools/choreography_probe.py.
"""
import time
import numpy as np
import pytest

from modes.Mode import Mode
from modes.Metronome_mode import Metronome_mode
from tools.choreography_matrix import measure_mode_choreography
from tools.choreography_probe import (
    HOP,
    OfflineClock,
    capture_telemetry,
    compute_rhythm_lock,
    make_listener,
    measure_mode_on_audio,
    step_listener,
)


def _make_synthetic_audio(duration_s: float = 12.0, sr: int = 44100) -> np.ndarray:
    """Synthesize a deterministic 44.1 kHz mono buffer: 110 Hz sine + periodic noise burst every 0.5 s."""
    rng = np.random.default_rng(12345)
    n = int(duration_s * sr)
    t = np.arange(n, dtype=np.float32) / float(sr)
    audio = 0.25 * np.sin(2.0 * np.pi * 110.0 * t).astype(np.float32)
    burst_period = sr // 2
    burst_len = int(0.03 * sr)
    for start in range(0, n - burst_len, burst_period):
        audio[start : start + burst_len] += 0.65 * rng.standard_normal(burst_len).astype(np.float32)
    return np.clip(audio, -1.0, 1.0)


def test_offline_clock_restores_time_even_on_error():
    orig_time = time.time
    with OfflineClock(start=500.0, step=0.5) as clk:
        assert time.time() == pytest.approx(500.0)
        clk.tick()
        assert time.time() == pytest.approx(500.5)
    assert time.time is orig_time

    with pytest.raises(RuntimeError):
        with OfflineClock(start=200.0):
            assert time.time is not orig_time
            raise RuntimeError("boom")
    assert time.time is orig_time


def test_ring_drains_under_offline_clock():
    mono = _make_synthetic_audio(12.0)
    tel = capture_telemetry(mono, start_s=6.0, duration_s=2.0, warmup_frames=330, nb_bands=8)
    assert tel.bands.shape == (120, 8)
    assert tel.flux.shape == (120, 8)
    assert float(tel.bands.sum()) > 0.0
    assert float(tel.flux.max()) > 0.0


def test_compute_rhythm_lock_matches_mode_property():
    mono = _make_synthetic_audio(8.0)
    with OfflineClock() as clock:
        listener = make_listener(nb_bands=8)
        for i in range(340):
            step_listener(listener, mono, i * HOP, clock)
        mode = Mode("t", "s", listener, None, list(range(16)), np.zeros((16, 3), dtype=np.int32), {})
        assert mode.rhythm_lock == pytest.approx(compute_rhythm_lock(listener))


def test_capture_is_deterministic():
    mono = _make_synthetic_audio(8.0)
    t1 = capture_telemetry(mono, start_s=5.5, duration_s=1.0, warmup_frames=310, nb_bands=8)
    t2 = capture_telemetry(mono, start_s=5.5, duration_s=1.0, warmup_frames=310, nb_bands=8)
    np.testing.assert_array_equal(t1.lock, t2.lock)
    np.testing.assert_array_equal(t1.trust, t2.trust)
    np.testing.assert_array_equal(t1.salience, t2.salience)
    np.testing.assert_array_equal(t1.flux, t2.flux)
    np.testing.assert_array_equal(t1.bands, t2.bands)


def test_measure_mode_on_audio_schema_matches_synthetic():
    mono = _make_synthetic_audio(3.0)
    probe_res = measure_mode_on_audio(
        Metronome_mode, mono, start_s=1.0, duration_s=0.25, warmup_frames=15, nb_bands=8
    )
    synth_res = measure_mode_choreography(Metronome_mode, num_leds=16, warmup_frames=5, eval_frames=10, nb_bands=8)
    assert set(probe_res.keys()) == set(synth_res.keys())
    assert set(probe_res["contributions"].keys()) == set(synth_res["contributions"].keys())
