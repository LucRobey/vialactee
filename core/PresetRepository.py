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
    # PERSISTENCE — Non-blocking file I/O
    # ============================================================

    def _persist_configurations_store_sync(self) -> bool:
        """Synchronous write — called via run_in_executor."""
        file_path = resolve_configurations_file_path(self.infos)
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
            logger.error(f"(PR) Failed to persist configurations.json: {e}")
            return False

    async def persist_configurations_store(self) -> bool:
        """Non-blocking configuration persistence."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._persist_configurations_store_sync)

    def _persist_app_config_value_sync(self, key: str, value: Any) -> None:
        """Synchronous write — called via run_in_executor."""
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
            logger.error(f"(PR) Failed to persist {key} in app_config.json: {e}")

    async def persist_app_config_value(self, key: str, value: Any) -> None:
        """Non-blocking app config persistence."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._persist_app_config_value_sync, key, value)
