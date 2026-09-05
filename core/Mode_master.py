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
import utils.Profiler as Profiler
from core.CommandRouter import router as command_router
from core.PresetRepository import PresetRepository
from config.Configuration_manager import resolve_configurations_file_path, resolve_segments_file_path



from contextlib import contextmanager




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
        self.hardware_profile = infos.get("hardware_profile", "full")
        self.listener = listener
        self.onRaspberry = infos.get("onRaspberry", False)
        self.leds_list = leds
        self.logger = logging.getLogger("Mode_master")
        self.profiler = Profiler.Profiler(infos.get("printCpuFpsInfo", False), self.logger, config=infos.get("profiler", {}))
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

        # Delegate configuration persistence to PresetRepository
        self._preset_repo = PresetRepository(infos)
        self.load_configurations()

        self.initiate_segments()
        self.mode_settings_catalog = self._build_mode_settings_catalog()
        self.initiate_configuration()
        self.transition_director = Transition_Director.Transition_Director(self, self.listener, self.infos)
        self.system_status = System_status.SystemStatus(self.infos, self.listener, self.leds_list, getattr(self, "profiler", None))

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
        self._preset_repo.configurations = self.configurations
        self._preset_repo.playlists = self.playlists
        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, self._preset_repo._persist_configurations_store_sync)
            return True
        except RuntimeError:
            return self._preset_repo._persist_configurations_store_sync()

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
            "hardwareProfile": self.hardware_profile,
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
            "autoTransitionTime": int(round(float(getattr(self.transition_director, "configuration_duration", 20.0)))),
            "playlists": list(self.playlists),
            "availableModes": available_modes,
            "segments": segments,
            "modeSettingsCatalog": list(self.mode_settings_catalog.values()),
            "modeSettings": self._get_effective_mode_settings(),
            "system": self.system_status.get_snapshot(self._websocket_count()),
        }

    async def update_forever(self) -> None:
        """
        Continuously update the system paced to the target FPS.
        """
        target_fps = getattr(self.profiler, "target_fps", 30.0) if hasattr(self, "profiler") else 30.0
        target_dt = 1.0 / target_fps if target_fps > 0 else 1.0 / 30.0

        while True:
            t0 = time.perf_counter()
            await self.update()
            elapsed = time.perf_counter() - t0
            sleep_time = max(0.001, target_dt - elapsed)

            with self.profiler.measure("idle_sleep"):
                await asyncio.sleep(sleep_time)

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

        with self.profiler.measure("listener"):
            self.listener.update()

        is_rpi_hardware = len(self.leds_list) > 0 and "Rpi_NeoPixels" in str(type(self.leds_list[0]))
        
        with self.profiler.measure("hardware_show"):
            if self.infos.get("onRaspberry", False) or self.infos.get("HARDWARE_MODE") == "rpi" or is_rpi_hardware:
                loop = asyncio.get_running_loop()
                for led_strip in self.leds_list:
                    await loop.run_in_executor(None, led_strip.show)
            else:
                for led_strip in self.leds_list:
                    led_strip.show()

        slowest_seg = None
        slowest_seg_time = 0.0
        slowest_mode_name = None

        with self.profiler.measure("modes_render"):
            if getattr(self.profiler, "track_slowest_mode", False) and getattr(self.profiler, "active", False):
                for seg in self.segments_list:
                    t0 = time.perf_counter()
                    seg.update(self.transition_director)
                    t_seg = time.perf_counter() - t0
                    if t_seg > slowest_seg_time:
                        slowest_seg_time = t_seg
                        slowest_seg = seg.name
                        slowest_mode_name = getattr(seg, "activ_mode", "unknown")
            else:
                for seg in self.segments_list:
                    seg.update(self.transition_director)

        if slowest_seg is not None:
            self.profiler.record_slowest_mode(slowest_seg, slowest_mode_name, slowest_seg_time)

        #==============================================
        self.current_time = time.time()
        
        with self.profiler.measure("transitions"):
            await self.transition_director.update(self.current_time)

        with self.profiler.measure("connector"):
            if self.appli_connector is not None:
                await self.appli_connector.broadcast_state_if_changed(self.get_state_snapshot())
                
        self.profiler.tick()


    def load_configurations(self) -> None:
        """
        Load modes and playlists from the configurations.json file.
        Delegates to PresetRepository for actual file I/O.
        """
        self._preset_repo.load_configurations()
        self.configurations = self._preset_repo.configurations
        self.playlists = self._preset_repo.playlists
        self.blocked_playlists = self._preset_repo.blocked_playlists
        self.shuffle_bag = self._preset_repo.shuffle_bag
        self.logger.debug(f"(MM) Loaded {len(self.playlists)} playlists")
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
        Initialize all segments based on the active segments configuration file.
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
                
        file_path = resolve_segments_file_path(self.infos)
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
        self._preset_repo.playlists = self.playlists
        success = self._preset_repo.set_only_playlist_active(playlist_name)
        if success:
            self.blocked_playlists = self._preset_repo.blocked_playlists
            self.shuffle_bag = self._preset_repo.shuffle_bag
        return success

    def _pick_random_conf_from_playlist(self, playlist_name: Any) -> Optional[Dict[str, Any]]:
        self._preset_repo.configurations = self.configurations
        self._preset_repo.playlists = self.playlists
        return self._preset_repo.pick_random_conf_from_playlist(playlist_name)

    def _find_configuration(self, configuration_name: Any, playlist_name: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        self._preset_repo.configurations = self.configurations
        self._preset_repo.playlists = self.playlists
        return self._preset_repo.find_configuration(configuration_name, playlist_name)

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
        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, self._preset_repo._persist_app_config_value_sync, key, value)
        except RuntimeError:
            self._preset_repo._persist_app_config_value_sync(key, value)

    async def process_instruction(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a WebSocket instruction by delegating to the CommandRouter.

        All handler logic has been extracted into core/CommandRouter.py as
        individually registered async handlers.
        """
        return await command_router.dispatch(self, instruction)

    def pick_a_random_conf(self) -> Dict[str, Any]:
        """
        Select a random configuration from the unblocked playlists using a shuffle bag approach.
        Delegates to PresetRepository.

        Returns:
            dict: The selected configuration dictionary.
        """
        self._preset_repo.configurations = self.configurations
        self._preset_repo.playlists = self.playlists
        self._preset_repo.blocked_playlists = self.blocked_playlists
        self._preset_repo.shuffle_bag = self.shuffle_bag
        new_conf = self._preset_repo.pick_a_random_conf(self.activ_configuration)
        self.shuffle_bag = self._preset_repo.shuffle_bag
        self.logger.debug(f"(MM)   pick_a_random_conf() :     conf = {new_conf}")
        return new_conf

            