"""Tests for the room-bounds adapter (config/room_bounds.py) and the engine setter."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import core.Transition_Engine as TE
from config.room_bounds import compute_room_bounds


class TestRoomBounds(unittest.TestCase):
    def _write_layout(self, data):
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(data, f)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_bounds_computed_from_layout(self):
        path = self._write_layout({"segs_1": [
            {"name": "a", "start": {"x": 10, "y": 5}, "step": {"x": 2, "y": 0}, "size": 50},
            {"name": "b", "start": {"x": 0, "y": 0}, "step": {"x": 0, "y": 3}, "size": 80},
        ]})
        with patch("config.room_bounds.resolve_segments_file_path", return_value=path):
            self.assertEqual(compute_room_bounds({}), (110, 240))

    def test_missing_file_returns_none(self):
        with patch("config.room_bounds.resolve_segments_file_path", return_value="does/not/exist.json"):
            self.assertIsNone(compute_room_bounds({}))

    def test_engine_setter_applies_and_ignores_invalid(self):
        old = (TE.ROOM_MAX_X, TE.ROOM_MAX_Y)
        self.addCleanup(TE.set_room_bounds, *old)
        TE.set_room_bounds(100, 50)
        self.assertEqual((TE.ROOM_MAX_X, TE.ROOM_MAX_Y), (100, 50))
        TE.set_room_bounds(0, -1)
        self.assertEqual((TE.ROOM_MAX_X, TE.ROOM_MAX_Y), (100, 50))


if __name__ == "__main__":
    unittest.main()
