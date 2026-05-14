import numpy as np
import asyncio
import json
import logging
import os
import random
import time
from typing import Dict, Any, List, Optional

import connectors.System_status as System_status
import core.Segment as Segment
import core.Listener as Listener
import core.Transition_Director as Transition_Director



from contextlib import contextmanager

class Profiler:
    """
    A simple context-manager based profiler to measure execution time of code blocks.
    """
    def __init__(self, active: bool, logger: logging.Logger) -> None:
        """
        Initialize the Profiler.

        Args:
            active (bool): Whether the profiler is active and should record times.
            logger (logging.Logger): The logger instance to use for output.
        """
        self.active = active
        self.logger = logger
        self.durations = []
        self.names = []
        self.start_times = {}

    @contextmanager
    def measure(self, name: str) -> Any:
        """
        Context manager to measure the execution time of a block of code.

        Args:
            name (str): The name/label for this measurement block.
        """
        if self.active:
            start = time.time()
            yield
            self.durations.append(time.time() - start)
            self.names.append(name)
        else:
            yield

    def print_results(self) -> None:
        """
        Print the accumulated profiling results to the logger.
        """
        if self.active and self.durations:
            self.logger.debug("=======================================================================")
            total = np.sum(self.durations)
            self.logger.debug(f"   |(MM) total = {total:.5f} secondes")
            if total > 0:
                nb_of_it_per_sec = 1 / total
                self.logger.debug(f"   |(MM) soit {nb_of_it_per_sec:.2f} itérations par seconde")
                for k in range(len(self.durations)):
                    percentage = 100 * float(self.durations[k]) / total
                    self.logger.debug(f"   |(MM) {self.names[k]}  :  {percentage:.2f}%")


class Mode_master:
    """
    Master controller for all visual segments, modes, and configurations.

    Manages the global state, playlists, and transitions between different
    configurations across the entire installation.
    """

    def __init__(self, listener: Any, infos: Dict[str, Any], *leds: Any) -> None:
        """
        Initialize the Mode_master.

        Args:
            listener: Reference to the global audio listener.
            infos (dict): Dictionary containing global configuration and metadata.
            *leds: References to the LED strip hardware/simulators.
        """
        self.infos = infos
        self.listener = listener
        self.onRaspberry            = infos.get("onRaspberry", False)
        self.printTimeOfCalculation = infos.get("printTimeOfCalculation", False)
        self.printModesDetails      = infos.get("printModesDetails", False)
        self.printAppDetails        = infos.get("printAppDetails", False)
        self.printConfigChanges     = infos.get("printConfigChanges", False)

        self.leds_list = leds
        self.logger = logging.getLogger("Mode_master")
        self.profiler = Profiler(self.printTimeOfCalculation, self.logger)
        self.current_time = time.time()
        self.appli_connector = None
        self.segments_list: List[Segment.Segment] = []
        self.segments_names_to_index: Dict[str, int] = {}
        self.activ_configuration: Dict[str, Any] = {}
        self.configurations: Dict[str, List[Dict[str, Any]]] = {}
        self.playlists: List[str] = []
        self.blocked_playlists: List[bool] = []
        self.shuffle_bag: List[Dict[str, Any]] = []
        self.transition_locked = False
        self.selected_transition_config = {"type": "fade_in_out", "duration": 2.0}
        self.queued_configuration_name: Optional[str] = None
        self.mode_settings_catalog: Dict[str, Dict[str, Any]] = {}
        self.pending_system_action: Optional[str] = None
        self._restart_requested = asyncio.Event()
        self._last_update_monotonic: Optional[float] = None

        self.load_configurations()

        self.initiate_segments()
        self.mode_settings_catalog = self._build_mode_settings_catalog()
        self.initiate_configuration()
        self.transition_director = Transition_Director.Transition_Director(self, self.listener, self.infos)
        self.system_status = System_status.SystemStatus(self.infos, self.listener, self.leds_list)

    def set_connector(self, connector: Any) -> None:
        """
        Set the application connector for external communications.

        Args:
            connector: The connector instance.
        """
        self.appli_connector = connector

    def _websocket_count(self) -> int:
        if self.appli_connector is None:
            return 0
        return len(getattr(self.appli_connector, "active_websockets", []))

    def _set_system_action_feedback(self, action: str, state: str, message: str) -> None:
        self.system_status.set_last_action(action, state, message)

    async def _restart_python_process_task(self) -> None:
        try:
            await asyncio.sleep(0.35)
            self._restart_requested.set()
        except Exception as exc:
            self.pending_system_action = None
            self.logger.error("(MM) Could not restart python process: %s", exc)
            self._set_system_action_feedback(
                "restart_python_loop",
                "error",
                f"Python restart failed: {exc}",
            )

    async def wait_for_restart_request(self) -> None:
        await self._restart_requested.wait()

    async def _reboot_raspberry_task(self) -> None:
        try:
            await asyncio.sleep(0.35)
            command = self.system_status.resolve_reboot_command()
            if command is None:
                raise RuntimeError("No reboot command found on this host.")

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            self.pending_system_action = None

            if process.returncode != 0:
                error_text = (stderr or stdout or b"").decode("utf-8", errors="ignore").strip()
                raise RuntimeError(error_text or f"Command exited with code {process.returncode}")

            self._set_system_action_feedback(
                "restart_raspberry_pi",
                "success",
                "Reboot command accepted. The Raspberry should relaunch the app after boot.",
            )
        except Exception as exc:
            self.pending_system_action = None
            self.logger.error("(MM) Could not reboot Raspberry host: %s", exc)
            self._set_system_action_feedback(
                "restart_raspberry_pi",
                "error",
                f"Reboot failed: {exc}",
            )

    def _selected_transition_label(self) -> str:
        transition_type = self.selected_transition_config.get("type")
        if transition_type == "explosion":
            return "CUT"
        if transition_type == "global_change":
            return "CROSSFADE"
        if transition_type == "fade_in_out":
            return "FADE IN/OUT"
        return str(transition_type or "FADE IN/OUT")

    def _copy_mode_settings_map(self, mode_settings: Any) -> Dict[str, Dict[str, Any]]:
        if not isinstance(mode_settings, dict):
            return {}

        copied: Dict[str, Dict[str, Any]] = {}
        for mode_name, settings in mode_settings.items():
            if isinstance(mode_name, str) and isinstance(settings, dict):
                copied[mode_name] = dict(settings)
        return copied

    def _build_mode_settings_catalog(self) -> Dict[str, Dict[str, Any]]:
        catalog: Dict[str, Dict[str, Any]] = {}
        for segment in self.segments_list:
            for entry in segment.get_mode_settings_catalog():
                mode_name = entry.get("mode")
                settings = entry.get("settings")
                if (
                    isinstance(mode_name, str)
                    and isinstance(settings, list)
                    and len(settings) > 0
                    and mode_name not in catalog
                ):
                    catalog[mode_name] = {
                        "mode": mode_name,
                        "label": entry.get("label", mode_name),
                        "settings": settings,
                    }
        return catalog

    def _mode_settings_defaults_for_mode(self, mode_name: str) -> Dict[str, Any]:
        entry = self.mode_settings_catalog.get(mode_name, {})
        defaults: Dict[str, Any] = {}
        for descriptor in entry.get("settings", []):
            key = descriptor.get("key")
            if not isinstance(key, str) or "default" not in descriptor:
                continue
            normalized_value, ok = self._normalize_mode_setting_value(descriptor, descriptor.get("default"))
            if ok:
                defaults[key] = normalized_value
        return defaults

    def _get_mode_setting_descriptor(self, mode_name: str, setting_key: str) -> Optional[Dict[str, Any]]:
        entry = self.mode_settings_catalog.get(mode_name, {})
        for descriptor in entry.get("settings", []):
            if descriptor.get("key") == setting_key:
                return descriptor
        return None

    def _normalize_mode_setting_value(self, descriptor: Dict[str, Any], value: Any) -> Any:
        value_type = descriptor.get("valueType")

        if value_type == "boolean":
            if not isinstance(value, bool):
                return None, False
            normalized_value = value
        elif value_type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None, False
            normalized_value = float(value)
            min_value = descriptor.get("min")
            max_value = descriptor.get("max")
            if isinstance(min_value, (int, float)):
                normalized_value = max(float(min_value), normalized_value)
            if isinstance(max_value, (int, float)):
                normalized_value = min(float(max_value), normalized_value)
            if descriptor.get("integer", False):
                normalized_value = int(round(normalized_value))
        else:
            if not isinstance(value, str):
                return None, False
            normalized_value = value

        options = descriptor.get("options")
        if isinstance(options, list) and len(options) > 0:
            allowed_values = [
                option.get("value")
                for option in options
                if isinstance(option, dict) and "value" in option
            ]
            if len(allowed_values) > 0 and normalized_value not in allowed_values:
                return None, False

        return normalized_value, True

    def _get_effective_mode_settings(self, configuration: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        config = configuration if isinstance(configuration, dict) else self.activ_configuration
        effective: Dict[str, Dict[str, Any]] = {
            mode_name: self._mode_settings_defaults_for_mode(mode_name)
            for mode_name in self.mode_settings_catalog
        }

        overrides = config.get("modeSettings", {})
        if not isinstance(overrides, dict):
            return effective

        for mode_name, settings in overrides.items():
            if mode_name not in self.mode_settings_catalog or not isinstance(settings, dict):
                continue

            merged = dict(effective.get(mode_name, {}))
            for descriptor in self.mode_settings_catalog[mode_name].get("settings", []):
                key = descriptor.get("key")
                if not isinstance(key, str) or key not in settings:
                    continue
                normalized_value, ok = self._normalize_mode_setting_value(descriptor, settings.get(key))
                if ok:
                    merged[key] = normalized_value
            effective[mode_name] = merged

        return effective

    def _apply_mode_settings_to_segments(self, mode_settings: Dict[str, Dict[str, Any]]) -> None:
        if not isinstance(mode_settings, dict):
            return

        for segment in self.segments_list:
            for mode_name, settings in mode_settings.items():
                if isinstance(mode_name, str) and isinstance(settings, dict):
                    segment.apply_mode_settings(mode_name, settings)

    def _apply_active_mode_settings(self) -> None:
        self._apply_mode_settings_to_segments(self._get_effective_mode_settings())

    def _persist_configurations_store(self) -> bool:
        file_path = os.path.join(os.path.dirname(__file__), "..", "data", "configurations.json")
        payload = {
            "playlists": list(self.playlists),
            "configurations": self.configurations,
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.write("\n")
            return True
        except Exception as e:
            self.logger.error(f"(MM) Failed to persist configurations.json: {e}")
            return False

    def _persist_active_configuration_mode_settings(self) -> bool:
        playlist_name = self.activ_configuration.get("playlist")
        configuration_name = self.activ_configuration.get("name")
        if not isinstance(playlist_name, str) or not isinstance(configuration_name, str):
            return False

        playlist_configs = self.configurations.get(playlist_name)
        if not isinstance(playlist_configs, list):
            return False

        for config in playlist_configs:
            if not isinstance(config, dict):
                continue
            if str(config.get("name", "")).strip().lower() != configuration_name.strip().lower():
                continue
            config["modeSettings"] = self._copy_mode_settings_map(self.activ_configuration.get("modeSettings", {}))
            return self._persist_configurations_store()

        return False

    def get_state_snapshot(self) -> Dict[str, Any]:
        """
        Build a JSON-serializable snapshot for the web interface.
        """
        active_playlist = self.activ_configuration.get("playlist")
        enabled_playlists = [
            playlist
            for index, playlist in enumerate(self.playlists)
            if index >= len(self.blocked_playlists) or not self.blocked_playlists[index]
        ]

        segments = []
        for segment in self.segments_list:
            segments.append({
                "id": segment.name.replace("Segment ", "", 1),
                "name": segment.name,
                "mode": segment.get_current_mode(),
                "direction": segment.way,
                "blocked": segment.isBlocked,
                "targetMode": segment.target_mode_name,
                "inTransition": segment.is_in_transition,
            })

        available_modes = sorted({
            mode_name
            for segment in self.segments_list
            for mode_name in getattr(segment, "modes", {}).keys()
        })

        return {
            "activePlaylist": active_playlist,
            "enabledPlaylists": enabled_playlists,
            "activeConfiguration": self.activ_configuration.get("name"),
            "queuedConfiguration": self.queued_configuration_name,
            "selectedTransition": self._selected_transition_label(),
            "transitionLocked": self.transition_locked,
            "transitionState": getattr(self.transition_director, "state", None),
            "transitionProgress": getattr(self.transition_director, "transition_progress", 0.0),
            "luminosity": int(round(max(0.0, min(1.0, float(getattr(self.listener, "luminosite", 0.0)))) * 100)),
            "sensibility": int(round(max(0.0, float(getattr(self.listener, "sensi", 0.0))) * 100)),
            "playlists": list(self.playlists),
            "availableModes": available_modes,
            "segments": segments,
            "modeSettingsCatalog": list(self.mode_settings_catalog.values()),
            "modeSettings": self._get_effective_mode_settings(),
            "system": self.system_status.get_snapshot(self._websocket_count()),
        }

    async def update_forever(self) -> None:
        """
        Continuously update the system at approximately 30 FPS.
        """
        while True:
            await self.update()
            await asyncio.sleep(1/30)

    async def update(self) -> None:
        """
        Perform a single update loop iteration.

        Updates the audio listener, flushes hardware LED buffers, updates all
        segments, and evaluates global transitions via the Transition_Director.
        """
        frame_start = time.monotonic()
        frame_dt = None if self._last_update_monotonic is None else frame_start - self._last_update_monotonic
        self._last_update_monotonic = frame_start
        self.system_status.note_loop_tick(frame_dt)

        # Profiler cleans up the time_time() boilerplate
        with self.profiler.measure("listener.update()"):
            self.listener.update()

        with self.profiler.measure("leds.show()"):
            is_rpi_hardware = len(self.leds_list) > 0 and "Rpi_NeoPixels" in str(type(self.leds_list[0]))
            if self.infos.get("onRaspberry", False) or self.infos.get("HARDWARE_MODE") == "rpi" or is_rpi_hardware:
                loop = asyncio.get_running_loop()
                for led_strip in self.leds_list:
                    await loop.run_in_executor(None, led_strip.show)
            else:
                for led_strip in self.leds_list:
                    led_strip.show()

        with self.profiler.measure("segments.update()"):
            for seg_index in range(len(self.segments_list)):
                self.segments_list[seg_index].update(self.transition_director)

        #==============================================
        self.current_time = time.time()
        
        await self.transition_director.update(self.current_time)

        if self.appli_connector is not None:
            await self.appli_connector.broadcast_state_if_changed(self.get_state_snapshot())

        self.profiler.print_results()
        # Clean profiler values for next frame
        self.profiler.durations.clear()
        self.profiler.names.clear()


    def load_configurations(self) -> None:
        """
        Load modes and playlists from the configurations.json file.
        """
        file_path = os.path.join(os.path.dirname(__file__), "..", "data", "configurations.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.configurations = data.get('configurations', {})
            self.playlists = list(self.configurations.keys())
            if self.printConfigChanges:
                self.logger.debug(f"(MM) Loaded {len(self.playlists)} playlists from {file_path}")
        except Exception as e:
            self.logger.error(f"Error reading JSON configuration file: {e}")
            self.configurations = {}
            self.playlists = []

        self.blocked_playlists = [False for _ in self.playlists]
        self.shuffle_bag = []
    def update_segments_modes(self, transition_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Apply the active configuration to all relevant segments.

        Args:
            transition_config (dict, optional): Configuration defining the type and
                duration of the transition. Defaults to None.
        """
        if transition_config is not None:
            self.transition_director.start_transition(transition_config)

        self._apply_active_mode_settings()

        active_modes = self.activ_configuration.get("modes", {})
        active_way = self.activ_configuration.get("way", {})
        for segment in self.segments_list:
            if not segment.isBlocked:
                self.logger.debug(f"(MM) update_segments_modes : {segment.name} non bloqué donc on ordonne de le changer")
                mode_name = active_modes.get(segment.name)
                if mode_name is not None:
                    segment.change_mode(mode_name, transition_config)
                way = active_way.get(segment.name)
                if way is not None:
                    segment.change_way(way)

 

    def initiate_configuration(self) -> None:
        """
        Initialize the starting configuration by picking a random one from available playlists.
        """
        #On initialise en prenant une conf au pif dans une playlist au pif
        self.activ_configuration = self._detach_configuration_modes(self.pick_a_random_conf())
        self.update_segments_modes()

        

    def initiate_segments(self) -> None:
        """
        Initialize all segments based on the segments.json configuration file.
        """
        def add_segments(info_list: List[Dict[str, Any]], leds: Any) -> None:
            offset = 0
            for segment_index in range(len(info_list)):
                seg_infos = info_list[segment_index]
                indexes = [i for i in range(offset,offset+seg_infos["size"])]
                new_segment = Segment.Segment(seg_infos["name"],self.listener, leds ,indexes,seg_infos["orientation"],self.infos)
                offset += seg_infos["size"]
                self.segments_list.append(new_segment)
                self.segments_names_to_index[seg_infos["name"]]=seg_infos["order"]
                
        import json
        import os
        file_path = os.path.join(os.path.dirname(__file__), "..", "config", "segments.json")
        with open(file_path, "r", encoding='utf-8') as f:
            data = json.load(f)
            
        for i, leds in enumerate(self.leds_list):
            key = f"segs_{i+1}"
            if key in data:
                add_segments(data[key], leds)


    async def change_configuration(self, transition_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Change the global active configuration to a new random one.

        Args:
            transition_config (dict, optional): Configuration defining the type and
                duration of the transition. Defaults to None.
        """
        #on pick une conf nouvelle au pif
        last_configuration = self.activ_configuration
        loop_guard = 0
        while (last_configuration==self.activ_configuration and loop_guard < 10):
            self.activ_configuration = self._detach_configuration_modes(self.pick_a_random_conf())
            loop_guard += 1
        #on l'applique à tous les segments
        self.update_segments_modes(transition_config)

    def _normalize_transition(self, transition_name: Any) -> Dict[str, Any]:
        if not isinstance(transition_name, str):
            return {"type": "fade_in_out", "duration": 2.0}

        normalized = transition_name.strip().upper()
        if normalized == "CUT":
            return {"type": "explosion", "duration": 0.0}
        if normalized == "CROSSFADE":
            return {"type": "global_change", "duration": 3.0}
        if normalized == "FADE IN/OUT":
            return {"type": "fade_in_out", "duration": 2.0}
        return {"type": "fade_in_out", "duration": 2.0}

    def _segment_name_from_id(self, segment_id: Any) -> Optional[str]:
        if not isinstance(segment_id, str) or len(segment_id.strip()) == 0:
            return None
        return f"Segment {segment_id.strip()}"

    def _find_segment_by_name(self, segment_name: str) -> Optional[Segment.Segment]:
        for segment in self.segments_list:
            if segment.name == segment_name:
                return segment
        return None

    def _set_only_playlist_active(self, playlist_name: Any) -> bool:
        if not isinstance(playlist_name, str):
            return False

        normalized_name = playlist_name.strip()
        if normalized_name.upper() == "CUSTOM":
            return False

        selected_index = None
        for index, name in enumerate(self.playlists):
            if name.lower() == normalized_name.lower():
                selected_index = index
                break

        if selected_index is None:
            return False

        self.blocked_playlists = [idx != selected_index for idx in range(len(self.playlists))]
        self.shuffle_bag = []
        return True

    def _pick_random_conf_from_playlist(self, playlist_name: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(playlist_name, str):
            return None

        selected_playlist = None
        for name in self.playlists:
            if name.lower() == playlist_name.strip().lower():
                selected_playlist = name
                break

        if selected_playlist is None:
            return None

        playlist_configs = self.configurations.get(selected_playlist, [])
        if len(playlist_configs) == 0:
            return None

        conf_index = random.randrange(len(playlist_configs))
        conf = playlist_configs[conf_index]
        return {
            "playlist": selected_playlist,
            "index": conf_index,
            "name": conf.get("name"),
            "modes": conf.get("modes", {}),
            "way": conf.get("way", {}),
            "modeSettings": conf.get("modeSettings", {}),
        }

    def _find_configuration(self, configuration_name: Any, playlist_name: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        if not isinstance(configuration_name, str):
            return None
        wanted_name = configuration_name.strip().lower()

        candidate_playlists = []
        if isinstance(playlist_name, str):
            candidate_playlists = [p for p in self.playlists if p.lower() == playlist_name.strip().lower()]
        if len(candidate_playlists) == 0:
            candidate_playlists = list(self.playlists)

        for playlist in candidate_playlists:
            for conf_index, conf in enumerate(self.configurations.get(playlist, [])):
                if conf.get("name", "").strip().lower() == wanted_name:
                    return {
                        "playlist": playlist,
                        "index": conf_index,
                        "name": conf.get("name"),
                        "modes": conf.get("modes", {}),
                        "way": conf.get("way", {}),
                        "modeSettings": conf.get("modeSettings", {}),
                    }
        return None

    def _detach_configuration_modes(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Shallow-copy modes/way so live segment swaps never mutate the in-memory playlist store.
        """
        if not isinstance(config, dict):
            return {}
        modes = config.get("modes")
        way = config.get("way")
        mode_settings = config.get("modeSettings")
        return {
            **config,
            "modes": dict(modes) if isinstance(modes, dict) else {},
            "way": dict(way) if isinstance(way, dict) else {},
            "modeSettings": self._copy_mode_settings_map(mode_settings),
        }

    def _apply_configuration(self, config: Dict[str, Any], transition_config: Optional[Dict[str, Any]]) -> None:
        self.activ_configuration = self._detach_configuration_modes(config)
        self.update_segments_modes(transition_config)

    def _persist_app_config_value(self, key: str, value: Any) -> None:
        self.infos[key] = value

        import json
        import os
        file_path = os.path.join(os.path.dirname(__file__), "..", "config", "app_config.json")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
            data[key] = value
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                f.write("\n")
        except Exception as e:
            self.logger.error(f"(MM) Failed to persist {key} in app_config.json: {e}")

    async def process_instruction(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        page = instruction.get("page")
        action = instruction.get("action")
        payload = instruction.get("payload", {})

        if not isinstance(payload, dict):
            return {"applied": False, "reason": "invalid_payload"}

        if page == "live_deck":
            if action == "set_luminosity":
                value = payload.get("value")
                if isinstance(value, (int, float)):
                    persisted_value = int(round(max(0.0, min(100.0, float(value)))))
                    self.listener.luminosite = persisted_value / 100.0
                    self._persist_app_config_value("luminosity", persisted_value)
                    return {"applied": True}
                return {"applied": False, "reason": "invalid_value"}

            if action == "set_sensibility":
                value = payload.get("value")
                if isinstance(value, (int, float)):
                    persisted_value = int(round(max(0.0, min(100.0, float(value)))))
                    self.listener.sensi = persisted_value / 100.0
                    self._persist_app_config_value("sensibility", persisted_value)
                    return {"applied": True}
                return {"applied": False, "reason": "invalid_value"}

            if action == "select_transition":
                self.selected_transition_config = self._normalize_transition(payload.get("transition"))
                return {"applied": True}

            if action == "select_configuration":
                configuration_name = payload.get("configuration")
                config = self._find_configuration(configuration_name)
                if config is not None:
                    self.queued_configuration_name = config["name"]
                    return {"applied": True}
                return {"applied": False, "reason": "unknown_configuration"}

            if action == "select_playlist":
                playlist_name = payload.get("playlist")
                if self._set_only_playlist_active(playlist_name):
                    config = self._pick_random_conf_from_playlist(playlist_name)
                    if config is not None:
                        self.queued_configuration_name = config["name"]
                        self._apply_configuration(config, self.selected_transition_config)
                        return {"applied": True, "configuration": config["name"]}
                    return {"applied": True}
                return {"applied": False, "reason": "unknown_playlist"}

            if action == "go_to_next_configuration":
                self.selected_transition_config = self._normalize_transition(payload.get("transition"))
                configuration_name = payload.get("configuration")
                config = self._find_configuration(configuration_name)
                if config is None:
                    config = self.pick_a_random_conf()
                self._apply_configuration(config, self.selected_transition_config)
                return {"applied": True}

            if action == "manual_drop":
                config = self._find_configuration(self.queued_configuration_name) if self.queued_configuration_name else None
                if config is None:
                    config = self.pick_a_random_conf()
                self._apply_configuration(config, self.selected_transition_config)
                return {"applied": True}

            if action == "lock_current_configuration":
                locked = payload.get("locked")
                self.transition_locked = bool(locked)
                return {"applied": True}

        if page == "topology":
            if action == "select_playlist_slot":
                if self._set_only_playlist_active(payload.get("playlist")):
                    return {"applied": True}
                return {"applied": False, "reason": "unknown_playlist"}

            if action == "select_configuration":
                if self._set_only_playlist_active(payload.get("playlist")):
                    self.shuffle_bag = []
                config = self._find_configuration(payload.get("configuration"), payload.get("playlist"))
                if config is not None:
                    self._apply_configuration(config, self.selected_transition_config)
                    return {"applied": True}
                return {"applied": False, "reason": "unknown_configuration"}

            if action == "select_segment_mode":
                segment_name = self._segment_name_from_id(payload.get("segmentId"))
                mode_name = payload.get("mode")
                if segment_name is None or not isinstance(mode_name, str):
                    return {"applied": False, "reason": "invalid_segment_or_mode"}
                segment = self._find_segment_by_name(segment_name)
                if segment is None:
                    return {"applied": False, "reason": "unknown_segment"}
                segment.execute_mode_swap(mode_name)
                return {"applied": True}

            if action == "toggle_segment_direction":
                segment_name = self._segment_name_from_id(payload.get("segmentId"))
                direction = payload.get("direction")
                if segment_name is None or direction not in ("UP", "DOWN"):
                    return {"applied": False, "reason": "invalid_segment_or_direction"}
                segment = self._find_segment_by_name(segment_name)
                if segment is None:
                    return {"applied": False, "reason": "unknown_segment"}
                segment.change_way(direction)
                return {"applied": True}

            if action in {"build_configuration", "modify_configuration"}:
                self.load_configurations()
                return {"applied": True}

            if action in {"set_editor_mode", "select_segment"}:
                return {"applied": True}

        if page == "mode_settings":
            if action == "set_mode_setting":
                mode_name = payload.get("mode")
                setting_key = payload.get("key")
                if not isinstance(mode_name, str) or not isinstance(setting_key, str):
                    return {"applied": False, "reason": "invalid_mode_setting"}

                descriptor = self._get_mode_setting_descriptor(mode_name, setting_key)
                if descriptor is None:
                    return {"applied": False, "reason": "unknown_mode_setting"}

                normalized_value, ok = self._normalize_mode_setting_value(descriptor, payload.get("value"))
                if not ok:
                    return {"applied": False, "reason": "invalid_setting_value"}

                current_mode_settings = self._copy_mode_settings_map(self.activ_configuration.get("modeSettings", {}))
                current_mode_settings.setdefault(mode_name, {})
                current_mode_settings[mode_name][setting_key] = normalized_value
                self.activ_configuration["modeSettings"] = current_mode_settings

                self._apply_active_mode_settings()
                persisted = self._persist_active_configuration_mode_settings()

                return {
                    "applied": True,
                    "mode": mode_name,
                    "key": setting_key,
                    "value": normalized_value,
                    "persisted": persisted,
                }

            return {"applied": False, "reason": "unsupported_mode_settings_action"}

        if page == "system":
            if action == "restart_python_loop":
                if self.pending_system_action is not None:
                    return {"applied": False, "reason": "system_action_already_pending"}

                capability = self.system_status.get_restart_python_capability()
                if not capability.get("available", False):
                    message = capability.get("reason") or "Python restart is unavailable."
                    self._set_system_action_feedback(action, "error", message)
                    return {"applied": False, "reason": "restart_python_unavailable", "message": message}

                self.pending_system_action = action
                self._set_system_action_feedback(
                    action,
                    "pending",
                    "Restarting the Python process...",
                )
                asyncio.create_task(self._restart_python_process_task())
                return {"applied": True, "status": "pending"}

            if action == "restart_raspberry_pi":
                if self.pending_system_action is not None:
                    return {"applied": False, "reason": "system_action_already_pending"}

                capability = self.system_status.get_reboot_raspberry_capability()
                if not capability.get("available", False):
                    message = capability.get("reason") or "Raspberry reboot is unavailable."
                    self._set_system_action_feedback(action, "error", message)
                    return {"applied": False, "reason": "restart_raspberry_unavailable", "message": message}

                self.pending_system_action = action
                self._set_system_action_feedback(
                    action,
                    "pending",
                    "Reboot command queued. The app should return automatically after boot.",
                )
                asyncio.create_task(self._reboot_raspberry_task())
                return {"applied": True, "status": "pending"}

            return {"applied": False, "reason": "unsupported_system_action"}

        return {"applied": False, "reason": "unsupported_instruction"}

    def pick_a_random_conf(self) -> Dict[str, Any]:
        """
        Select a random configuration from the unblocked playlists using a shuffle bag approach.

        Returns:
            dict: The selected configuration dictionary.
        """
        # If our shuffle bag is empty, we must refill it with all available configurations
        if len(self.shuffle_bag) == 0:
            for playlist_index in range(len(self.playlists)):
                if not self.blocked_playlists[playlist_index]:
                    playlist_name = self.playlists[playlist_index]
                    # Add every configuration from this playlist into the bag
                    for conf_index in range(len(self.configurations[playlist_name])):
                        self.shuffle_bag.append({
                            "playlist": playlist_name,
                            "index": conf_index,
                            "name": self.configurations[playlist_name][conf_index]["name"],
                            "modes": self.configurations[playlist_name][conf_index]["modes"],
                            "way": self.configurations[playlist_name][conf_index]["way"],
                            "modeSettings": self.configurations[playlist_name][conf_index].get("modeSettings", {}),
                        })
            # Shuffle the bag like a deck of cards
            random.shuffle(self.shuffle_bag)

        # Fallback just in case all playlists are somehow blocked preventing refill
        if len(self.shuffle_bag) == 0:
            return self.activ_configuration

        # Pop the next configuration from the shuffle bag
        new_conf = self.shuffle_bag.pop()

        self.logger.debug(f"(MM)   pick_a_random_conf() :     conf = {new_conf}")
        return new_conf

            