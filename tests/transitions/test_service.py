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

    def test_song_change_countdown_triggers_front_door_orders(self):
        # 1. Arm song change with 0.1s lookahead
        self.svc.update(0.033, MusicSnapshot(live_is_song_change=True, lookahead_seconds=0.10))
        # 2. Advance 0.05s: countdown not reached 0 yet
        self.assertIsNone(self.svc.update(0.05, MusicSnapshot(beat_phase=0.5)))
        # 3. Advance past 0.10s: countdown reaches 0.0, downbeat hit
        orders = self.svc.update(0.06, beat_music())
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "song_change")

    def test_structural_change_countdown_triggers_front_door_orders(self):
        self.svc.update(0.033, MusicSnapshot(live_is_verse_chorus_change=True, lookahead_seconds=0.08))
        self.assertIsNone(self.svc.update(0.04, MusicSnapshot(beat_phase=0.5)))
        orders = self.svc.update(0.05, beat_music())
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "structural_change")

    def test_pre_drop_buildup_triggers_front_door_orders(self):
        # Buildup with 4.0s countdown -> duration 5.0s (4.0 / 0.80)
        orders = self.svc.update(0.033, beat_music(scene="BUILDUP", drop_countdown=4.0, lookahead_seconds=4.0))
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "pre_drop_buildup")
        for o in orders.orders:
            self.assertEqual(o.technique, "explosion")
            self.assertAlmostEqual(o.duration, 5.0, places=2)

    def test_real_time_drop_impact_triggers_front_door_orders_immediately(self):
        # Not on a downbeat (beat_phase = 0.60, is_beat = False)
        orders = self.svc.update(0.033, MusicSnapshot(is_drop_impact=True, beat_phase=0.60, is_beat=False))
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "drop_impact")
        for o in orders.orders:
            self.assertEqual(o.technique, "explosion")
            self.assertAlmostEqual(o.duration, 0.4)

    def test_chill_timer_transition_ripples_center_out(self):
        self.svc.set_auto_interval(0.1)
        chill_music = MusicSnapshot(scene="CHILL", energy=0.2, salience=0.1, beat_phase=0.0, is_beat=True)
        # The scene-level technique choice is still a soft fade...
        self.assertEqual(self.svc._manager.select_transition_technique(chill_music)["type"], "fade_in_out")
        # Advance until timer fires
        orders = None
        for _ in range(10):
            orders = self.svc.update(0.05, chill_music)
            if orders is not None:
                break
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "timer")
        # ...but automatic transitions are staggered: the 4 vertical pillars ripple center-out
        offsets = sorted(o.start_offset for o in orders.orders)
        self.assertEqual(offsets, [0.075, 0.075, 0.225, 0.225])
        for o in orders.orders:
            self.assertEqual(o.technique, "vertical_wipe")
            self.assertIsNone(o.direction)
            self.assertAlmostEqual(o.duration, 2.0)


    def test_pre_drop_buildup_emits_immediately_without_waiting_for_downbeat(self):
        # Off-beat frame (beat_phase = 0.50, is_beat = False)
        orders = self.svc.update(0.033, MusicSnapshot(scene="BUILDUP", drop_countdown=4.0, beat_phase=0.50, is_beat=False))
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "pre_drop_buildup")
        for o in orders.orders:
            self.assertEqual(o.technique, "explosion")
            self.assertAlmostEqual(o.duration, 5.0, places=2)

    def test_song_change_countdown_emits_immediately_off_beat(self):
        # 1. Arm song change with 0.1s lookahead
        self.svc.update(0.033, MusicSnapshot(live_is_song_change=True, lookahead_seconds=0.10))
        # 2. Advance 0.05s: countdown not reached 0 yet
        self.assertIsNone(self.svc.update(0.05, MusicSnapshot(beat_phase=0.5)))
        # 3. Advance past 0.10s: countdown reaches 0.0, off-beat (beat_phase=0.7, is_beat=False)
        orders = self.svc.update(0.06, MusicSnapshot(beat_phase=0.7, is_beat=False))
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "song_change")

    # --- staggering policy: automatic = staggered, manual / drop = instant -------

    def test_auto_timer_transition_is_staggered(self):
        self.svc.set_auto_interval(0.1)
        orders = None
        for _ in range(10):
            orders = self.svc.update(0.05, beat_music())
            if orders is not None:
                break
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "timer")
        self.assertTrue(any(o.start_offset > 0.0 for o in orders.orders))

    def test_song_change_transition_is_staggered(self):
        self.svc.update(0.033, MusicSnapshot(live_is_song_change=True, lookahead_seconds=0.10))
        self.assertIsNone(self.svc.update(0.05, MusicSnapshot(beat_phase=0.5)))
        orders = self.svc.update(0.06, beat_music())
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "song_change")
        self.assertTrue(any(o.start_offset > 0.0 for o in orders.orders))

    def test_structural_change_transition_is_staggered(self):
        self.svc.update(0.033, MusicSnapshot(live_is_verse_chorus_change=True, lookahead_seconds=0.08))
        self.assertIsNone(self.svc.update(0.04, MusicSnapshot(beat_phase=0.5)))
        orders = self.svc.update(0.05, beat_music())
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "structural_change")
        self.assertTrue(any(o.start_offset > 0.0 for o in orders.orders))

    def test_manual_request_next_stays_instant(self):
        self.svc.request_next()
        orders = self.svc.update(0.01, beat_music())
        self.assertIsNotNone(orders)
        self.assertEqual(orders.reason, "request_next")
        self.assertTrue(all(o.start_offset == 0.0 for o in orders.orders))

    def test_drop_triggers_are_never_staggered(self):
        """Drop alignment (climax lands when the drop hits the speakers) needs simultaneous starts."""
        buildup = self.svc.update(0.033, beat_music(scene="BUILDUP", drop_countdown=4.0, lookahead_seconds=4.0))
        self.assertEqual(buildup.reason, "pre_drop_buildup")
        self.assertTrue(all(o.start_offset == 0.0 for o in buildup.orders))

        svc = create_transition_service({"auto_transition_time": 20.0})
        svc.set_installation(installation())
        impact = svc.update(0.033, MusicSnapshot(is_drop_impact=True, beat_phase=0.60, is_beat=False))
        self.assertEqual(impact.reason, "drop_impact")
        self.assertTrue(all(o.start_offset == 0.0 for o in impact.orders))

    def test_request_next_staggered_timing_and_director_sync(self):
        """Verifies staggered request produces staggered offsets and keeps director active until max time."""
        self.svc.request_next(staggered=True)
        orders = self.svc.update(0.01, beat_music())
        self.assertIsNotNone(orders)
        self.assertEqual(len(orders.orders), 4)

        offsets = [o.start_offset for o in orders.orders]
        durations = [o.duration for o in orders.orders]
        max_time = max(o + d for o, d in zip(offsets, durations))

        # At least one segment has a staggered offset
        self.assertTrue(any(o > 0.0 for o in offsets))

        # Director duration must be synchronized to max_time
        status = self.svc.get_status()
        self.assertTrue(status.is_in_transition)
        self.assertEqual(status.state, "TRANSITION_DUAL")
        self.assertAlmostEqual(self.svc._director.transition_duration, max_time, places=2)

        # Acknowledge all segments accepted
        self.svc.acknowledge(OrderAck(accepted=tuple(o.segment for o in orders.orders)))

        # Advance halfway through max_time
        mid_time = max_time * 0.5
        steps = int(mid_time / 0.033)
        for _ in range(steps):
            self.svc.update(0.033, MusicSnapshot())
        status_mid = self.svc.get_status()
        self.assertTrue(status_mid.is_in_transition)
        self.assertEqual(status_mid.state, "TRANSITION_DUAL")
        self.assertLess(status_mid.progress, 1.0)

        # Advance past max_time: must transition to PASSATION
        remaining = int((max_time * 0.6) / 0.033)
        for _ in range(remaining):
            self.svc.update(0.033, MusicSnapshot())
        status_end = self.svc.get_status()
        self.assertFalse(status_end.is_in_transition)
        self.assertEqual(status_end.state, "PASSATION")
        self.assertAlmostEqual(status_end.progress, 1.0)

    def test_drop_impact_interrupts_ongoing_staggered_transition(self):
        """A real-time drop impact mid-way through a staggered transition immediately emits explosion orders."""
        self.svc.request_next(staggered=True)
        orders = self.svc.update(0.01, beat_music())
        self.assertIsNotNone(orders)
        self.svc.acknowledge(OrderAck(accepted=tuple(o.segment for o in orders.orders)))

        # Advance halfway through staggered transition
        for _ in range(10):
            self.svc.update(0.033, MusicSnapshot())
        self.assertTrue(self.svc.get_status().is_in_transition)

        # Drop impact arrives!
        drop_orders = self.svc.update(0.033, MusicSnapshot(is_drop_impact=True, beat_phase=0.6, is_beat=False))
        self.assertIsNotNone(drop_orders)
        self.assertEqual(drop_orders.reason, "drop_impact")
        for o in drop_orders.orders:
            self.assertEqual(o.technique, "explosion")
            self.assertAlmostEqual(o.duration, 0.4)

    def test_front_door_enforces_5s_cooldown_between_automatic_transitions(self):
        """Verifies automatic music triggers are blocked for 5.0s after a transition completes."""
        # 1. Trigger and complete a quick drop transition
        self.svc.request_drop()
        orders = self.svc.update(0.033, beat_music())
        self.assertIsNotNone(orders)
        self.svc.acknowledge(OrderAck(accepted=tuple(o.segment for o in orders.orders)))

        # Advance past 0.4s to complete the transition
        for _ in range(15):
            self.svc.update(0.033, MusicSnapshot())
        status = self.svc.get_status()
        self.assertEqual(status.state, "PASSATION")
        self.assertAlmostEqual(status.progress, 1.0)
        # Cooldown must be active (5.0s)
        self.assertGreater(status.cooldown_remaining, 4.0)

        # 2. At +1.0s into cooldown (4.0s remaining): arm live song change
        self.svc.update(0.033, MusicSnapshot(live_is_song_change=True, lookahead_seconds=0.0))
        # Tick for 2 seconds: song change countdown reached 0, but cooldown blocks it
        for _ in range(60):
            orders_cooldown = self.svc.update(0.033, beat_music())
            self.assertIsNone(orders_cooldown, "Automatic transition must not trigger during 5s cooldown")

        status_mid = self.svc.get_status()
        self.assertGreater(status_mid.cooldown_remaining, 0.0)

        # 3. Advance past the remaining cooldown period (total > 5.0s after completion)
        armed_orders = None
        for _ in range(90):
            armed_orders = self.svc.update(0.033, beat_music())
            if armed_orders is not None:
                break

        self.assertIsNotNone(armed_orders, "Deferred song change must trigger once 5s cooldown expires")
        self.assertEqual(armed_orders.reason, "song_change")

    def test_front_door_urgent_drop_bypasses_cooldown(self):
        """A real-time drop impact must bypass the 5-second cooldown immediately."""
        self.svc.request_drop()
        orders = self.svc.update(0.033, beat_music())
        self.svc.acknowledge(OrderAck(accepted=tuple(o.segment for o in orders.orders)))
        for _ in range(15):
            self.svc.update(0.033, MusicSnapshot())
        self.assertGreater(self.svc.get_status().cooldown_remaining, 4.0)

        # Drop impact arrives during active cooldown!
        drop_orders = self.svc.update(0.033, MusicSnapshot(is_drop_impact=True, beat_phase=0.6, is_beat=False))
        self.assertIsNotNone(drop_orders, "Urgent drop impact must bypass cooldown security")
        self.assertEqual(drop_orders.reason, "drop_impact")

    def test_front_door_manual_request_next_bypasses_cooldown(self):
        """Manual UI overrides (request_next) must bypass the 5-second cooldown."""
        self.svc.request_drop()
        orders = self.svc.update(0.033, beat_music())
        self.svc.acknowledge(OrderAck(accepted=tuple(o.segment for o in orders.orders)))
        for _ in range(15):
            self.svc.update(0.033, MusicSnapshot())
        self.assertGreater(self.svc.get_status().cooldown_remaining, 4.0)

        # User clicks 'Next Mode' in UI during active cooldown
        self.svc.request_next()
        next_orders = self.svc.update(0.033, beat_music())
        self.assertIsNotNone(next_orders, "Manual request_next must bypass cooldown security")
        self.assertEqual(next_orders.reason, "request_next")

    def test_manual_request_next_not_overwritten_by_song_change_during_downbeat_wait(self):
        """A manual request waiting for a downbeat is not overwritten by an automatic song change."""
        # 1. Complete a quick transition to start 5.0s cooldown
        self.svc.request_drop()
        orders = self.svc.update(0.033, beat_music())
        self.svc.acknowledge(OrderAck(accepted=tuple(o.segment for o in orders.orders)))
        for _ in range(15):
            self.svc.update(0.033, MusicSnapshot())
        status = self.svc.get_status()
        self.assertTrue(status.is_cooling_down)
        self.assertGreater(status.cooldown_remaining, 4.0)

        # 2. User clicks 'Next Mode' (manual override) while off-beat (beat_phase = 0.5)
        self.svc.request_next()
        # Mid-beat update: transition should not fire yet
        off_beat = MusicSnapshot(beat_phase=0.5, is_beat=False)
        orders_pending = self.svc.update(0.033, off_beat)
        self.assertIsNone(orders_pending)

        # 3. Live song change arrives while manual transition is still pending downbeat
        song_change_music = MusicSnapshot(beat_phase=0.5, is_beat=False, is_song_change=True)
        orders_sc = self.svc.update(0.033, song_change_music)
        self.assertIsNone(orders_sc)

        # 4. Downbeat arrives: the user's manual transition MUST fire, NOT the song change!
        on_beat = MusicSnapshot(beat_phase=0.01, is_beat=True)
        orders_fired = self.svc.update(0.033, on_beat)
        self.assertIsNotNone(orders_fired)
        self.assertEqual(orders_fired.reason, "request_next", "Manual request must not be displaced by automatic triggers")

    def test_all_blocked_segments_do_not_desync_director_into_transition_dual(self):
        """When all segments are blocked, firing a transition must not leave the director stuck in TRANSITION_DUAL."""
        all_blocked = tuple(f"Segment v{i}" for i in range(1, 5))
        self.svc.set_installation(installation(blocked=all_blocked))

        # 1. Immediate drop request while all segments are blocked
        self.svc.request_drop()
        orders = self.svc.update(0.033, beat_music())
        self.assertIsNone(orders)
        status = self.svc.get_status()
        self.assertEqual(status.state, "PASSATION")
        self.assertFalse(status.is_in_transition)

        # 2. Beat-quantized request_next while all segments are blocked
        self.svc.request_next()
        orders = self.svc.update(0.033, beat_music())
        self.assertIsNone(orders)
        status = self.svc.get_status()
        self.assertEqual(status.state, "PASSATION")
        self.assertFalse(status.is_in_transition)
        self.assertFalse(self.svc._director.is_pending)

        # 3. Unblock one segment: subsequent transition fires cleanly
        self.svc.set_installation(installation(blocked=all_blocked[1:]))
        self.svc.request_next()
        orders_unblocked = self.svc.update(0.033, beat_music())
        self.assertIsNotNone(orders_unblocked)
        self.assertEqual(len(orders_unblocked.orders), 1)
        self.assertEqual(orders_unblocked.orders[0].segment, "Segment v1")
        self.assertTrue(self.svc.get_status().is_in_transition)

    def test_segments_blocked_during_downbeat_wait_window_do_not_desync_director(self):
        """If segments are unblocked when queued (quantize_downbeat=True) and all become blocked before the beat, director stays in PASSATION."""
        self.svc.request_next()
        # Off-beat tick: still waiting for beat
        self.assertIsNone(self.svc.update(0.033, MusicSnapshot(beat_phase=0.5, is_beat=False)))
        self.assertTrue(self.svc._director.is_pending)

        # All segments become blocked during the downbeat wait window
        all_blocked = tuple(f"Segment v{i}" for i in range(1, 5))
        self.svc.set_installation(installation(blocked=all_blocked))

        # Beat arrives: _execute_transition runs with 0 unblocked segments
        orders = self.svc.update(0.033, beat_music())
        self.assertIsNone(orders)
        status = self.svc.get_status()
        self.assertEqual(status.state, "PASSATION")
        self.assertFalse(status.is_in_transition)
        self.assertFalse(self.svc._director.is_pending)
        self.assertEqual(self.svc._reason, "")

    def test_immediate_drop_supersedes_pending_downbeat_transition(self):
        """An immediate transition (request_drop or drop_impact) while waiting for a beat must cancel the stale pending transition."""
        # Queue beat-quantized transition while off-beat
        self.svc.request_next()
        self.assertIsNone(self.svc.update(0.033, MusicSnapshot(beat_phase=0.5, is_beat=False)))

        # Immediate drop arrives before beat
        self.svc.request_drop()
        drop_orders = self.svc.update(0.033, MusicSnapshot(beat_phase=0.5, is_beat=False))
        self.assertIsNotNone(drop_orders)
        self.assertEqual(drop_orders.reason, "request_drop")
        self.assertEqual(self.svc.get_status().progress, 0.0)
        self.svc.acknowledge(OrderAck(accepted=tuple(o.segment for o in drop_orders.orders)))

        # Complete the 0.4s drop transition
        for _ in range(15):
            self.svc.update(0.033, MusicSnapshot(beat_phase=0.5, is_beat=False))
        self.assertFalse(self.svc.get_status().is_in_transition)
        self.assertTrue(self.svc.get_status().is_cooling_down)

        # Next beat arrives during cooldown: stale pending transition must NOT fire
        self.assertIsNone(self.svc.update(0.033, beat_music()))
        self.assertTrue(self.svc.get_status().is_cooling_down)

    def test_duplicate_request_drop_emits_one_order_per_segment(self):
        """Calling request_drop multiple times before update() must emit only one order per segment."""
        self.svc.request_drop()
        self.svc.request_drop()
        orders = self.svc.update(0.033, beat_music())
        self.assertIsNotNone(orders)
        self.assertEqual(len(orders.orders), 4)

    def test_request_next_queued_during_active_transition_preserves_reason(self):
        """A request_next queued during TRANSITION_DUAL preserves its reason across transition completion until the beat."""
        self.svc.request_drop()
        drop_orders = self.svc.update(0.033, beat_music())
        self.svc.acknowledge(OrderAck(accepted=tuple(o.segment for o in drop_orders.orders)))
        self.assertTrue(self.svc.get_status().is_in_transition)

        # Queue request_next while drop transition is still running
        self.svc.request_next()

        # Advance off-beat until drop transition finishes
        for _ in range(15):
            self.assertIsNone(self.svc.update(0.033, MusicSnapshot(beat_phase=0.5, is_beat=False)))
        self.assertFalse(self.svc.get_status().is_in_transition)

        # Now beat arrives: queued request_next fires with its reason intact
        next_orders = self.svc.update(0.033, beat_music())
        self.assertIsNotNone(next_orders)
        self.assertEqual(next_orders.reason, "request_next")


if __name__ == "__main__":
    unittest.main()


