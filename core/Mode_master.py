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
import music.api as Listener
import core.TransitionBridge as TransitionBridge
from config.room_bounds import compute_room_bounds
from transitions.api import create_transition_service
from mood.api import create_mood_service
from modes.Mode import Mode
from config.Configuration_manager import resolve_segments_file_path
from config.coherence_loader import load_coherence_config
import utils.Profiler as Profiler
from core.CommandRouter import router as command_router
from core.AppConfigStore import AppConfigStore


class Mode_master:
    """
    Master controller for all visual segments and modes.

    Manages the global state, dynamic mode DNA allocation, and transitions
    across the entire installation.
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
        self._is_rpi_hardware: bool = len(self.leds_list) > 0 and "Rpi_NeoPixels" in type(self.leds_list[0]).__name__
        self._state_dirty: bool = True
        self.logger = logging.getLogger("Mode_master")
        self.profiler = Profiler.Profiler(infos.get("printCpuFpsInfo", False), self.logger, config=infos.get("profiler", {}))
        self.current_time = time.time()
        self.appli_connector = None
        self.segments_list: List[Segment.Segment] = []
        self.segments_names_to_index: Dict[str, int] = {}
        self.mode_settings: Dict[str, Dict[str, Any]] = {}
        self.mode_settings_catalog: Dict[str, Dict[str, Any]] = {}
        self.pending_system_action: Optional[str] = None
        self._restart_requested = asyncio.Event()
        self._last_update_monotonic: Optional[float] = None

        # Delegate app config persistence to AppConfigStore
        self._app_config_store = AppConfigStore(infos)

        self._room_bounds = compute_room_bounds(infos)

        self.initiate_segments()
        self.mode_settings_catalog = self._build_mode_settings_catalog()
        self.transitions = create_transition_service(self.infos)
        if len(self.leds_list) > 0 and hasattr(self.leds_list[0], "set_transition_controller"):
            self.leds_list[0].set_transition_controller(self.transitions)
        self.mood = create_mood_service(auto_scene=True)  # auto_scene is a code default (off) in mood.api
        Mode.bind_mood_colors(self.mood.colors())
        Mode.bind_mood_modifiers(self.mood.modifiers())
        self.initiate_modes()
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
            normalized_value, ok = Mode.normalize_setting_value(descriptor, descriptor.get("default"))
            if ok:
                defaults[key] = normalized_value
        return defaults

    def _get_mode_setting_descriptor(self, mode_name: str, setting_key: str) -> Optional[Dict[str, Any]]:
        entry = self.mode_settings_catalog.get(mode_name, {})
        for descriptor in entry.get("settings", []):
            if descriptor.get("key") == setting_key:
                return descriptor
        return None

    def _get_effective_mode_settings(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        override_map = overrides if isinstance(overrides, dict) else self.mode_settings
        effective: Dict[str, Dict[str, Any]] = {
            mode_name: self._mode_settings_defaults_for_mode(mode_name)
            for mode_name in self.mode_settings_catalog
        }

        # Apply persisted overrides from infos["mode_settings"] and active runtime overrides
        persisted = self.infos.get("mode_settings")
        if isinstance(persisted, dict):
            for mode_name, settings in persisted.items():
                if mode_name in effective and isinstance(settings, dict):
                    effective[mode_name].update(settings)

        if isinstance(override_map, dict):
            for mode_name, settings in override_map.items():
                if mode_name not in self.mode_settings_catalog or not isinstance(settings, dict):
                    continue
                merged = dict(effective.get(mode_name, {}))
                for descriptor in self.mode_settings_catalog[mode_name].get("settings", []):
                    key = descriptor.get("key")
                    if not isinstance(key, str) or key not in settings:
                        continue
                    normalized_value, ok = Mode.normalize_setting_value(descriptor, settings.get(key))
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

    def _persist_mode_settings(self) -> bool:
        mode_settings = self._copy_mode_settings_map(self.mode_settings)
        self._persist_app_config_value("mode_settings", mode_settings)
        return True

    def get_state_snapshot(self) -> Dict[str, Any]:
        """
        Build a JSON-serializable snapshot for the web interface.
        """
        segments = []
        for segment in self.segments_list:
            segments.append({
                "id": getattr(segment, "id", "") or segment.name.replace("Segment ", "", 1),
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

        transition_status = self.transitions.get_status()
        return {
            "hardwareProfile": self.hardware_profile,
            "selectedTransition": "DYNAMIC",
            "transitionLocked": transition_status.is_locked,
            "transitionState": transition_status.state,
            "transitionProgress": transition_status.progress,
            "luminosity": int(round(max(0.0, min(1.0, float(getattr(self.listener, "luminosite", 0.0)))) * 100)),
            "sensibility": int(round(max(0.0, float(getattr(self.listener, "sensi", 0.0))) * 100)),
            "autoTransitionTime": int(round(transition_status.auto_interval)),
            "availableModes": available_modes,
            "activeMood": self.mood.get_status().palette,
            "availableMoods": list(self.mood.get_status().available_palettes),
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
        segments, and drives global transitions through the transition service.
        """
        frame_start = time.monotonic()
        frame_dt = None if self._last_update_monotonic is None else frame_start - self._last_update_monotonic
        self._last_update_monotonic = frame_start
        self.system_status.note_loop_tick(frame_dt)

        with self.profiler.measure("listener"):
            if not getattr(self.listener, "is_externally_clocked", False):
                self.listener.update()

        with self.profiler.measure("hardware_show"):
            if self.infos.get("onRaspberry", False) or self.infos.get("HARDWARE_MODE") == "rpi" or self._is_rpi_hardware:
                loop = asyncio.get_running_loop()
                for led_strip in self.leds_list:
                    await loop.run_in_executor(None, led_strip.show)
            else:
                for led_strip in self.leds_list:
                    led_strip.show()

        slowest_seg = None
        slowest_seg_time = 0.0
        slowest_mode_name = None

        transition_status = self.transitions.get_status()
        blend = self.transitions.blend
        dt = frame_dt or 0.033
        with self.profiler.measure("modes_render"):
            if getattr(self.profiler, "track_slowest_mode", False) and getattr(self.profiler, "active", False):
                for seg in self.segments_list:
                    t0 = time.perf_counter()
                    seg.update(transition_status, blend, dt=dt)
                    t_seg = time.perf_counter() - t0
                    if t_seg > slowest_seg_time:
                        slowest_seg_time = t_seg
                        slowest_seg = seg.name
                        slowest_mode_name = getattr(seg, "activ_mode", "unknown")
            else:
                for seg in self.segments_list:
                    seg.update(transition_status, blend, dt=dt)

        if slowest_seg is not None:
            self.profiler.record_slowest_mode(slowest_seg, slowest_mode_name, slowest_seg_time)

        self.current_time = time.time()
        with self.profiler.measure("transitions"):
            music = TransitionBridge.build_music_snapshot(self.listener)
            self.mood.update(dt, music.scene)
            orders = self.transitions.update(dt, music)
            if orders is not None:
                self.transitions.acknowledge(TransitionBridge.apply_orders(self, orders))
        with self.profiler.measure("connector"):
            if self.appli_connector is not None:
                await self.appli_connector.on_frame_tick(self)
        self.profiler.tick()

    def initiate_modes(self) -> None:
        """
        Coherent startup: configure coherence policy, push installation, allocate
        initial modes via TransitionService.allocate_initial, and apply them without animation.
        """
        try:
            self.transitions.configure(load_coherence_config(self.infos))
            self._push_installation()
        except Exception as exc:
            self.logger.warning("(MM) Could not load coherence policy, using default: %s", exc)
            self.transitions.configure(None)  # type: ignore[arg-type]
            self._push_installation()

        music = TransitionBridge.build_music_snapshot(self.listener)
        initial_alloc = self.transitions.allocate_initial(music) if hasattr(self.transitions, "allocate_initial") else {}

        for segment in self.segments_list:
            avail = list(segment.modes.keys())
            mode_name = (
                initial_alloc.get(segment.name)
                or initial_alloc.get(getattr(segment, "id", ""))
                or (random.choice(avail) if avail else "Rainbow")
            )
            direction = random.choice(["UP", "DOWN"])
            segment.change_mode(mode_name)
            segment.change_way(direction)

        self.mode_settings = self._get_effective_mode_settings({})
        self._apply_active_mode_settings()
        self._state_dirty = True

    def initiate_segments(self) -> None:
        """
        Initialize all segments based on the active segments configuration file.
        """
        def add_segments(info_list: List[Dict[str, Any]], leds: Any) -> None:
            offset = 0
            for segment_index in range(len(info_list)):
                seg_infos = info_list[segment_index]
                indexes = [i for i in range(offset, offset + seg_infos["size"])]
                new_segment = Segment.Segment(
                    seg_infos["name"],
                    self.listener,
                    leds,
                    indexes,
                    seg_infos["orientation"],
                    self.infos,
                    seg_id=seg_infos.get("id", ""),
                    tags=tuple(seg_infos.get("tags", ())),
                )
                offset += seg_infos["size"]
                self.segments_list.append(new_segment)
                self.segments_names_to_index[seg_infos["name"]] = seg_infos["order"]
        file_path = resolve_segments_file_path(self.infos)
        with open(file_path, "r", encoding='utf-8') as f:
            data = json.load(f)
        for i, leds in enumerate(self.leds_list):
            key = f"segs_{i+1}"
            if key in data:
                add_segments(data[key], leds)

    def _push_installation(self) -> None:
        """Describe the current segments to the transition sector."""
        self.transitions.set_installation(
            TransitionBridge.build_installation_snapshot(self.segments_list, self._room_bounds)
        )

    def _segment_name_from_id(self, segment_id: Any) -> Optional[str]:
        if not isinstance(segment_id, str) or len(segment_id.strip()) == 0:
            return None
        return f"Segment {segment_id.strip()}"

    def _find_segment_by_name(self, segment_name: str) -> Optional[Segment.Segment]:
        for segment in self.segments_list:
            if segment.name == segment_name or getattr(segment, "id", "") == segment_name:
                return segment
        return None

    def _persist_app_config_value(self, key: str, value: Any) -> None:
        self.infos[key] = value
        self._app_config_store.persist_app_config_debounced(key, value)
        self._state_dirty = True

    def flush_sync(self) -> None:
        """Flushes any pending snapshots in AppConfigStore synchronously."""
        self._app_config_store.flush_sync()

    async def process_instruction(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a WebSocket instruction by delegating to the CommandRouter.
        """
        result = await command_router.dispatch(self, instruction)
        if result.get("applied", False):
            self._state_dirty = True
        return result