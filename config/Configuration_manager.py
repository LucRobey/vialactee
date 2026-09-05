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


def resolve_audio_config(infos: dict) -> dict:
    """
    Intelligently resolves audio devices (input, output) and fakeDelay
    based on infos['audio_preset'].
    Supported presets: 'spotify', 'spotify_aux', 'aux', 'mic', 'custom'.
    """
    if not isinstance(infos, dict):
        return infos

    preset = str(infos.get("audio_preset", "spotify")).lower().strip()
    if preset == "custom":
        return infos

    import logging
    logger = logging.getLogger("AudioConfig")

    try:
        import sounddevice as sd
        devices = sd.query_devices()
        default_in, default_out = sd.default.device
    except Exception as e:
        logger.warning(
            f"Unable to query sounddevice ({e}). Keeping raw audio config."
        )
        return infos

    def find_device(patterns, kind="input", exclude_patterns=None):
        exclude_patterns = [x.lower() for x in (exclude_patterns or [])]
        for idx, dev in enumerate(devices):
            name = dev["name"].lower()
            if any(ex in name for ex in exclude_patterns):
                continue
            is_valid_kind = (dev["max_input_channels"] > 0) if kind == "input" else (dev["max_output_channels"] > 0)
            if is_valid_kind and any(pat.lower() in name for pat in patterns):
                return idx, dev["name"]
        return None, None

    if preset == "spotify":
        idx_in, name_in = find_device(["cable output", "vb-audio", "virtual audio cable", "virtual cable", "cable-a", "cable-b"], kind="input")
        idx_out, name_out = find_device(
            ["speakers", "haut-parleur"],
            kind="output",
            exclude_patterns=["cable", "vb-audio"]
        )
        if idx_in is not None:
            infos["input_device_id"] = idx_in
            infos["output_device_id"] = idx_out if idx_out is not None else default_out
            infos["fakeDelay"] = 5.0
            logger.info(f"[AudioPreset: spotify] In: '{name_in}' (idx={idx_in}), Out: '{name_out}' (idx={infos['output_device_id']}), fakeDelay=5.0s")
        else:
            logger.warning(
                "[AudioPreset: spotify] Virtual Cable not detected. "
                "Download VB-Audio Cable from https://vb-audio.com/Cable/ to capture Spotify with 5s delay. "
                f"Falling back to default input (idx={default_in})."
            )
            infos["input_device_id"] = default_in
            infos["output_device_id"] = idx_out if idx_out is not None else default_out
            infos["fakeDelay"] = 5.0

    elif preset == "spotify_aux":
        idx_in, name_in = find_device(["cable output", "vb-audio", "virtual audio cable", "virtual cable", "cable-a", "cable-b"], kind="input")
        idx_out, name_out = find_device(
            ["casque", "headphones", "headphone", "aux", "line out", "speakers 2"],
            kind="output",
            exclude_patterns=["cable", "vb-audio"]
        )
        if idx_out is None:
            idx_out, name_out = find_device(
                ["speakers", "haut-parleur"],
                kind="output",
                exclude_patterns=["cable", "vb-audio"]
            )
        if idx_in is not None:
            infos["input_device_id"] = idx_in
            infos["output_device_id"] = idx_out if idx_out is not None else default_out
            infos["fakeDelay"] = 5.0
            logger.info(f"[AudioPreset: spotify_aux] In: '{name_in}' (idx={idx_in}), Out: '{name_out}' (idx={infos['output_device_id']}), fakeDelay=5.0s")
        else:
            logger.warning(
                "[AudioPreset: spotify_aux] Virtual Cable not detected. "
                "Download VB-Audio Cable from https://vb-audio.com/Cable/ to use 5s anticipation mode."
            )
            infos["input_device_id"] = default_in
            infos["output_device_id"] = idx_out if idx_out is not None else default_out
            infos["fakeDelay"] = 5.0

    elif preset == "aux":
        idx_in, name_in = find_device(["line in", "entrée ligne", "line-in", "aux"], kind="input")
        if idx_in is None:
            idx_in = default_in
            name_in = devices[default_in]["name"] if default_in is not None and default_in >= 0 else "Default Mic"
        idx_out, name_out = find_device(
            ["speakers", "haut-parleur", "line out", "casque", "headphones"],
            kind="output",
            exclude_patterns=["cable", "vb-audio"]
        )
        infos["input_device_id"] = idx_in
        infos["output_device_id"] = idx_out if idx_out is not None else default_out
        infos["fakeDelay"] = 5.0
        logger.info(f"[AudioPreset: aux] In: '{name_in}' (idx={idx_in}), Out: '{name_out}' (idx={infos['output_device_id']}), fakeDelay=5.0s")

    elif preset == "mic":
        infos["input_device_id"] = default_in
        infos["output_device_id"] = None
        infos["fakeDelay"] = 0.0
        mic_name = devices[default_in]["name"] if default_in is not None and default_in >= 0 else "Default Mic"
        logger.info(f"[AudioPreset: mic] Using default microphone '{mic_name}' (idx={default_in}), fakeDelay=0.0s")

    else:
        logger.warning(f"Unknown audio_preset '{preset}'. Keeping raw configuration.")

    return infos