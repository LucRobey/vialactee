"""
tests/test_studio_mutes.py
Unit and static conflict tests for Mode Studio choreography mute key bindings (Ctrl+B/L/S/T/M and Ctrl+0).
"""
import os
import unittest

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

from tools.choreography_matrix import SyntheticListener
from tools.studio_mutes import CLEAR_MUTES_KEY, CTRL_KEY_MAP, format_hud_line, handle_studio_key
from utils.driver_mute import DriverMuteProxy


@unittest.skipUnless(HAS_PYGAME, "pygame is required for Mode Studio key binding tests")
class TestStudioMutesKeyBindings(unittest.TestCase):
    def setUp(self):
        self.listener = SyntheticListener(nb_bands=8)
        self.proxy = DriverMuteProxy(self.listener)

    def test_key_map_table_is_complete_and_valid(self):
        """Static table maps K_b/l/s/t/m to the 5 mute channels and K_0 to clear."""
        self.assertEqual(
            CTRL_KEY_MAP,
            {
                "K_b": "beat",
                "K_l": "level",
                "K_s": "spectrum",
                "K_t": "transient",
                "K_m": "macro",
            },
        )
        self.assertEqual(CLEAR_MUTES_KEY, "K_0")

    def test_ctrl_combinations_toggle_each_channel_and_ctrl_0_clears(self):
        """1. Each Ctrl combination toggles exactly its channel; Ctrl+0 clears all mutes."""
        for key_name, expected_channel in CTRL_KEY_MAP.items():
            key_code = getattr(pygame, key_name)
            msg_on = handle_studio_key(self.proxy, key_code, pygame.KMOD_CTRL)
            self.assertIsNotNone(msg_on)
            self.assertEqual(self.proxy.muted, (expected_channel,))

            msg_off = handle_studio_key(self.proxy, key_code, pygame.KMOD_CTRL)
            self.assertIsNotNone(msg_off)
            self.assertEqual(self.proxy.muted, ())

        # Enable multiple channels and clear with Ctrl+0
        handle_studio_key(self.proxy, pygame.K_b, pygame.KMOD_CTRL)
        handle_studio_key(self.proxy, pygame.K_s, pygame.KMOD_CTRL)
        self.assertEqual(self.proxy.muted, ("beat", "spectrum"))

        msg_clear = handle_studio_key(self.proxy, pygame.K_0, pygame.KMOD_CTRL)
        self.assertEqual(msg_clear, "CHOREOGRAPHY MUTES: CLEARED")
        self.assertEqual(self.proxy.muted, ())

    def test_keys_without_ctrl_are_ignored(self):
        """2. Plain B, L, S, T, M, 0, and F1..F5 without Ctrl return None (no stolen Studio keys)."""
        unmodified_keys = [
            pygame.K_b,
            pygame.K_l,
            pygame.K_s,
            pygame.K_t,
            pygame.K_m,
            pygame.K_0,
            pygame.K_F1,
            pygame.K_F2,
            pygame.K_F3,
            pygame.K_F4,
            pygame.K_F5,
        ]
        for k in unmodified_keys:
            self.assertIsNone(handle_studio_key(self.proxy, k, 0), f"Plain key {k} should not be consumed")
            self.assertIsNone(
                handle_studio_key(self.proxy, k, pygame.KMOD_SHIFT),
                f"Shift+key {k} should not be consumed",
            )
        self.assertEqual(self.proxy.muted, ())

    def test_mode_studio_has_no_conflicting_kmod_ctrl_handlers(self):
        """3. Static check: tools/mode_studio.py contains no KMOD_CTRL handling of its own."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        studio_path = os.path.join(repo_root, "tools", "mode_studio.py")
        with open(studio_path, "r", encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn("KMOD_CTRL", source)
        self.assertNotIn("K_LCTRL", source)
        self.assertNotIn("K_RCTRL", source)

    def test_ctrl_with_shift_or_alt_does_not_trigger(self):
        """4. Ctrl+B held with Shift or Alt does not trigger (only plain Ctrl)."""
        for extra_mod in (pygame.KMOD_SHIFT, pygame.KMOD_ALT, pygame.KMOD_SHIFT | pygame.KMOD_ALT):
            res = handle_studio_key(self.proxy, pygame.K_b, pygame.KMOD_CTRL | extra_mod)
            self.assertIsNone(res)
            self.assertEqual(self.proxy.muted, ())

    def test_format_hud_line(self):
        """Verify HUD readout formatting when unmuted and muted."""
        class _DummyMode:
            LEAD = "spectrum"
            SECONDARY = ("beat",)

        self.assertEqual(
            format_hud_line(self.proxy, _DummyMode()),
            "LEAD: spectrum · SECONDARY: beat · muted: [none]",
        )
        self.proxy.set_muted("beat", True)
        self.assertEqual(
            format_hud_line(self.proxy, _DummyMode()),
            "LEAD: spectrum · SECONDARY: beat · muted: [beat]",
        )


if __name__ == "__main__":
    unittest.main()
