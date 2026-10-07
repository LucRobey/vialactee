"""
Contract tests for transitions/api.py (the doors).
Guards the shapes both sides rely on, so the inside can be rewritten freely.
"""
import ast
import dataclasses
import inspect
import unittest

import numpy as np

from transitions import api
from transitions.api import (
    InstallationSnapshot,
    MusicSnapshot,
    OrderAck,
    PaletteRequest,
    SegmentDescriptor,
    SegmentOrder,
    TransitionOrders,
    TransitionService,
    TransitionStatus,
)


class TestDataShapes(unittest.TestCase):
    def test_all_shapes_are_frozen(self):
        for cls in (MusicSnapshot, SegmentDescriptor, InstallationSnapshot, SegmentOrder,
                    PaletteRequest, TransitionOrders, OrderAck, TransitionStatus):
            self.assertTrue(dataclasses.is_dataclass(cls), cls)
            inst = cls() if cls not in (SegmentDescriptor, SegmentOrder, PaletteRequest) else None
            if cls is SegmentDescriptor:
                inst = cls(name="Segment v1")
            elif cls is SegmentOrder:
                inst = cls(segment="s", target_mode="m", technique="t", duration=1.0)
            elif cls is PaletteRequest:
                inst = cls(palette="Cyberpunk")
            first_field = dataclasses.fields(cls)[0].name
            with self.assertRaises(dataclasses.FrozenInstanceError):
                setattr(inst, first_field, getattr(inst, first_field))

    def test_music_snapshot_constructible_with_no_arguments(self):
        m = MusicSnapshot()
        self.assertEqual(m.scene, "CHILL")
        self.assertEqual(m.lookahead_seconds, 5.0)

    def test_installation_snapshot_dimensions_are_optional(self):
        self.assertIsNone(InstallationSnapshot().room_bounds)

    def test_orders_are_per_segment_and_may_differ(self):
        orders = TransitionOrders(orders=(
            SegmentOrder("Segment v1", "Rainbow", "global_change", 2.0),
            SegmentOrder("Segment v2", "Hyper Strobe", "explosion", 0.4, direction="DOWN", start_offset=0.2),
        ))
        self.assertEqual({o.technique for o in orders.orders}, {"global_change", "explosion"})
        self.assertIsNone(orders.palette)

    def test_status_defaults_are_idle(self):
        s = TransitionStatus()
        self.assertEqual(s.state, "PASSATION")
        self.assertFalse(s.is_in_transition)
        self.assertEqual(s.progress, 0.0)


class TestFrontDoor(unittest.TestCase):
    def test_front_door_is_synchronous(self):
        for name, fn in inspect.getmembers(TransitionService, inspect.isfunction):
            self.assertFalse(inspect.iscoroutinefunction(fn), name)

    def test_front_door_exposes_every_door(self):
        expected = {
            "set_installation", "update", "acknowledge",
            "request_next", "request_drop", "set_locked", "set_auto_interval",
            "blend", "get_status",
        }
        public = {n for n, _ in inspect.getmembers(TransitionService, inspect.isfunction) if not n.startswith("_")}
        self.assertEqual(expected, public)

    def test_update_signature(self):
        params = list(inspect.signature(TransitionService.update).parameters)
        self.assertEqual(params, ["self", "dt", "music"])

    def test_blend_signature_is_in_place(self):
        sig = inspect.signature(TransitionService.blend)
        self.assertEqual(list(sig.parameters), ["self", "dest_buffer", "incoming_buffer", "progress", "technique", "coords"])
        self.assertIs(sig.return_annotation, None)

    def test_unimplemented_contract_raises(self):
        with self.assertRaises(NotImplementedError):
            TransitionService().blend(np.zeros((1, 3)), np.zeros((1, 3)), 0.5, "fade_in_out")


class TestWallPrerequisites(unittest.TestCase):
    def test_api_imports_only_stdlib_and_numpy(self):
        tree = ast.parse(inspect.getsource(api))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        self.assertTrue(roots <= {"dataclasses", "typing", "numpy", "transitions"}, roots)


if __name__ == "__main__":
    unittest.main()
