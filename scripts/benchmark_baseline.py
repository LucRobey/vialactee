"""
Performance Profiling Baseline Script for Vialactée.

Measures memory allocation rate, garbage collection statistics, and execution
timings for core pipeline components (Listener, Segment update_leds, etc.).

Run with:
    python scripts/benchmark_baseline.py
"""
import time
import tracemalloc
import os
import sys
import gc
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.Listener import Listener
from core.Segment import Segment


def benchmark_listener(num_frames: int = 300) -> None:
    """Benchmark Listener.update() allocation count and time across N frames."""
    infos = {
        "hardware_profile": "full",
        "useMicrophone": False,
        "fakeDelay": 5.0,
        "printCpuFpsInfo": False,
    }
    listener = Listener(infos)

    # Warmup
    for _ in range(30):
        listener.update()

    gc.collect()
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()
    start_time = time.perf_counter()

    for _ in range(num_frames):
        listener.update()

    elapsed = time.perf_counter() - start_time
    snapshot_after = tracemalloc.take_snapshot()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    fps = num_frames / elapsed
    stats = snapshot_after.compare_to(snapshot_before, 'lineno')
    total_alloc_diff = sum(stat.size_diff for stat in stats if stat.size_diff > 0)

    print("=" * 60)
    print(f"LISTENER BENCHMARK ({num_frames} frames @ simulated fake FFT)")
    print(f"  Time elapsed:       {elapsed * 1000:.2f} ms ({fps:.1f} FPS equivalent)")
    print(f"  Per-frame latency:  {(elapsed / num_frames) * 1000:.3f} ms")
    print(f"  Memory allocated:   {total_alloc_diff / 1024:.2f} KB total")
    print(f"  Per-frame alloc:    {total_alloc_diff / num_frames:.1f} bytes/frame")
    print(f"  Peak traced memory: {peak / 1024:.2f} KB")
    print("=" * 60)


def benchmark_segment_leds(num_segments: int = 11, leds_per_seg: int = 120, num_frames: int = 300) -> None:
    """Benchmark Segment.update_leds() allocation count across N frames."""
    total_leds = num_segments * leds_per_seg
    global_leds = np.zeros((total_leds, 3), dtype=np.int32)

    infos = {
        "hardware_profile": "full",
        "useMicrophone": False,
        "fakeDelay": 5.0,
        "printCpuFpsInfo": False,
    }
    listener = Listener(infos)

    segments = []
    for s in range(num_segments):
        indexes = list(range(s * leds_per_seg, (s + 1) * leds_per_seg))
        seg = Segment(
            name=f"Segment v{s + 1}",
            listener=listener,
            leds=global_leds,
            indexes=indexes,
            orientation="vertical",
            infos=infos,
        )
        segments.append(seg)

    gc.collect()
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()
    start_time = time.perf_counter()

    for _ in range(num_frames):
        for seg in segments:
            seg.update_leds()

    elapsed = time.perf_counter() - start_time
    snapshot_after = tracemalloc.take_snapshot()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    stats = snapshot_after.compare_to(snapshot_before, 'lineno')
    total_alloc_diff = sum(stat.size_diff for stat in stats if stat.size_diff > 0)

    print("=" * 60)
    print(f"SEGMENT LEDS BENCHMARK ({num_segments} segments, {num_frames} frames)")
    print(f"  Time elapsed:       {elapsed * 1000:.2f} ms")
    print(f"  Per-frame latency:  {(elapsed / num_frames) * 1000:.3f} ms for all {num_segments} segments")
    print(f"  Memory allocated:   {total_alloc_diff / 1024:.2f} KB total")
    print(f"  Per-frame alloc:    {total_alloc_diff / num_frames:.1f} bytes/frame")
    print(f"  Peak traced memory: {peak / 1024:.2f} KB")
    print("=" * 60)


if __name__ == "__main__":
    print("\n--- RUNNING VIALACTEE PERFORMANCE PROFILING BASELINE ---")
    benchmark_listener(300)
    benchmark_segment_leds(11, 120, 300)
    print("Benchmark complete.\n")
