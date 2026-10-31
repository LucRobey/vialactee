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
    ModeProfile,
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
        for cls in (MusicSnapshot, ModeProfile, SegmentDescriptor, InstallationSnapshot, SegmentOrder,
                    PaletteRequest, TransitionOrders, OrderAck, TransitionStatus):
            self.assertTrue(dataclasses.is_dataclass(cls), cls)
            inst = cls() if cls not in (ModeProfile, SegmentDescriptor, SegmentOrder, PaletteRequest) else None
            if cls is ModeProfile:
                inst = cls(name="Rainbow")
            elif cls is SegmentDescriptor:
                inst = cls(name="Segment v1")
            elif cls is SegmentOrder:
                inst = cls(segment="s", target_mode="m", technique="t", duration=1.0)
            elif cls is PaletteRequest:
                inst = cls(palette="Cyberpunk")
            first_field = dataclasses.fields(cls)[0].name
            with self.assertRaises(dataclasses.FrozenInstanceError):
                setattr(inst, first_field, getattr(inst, first_field))

    def test_mode_profile_contract(self):
        prof = ModeProfile(name="Rainbow", dna=(0.8, 0.4, 0.5, 0.2), tags=("lead:spectrum", "axis:both"))
        self.assertEqual(prof.name, "Rainbow")
        self.assertEqual(prof.dna, (0.8, 0.4, 0.5, 0.2))
        self.assertEqual(prof.tags, ("lead:spectrum", "axis:both"))

        prof_default = ModeProfile(name="Power Bar")
        self.assertEqual(prof_default.dna, (0.5, 0.5, 0.5, 0.5))
        self.assertEqual(prof_default.tags, ())

    def test_segment_descriptor_extension_and_backward_compatibility(self):
        # Legacy positional single arg
        d1 = SegmentDescriptor("Segment v1")
        self.assertEqual(d1.name, "Segment v1")
        self.assertEqual(d1.orientation, "vertical")
        self.assertEqual(d1.available_modes, ())
        self.assertEqual(d1.active_mode, "")
        self.assertFalse(d1.is_blocked)
        self.assertEqual(d1.id, "")
        self.assertEqual(d1.tags, ())

        # Legacy positional 4 args (as in transitions/fakes.py)
        d4 = SegmentDescriptor("Segment v1", "vertical", ("Rainbow", "Power Bar"), "Rainbow")
        self.assertEqual(d4.name, "Segment v1")
        self.assertEqual(d4.orientation, "vertical")
        self.assertEqual(d4.available_modes, ("Rainbow", "Power Bar"))
        self.assertEqual(d4.active_mode, "Rainbow")
        self.assertFalse(d4.is_blocked)
        self.assertEqual(d4.id, "")
        self.assertEqual(d4.tags, ())

        # Extended keyword initialization with id and tags
        dex = SegmentDescriptor(name="Segment v1", id="v1", tags=("tier:full", "orientation:vertical"))
        self.assertEqual(dex.id, "v1")
        self.assertEqual(dex.tags, ("tier:full", "orientation:vertical"))

    def test_installation_snapshot_modes_extension(self):
        snap_empty = InstallationSnapshot()
        self.assertEqual(snap_empty.segments, ())
        self.assertEqual(snap_empty.modes, ())
        self.assertIsNone(snap_empty.room_bounds)

        prof = ModeProfile(name="Rainbow")
        snap_modes = InstallationSnapshot(segments=(), modes=(prof,), room_bounds=(430, 246))
        self.assertEqual(snap_modes.modes, (prof,))
        self.assertEqual(snap_modes.room_bounds, (430, 246))

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
            "set_installation", "set_installation_snapshot", "update", "acknowledge",
            "request_next", "request_drop", "set_locked", "set_auto_interval",
            "blend", "get_status", "configure", "allocate_initial",
        }
        public = {n for n, _ in inspect.getmembers(TransitionService, inspect.isfunction) if not n.startswith("_")}
        self.assertEqual(expected, public)

    def test_configure_door_interface(self):
        policy = {"settings": {"maxDifferentModes": 3}}
        svc = TransitionService()
        svc.configure(policy)
        self.assertEqual(svc._policy, policy)
        self.assertEqual(svc.policy, policy)

        # Module-level configure
        api.configure(policy)
        self.assertEqual(api.get_default_service()._policy, policy)

    def test_allocate_initial_door_interface(self):
        segs = (
            SegmentDescriptor(name="Segment v1", id="v1", active_mode="Rainbow"),
            SegmentDescriptor(name="Segment v2", id="v2", active_mode="Power Bar", is_blocked=True),
            SegmentDescriptor(name="Segment v3", id="", available_modes=("Metronome",)),
        )
        snap = InstallationSnapshot(segments=segs)
        svc = TransitionService()
        svc.set_installation(snap)
        alloc = svc.allocate_initial()
        self.assertEqual(alloc["Segment v1"], "Rainbow")
        self.assertEqual(alloc["Segment v2"], "Power Bar")
        self.assertEqual(alloc["Segment v3"], "Metronome")

        # Module-level allocate_initial
        api.get_default_service().set_installation(snap)
        alloc_mod = api.allocate_initial()
        self.assertIn("Segment v1", alloc_mod)
        self.assertEqual(alloc_mod["Segment v2"], "Power Bar")
        self.assertIn("Segment v3", alloc_mod)

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
