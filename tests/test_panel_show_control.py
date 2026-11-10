"""
tests/test_panel_show_control.py - desktop control panel (pygame window opened by Main.py):
HOLD / LIVE switch and per-segment mode picking, end to end from panel click to Mode_master.
"""
import json
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pygame

import hardware.Fake_ESP32 as Fake_ESP32
from core.Mode_master import Mode_master
from hardware.Fake_leds import FakeLedsVisualizer
from hardware.Udp_Sender import Udp_Sender, SEGMENT_METADATA_PORT


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


class TestHudShowControl(unittest.TestCase):
    def setUp(self):
        self.visualizer = FakeLedsVisualizer()
        self.hud = self.visualizer.hud
        self.hud.is_locked = False
        self.hud.mode_catalog = {}
        self.hud._optimistic_modes = {}
        self.sent = []
        self.visualizer.set_control_handler(self.sent.append)
        self.visualizer.segment_modes.clear()
        self.visualizer.set_hud_only(True)

    def tearDown(self):
        self.visualizer.set_control_handler(None)
        self.visualizer.set_hud_only(False)

    def _render(self, transition_data=None):
        self.visualizer._transition_data = transition_data
        with patch.object(self.visualizer, "handle_events"):
            self.visualizer.show()

    def test_hold_button_toggles_lock_in_both_directions(self):
        self._render({"is_locked": False})
        self.assertTrue(self.hud.handle_event(click(self.hud._rect_hold.center), MagicMock(), self.visualizer.send_control_command))
        self.assertEqual(self.sent[-1], {"type": "set_locked", "locked": True})

        self._render({"is_locked": True})
        self.assertTrue(self.hud.is_locked)
        self.hud.handle_event(click(self.hud._rect_hold.center), MagicMock(), self.visualizer.send_control_command)
        self.assertEqual(self.sent[-1], {"type": "set_locked", "locked": False})

    def test_h_hotkey_toggles_lock(self):
        self._render({"is_locked": False})
        self.assertTrue(self.hud.handle_event(key(pygame.K_h), MagicMock(), self.visualizer.send_control_command))
        self.assertEqual(self.sent[-1], {"type": "set_locked", "locked": True})

    def test_controls_are_inert_without_a_command_sink(self):
        self._render({"is_locked": False})
        self.assertFalse(self.hud.handle_event(click(self.hud._rect_hold.center), MagicMock()))
        self.assertFalse(self.hud.handle_event(key(pygame.K_h), MagicMock()))

    def test_segment_arrows_cycle_modes_with_wraparound(self):
        names = [n for ch in self.visualizer.segments_def for (_s, _o, _x, _y, n, _c) in ch]
        name = names[0]
        seg_id = name[len("segment_"):]
        self.hud.mode_catalog = {seg_id: ["Alpha", "Beta", "Gamma"]}
        self.visualizer.set_segment_mode(name, "Gamma")
        self._render({"is_locked": True})

        rects = {n: (p, nx) for n, p, nx in self.hud._row_rects}
        self.assertEqual(list(rects), [name], "only segments with a known catalog get arrows")
        prev_rect, next_rect = rects[name]

        self.hud.handle_event(click(next_rect.center), MagicMock(), self.visualizer.send_control_command)
        self.assertEqual(self.sent[-1], {"type": "set_segment_mode", "segment": seg_id, "mode": "Alpha"})

        # A second click before the panel hears back chains from the first one, not from "Gamma"
        self.hud.handle_event(click(next_rect.center), MagicMock(), self.visualizer.send_control_command)
        self.assertEqual(self.sent[-1]["mode"], "Beta")

        self.hud._optimistic_modes.clear()
        self.hud.handle_event(click(prev_rect.center), MagicMock(), self.visualizer.send_control_command)
        self.assertEqual(self.sent[-1]["mode"], "Beta")  # Gamma -> previous

    def test_unknown_current_mode_starts_from_the_ends(self):
        name = "segment_v4"
        self.hud.mode_catalog = {"v4": ["Alpha", "Beta"]}
        self.hud._cycle_segment_mode(name, 1, self.sent.append)
        self.assertEqual(self.sent[-1]["mode"], "Alpha")
        self.hud._optimistic_modes.clear()
        self.hud._cycle_segment_mode(name, -1, self.sent.append)
        self.assertEqual(self.sent[-1]["mode"], "Beta")

    def test_control_panel_fits_in_the_hud_only_window(self):
        self._render({"is_locked": False})
        width, height = self.visualizer._current_window_size
        self.assertLessEqual(self.hud._rect_hold.right, width)
        self.assertLessEqual(self.hud._rect_hold.bottom, height)
        self.assertLessEqual(self.hud._rect_global_next.right, width)
        self.assertLessEqual(self.hud._rect_global_apply.bottom, height)
        self.assertLessEqual(self.hud._rect_mood_next.right, width)
        self.assertLessEqual(self.hud._rect_mood_apply.bottom, height)
        self.assertLessEqual(self.hud._rect_mood_auto.bottom, height)

    def test_mood_selector_buttons_hotkeys_and_auto_toggle(self):
        self.hud.selected_mood_idx = 0
        self.hud.mood_auto_scene = True
        self._render({"is_locked": False})

        # 1. Clicking > on the Mood row steps to the next palette and dispatches set_mood
        self.assertTrue(
            self.hud.handle_event(click(self.hud._rect_mood_next.center), MagicMock(), self.visualizer.send_control_command)
        )
        self.assertEqual(self.sent[-1], {"type": "set_mood", "palette": self.hud.mood_palettes[1]})

        # 2. Clicking < steps back to palette 0
        self.assertTrue(
            self.hud.handle_event(click(self.hud._rect_mood_prev.center), MagicMock(), self.visualizer.send_control_command)
        )
        self.assertEqual(self.sent[-1], {"type": "set_mood", "palette": self.hud.mood_palettes[0]})

        # 3. Clicking the center MOOD bar re-applies the currently selected palette
        self.assertTrue(
            self.hud.handle_event(click(self.hud._rect_mood_apply.center), MagicMock(), self.visualizer.send_control_command)
        )
        self.assertEqual(self.sent[-1], {"type": "set_mood", "palette": self.hud.mood_palettes[0]})

        # 4. Hotkey M steps forward; Shift+M steps backward
        self.assertTrue(self.hud.handle_event(key(pygame.K_m), MagicMock(), self.visualizer.send_control_command))
        self.assertEqual(self.sent[-1], {"type": "set_mood", "palette": self.hud.mood_palettes[1]})
        shift_m = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, mod=pygame.KMOD_SHIFT)
        self.assertTrue(self.hud.handle_event(shift_m, MagicMock(), self.visualizer.send_control_command))
        self.assertEqual(self.sent[-1], {"type": "set_mood", "palette": self.hud.mood_palettes[0]})

        # 5. Clicking AUTO: ON/OFF button or pressing A toggles mood_auto_scene in both directions
        self.assertTrue(
            self.hud.handle_event(click(self.hud._rect_mood_auto.center), MagicMock(), self.visualizer.send_control_command)
        )
        self.assertFalse(self.hud.mood_auto_scene)
        self.assertEqual(self.sent[-1], {"type": "set_mood_auto", "auto_scene": False})

        self.assertTrue(self.hud.handle_event(key(pygame.K_a), MagicMock(), self.visualizer.send_control_command))
        self.assertTrue(self.hud.mood_auto_scene)
        self.assertEqual(self.sent[-1], {"type": "set_mood_auto", "auto_scene": True})

        # 6. Live crossfade status updates mood_palette, mood_target, and mood_auto_scene immediately without resetting timestamps
        self._render({
            "is_locked": False,
            "mood_palette": "Cyberpunk",
            "mood_target": "Solar Ember",
            "mood_progress": 0.5,
            "mood_is_transitioning": True,
            "mood_auto_scene": False,
            "mood_colors": [[255, 40, 10], [250, 140, 20], [255, 220, 90], [20, 8, 4]],
        })
        self.assertEqual(self.hud.mood_palette, "Cyberpunk")
        self.assertEqual(self.hud.mood_target, "Solar Ember")
        self.assertAlmostEqual(self.hud.mood_progress, 0.5)
        self.assertTrue(self.hud.mood_is_transitioning)
        self.assertFalse(self.hud.mood_auto_scene)
        self.assertEqual(self.hud.mood_colors[0], (255, 40, 10))

    def test_global_scope_toggle_and_global_mode_picker(self):
        self.hud.global_scope = False
        self.hud.selected_global_idx = 0
        self._render({"is_locked": True})

        # 1. Hotkey G or clicking _rect_scope switches from Local to Global scope
        self.assertTrue(self.hud.handle_event(key(pygame.K_g), MagicMock(), self.visualizer.send_control_command))
        self.assertTrue(self.hud.global_scope)
        self.assertEqual(
            self.sent[-1],
            {"type": "set_mode_scope", "scope": "global", "mode": self.hud.global_modes[0]},
        )

        # 2. Clicking > on the Global Mode row steps to the next Global Mode
        self.assertTrue(
            self.hud.handle_event(click(self.hud._rect_global_next.center), MagicMock(), self.visualizer.send_control_command)
        )
        self.assertEqual(
            self.sent[-1],
            {"type": "set_global_mode", "mode": self.hud.global_modes[1]},
        )

        # 3. Clicking _rect_scope returns to Local scope
        self.assertTrue(
            self.hud.handle_event(click(self.hud._rect_scope.center), MagicMock(), self.visualizer.send_control_command)
        )
        self.assertFalse(self.hud.global_scope)
        self.assertEqual(self.sent[-1], {"type": "set_mode_scope", "scope": "local"})

    def test_segment_arrows_skip_global_modes_when_mixed_in_catalog(self):
        name = "segment_v4"
        self.hud.mode_catalog = {"v4": ["Alpha", "Monolithic Beat Blast", "Beta"]}
        self.visualizer.set_segment_mode(name, "Alpha")
        self.hud._cycle_segment_mode(name, 1, self.sent.append)
        self.assertEqual(self.sent[-1]["mode"], "Beta")

    def test_commands_go_over_udp_without_an_in_process_handler(self):
        self.visualizer.set_control_handler(None)
        self.visualizer._control_sock = MagicMock()
        self.visualizer.send_control_command({"type": "set_locked", "locked": True})
        payload, addr = self.visualizer._control_sock.sendto.call_args[0]
        self.assertEqual(json.loads(payload.decode()), {"type": "set_locked", "locked": True})
        self.assertEqual(addr, ("127.0.0.1", 9004))

    def test_panel_process_ingests_catalog_and_lock_state(self):
        catalog = json.dumps({"type": "mode_catalog", "modes": {"v4": ["A", "B"]}}).encode()
        trans = json.dumps({"type": "transition_state", "is_locked": True}).encode()
        meta = MagicMock()
        meta.recvfrom.side_effect = [(catalog, ("127.0.0.1", 9003)), (trans, ("127.0.0.1", 9003)), BlockingIOError()]
        Fake_ESP32.drain_metadata_packets(meta, self.visualizer)
        self.assertEqual(self.hud.mode_catalog, {"v4": ["A", "B"]})
        self._render(self.visualizer._transition_data)
        self.assertTrue(self.hud.is_locked)


class TestUdpSenderPanelLink(unittest.TestCase):
    def setUp(self):
        self.sender = Udp_Sender("127.0.0.1", 9001, 100)
        self.sender.sock.close()
        self.sender.sock = MagicMock()
        self.transitions = MagicMock()
        self.transitions.get_status.return_value = MagicMock(
            is_in_transition=False, is_pending=False, progress=0.0, technique=None, is_locked=True)
        self.sender._transitions = self.transitions
        self.sender._control_sock = MagicMock()

    def _queue(self, *payloads):
        self.sender._control_sock.recvfrom.side_effect = [
            (json.dumps(p).encode(), ("127.0.0.1", 1)) for p in payloads
        ] + [BlockingIOError()]

    def test_panel_commands_reach_the_handler_and_transitions_still_work(self):
        handler = MagicMock()
        self.sender.set_control_handler(handler)
        self._queue(
            {"type": "set_locked", "locked": True},
            {"type": "request_transition", "technique": "AUTO", "duration": 2.0},
            {"type": "set_segment_mode", "segment": "v4", "mode": "Rainbow"},
        )
        self.sender._poll_control_requests()
        self.assertEqual([c[0][0]["type"] for c in handler.call_args_list], ["set_locked", "set_segment_mode"])
        self.transitions.request_next.assert_called_once_with(technique=None, duration=2.0)

    def test_handler_failure_does_not_break_the_poll_loop(self):
        self.sender.set_control_handler(MagicMock(side_effect=RuntimeError("boom")))
        self._queue({"type": "set_locked", "locked": True}, {"type": "request_transition", "technique": "x", "duration": 1})
        self.sender._poll_control_requests()
        self.transitions.request_next.assert_called_once()

    def test_transition_state_carries_the_lock_and_catalog_is_sent_at_1hz(self):
        self.sender.set_control_handler(MagicMock(), {"v4": ["A", "B"]})
        with patch("time.monotonic", return_value=5000.0):
            self.sender._send_transition_state()
            self.sender._send_mode_catalog()
            self.sender._send_mode_catalog()  # throttled
        sent = [json.loads(c[0][0].decode()) for c in self.sender.sock.sendto.call_args_list
                if c[0][1] == ("127.0.0.1", SEGMENT_METADATA_PORT)]
        self.assertEqual([p["type"] for p in sent], ["transition_state", "mode_catalog"])
        self.assertTrue(sent[0]["is_locked"])
        self.assertEqual(sent[1]["modes"], {"v4": ["A", "B"]})

    def test_transition_state_includes_mood_status_when_mood_controller_set(self):
        from mood.api import create_mood_service
        mood_svc = create_mood_service(initial_palette="Cyberpunk", auto_scene=True)
        mood_svc.request_palette("Solar Ember", duration=2.0, hold=45.0)
        self.sender.set_mood_controller(mood_svc)
        with patch("time.monotonic", return_value=5100.0):
            self.sender._send_transition_state()
        sent = [json.loads(c[0][0].decode()) for c in self.sender.sock.sendto.call_args_list
                if c[0][1] == ("127.0.0.1", SEGMENT_METADATA_PORT)]
        self.assertEqual(len(sent), 1)
        payload = sent[0]
        self.assertEqual(payload["mood_palette"], "Cyberpunk")
        self.assertEqual(payload["mood_target"], "Solar Ember")
        self.assertTrue(payload["mood_is_transitioning"])
        self.assertTrue(payload["mood_auto_scene"])
        self.assertIn("Solar Ember", payload["available_moods"])
        self.assertEqual(len(payload["mood_colors"]), 4)


class TestModeMasterPanelCommands(unittest.TestCase):
    def setUp(self):
        listener = MagicMock()
        listener.luminosite = 0.8
        listener.sensi = 0.5
        listener.smoothed_fft_band_values = np.zeros(16)
        listener.asserved_fft_band = np.zeros(16)
        listener._delayed_asserved_fft_band = np.zeros(16)
        listener.nb_of_fft_band = 16
        listener.asserved_total_power = 0.0
        infos = {"onRaspberry": False, "HARDWARE_MODE": "simulation", "printCpuFpsInfo": False,
                 "auto_transition_time": 25.0}
        self.mm = Mode_master(listener, infos, np.zeros((785, 3), dtype=np.int32), np.zeros((519, 3), dtype=np.int32))

    def test_hold_and_resume(self):
        self.assertTrue(self.mm.handle_panel_command({"type": "set_locked", "locked": True}))
        self.assertTrue(self.mm.get_state_snapshot()["transitionLocked"])
        self.assertTrue(self.mm.handle_panel_command({"type": "set_locked", "locked": False}))
        self.assertFalse(self.mm.get_state_snapshot()["transitionLocked"])

    def test_segment_mode_pick_is_instant_and_validated(self):
        catalog = self.mm._panel_mode_catalog()
        self.assertEqual(len(catalog), 11)
        seg = self.mm._find_segment_by_name("v4")
        target = next(m for m in catalog["v4"] if m != seg.get_current_mode())
        self.assertTrue(self.mm.handle_panel_command({"type": "set_segment_mode", "segment": "v4", "mode": target}))
        self.assertEqual(seg.get_current_mode(), target)
        self.assertFalse(seg.is_in_transition)

        before = seg.get_current_mode()
        for bad in ({"segment": "nope", "mode": target}, {"segment": "v4", "mode": "No Such Mode"},
                    {"segment": 4, "mode": target}, {"segment": "v4", "mode": None}):
            self.assertFalse(self.mm.handle_panel_command({"type": "set_segment_mode", **bad}))
        self.assertEqual(seg.get_current_mode(), before)
        self.assertFalse(self.mm.handle_panel_command({"type": "unknown"}))

    def test_catalog_lists_exactly_what_each_segment_can_run(self):
        catalog = self.mm._panel_mode_catalog()
        for segment in self.mm.segments_list:
            self.assertEqual(catalog[segment.id], sorted(segment.modes))

    def test_global_mode_and_scope_commands_on_mode_master(self):
        # 1. set_global_mode switches all 11 segments to the chosen Global Mode
        self.assertTrue(self.mm.handle_panel_command({"type": "set_global_mode", "mode": "Concentric Radial Ripple"}))
        for seg in self.mm.segments_list:
            self.assertEqual(seg.get_current_mode(), "Concentric Radial Ripple")
        self.assertTrue(getattr(self.mm, "_use_global_modes", False))

        # Reject non-global modes on set_global_mode
        self.assertFalse(self.mm.handle_panel_command({"type": "set_global_mode", "mode": "Rainbow"}))

        # 2. set_mode_scope 'local' switches all segments back to local modes
        self.assertTrue(self.mm.handle_panel_command({"type": "set_mode_scope", "scope": "local"}))
        self.assertFalse(getattr(self.mm, "_use_global_modes", True))
        for seg in self.mm.segments_list:
            self.assertFalse(getattr(seg.modes[seg.get_current_mode()], "IS_GLOBAL", False))

        # 3. set_mode_scope 'global' activates the requested Global Mode across all segments
        self.assertTrue(self.mm.handle_panel_command({"type": "set_mode_scope", "scope": "global", "mode": "Horizon Scanning Blade"}))
        self.assertTrue(getattr(self.mm, "_use_global_modes", False))
        for seg in self.mm.segments_list:
            self.assertEqual(seg.get_current_mode(), "Horizon Scanning Blade")

    def test_mood_and_auto_scene_commands_on_mode_master(self):
        # 1. set_mood requests a valid palette on Mode_master.mood
        self.assertTrue(self.mm.handle_panel_command({"type": "set_mood", "palette": "Solar Ember"}))
        self.assertEqual(self.mm.mood.get_status().target_palette, "Solar Ember")

        # Reject unknown or non-string palettes
        self.assertFalse(self.mm.handle_panel_command({"type": "set_mood", "palette": "NonExistentMood"}))
        self.assertFalse(self.mm.handle_panel_command({"type": "set_mood", "palette": ""}))
        self.assertFalse(self.mm.handle_panel_command({"type": "set_mood", "palette": None}))

        # 2. set_mood_auto toggles auto_scene
        self.assertTrue(self.mm.handle_panel_command({"type": "set_mood_auto", "auto_scene": False}))
        self.assertFalse(self.mm.mood.get_status().auto_scene)
        self.assertTrue(self.mm.handle_panel_command({"type": "set_mood_auto", "auto_scene": True}))
        self.assertTrue(self.mm.mood.get_status().auto_scene)


if __name__ == "__main__":
    unittest.main()
