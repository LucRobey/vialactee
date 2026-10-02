"""
core/PresetRepository.py - Application Configuration & Debounced Atomic Storage.

Manages persistent storage for app_config.json with non-blocking debounced atomic I/O.
Offloads disk operations via asyncio's run_in_executor to protect the 30 FPS render loop.

Guarantees:
- AXIOM-01: Execution time <= 0.01 ms per frame in steady-state.
- AXIOM-02: Zero dynamic heap allocations in hot-path.
- AXIOM-07: Code length <= 500 lines.
"""

import asyncio
import json
import logging
import os
import random
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PresetRepository:
    """
    Manages persistent storage for app_config.json.
    Non-blocking atomic disk persistence with debounce protection.
    """

    def __init__(self, infos: Dict[str, Any]) -> None:
        self.infos = infos

        # Debounced persistence state for app_config
        self._app_config_flush_task: Optional[asyncio.Task] = None
        self._pending_app_config_snapshot: Optional[str] = None
        self._pending_app_config_file_path: Optional[str] = None
        self._pending_app_config_updates: Dict[str, Any] = {}
        self._app_config_cache: Optional[Dict[str, Any]] = None
        self._app_config_cached_path: Optional[str] = None

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
        if self._app_config_flush_task is not None and not self._app_config_flush_task.done():
            self._app_config_flush_task.cancel()

        if self._pending_app_config_snapshot is not None and self._pending_app_config_file_path is not None:
            self._atomic_write(self._pending_app_config_file_path, self._pending_app_config_snapshot)
            self._pending_app_config_snapshot = None
            self._pending_app_config_updates.clear()
