import numpy as np
from modes.Mode import Mode


class LegacyMode(Mode):
    """Simulates a legacy mode that only overrides run()."""
    def run(self):
        self.rgb_list[:] = [10, 20, 30]


class ModernMode(Mode):
    """Simulates a modern mode that overrides render()."""
    def render(self, buffer=None, audio_ctx=None, frame_info=None):
        target = buffer if buffer is not None else self.rgb_list
        target[:] = [40, 50, 60]


def test_legacy_mode_update():
    rgb = np.zeros((10, 3), dtype=np.int32)
    mode = LegacyMode("Legacy", "Seg1", None, None, list(range(10)), rgb, {})
    mode.update()
    assert np.all(mode.rgb_list == [10, 20, 30])


def test_legacy_mode_render_redirection():
    primary_rgb = np.zeros((10, 3), dtype=np.int32)
    secondary_rgb = np.zeros((10, 3), dtype=np.int32)
    mode = LegacyMode("Legacy", "Seg1", None, None, list(range(10)), primary_rgb, {})

    mode.render(buffer=secondary_rgb)
    # Secondary buffer should have received the render
    assert np.all(secondary_rgb == [10, 20, 30])
    # Primary buffer must remain untouched
    assert np.all(primary_rgb == 0)
    # Pointer must be restored to primary_rgb
    assert mode.rgb_list is primary_rgb


def test_modern_mode_render():
    primary_rgb = np.zeros((10, 3), dtype=np.int32)
    secondary_rgb = np.zeros((10, 3), dtype=np.int32)
    mode = ModernMode("Modern", "Seg1", None, None, list(range(10)), primary_rgb, {})

    mode.render(buffer=secondary_rgb)
    assert np.all(secondary_rgb == [40, 50, 60])
    assert np.all(primary_rgb == 0)


def test_shining_stars_mode_settings_and_activation():
    from unittest.mock import MagicMock
    from modes.Shining_stars_mode import Shining_stars_mode

    mock_listener = MagicMock()
    mock_listener.nb_of_fft_band = 8
    mock_listener.band_flux = np.zeros(8, dtype=np.float64)

    rgb = np.zeros((80, 3), dtype=np.int32)
    mode = Shining_stars_mode("Shining Stars", "v1", mock_listener, None, list(range(80)), rgb, {})

    # 1. Verify schema and default settings
    schema = mode.get_settings_schema()
    keys = [item["key"] for item in schema]
    assert "threshold" in keys
    assert "fade_ratio" in keys
    assert "sub_segment_size" in keys

    # 2. Test apply_settings & export_settings
    mode.apply_settings({"threshold": 25.0, "fade_ratio": 0.2, "sub_segment_size": 30})
    exported = mode.export_settings()
    assert exported["threshold"] == 25.0
    assert exported["fade_ratio"] == 0.2
    assert exported["sub_segment_size"] == 30

    # 3. Dormant when flux is below threshold
    mock_listener.band_flux = np.array([10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    mode.run()
    assert np.all(mode.rgb_list == 0)

    # 4. Active ignition when flux breaches threshold
    mock_listener.band_flux = np.array([30.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    mode.run()
    assert np.any(mode.rgb_list > 0)

    # 5. Natural smooth fade to black when audio subsides
    mock_listener.band_flux = np.zeros(8, dtype=np.float64)
    for _ in range(60):
        mode.run()
    assert np.all(mode.rgb_list == 0)


def test_shining_stars_mode_zero_heap_allocation():
    import tracemalloc
    from unittest.mock import MagicMock
    from modes.Shining_stars_mode import Shining_stars_mode

    mock_listener = MagicMock()
    mock_listener.nb_of_fft_band = 8
    # All 8 bands breach threshold to trigger 8 lightUp() calls per frame
    mock_listener.band_flux = np.array([50.0] * 8)

    rgb = np.zeros((100, 3), dtype=np.int32)
    mode = Shining_stars_mode("Shining Stars", "v1", mock_listener, None, list(range(100)), rgb, {})

    # Warmup loop to populate any one-time internal caches
    for _ in range(50):
        mode.run()

    tracemalloc.start()
    s1 = tracemalloc.take_snapshot()
    # 300 frames * 8 bands = 2,400 lightUp invocations (wrapping through 256 pool > 9 times)
    for _ in range(300):
        mode.run()
    s2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    non_tm = [
        stat for stat in s2.compare_to(s1, 'lineno')
        if 'tracemalloc' not in stat.traceback.format()[0]
    ]
    mode_allocs = [stat for stat in non_tm if 'Shining_stars_mode.py' in stat.traceback.format()[0]]
    assert len(mode_allocs) == 0, f"Dynamic allocations detected in Shining_stars_mode.run(): {mode_allocs}"


def test_shining_stars_mode_boundary_conditions():
    from unittest.mock import MagicMock
    from modes.Shining_stars_mode import Shining_stars_mode

    mock_listener = MagicMock()
    mock_listener.nb_of_fft_band = 8
    mock_listener.band_flux = np.array([50.0] * 8)

    # Empty strip
    rgb_empty = np.zeros((0, 3), dtype=np.int32)
    mode_empty = Shining_stars_mode("Shining Stars", "empty", mock_listener, None, [], rgb_empty, {})
    mode_empty.run()
    assert len(mode_empty.rgb_list) == 0

    # Very small strip (nb_of_leds < sub_segment_size)
    rgb_small = np.zeros((3, 3), dtype=np.int32)
    mode_small = Shining_stars_mode("Shining Stars", "small", mock_listener, None, [0, 1, 2], rgb_small, {"sub_segment_size": 40, "fade_ratio": 0.15})
    assert mode_small.sub_segment_size == 40
    assert mode_small.fade_ratio == 0.15
    mode_small.run()
    assert np.any(rgb_small > 0)

    # Safe execution with None listener or None band_flux
    rgb_safe = np.zeros((10, 3), dtype=np.int32)
    mode_none_listener = Shining_stars_mode("Shining Stars", "none_l", None, None, list(range(10)), rgb_safe, {})
    mode_none_listener.run()  # Should not raise

    mock_none_flux = MagicMock()
    mock_none_flux.nb_of_fft_band = 8
    mock_none_flux.band_flux = None
    mode_none_flux = Shining_stars_mode("Shining Stars", "none_f", mock_none_flux, None, list(range(10)), rgb_safe, {})
    mode_none_flux.run()  # Should not raise

