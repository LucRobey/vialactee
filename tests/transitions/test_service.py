"""
Headless tests of the sealed transition sector through its front door only:
fake music + fake installation, no Mode_master, no hardware, no audio.
"""
import unittest

import numpy as np

import transitions.engine as engine
from transitions.api import (
    InstallationSnapshot,
    MusicSnapshot,
    OrderAck,
    SegmentDescriptor,
    create_transition_service,
)

MODES = ("Rainbow", "Plasma Fire", "Hyper Strobe", "Metronome")


def installation(blocked=()):
    segs = tuple(
        SegmentDescriptor(name=f"Segment v{i}", orientation="vertical", available_modes=MODES,
                          active_mode="Rainbow", is_blocked=(f"Segment v{i}" in blocked))
        for i in range(1, 5)
    )
    return InstallationSnapshot(segments=segs)


def beat_music(**kw):
    return MusicSnapshot(beat_phase=0.0, is_beat=True, energy=0.5, salience=0.5, **kw)


class TestFrontDoorBehavior(unittest.TestCase):
    def setUp(self):
        self.svc = create_transition_service({"auto_transition_time": 20.0})
        self.svc.set_installation(installation())

    def test_idle_update_returns_nothing(self):
        self.assertIsNone(self.svc.update(0.033, MusicSnapshot()))
        self.assertFalse(self.svc.get_status().is_in_transition)

    def test_drop_request_orders_every_segment_with_explosion(self):
        self.svc.request_drop()
        orders = self.svc.update(0.033, beat_music())
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "request_drop")
        self.assertEqual(len(orders.orders), 4)
        for o in orders.orders:
            self.assertEqual(o.technique, "explosion")
            self.assertAlmostEqual(o.duration, 0.4)
            self.assertIn(o.target_mode, MODES)
        status = self.svc.get_status()
        self.assertTrue(status.is_in_transition)
        self.assertEqual(status.technique, "explosion")

    def test_request_next_waits_for_a_beat_then_fires(self):
        self.svc.request_next()
        self.assertIsNone(self.svc.update(0.01, MusicSnapshot(beat_phase=0.5, is_beat=False)))
        orders = self.svc.update(0.01, beat_music())
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "request_next")

    def test_request_next_with_named_technique(self):
        self.svc.request_next("directional_wipe")
        orders = self.svc.update(0.01, beat_music())
        self.assertEqual({o.technique for o in orders.orders}, {"vertical_wipe"})

    def test_ack_with_nobody_accepting_cancels_the_transition(self):
        self.svc.request_drop()
        self.svc.update(0.033, beat_music())
        self.svc.acknowledge(OrderAck(accepted=(), refused=("Segment v1",)))
        self.assertFalse(self.svc.get_status().is_in_transition)

    def test_ack_with_acceptance_keeps_the_transition(self):
        self.svc.request_drop()
        self.svc.update(0.033, beat_music())
        self.svc.acknowledge(OrderAck(accepted=("Segment v1",)))
        self.assertTrue(self.svc.get_status().is_in_transition)

    def test_auto_timer_fires_orders(self):
        self.svc.set_auto_interval(1.0)
        fired = None
        for _ in range(120):
            fired = self.svc.update(0.033, beat_music())
            if fired:
                break
        self.assertIsNotNone(fired)
        self.assertEqual(fired.reason, "timer")

    def test_lock_blocks_the_auto_timer(self):
        self.svc.set_auto_interval(1.0)
        self.svc.set_locked(True)
        self.assertTrue(self.svc.get_status().is_locked)
        for _ in range(200):
            self.assertIsNone(self.svc.update(0.033, beat_music()))

    def test_interval_is_reported_in_status(self):
        self.svc.set_auto_interval(42)
        self.assertEqual(self.svc.get_status().auto_interval, 42.0)

    def test_progress_runs_to_completion(self):
        self.svc.request_drop()
        self.svc.update(0.033, beat_music())
        for _ in range(60):
            self.svc.update(0.033, MusicSnapshot())
        status = self.svc.get_status()
        self.assertEqual(status.state, "PASSATION")
        self.assertEqual(status.progress, 1.0)

    def test_blend_writes_in_place(self):
        dest = np.zeros((10, 3), dtype=np.int32)
        incoming = np.full((10, 3), 200, dtype=np.int32)
        before_id = id(dest)
        self.assertIsNone(self.svc.blend(dest, incoming, 1.0, "fade_in_out"))
        self.assertEqual(id(dest), before_id)
        np.testing.assert_array_equal(dest, incoming)

    def test_room_bounds_arrive_through_the_installation_door(self):
        old = (engine.ROOM_MAX_X, engine.ROOM_MAX_Y)
        self.addCleanup(engine.set_room_bounds, *old)
        self.svc.set_installation(InstallationSnapshot(room_bounds=(111, 77)))
        self.assertEqual((engine.ROOM_MAX_X, engine.ROOM_MAX_Y), (111, 77))

    def test_no_installation_means_no_orders(self):
        svc = create_transition_service()
        svc.request_drop()
        self.assertIsNone(svc.update(0.033, beat_music()))


if __name__ == "__main__":
    unittest.main()
