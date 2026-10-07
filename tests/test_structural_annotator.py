"""
tests/test_structural_annotator.py - Unit tests for tools/structural_annotator.py.
"""

from __future__ import annotations
import os
import sys
import json
import tempfile
import unittest
import numpy as np

# Ensure repository root is on sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.structural_annotator import (
    AudioStreamer,
    WaveformEnvelope,
    AnnotationManager,
    StructuralAnnotatorApp,
    EVENT_CLIMAX,
    EVENT_BUILDUP,
    EVENT_BREAKDOWN,
    EVENT_SECTION,
)


class TestAudioStreamer(unittest.TestCase):
    def setUp(self):
        self.sr = 44100
        # 2 seconds of test sine tone
        t = np.linspace(0, 2.0, self.sr * 2, endpoint=False)
        self.audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    def test_streamer_initialization_and_duration(self):
        streamer = AudioStreamer(self.audio, sample_rate=self.sr)
        self.assertEqual(streamer.sample_rate, self.sr)
        self.assertEqual(streamer.total_samples, self.sr * 2)
        self.assertAlmostEqual(streamer.total_duration, 2.0, places=3)
        self.assertFalse(streamer.is_playing)
        streamer.stop()

    def test_streamer_seek_and_time(self):
        streamer = AudioStreamer(self.audio, sample_rate=self.sr)
        streamer.seek(1.25)
        # Strict sample accuracy verification (zero latency drift when paused)
        self.assertAlmostEqual(streamer.get_current_time(), 1.25, places=3)
        # Clamping
        streamer.seek(-5.0)
        self.assertEqual(streamer.get_current_time(), 0.0)
        streamer.seek(10.0)
        self.assertAlmostEqual(streamer.get_current_time(), 2.0, places=2)
        streamer.stop()

    def test_streamer_pause_seek_accuracy_after_playing(self):
        import time
        streamer = AudioStreamer(self.audio, sample_rate=self.sr)
        streamer.play()
        time.sleep(0.05)
        streamer.pause()
        streamer.seek(0.75)
        # Paused seeking must not subtract DAC latency
        self.assertAlmostEqual(streamer.get_current_time(), 0.75, places=3)
        streamer.stop()

    def test_streamer_play_pause(self):
        streamer = AudioStreamer(self.audio, sample_rate=self.sr)
        streamer.play()
        self.assertTrue(streamer.is_playing)
        streamer.pause()
        self.assertFalse(streamer.is_playing)
        streamer.toggle_play()
        self.assertTrue(streamer.is_playing)
        streamer.stop()


class TestWaveformEnvelope(unittest.TestCase):
    def test_envelope_calculation(self):
        sr = 44100
        t = np.linspace(0, 5.0, sr * 5, endpoint=False)
        audio = (np.sin(2 * np.pi * 100 * t)).astype(np.float32)

        env = WaveformEnvelope(audio, sample_rate=sr, overview_bins=500)
        self.assertEqual(len(env.overview_min), 500)
        self.assertEqual(len(env.overview_max), 500)
        self.assertTrue(np.all(env.overview_max <= 1.05))
        self.assertTrue(np.all(env.overview_min >= -1.05))

    def test_timeline_slice(self):
        sr = 44100
        audio = np.zeros(sr * 10, dtype=np.float32)
        audio[sr * 2 : sr * 3] = 0.8  # pulse at 2s..3s
        env = WaveformEnvelope(audio, sample_rate=sr)

        sub_min, sub_max = env.get_timeline_slice(1.5, 3.5, target_pixels=100)
        self.assertEqual(len(sub_min), 100)
        self.assertEqual(len(sub_max), 100)
        self.assertTrue(np.max(sub_max) >= 0.75)

    def test_timeline_slice_negative_padding_and_boundaries(self):
        sr = 44100
        audio = np.zeros(sr * 10, dtype=np.float32)
        audio[0 : sr * 2] = 0.9  # pulse at 0s..2s
        env = WaveformEnvelope(audio, sample_rate=sr)

        # Centered around 0.0s (-8.0s to +8.0s)
        sub_min, sub_max = env.get_timeline_slice(-8.0, 8.0, target_pixels=160)
        self.assertEqual(len(sub_min), 160)
        self.assertEqual(len(sub_max), 160)
        # Pixels 0..79 represent negative time (<0s) and must be zero
        self.assertEqual(np.max(sub_max[:80]), 0.0)
        # Pixels representing 0s..2s must contain pulse
        self.assertTrue(np.max(sub_max[80:100]) >= 0.85)


class TestAnnotationManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.json_path = os.path.join(self.temp_dir.name, "test_annotations.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ensure_track_and_save(self):
        mgr = AnnotationManager(self.json_path)
        td = mgr.ensure_track("TestTrack", 120.5)
        self.assertEqual(td["duration_sec"], 120.5)
        self.assertEqual(td["status"], "unreviewed")
        self.assertEqual(td["events"], [])

        saved = mgr.save()
        self.assertTrue(saved)
        self.assertTrue(os.path.exists(self.json_path))

        # Re-read
        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("TestTrack", data["tracks"])
        self.assertEqual(data["tracks"]["TestTrack"]["duration_sec"], 120.5)

    def test_auto_linking_buildup_and_drop(self):
        mgr = AnnotationManager(self.json_path)
        td = mgr.ensure_track("Genesis", 235.0)

        # 1. Add Buildup at 45.0s
        evt1 = {
            "id": "evt_001",
            "type": EVENT_BUILDUP,
            "time_sec": 45.0,
            "raw_tap_sec": 45.0,
            "snapped_to_downbeat": False,
            "snap_delta_ms": 0.0,
            "pair_id": None,
            "note": "",
        }
        td["events"].append(evt1)

        # 2. Add Climax at 53.0s (within 45s of buildup)
        evt2 = {
            "id": "evt_002",
            "type": EVENT_CLIMAX,
            "time_sec": 53.0,
            "raw_tap_sec": 53.0,
            "snapped_to_downbeat": False,
            "snap_delta_ms": 0.0,
            "pair_id": None,
            "note": "",
        }
        mgr.auto_link_pair("Genesis", evt2)
        td["events"].append(evt2)

        self.assertIsNotNone(evt1.get("pair_id"))
        self.assertEqual(evt1["pair_id"], evt2["pair_id"])
        self.assertEqual(evt2["pair_id"], "drop_evt_002")

    def test_undo_redo_stack(self):
        mgr = AnnotationManager(self.json_path)
        td = mgr.ensure_track("Genesis", 235.0)

        # State 0: empty
        mgr.push_state("Genesis")
        # Add event 1
        td["events"].append({"id": "evt_001", "type": EVENT_SECTION, "time_sec": 10.0})

        # State 1: 1 event
        mgr.push_state("Genesis")
        # Add event 2
        td["events"].append({"id": "evt_002", "type": EVENT_CLIMAX, "time_sec": 20.0})
        self.assertEqual(len(td["events"]), 2)

        # Undo -> should have 1 event
        self.assertTrue(mgr.undo("Genesis"))
        self.assertEqual(len(td["events"]), 1)
        self.assertEqual(td["events"][0]["id"], "evt_001")

        # Undo -> should have 0 events
        self.assertTrue(mgr.undo("Genesis"))
        self.assertEqual(len(td["events"]), 0)

        # Redo -> should have 1 event
        self.assertTrue(mgr.redo("Genesis"))
        self.assertEqual(len(td["events"]), 1)

        # Redo -> should have 2 events
        self.assertTrue(mgr.redo("Genesis"))
        self.assertEqual(len(td["events"]), 2)


class TestStructuralAnnotatorAppHeadless(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = StructuralAnnotatorApp(
            repo_root=_REPO_ROOT,
            initial_track="Genesis",
            headless=True
        )

    def tearDown(self):
        if self.app.streamer:
            self.app.streamer.stop()
        self.temp_dir.cleanup()

    def test_headless_initialization_and_track_loading(self):
        self.assertEqual(self.app.current_track_name(), "Genesis")
        self.assertGreater(len(self.app.track_list), 0)
        self.assertIsNotNone(self.app.envelope)
        self.assertGreater(self.app.streamer.total_duration, 0.0)

    def test_add_event_and_reflex_compensation(self):
        # 1. While paused: 0ms reflex compensation
        self.app.streamer.seek(30.0)
        self.app.streamer.pause()
        self.app.add_event(EVENT_SECTION)

        evt = self.app.get_selected_event()
        self.assertIsNotNone(evt)
        self.assertEqual(evt["type"], EVENT_SECTION)
        self.assertAlmostEqual(evt["time_sec"], 30.0, places=2)
        self.assertAlmostEqual(evt["raw_tap_sec"], 30.0, places=2)

        # 2. While playing: -100ms reflex compensation
        self.app.streamer.seek(50.0)
        self.app.streamer.play()
        self.app.add_event(EVENT_CLIMAX)

        evt2 = self.app.get_selected_event()
        self.assertIsNotNone(evt2)
        self.assertEqual(evt2["type"], EVENT_CLIMAX)
        # raw_tap_sec is ~50.0s, effective time_sec is ~49.9s (-100ms)
        self.assertAlmostEqual(evt2["raw_tap_sec"], 50.0, delta=0.1)
        self.assertAlmostEqual(evt2["time_sec"], 49.9, delta=0.1)

    def test_marker_nudging(self):
        self.app.streamer.seek(15.0)
        self.app.streamer.pause()
        self.app.add_event(EVENT_BREAKDOWN)
        old_t = self.app.get_selected_event()["time_sec"]

        # Nudge +10ms
        self.app.nudge_selected(0.010)
        self.assertAlmostEqual(self.app.get_selected_event()["time_sec"], old_t + 0.010, places=3)

        # Nudge -10ms
        self.app.nudge_selected(-0.010)
        self.assertAlmostEqual(self.app.get_selected_event()["time_sec"], old_t, places=3)

    def test_marker_snapping_to_downbeat(self):
        if len(self.app.downbeats) > 0:
            target_db = self.app.downbeats[5]
            # Place marker 80ms before downbeat while playing (-100ms reflex compensation)
            self.app.streamer.seek(target_db - 0.080)
            self.app.streamer.play()
            self.app.add_event(EVENT_CLIMAX)
            evt = self.app.get_selected_event()
            pre_snap_time = evt["time_sec"]

            # Snap to downbeat
            self.app.snap_selected_to_downbeat()
            self.assertTrue(evt["snapped_to_downbeat"])
            self.assertAlmostEqual(evt["time_sec"], target_db, places=3)

            # Toggle un-snap: must restore pre_snap_time (preserving reflex offset)
            self.app.snap_selected_to_downbeat()
            evt_unsnapped = self.app.get_selected_event()
            self.assertFalse(evt_unsnapped["snapped_to_downbeat"])
            self.assertAlmostEqual(evt_unsnapped["time_sec"], pre_snap_time, places=3)

    def test_delete_paired_event_unlinks_partner(self):
        self.app.streamer.pause()
        self.app.streamer.seek(10.0)
        self.app.add_event(EVENT_BUILDUP)
        b_id = self.app.selected_event_id

        self.app.streamer.seek(18.0)
        self.app.add_event(EVENT_CLIMAX)
        d_id = self.app.selected_event_id

        events = self.app.current_track_data()["events"]
        evt_b = next(e for e in events if e["id"] == b_id)
        evt_d = next(e for e in events if e["id"] == d_id)
        self.assertIsNotNone(evt_b.get("pair_id"))
        self.assertEqual(evt_b["pair_id"], evt_d["pair_id"])

        # Delete the drop -> partner buildup's pair_id must be cleared to None
        self.app.selected_event_id = d_id
        self.app.delete_selected()
        self.assertIsNone(evt_b.get("pair_id"))

    def test_arbitrary_track_path_resolution(self):
        from tools.structural_annotator import resolve_audio_file
        # Direct relative file path
        res = resolve_audio_file("assets/musics/mp3_files/Genesis.mp3", _REPO_ROOT)
        self.assertIsNotNone(res)
        # Filename with extension
        res2 = resolve_audio_file("Genesis.mp3", _REPO_ROOT)
        self.assertIsNotNone(res2)

    def test_track_cycling(self):
        first_track = self.app.current_track_name()
        self.app.change_track(1)
        second_track = self.app.current_track_name()
        self.assertNotEqual(first_track, second_track)
        self.app.change_track(-1)
        self.assertEqual(self.app.current_track_name(), first_track)


if __name__ == "__main__":
    unittest.main()
