"""
PresetRepository: Encapsulates configuration persistence, shuffle bag logic,
and playlist selection — extracted from Mode_master.

All file I/O is offloaded to asyncio's run_in_executor to prevent blocking
the 30 FPS render loop when the user drags UI sliders.
"""
import asyncio
import json
import logging
import os
import random
import time
from typing import Dict, Any, List, Optional

from config.Configuration_manager import resolve_configurations_file_path

logger = logging.getLogger(__name__)


class PresetRepository:
    """
    Manages configuration presets, playlists, and persistent storage.

    Responsibilities:
        - Loading/saving configurations.json and app_config.json
        - Shuffle bag random configuration selection
        - Playlist activation/deactivation
        - Non-blocking file I/O via run_in_executor
    """

    def __init__(self, infos: Dict[str, Any]) -> None:
        self.infos = infos
        self.configurations: Dict[str, List[Dict[str, Any]]] = {}
        self.playlists: List[str] = []
        self.blocked_playlists: List[bool] = []
        self.shuffle_bag: List[Dict[str, Any]] = []

        # Debounced persistence state for configurations
        self._flush_task: Optional[asyncio.Task] = None
        self._pending_snapshot: Optional[str] = None
        self._pending_file_path: Optional[str] = None

        # Debounced persistence state for app_config
        self._app_config_flush_task: Optional[asyncio.Task] = None
        self._pending_app_config_snapshot: Optional[str] = None
        self._pending_app_config_file_path: Optional[str] = None
        self._pending_app_config_updates: Dict[str, Any] = {}
        self._app_config_cache: Optional[Dict[str, Any]] = None
        self._app_config_cached_path: Optional[str] = None

    def load_configurations(self) -> None:
        """Load modes and playlists from the configurations.json file."""
        file_path = resolve_configurations_file_path(self.infos)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.configurations = data.get('configurations', {})
            self.playlists = list(self.configurations.keys())
            logger.debug(f"(PR) Loaded {len(self.playlists)} playlists from {file_path}")
        except Exception as e:
            logger.error(f"(PR) Error reading JSON configuration file: {e}")
            self.configurations = {}
            self.playlists = []

        self.blocked_playlists = [False for _ in self.playlists]
        self.shuffle_bag = []

    def pick_a_random_conf(self, activ_configuration: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Select a random configuration from the unblocked playlists using a shuffle bag approach.

        Returns:
            dict: The selected configuration dictionary.
        """
        if len(self.shuffle_bag) == 0:
            for playlist_index in range(len(self.playlists)):
                if not self.blocked_playlists[playlist_index]:
                    playlist_name = self.playlists[playlist_index]
                    for conf_index in range(len(self.configurations[playlist_name])):
                        self.shuffle_bag.append({
                            "playlist": playlist_name,
                            "index": conf_index,
                            "name": self.configurations[playlist_name][conf_index]["name"],
                            "modes": self.configurations[playlist_name][conf_index]["modes"],
                            "way": self.configurations[playlist_name][conf_index]["way"],
                            "modeSettings": self.configurations[playlist_name][conf_index].get("modeSettings", {}),
                        })
            random.shuffle(self.shuffle_bag)

        if len(self.shuffle_bag) == 0:
            return activ_configuration if activ_configuration is not None else {}

        new_conf = self.shuffle_bag.pop()
        logger.debug(f"(PR) pick_a_random_conf(): conf = {new_conf}")
        return new_conf

    def set_only_playlist_active(self, playlist_name: Any) -> bool:
        """Activate only the given playlist, blocking all others."""
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

    def pick_random_conf_from_playlist(self, playlist_name: Any) -> Optional[Dict[str, Any]]:
        """Pick a random configuration from a specific playlist."""
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

    def find_configuration(self, configuration_name: Any, playlist_name: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """Find a specific configuration by name, optionally within a specific playlist."""
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

    # ============================================================
    # PERSISTENCE — Non-blocking & Debounced Atomic File I/O
    # ============================================================

    def _atomic_write(self, file_path: str, content: str) -> bool:
        """Atomic write using unique temporary file replacement to prevent corrupted files and lock conflicts."""
        abs_path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        unique_id = f"{os.getpid()}_{time.time_ns()}_{random.randint(1000, 9999)}"
        tmp_path = f"{abs_path}.{unique_id}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
            for attempt in range(5):
                try:
                    os.replace(tmp_path, abs_path)
                    return True
                except PermissionError:
                    if attempt < 4:
                        time.sleep(0.01 * (attempt + 1))
                    else:
                        raise
            return False
        except Exception as e:
            logger.error(f"(PR) Atomic write failed for {file_path}: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return False

    def _resolve_app_config_path(self) -> str:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "app_config.json"))

    def _get_app_config_cache(self) -> Dict[str, Any]:
        """In-memory cache for app_config to prevent synchronous disk I/O during rapid slider adjustments."""
        file_path = self._resolve_app_config_path()
        if self._app_config_cache is None or self._app_config_cached_path != file_path:
            self._app_config_cached_path = file_path
            data = {}
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            data = loaded
                except Exception as e:
                    logger.warning(f"(PR) Failed reading app_config.json for cache: {e}")
            self._app_config_cache = data
        return self._app_config_cache

    def persist_configurations_debounced(self, delay_seconds: float = 0.5) -> None:
        """
        Immediately serializes the configuration dictionary to an immutable JSON string,
        then debounces the background disk write. Superseded tasks cancel cleanly.
        """
        file_path = resolve_configurations_file_path(self.infos)
        payload = {
            "playlists": list(self.playlists),
            "configurations": self.configurations,
        }
        # Serialize immediately to eliminate concurrent dictionary mutation races
        snapshot = json.dumps(payload, indent=2) + "\n"
        self._pending_snapshot = snapshot
        self._pending_file_path = file_path

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._atomic_write(file_path, snapshot)
            self._pending_snapshot = None
            return

        if self._flush_task is not None and not self._flush_task.done():
            self._flush_task.cancel()

        async def _flush():
            try:
                await asyncio.sleep(delay_seconds)
                content = self._pending_snapshot
                if content is not None:
                    await loop.run_in_executor(None, self._atomic_write, file_path, content)
                    if self._pending_snapshot == content:
                        self._pending_snapshot = None
            except asyncio.CancelledError:
                # Intentionally pass: a newer slider event superseded this task
                pass

        self._flush_task = loop.create_task(_flush())

    def _persist_configurations_store_sync(self) -> bool:
        """Synchronous atomic write for configurations."""
        file_path = resolve_configurations_file_path(self.infos)
        payload = {
            "playlists": list(self.playlists),
            "configurations": self.configurations,
        }
        snapshot = json.dumps(payload, indent=2) + "\n"
        success = self._atomic_write(file_path, snapshot)
        if success:
            self._pending_snapshot = None
        return success

    async def persist_configurations_store(self) -> bool:
        """Non-blocking configuration persistence (delegates to debounced atomic write)."""
        self.persist_configurations_debounced()
        return True

    def persist_app_config_debounced(self, key: str, value: Any, delay_seconds: float = 0.5) -> None:
        """
        Applies key/value updates to app_config.json, immediately serializes an immutable
        snapshot, and debounces the background atomic disk write without blocking the event loop.
        """
        file_path = self._resolve_app_config_path()
        data = self._get_app_config_cache()
        data[key] = value
        self._pending_app_config_updates[key] = value

        snapshot = json.dumps(data, indent=4) + "\n"
        self._pending_app_config_snapshot = snapshot
        self._pending_app_config_file_path = file_path

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._atomic_write(file_path, snapshot)
            self._pending_app_config_snapshot = None
            self._pending_app_config_updates.clear()
            return

        if self._app_config_flush_task is not None and not self._app_config_flush_task.done():
            self._app_config_flush_task.cancel()

        async def _flush_app_config():
            try:
                await asyncio.sleep(delay_seconds)
                content = self._pending_app_config_snapshot
                if content is not None:
                    await loop.run_in_executor(None, self._atomic_write, file_path, content)
                    if self._pending_app_config_snapshot == content:
                        self._pending_app_config_snapshot = None
                        self._pending_app_config_updates.clear()
            except asyncio.CancelledError:
                pass

        self._app_config_flush_task = loop.create_task(_flush_app_config())

    def _persist_app_config_value_sync(self, key: str, value: Any) -> None:
        """Synchronous atomic write for app_config.json."""
        file_path = self._resolve_app_config_path()
        data = self._get_app_config_cache()
        data[key] = value
        self._pending_app_config_updates[key] = value
        snapshot = json.dumps(data, indent=4) + "\n"
        success = self._atomic_write(file_path, snapshot)
        if success:
            self._pending_app_config_snapshot = None
            self._pending_app_config_updates.clear()

    async def persist_app_config_value(self, key: str, value: Any) -> None:
        """Non-blocking app config persistence (delegates to debounced atomic write)."""
        self.persist_app_config_debounced(key, value)

    def flush_sync(self) -> None:
        """Flushes any pending snapshots synchronously and cancels background tasks."""
        if self._flush_task is not None and not self._flush_task.done():
            self._flush_task.cancel()
        if self._app_config_flush_task is not None and not self._app_config_flush_task.done():
            self._app_config_flush_task.cancel()

        if self._pending_snapshot is not None and self._pending_file_path is not None:
            self._atomic_write(self._pending_file_path, self._pending_snapshot)
            self._pending_snapshot = None
        if self._pending_app_config_snapshot is not None and self._pending_app_config_file_path is not None:
            self._atomic_write(self._pending_app_config_file_path, self._pending_app_config_snapshot)
            self._pending_app_config_snapshot = None
            self._pending_app_config_updates.clear()
