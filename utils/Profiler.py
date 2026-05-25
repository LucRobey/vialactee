import time
import logging
from contextlib import contextmanager

class Profiler:
    def __init__(self, active: bool = False, logger: logging.Logger = None):
        self.active = active
        self.logger = logger or logging.getLogger(__name__)
        self.metrics = {}
        self.ema_alpha = 0.1  # Smoothing factor (10% new value, 90% old value)
        
        self.last_tick_time = None
        self.fps = 0.0
        
        # Logging timing
        self.last_print_time = time.perf_counter()
        self.print_interval = 5.0  # Log summary every 5 seconds if active

    @contextmanager
    def measure(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            if name not in self.metrics:
                self.metrics[name] = duration
            else:
                self.metrics[name] = (self.metrics[name] * (1.0 - self.ema_alpha)) + (duration * self.ema_alpha)

    def tick(self):
        """Called once per frame/loop to calculate overall FPS and trigger periodic logging."""
        now = time.perf_counter()
        if self.last_tick_time is not None:
            dt = now - self.last_tick_time
            if dt > 0:
                current_fps = 1.0 / dt
                if self.fps == 0.0:
                    self.fps = current_fps
                else:
                    self.fps = (self.fps * (1.0 - self.ema_alpha)) + (current_fps * self.ema_alpha)
        
        self.last_tick_time = now

        if self.active and (now - self.last_print_time) >= self.print_interval:
            self._print_summary()
            self.last_print_time = now

    def _print_summary(self):
        # Format the metrics into a single line to avoid spamming the console
        parts = [f"FPS: {self.fps:.1f}"]
        
        # Sort to keep order consistent
        for name in sorted(self.metrics.keys()):
            ms = self.metrics[name] * 1000.0
            parts.append(f"{name}: {ms:.2f}ms")
            
        summary_str = " | ".join(parts)
        self.logger.info(f"(Profiler) {summary_str}")

    def get_metrics(self):
        """Returns a dict with fps and smoothed timing (in ms) for each measured block."""
        result = {"fps": round(self.fps, 1)}
        for name, duration in self.metrics.items():
            result[f"{name}_ms"] = round(duration * 1000.0, 2)
        return result
