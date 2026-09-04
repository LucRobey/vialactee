import json
import os


def resolve_segments_file_path(infos=None):
    profile = "full"
    if isinstance(infos, dict):
        profile = infos.get("hardware_profile", "full")
    else:
        try:
            app_cfg_path = os.path.join(os.path.dirname(__file__), "app_config.json")
            if os.path.exists(app_cfg_path):
                with open(app_cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    profile = cfg.get("hardware_profile", "full")
        except Exception:
            profile = "full"

    if profile == "small":
        small_path = os.path.join(os.path.dirname(__file__), "segments_small.json")
        if os.path.exists(small_path):
            return small_path

    full_path = os.path.join(os.path.dirname(__file__), "segments_full.json")
    if os.path.exists(full_path):
        return full_path

    legacy_path = os.path.join(os.path.dirname(__file__), "segments.json")
    if os.path.exists(legacy_path):
        return legacy_path

    return full_path


def resolve_configurations_file_path(infos=None):
    profile = "full"
    if isinstance(infos, dict):
        profile = infos.get("hardware_profile", "full")
    else:
        try:
            app_cfg_path = os.path.join(os.path.dirname(__file__), "app_config.json")
            if os.path.exists(app_cfg_path):
                with open(app_cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    profile = cfg.get("hardware_profile", "full")
        except Exception:
            profile = "full"

    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    if profile == "small":
        small_path = os.path.join(data_dir, "configurations_small.json")
        if os.path.exists(small_path):
            return small_path

    full_path = os.path.join(data_dir, "configurations_full.json")
    if os.path.exists(full_path):
        return full_path

    return os.path.join(data_dir, "configurations.json")


class Configurations_manager:
    def __init__(self, infos=None):
        self.infos = infos
        self._segment_coords_by_name = None

    def _build_line_coordinates(self, length, start_x, start_y, step_x, step_y):
        return [[start_x + (i * step_x), start_y + (i * step_y)] for i in range(length)]

    def _iter_segment_definitions(self, payload):
        if isinstance(payload.get("segments"), list):
            return payload["segments"]

        segment_definitions = []
        for key, value in payload.items():
            if key.startswith("segs_") and isinstance(value, list):
                segment_definitions.extend(value)
        return segment_definitions

    def _load_segments_locations(self):
        config_path = resolve_segments_file_path(self.infos)
        with open(config_path, "r", encoding="utf-8") as file:
            payload = json.load(file)

        segments = self._iter_segment_definitions(payload)
        coords_by_name = {}
        for segment in segments:
            if not isinstance(segment, dict) or "start" not in segment or "step" not in segment:
                continue
            name = segment["name"]
            length = int(segment.get("length", segment.get("size", 0)))
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