import time
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple


class Profiler:
    """
    High-resolution performance profiler and FPS stability monitor.

    Provides granular sub-millisecond execution timings across installation subsystems
    (listener, modes rendering, hardware show, transitions, connector, idle sleep),
    computes frame budget and CPU load %, detects frame rate drops and micro-stutters
    (min FPS, 1% low, jitter), tracks the slowest active segment/mode, and generates
    configurable log outputs (compact one-liner, visual ASCII dashboard, or alerts-only).
    """

    def __init__(
        self,
        active: bool = False,
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.active = bool(active)
        self.logger = logger or logging.getLogger(__name__)
        config = config or {}

        # Configuration options
        self.print_interval = float(config.get("interval_seconds", 5.0))
        self.format = str(config.get("format", "compact")).lower()
        self.target_fps = float(config.get("target_fps", 30.0))
        self.frame_budget_ms = 1000.0 / self.target_fps if self.target_fps > 0 else 33.33
        self.alert_threshold_ms = float(config.get("alert_threshold_ms", 35.0))
        self.track_slowest_mode = bool(config.get("track_slowest_mode", True))

        # Smoothed block metrics (EMA duration in seconds) for backwards compatibility
        self.metrics: Dict[str, float] = {}
        self.ema_alpha = 0.1

        # Current frame storage
        self.current_frame_metrics: Dict[str, float] = {}

        # Timing and FPS tracking
        self.last_tick_time: Optional[float] = None
        self.fps = 0.0
        self.last_print_time = time.perf_counter()
        self.last_alert_time = 0.0

        # Rolling window statistics (accumulated between print intervals)
        self._window_dts: List[float] = []
        self._window_frame_times: List[float] = []
        self._window_dropped_frames = 0
        self._window_total_frames = 0
        self._window_slowest_seg: Optional[str] = None
        self._window_slowest_mode: Optional[str] = None
        self._window_slowest_time = 0.0

        # Cached summary metrics for get_metrics()
        self.actual_fps = 0.0
        self.min_fps = 0.0
        self.p99_low_fps = 0.0
        self.avg_frame_time_ms = 0.0
        self.max_frame_time_ms = 0.0
        self.load_percent = 0.0
        self.jitter_ms = 0.0
        self.dropped_frames_count = 0
        self.slowest_seg: Optional[str] = None
        self.slowest_mode: Optional[str] = None
        self.slowest_mode_ms = 0.0

    @contextmanager
    def measure(self, name: str):
        """Context manager to measure execution duration of a named code block."""
        if not self.active:
            yield
            return

        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.current_frame_metrics[name] = duration
            if name not in self.metrics:
                self.metrics[name] = duration
            else:
                self.metrics[name] = (self.metrics[name] * (1.0 - self.ema_alpha)) + (duration * self.ema_alpha)

    def record_slowest_mode(self, segment_name: str, mode_name: str, duration: float) -> None:
        """Record the execution duration of an individual segment mode."""
        if not self.active or not self.track_slowest_mode:
            return
        if duration > self._window_slowest_time:
            self._window_slowest_time = duration
            self._window_slowest_seg = segment_name
            self._window_slowest_mode = mode_name

    def tick(self, frame_compute_time: Optional[float] = None) -> None:
        """
        Called once per frame to update loop timing, accumulate window statistics,
        detect immediate frame spikes, and trigger periodic log reporting.
        """
        now = time.perf_counter()

        if self.last_tick_time is not None:
            dt = now - self.last_tick_time
            if dt > 0:
                current_fps = 1.0 / dt
                if self.fps == 0.0:
                    self.fps = current_fps
                else:
                    self.fps = (self.fps * (1.0 - self.ema_alpha)) + (current_fps * self.ema_alpha)

                if self.active:
                    self._window_dts.append(dt)

        self.last_tick_time = now

        if not self.active:
            self.current_frame_metrics.clear()
            return

        # Calculate active compute time (excluding idle_sleep)
        if frame_compute_time is None:
            active_duration = sum(
                duration
                for name, duration in self.current_frame_metrics.items()
                if name != "idle_sleep"
            )
        else:
            active_duration = frame_compute_time

        self._window_frame_times.append(active_duration)
        self._window_total_frames += 1

        budget_sec = self.frame_budget_ms / 1000.0
        if active_duration > budget_sec:
            self._window_dropped_frames += 1

        # Check for immediate spike alert
        active_ms = active_duration * 1000.0
        if active_ms >= self.alert_threshold_ms and (now - self.last_alert_time) >= 1.0:
            self._log_spike_alert(active_ms)
            self.last_alert_time = now

        # Periodic summary report
        if (now - self.last_print_time) >= self.print_interval:
            self._process_window_and_log(now)
            self.last_print_time = now

        self.current_frame_metrics.clear()

    def _log_spike_alert(self, active_ms: float) -> None:
        """Emit an immediate warning log when an individual frame exceeds threshold."""
        breakdown_parts = []
        for name in sorted(self.current_frame_metrics.keys()):
            if name == "idle_sleep":
                continue
            ms = self.current_frame_metrics[name] * 1000.0
            breakdown_parts.append(f"{name}: {ms:.1f}ms")

        slowest_str = ""
        if self._window_slowest_seg:
            slowest_str = f" | Slowest: {self._window_slowest_seg} [{self._window_slowest_mode}]"

        breakdown_str = " | ".join(breakdown_parts)
        self.logger.warning(
            f"(Profiler) [SPIKE] Frame took {active_ms:.1f}ms (Budget: {self.frame_budget_ms:.1f}ms){slowest_str} -> {breakdown_str}"
        )

    def _process_window_and_log(self, now: float) -> None:
        """Aggregate windowed metrics and emit summary log in configured format."""
        if self._window_total_frames == 0:
            return

        window_duration = sum(self._window_dts) if self._window_dts else (now - self.last_print_time)
        actual_fps = (len(self._window_dts) / window_duration) if window_duration > 0 else self.fps
        min_fps = (1.0 / max(self._window_dts)) if self._window_dts and max(self._window_dts) > 0 else actual_fps

        # 1% Low FPS
        if len(self._window_dts) >= 10:
            sorted_dts = sorted(self._window_dts)
            p99_idx = min(int(len(sorted_dts) * 0.99), len(sorted_dts) - 1)
            p99_dt = sorted_dts[p99_idx]
            p99_low_fps = 1.0 / p99_dt if p99_dt > 0 else min_fps
        else:
            p99_low_fps = min_fps

        avg_frame_time = sum(self._window_frame_times) / len(self._window_frame_times)
        avg_frame_time_ms = avg_frame_time * 1000.0
        max_frame_time_ms = max(self._window_frame_times) * 1000.0 if self._window_frame_times else avg_frame_time_ms
        load_percent = (avg_frame_time_ms / self.frame_budget_ms) * 100.0 if self.frame_budget_ms > 0 else 0.0

        # Jitter (standard deviation of inter-frame interval)
        if len(self._window_dts) > 1:
            mean_dt = sum(self._window_dts) / len(self._window_dts)
            variance = sum((x - mean_dt) ** 2 for x in self._window_dts) / (len(self._window_dts) - 1)
            jitter_ms = (variance ** 0.5) * 1000.0
        else:
            jitter_ms = 0.0

        # Cache values for external consumers (System_status / Web UI)
        self.actual_fps = actual_fps
        self.min_fps = min_fps
        self.p99_low_fps = p99_low_fps
        self.avg_frame_time_ms = avg_frame_time_ms
        self.max_frame_time_ms = max_frame_time_ms
        self.load_percent = load_percent
        self.jitter_ms = jitter_ms
        self.dropped_frames_count = self._window_dropped_frames
        self.slowest_seg = self._window_slowest_seg
        self.slowest_mode = self._window_slowest_mode
        self.slowest_mode_ms = self._window_slowest_time * 1000.0

        # Format and log output
        if self.format == "dashboard":
            self._print_dashboard(window_duration)
        elif self.format == "alerts_only":
            pass  # In alerts_only mode, periodic logs are suppressed
        else:
            # Default to compact
            self._print_compact()

        # Reset window accumulators
        self._window_dts.clear()
        self._window_frame_times.clear()
        self._window_dropped_frames = 0
        self._window_total_frames = 0
        self._window_slowest_seg = None
        self._window_slowest_mode = None
        self._window_slowest_time = 0.0

    def _print_compact(self) -> None:
        """Print a single-line compact summary."""
        parts = [
            f"FPS: {self.actual_fps:.1f}/{self.target_fps:.0f} (Load: {self.load_percent:.1f}% | {self.avg_frame_time_ms:.2f}ms)",
            f"Min: {self.min_fps:.1f}",
            f"Drops: {self.dropped_frames_count}/{self._window_total_frames}",
            f"Jitter: +/-{self.jitter_ms:.2f}ms",
        ]

        component_parts = []
        for name in sorted(self.metrics.keys()):
            if name == "idle_sleep":
                continue
            ms = self.metrics[name] * 1000.0
            if name == "modes_render" and self.slowest_seg and self.slowest_mode:
                component_parts.append(f"{name}: {ms:.2f}ms [Slowest: {self.slowest_seg} ({self.slowest_mode}) {self.slowest_mode_ms:.2f}ms]")
            else:
                component_parts.append(f"{name}: {ms:.2f}ms")

        summary_str = " | ".join(parts) + " | " + " | ".join(component_parts)
        self.logger.info(f"(Profiler) {summary_str}")

    def _print_dashboard(self, window_duration: float) -> None:
        """Print a structured multi-line ASCII dashboard."""
        headroom_ms = max(0.0, self.frame_budget_ms - self.avg_frame_time_ms)
        filled = min(10, max(0, int(round((self.load_percent / 100.0) * 10))))
        load_bar = "=" * filled + "." * (10 - filled)

        lines = [
            f"+-- [PROFILER SUMMARY - {window_duration:.1f}s window] " + "-" * 37 + "+",
            f"| FPS: {self.actual_fps:.1f} / {self.target_fps:.0f}   [{load_bar}] {self.load_percent:.1f}% Load (Budget: {self.frame_budget_ms:.1f}ms | Headroom: {headroom_ms:.1f}ms)",
            f"| Frame Time: Avg {self.avg_frame_time_ms:.2f}ms | Max {self.max_frame_time_ms:.2f}ms | 1% Low: {self.p99_low_fps:.1f} fps | Jitter: +/-{self.jitter_ms:.2f}ms | Drops: {self.dropped_frames_count}/{self._window_total_frames}",
            "+" + "-" * 74 + "+",
        ]

        # Calculate component percentage of total compute time
        total_compute = sum(v for k, v in self.metrics.items() if k != "idle_sleep")
        for name in sorted(self.metrics.keys()):
            ms = self.metrics[name] * 1000.0
            if name == "idle_sleep":
                lines.append(f"|  {name:<16}: {ms:>6.2f} ms  (sleeping headroom)")
            else:
                pct = (self.metrics[name] / total_compute * 100.0) if total_compute > 0 else 0.0
                slowest_extra = ""
                if name == "modes_render" and self.slowest_seg and self.slowest_mode:
                    slowest_extra = f"  --> Slowest: {self.slowest_seg} [{self.slowest_mode}] ({self.slowest_mode_ms:.2f}ms)"
                lines.append(f"|  {name:<16}: {ms:>6.2f} ms  ({pct:>5.1f}%){slowest_extra}")

        lines.append("+" + "-" * 74 + "+")
        self.logger.info("(Profiler)\n" + "\n".join(lines))

    def get_metrics(self) -> Dict[str, Any]:
        """
        Returns a dictionary with FPS, load metrics, and timing breakdown in milliseconds.
        Preserves backward compatibility keys ('fps', '<name>_ms', 'app_ms', 'mode_master_ms')
        for SystemStatus and the web interface.
        """
        result: Dict[str, Any] = {
            "fps": round(self.actual_fps if self.actual_fps > 0 else self.fps, 1),
            "target_fps": round(self.target_fps, 1),
            "min_fps": round(self.min_fps, 1) if self.min_fps > 0 else round(self.fps, 1),
            "p99_low_fps": round(self.p99_low_fps, 1) if self.p99_low_fps > 0 else round(self.fps, 1),
            "load_percent": round(self.load_percent, 1),
            "frame_time_ms": round(self.avg_frame_time_ms, 2),
            "max_frame_time_ms": round(self.max_frame_time_ms, 2),
            "jitter_ms": round(self.jitter_ms, 2),
            "dropped_frames": self.dropped_frames_count,
            "slowest_mode": f"{self.slowest_seg} [{self.slowest_mode}]" if self.slowest_seg else None,
            "slowest_mode_ms": round(self.slowest_mode_ms, 2) if self.slowest_seg else None,
        }

        # Include all smoothed block metrics in ms
        for name, duration in self.metrics.items():
            result[f"{name}_ms"] = round(duration * 1000.0, 2)

        # Backward compatibility aliases for existing consumers
        if "hardware_show_ms" in result and "app_ms" not in result:
            result["app_ms"] = result["hardware_show_ms"]
        if "modes_render_ms" in result and "mode_master_ms" not in result:
            result["mode_master_ms"] = result["modes_render_ms"]

        return result
