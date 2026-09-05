"""
Unit tests for utils/Profiler.py.
Verifies inactive overhead, block measurement, windowed statistics,
slowest mode tracking, spike detection, formatters, and get_metrics backward compatibility.
"""
import time
import unittest
from unittest.mock import MagicMock

from utils.Profiler import Profiler


class TestProfiler(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()

    def test_inactive_profiler_does_not_log(self):
        profiler = Profiler(active=False, logger=self.mock_logger)
        with profiler.measure("test_block"):
            time.sleep(0.001)

        profiler.tick()
        self.mock_logger.info.assert_not_called()
        self.mock_logger.warning.assert_not_called()

        metrics = profiler.get_metrics()
        self.assertIn("fps", metrics)
        self.assertEqual(metrics["fps"], 0.0)

    def test_measure_records_timings_and_ema(self):
        profiler = Profiler(active=True, logger=self.mock_logger)
        with profiler.measure("render"):
            time.sleep(0.002)

        self.assertIn("render", profiler.current_frame_metrics)
        self.assertGreater(profiler.current_frame_metrics["render"], 0.001)
        self.assertIn("render", profiler.metrics)
        self.assertGreater(profiler.metrics["render"], 0.001)

    def test_slowest_mode_tracking(self):
        profiler = Profiler(
            active=True,
            logger=self.mock_logger,
            config={"track_slowest_mode": True}
        )
        profiler.record_slowest_mode("Segment v1", "SolidColor", 0.001)
        profiler.record_slowest_mode("Segment v2", "Supernova", 0.008)
        profiler.record_slowest_mode("Segment v3", "Pulse", 0.003)

        self.assertEqual(profiler._window_slowest_seg, "Segment v2")
        self.assertEqual(profiler._window_slowest_mode, "Supernova")
        self.assertAlmostEqual(profiler._window_slowest_time, 0.008, places=4)

    def test_compact_formatting_and_window_aggregation(self):
        profiler = Profiler(
            active=True,
            logger=self.mock_logger,
            config={
                "interval_seconds": 0.05,
                "format": "compact",
                "target_fps": 30.0,
            }
        )
        profiler.last_print_time = time.perf_counter() - 0.1

        with profiler.measure("listener"):
            pass
        with profiler.measure("modes_render"):
            pass
        profiler.record_slowest_mode("Segment v1", "Supernova", 0.004)

        profiler.tick()

        self.mock_logger.info.assert_called_once()
        log_message = self.mock_logger.info.call_args[0][0]
        self.assertIn("(Profiler)", log_message)
        self.assertIn("FPS:", log_message)
        self.assertIn("Load:", log_message)
        self.assertIn("Supernova", log_message)

    def test_dashboard_formatting(self):
        profiler = Profiler(
            active=True,
            logger=self.mock_logger,
            config={
                "interval_seconds": 0.05,
                "format": "dashboard",
                "target_fps": 30.0,
            }
        )
        profiler.last_print_time = time.perf_counter() - 0.1

        with profiler.measure("listener"):
            pass
        with profiler.measure("modes_render"):
            pass
        profiler.record_slowest_mode("Segment v1", "Supernova", 0.004)

        profiler.tick()

        self.mock_logger.info.assert_called_once()
        log_message = self.mock_logger.info.call_args[0][0]
        self.assertIn("PROFILER SUMMARY", log_message)
        self.assertIn("Load", log_message)
        self.assertIn("modes_render", log_message)
        self.assertIn("Supernova", log_message)

    def test_spike_alert_triggers_warning(self):
        profiler = Profiler(
            active=True,
            logger=self.mock_logger,
            config={
                "alert_threshold_ms": 5.0,  # 5ms threshold
            }
        )
        with profiler.measure("heavy_block"):
            time.sleep(0.008)  # 8ms > 5ms threshold

        profiler.tick()
        self.mock_logger.warning.assert_called_once()
        warning_message = self.mock_logger.warning.call_args[0][0]
        self.assertIn("[SPIKE]", warning_message)
        self.assertIn("heavy_block:", warning_message)

    def test_alerts_only_mode_suppresses_summary(self):
        profiler = Profiler(
            active=True,
            logger=self.mock_logger,
            config={
                "interval_seconds": 0.01,
                "format": "alerts_only",
                "alert_threshold_ms": 50.0,
            }
        )
        profiler.last_print_time = time.perf_counter() - 0.1

        with profiler.measure("normal_block"):
            pass

        profiler.tick()
        # Summary should not be printed in alerts_only mode
        self.mock_logger.info.assert_not_called()

    def test_get_metrics_backward_compatibility_and_fields(self):
        profiler = Profiler(active=True, logger=self.mock_logger)
        with profiler.measure("hardware_show"):
            pass
        with profiler.measure("modes_render"):
            pass

        metrics = profiler.get_metrics()
        # Verify core backward-compatible keys
        self.assertIn("fps", metrics)
        self.assertIn("target_fps", metrics)
        self.assertIn("min_fps", metrics)
        self.assertIn("load_percent", metrics)
        self.assertIn("frame_time_ms", metrics)
        self.assertIn("jitter_ms", metrics)
        self.assertIn("dropped_frames", metrics)
        # Verify backward compatibility aliases
        self.assertIn("hardware_show_ms", metrics)
        self.assertIn("app_ms", metrics)
        self.assertIn("modes_render_ms", metrics)
        self.assertIn("mode_master_ms", metrics)


if __name__ == "__main__":
    unittest.main()
