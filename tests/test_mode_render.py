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
