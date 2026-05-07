import json
import os


class Configurations_manager:
    def __init__(self):
        self._segment_coords_by_name = None

    def _build_line_coordinates(self, length, start_x, start_y, step_x, step_y):
        return [[start_x + (i * step_x), start_y + (i * step_y)] for i in range(length)]

    def _load_segments_locations(self):
        config_path = os.path.join(os.path.dirname(__file__), "segments_locations.json")
        with open(config_path, "r", encoding="utf-8") as file:
            payload = json.load(file)

        segments = payload.get("segments", [])
        coords_by_name = {}
        for segment in segments:
            name = segment["name"]
            length = int(segment["length"])
            start_x = int(segment["start"]["x"])
            start_y = int(segment["start"]["y"])
            step_x = int(segment["step"]["x"])
            step_y = int(segment["step"]["y"])
            coords_by_name[name] = self._build_line_coordinates(length, start_x, start_y, step_x, step_y)

        return coords_by_name

    def get_segment_coordinates(self, segment_name):
        if self._segment_coords_by_name is None:
            self._segment_coords_by_name = self._load_segments_locations()
        return self._segment_coords_by_name.get(segment_name)