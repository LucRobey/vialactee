"""
CommandRouter: Decorator-based instruction routing extracted from Mode_master.

Replaces the 199-line if/else cascade in Mode_master.process_instruction with
a clean registration API. Each handler is a standalone async function registered
by (page, action) pair.
"""
import logging
from typing import Dict, Any, Callable, Awaitable, Optional, Tuple

logger = logging.getLogger(__name__)

# Type alias for handler functions
InstructionHandler = Callable[..., Awaitable[Dict[str, Any]]]


class CommandRouter:
    """
    Routes WebSocket instructions to registered handler functions.

    Usage:
        router = CommandRouter()

        @router.register("live_deck", "set_luminosity")
        async def handle_set_luminosity(mode_master, payload):
            ...
            return {"applied": True}

        result = await router.dispatch(mode_master, instruction)
    """

    def __init__(self) -> None:
        self._handlers: Dict[Tuple[str, str], InstructionHandler] = {}

    def register(self, page: str, action: str) -> Callable:
        """Decorator to register a handler for a (page, action) pair."""
        def decorator(func: InstructionHandler) -> InstructionHandler:
            key = (page, action)
            if key in self._handlers:
                logger.warning(f"(CR) Overwriting handler for {page}/{action}")
            self._handlers[key] = func
            return func
        return decorator

    async def dispatch(self, mode_master: Any, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch an instruction to the appropriate registered handler.

        Args:
            mode_master: The Mode_master instance (passed as context to handlers).
            instruction: The instruction dict with 'page', 'action', 'payload' keys.

        Returns:
            A result dict with at minimum {"applied": True/False}.
        """
        page = instruction.get("page")
        action = instruction.get("action")
        payload = instruction.get("payload", {})

        if not isinstance(payload, dict):
            return {"applied": False, "reason": "invalid_payload"}

        handler = self._handlers.get((page, action))
        if handler is None:
            return {"applied": False, "reason": "unsupported_instruction"}

        try:
            return await handler(mode_master, payload)
        except Exception as e:
            logger.error(f"(CR) Handler error for {page}/{action}: {e}")
            return {"applied": False, "reason": "handler_error", "message": str(e)}


# ============================================================
# GLOBAL ROUTER INSTANCE — handlers registered below
# ============================================================
router = CommandRouter()


# ========================
# PAGE: live_deck
# ========================

@router.register("live_deck", "set_luminosity")
async def _handle_set_luminosity(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    value = payload.get("value")
    if isinstance(value, (int, float)):
        persisted_value = int(round(max(0.0, min(100.0, float(value)))))
        mm.listener.luminosite = persisted_value / 100.0
        mm._persist_app_config_value("luminosity", persisted_value)
        return {"applied": True}
    return {"applied": False, "reason": "invalid_value"}


@router.register("live_deck", "set_sensibility")
async def _handle_set_sensibility(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    value = payload.get("value")
    if isinstance(value, (int, float)):
        persisted_value = int(round(max(0.0, min(100.0, float(value)))))
        mm.listener.sensi = persisted_value / 100.0
        mm._persist_app_config_value("sensibility", persisted_value)
        return {"applied": True}
    return {"applied": False, "reason": "invalid_value"}


@router.register("live_deck", "set_auto_transition_time")
async def _handle_set_auto_transition_time(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    value = payload.get("value")
    if isinstance(value, (int, float)):
        persisted_value = int(round(max(1.0, float(value))))
        mm.transition_director.configuration_duration = float(persisted_value)
        mm._persist_app_config_value("auto_transition_time", persisted_value)
        return {"applied": True}
    return {"applied": False, "reason": "invalid_value"}


@router.register("live_deck", "select_transition")
async def _handle_select_transition(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    mm.selected_transition_config = mm._normalize_transition(payload.get("transition"))
    return {"applied": True}


@router.register("live_deck", "select_configuration")
async def _handle_select_configuration(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    configuration_name = payload.get("configuration")
    config = mm._find_configuration(configuration_name)
    if config is not None:
        mm.queued_configuration_name = config["name"]
        return {"applied": True}
    return {"applied": False, "reason": "unknown_configuration"}


@router.register("live_deck", "select_playlist")
async def _handle_select_playlist(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    playlist_name = payload.get("playlist")
    if mm._set_only_playlist_active(playlist_name):
        config = mm._pick_random_conf_from_playlist(playlist_name)
        if config is not None:
            mm.queued_configuration_name = config["name"]
            mm._apply_configuration(config, mm.selected_transition_config)
            return {"applied": True, "configuration": config["name"]}
        return {"applied": True}
    return {"applied": False, "reason": "unknown_playlist"}


@router.register("live_deck", "go_to_next_configuration")
async def _handle_go_to_next_configuration(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    mm.selected_transition_config = mm._normalize_transition(payload.get("transition"))
    configuration_name = payload.get("configuration")
    config = mm._find_configuration(configuration_name)
    if config is None:
        config = mm.pick_a_random_conf()
    mm._apply_configuration(config, mm.selected_transition_config)
    return {"applied": True}


@router.register("live_deck", "manual_drop")
async def _handle_manual_drop(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    config = mm._find_configuration(mm.queued_configuration_name) if mm.queued_configuration_name else None
    if config is None:
        config = mm.pick_a_random_conf()
    mm._apply_configuration(config, mm.selected_transition_config)
    return {"applied": True}


@router.register("live_deck", "lock_current_configuration")
async def _handle_lock_current_configuration(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    locked = payload.get("locked")
    mm.transition_locked = bool(locked)
    return {"applied": True}


# ========================
# PAGE: topology
# ========================

@router.register("topology", "select_playlist_slot")
async def _handle_topology_select_playlist_slot(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    if mm._set_only_playlist_active(payload.get("playlist")):
        return {"applied": True}
    return {"applied": False, "reason": "unknown_playlist"}


@router.register("topology", "select_configuration")
async def _handle_topology_select_configuration(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    if mm._set_only_playlist_active(payload.get("playlist")):
        mm.shuffle_bag = []
    config = mm._find_configuration(payload.get("configuration"), payload.get("playlist"))
    if config is not None:
        mm._apply_configuration(config, mm.selected_transition_config)
        return {"applied": True}
    return {"applied": False, "reason": "unknown_configuration"}


@router.register("topology", "select_segment_mode")
async def _handle_topology_select_segment_mode(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    segment_name = mm._segment_name_from_id(payload.get("segmentId"))
    mode_name = payload.get("mode")
    if segment_name is None or not isinstance(mode_name, str):
        return {"applied": False, "reason": "invalid_segment_or_mode"}
    segment = mm._find_segment_by_name(segment_name)
    if segment is None:
        return {"applied": False, "reason": "unknown_segment"}
    segment.execute_mode_swap(mode_name)
    return {"applied": True}


@router.register("topology", "toggle_segment_direction")
async def _handle_topology_toggle_segment_direction(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    segment_name = mm._segment_name_from_id(payload.get("segmentId"))
    direction = payload.get("direction")
    if segment_name is None or direction not in ("UP", "DOWN"):
        return {"applied": False, "reason": "invalid_segment_or_direction"}
    segment = mm._find_segment_by_name(segment_name)
    if segment is None:
        return {"applied": False, "reason": "unknown_segment"}
    segment.change_way(direction)
    return {"applied": True}


@router.register("topology", "build_configuration")
async def _handle_topology_build_configuration(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    mm.load_configurations()
    return {"applied": True}


@router.register("topology", "modify_configuration")
async def _handle_topology_modify_configuration(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    mm.load_configurations()
    return {"applied": True}


@router.register("topology", "set_editor_mode")
async def _handle_topology_set_editor_mode(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"applied": True}


@router.register("topology", "select_segment")
async def _handle_topology_select_segment(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"applied": True}


# ========================
# PAGE: mode_settings
# ========================

@router.register("mode_settings", "set_mode_setting")
async def _handle_set_mode_setting(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    mode_name = payload.get("mode")
    setting_key = payload.get("key")
    if not isinstance(mode_name, str) or not isinstance(setting_key, str):
        return {"applied": False, "reason": "invalid_mode_setting"}

    descriptor = mm._get_mode_setting_descriptor(mode_name, setting_key)
    if descriptor is None:
        return {"applied": False, "reason": "unknown_mode_setting"}

    normalized_value, ok = mm._normalize_mode_setting_value(descriptor, payload.get("value"))
    if not ok:
        return {"applied": False, "reason": "invalid_setting_value"}

    current_mode_settings = mm._copy_mode_settings_map(mm.activ_configuration.get("modeSettings", {}))
    current_mode_settings.setdefault(mode_name, {})
    current_mode_settings[mode_name][setting_key] = normalized_value
    mm.activ_configuration["modeSettings"] = current_mode_settings

    mm._apply_active_mode_settings()
    persisted = mm._persist_active_configuration_mode_settings()

    return {
        "applied": True,
        "mode": mode_name,
        "key": setting_key,
        "value": normalized_value,
        "persisted": persisted,
    }


# ========================
# PAGE: system
# ========================

@router.register("system", "restart_python_loop")
async def _handle_restart_python_loop(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    import asyncio
    if mm.pending_system_action is not None:
        return {"applied": False, "reason": "system_action_already_pending"}

    capability = mm.system_status.get_restart_python_capability()
    if not capability.get("available", False):
        message = capability.get("reason") or "Python restart is unavailable."
        mm._set_system_action_feedback("restart_python_loop", "error", message)
        return {"applied": False, "reason": "restart_python_unavailable", "message": message}

    mm.pending_system_action = "restart_python_loop"
    mm._set_system_action_feedback(
        "restart_python_loop",
        "pending",
        "Restarting the Python process...",
    )
    asyncio.create_task(mm._restart_python_process_task())
    return {"applied": True, "status": "pending"}


@router.register("system", "restart_raspberry_pi")
async def _handle_restart_raspberry_pi(mm: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    import asyncio
    if mm.pending_system_action is not None:
        return {"applied": False, "reason": "system_action_already_pending"}

    capability = mm.system_status.get_reboot_raspberry_capability()
    if not capability.get("available", False):
        message = capability.get("reason") or "Raspberry reboot is unavailable."
        mm._set_system_action_feedback("restart_raspberry_pi", "error", message)
        return {"applied": False, "reason": "restart_raspberry_unavailable", "message": message}

    mm.pending_system_action = "restart_raspberry_pi"
    mm._set_system_action_feedback(
        "restart_raspberry_pi",
        "pending",
        "Reboot command queued. The app should return automatically after boot.",
    )
    asyncio.create_task(mm._reboot_raspberry_task())
    return {"applied": True, "status": "pending"}
