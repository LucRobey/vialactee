"""
core/PanelCommands.py - Commands sent by the desktop control panel (the pygame window opened by Main.py).

Each handler takes the Mode_master and the command dict, runs synchronously on the
render loop, and returns True when the command was applied.

- set_locked {locked}:           HOLD / LIVE, freezes or resumes automatic transitions.
- set_segment_mode {segment, mode}: puts one segment (or, for a Global Mode, every segment) on a mode.
- set_global_mode {mode}:        puts every segment on a Global Mode and switches to global scope.
- set_mode_scope {scope, mode?}: "global" (unison Global Modes) or "local" (per-segment allocation).
- set_mood {palette}:            manual palette pick, pausing auto-scene for DEFAULT_MANUAL_HOLD seconds.
- set_mood_auto {auto_scene}:    turns mood auto-scene on or off.

select_segment_mode() is also the entry point for the web UI's topology/select_segment_mode
instruction, so a mode picked there switches the transition scope exactly like the panel does.
"""
from typing import Any, Callable, Dict

import core.TransitionBridge as TransitionBridge
from mood.api import DEFAULT_MANUAL_HOLD


def _is_global(mode: Any) -> bool:
    return bool(getattr(mode, "IS_GLOBAL", False))


def sync_mode_scope(mode_master: Any, use_global: bool) -> None:
    """Switch the transition sector between Global Modes (unison) and Local Modes (per-segment)."""
    mode_master._use_global_modes = bool(use_global)
    if use_global and mode_master.segments_list:
        sids = [
            str(getattr(s, "id", "") or s.name.replace("Segment ", "", 1))
            for s in mode_master.segments_list
        ]
        policy = {
            "version": 1,
            "settings": {"maxDifferentModes": 1, "temperature": 1.0, "memoryDepth": 8, "repeatPenalty": 3.0},
            "zones": {
                "chandelier": {
                    "segments": sids,
                    "groupings": [{"id": "global-unison", "weight": 1, "groups": [["all"]]}],
                }
            },
            "rules": [],
        }
        mode_master.transitions.configure(policy)
        mode_master._push_installation()
    else:
        mode_master._push_installation()
        from config.coherence_loader import load_coherence_config
        try:
            mode_master.transitions.configure(load_coherence_config(mode_master.infos))
        except Exception:
            mode_master.transitions.configure(None)


def _swap_all_to_global(mode_master: Any, norm_name: str) -> None:
    for seg in mode_master.segments_list:
        seg.execute_mode_swap(norm_name)
    sync_mode_scope(mode_master, True)


def _set_locked(mode_master: Any, command: Dict[str, Any]) -> bool:
    mode_master.transitions.set_locked(bool(command.get("locked")))
    return True


def select_segment_mode(mode_master: Any, segment_ref: Any, mode_name: Any) -> bool:
    """
    Put one segment (or, for a Global Mode, every segment) on a mode and keep the transition
    sector's scope in step with the choice. Shared by the desktop panel and the web UI
    (core/CommandRouter.py), so both leave the sector in the same state.
    """
    if not isinstance(segment_ref, str) or not isinstance(mode_name, str):
        return False
    segment = mode_master._find_segment_by_name(segment_ref)
    if segment is None or segment._normalize_mode_name(mode_name) not in segment.modes:
        return False
    norm_name = segment._normalize_mode_name(mode_name)
    is_global = _is_global(segment.modes[norm_name])
    for seg in (mode_master.segments_list if is_global else [segment]):
        seg.execute_mode_swap(norm_name)
    if is_global != bool(getattr(mode_master, "_use_global_modes", False)):
        sync_mode_scope(mode_master, is_global)
    else:
        mode_master._push_installation()
    return True


def _set_segment_mode(mode_master: Any, command: Dict[str, Any]) -> bool:
    return select_segment_mode(mode_master, command.get("segment"), command.get("mode"))


def _set_global_mode(mode_master: Any, command: Dict[str, Any]) -> bool:
    mode_name = command.get("mode")
    if not isinstance(mode_name, str) or not mode_master.segments_list:
        return False
    seg0 = mode_master.segments_list[0]
    norm_name = seg0._normalize_mode_name(mode_name)
    if norm_name not in seg0.modes or not _is_global(seg0.modes[norm_name]):
        return False
    _swap_all_to_global(mode_master, norm_name)
    return True


def _scope_global(mode_master: Any, command: Dict[str, Any]) -> bool:
    seg0 = mode_master.segments_list[0]
    req = command.get("mode")
    norm_name = seg0._normalize_mode_name(req) if isinstance(req, str) else ""
    if norm_name not in seg0.modes or not _is_global(seg0.modes[norm_name]):
        gmodes = sorted(k for k, m in seg0.modes.items() if _is_global(m))
        if not gmodes:
            return False
        norm_name = gmodes[0]
    _swap_all_to_global(mode_master, norm_name)
    return True


def _scope_local(mode_master: Any) -> bool:
    sync_mode_scope(mode_master, False)
    transitions = mode_master.transitions
    music = TransitionBridge.build_music_snapshot(mode_master.listener)
    alloc = transitions.allocate_initial(music) if hasattr(transitions, "allocate_initial") else {}
    for seg in mode_master.segments_list:
        local_modes = sorted(k for k, m in seg.modes.items() if not _is_global(m))
        fallback = local_modes[0] if local_modes else seg.get_current_mode()
        target = alloc.get(seg.name) or alloc.get(getattr(seg, "id", "")) or fallback
        if target in seg.modes:
            seg.execute_mode_swap(target)
    mode_master._push_installation()
    return True


def _set_mode_scope(mode_master: Any, command: Dict[str, Any]) -> bool:
    if not mode_master.segments_list:
        return False
    scope = command.get("scope")
    if scope == "global":
        return _scope_global(mode_master, command)
    if scope == "local":
        return _scope_local(mode_master)
    return False


def _set_mood(mode_master: Any, command: Dict[str, Any]) -> bool:
    mood = getattr(mode_master, "mood", None)
    palette = command.get("palette") or command.get("mood")
    if mood is None or not isinstance(palette, str):
        return False
    return bool(mood.request_palette(palette, hold=DEFAULT_MANUAL_HOLD))


def _set_mood_auto(mode_master: Any, command: Dict[str, Any]) -> bool:
    mood = getattr(mode_master, "mood", None)
    auto_scene = command.get("auto_scene")
    if mood is None or not isinstance(auto_scene, bool):
        return False
    mood.set_auto_scene(auto_scene)
    return True


_HANDLERS: Dict[str, Callable[[Any, Dict[str, Any]], bool]] = {
    "set_locked": _set_locked,
    "set_segment_mode": _set_segment_mode,
    "set_global_mode": _set_global_mode,
    "set_mode_scope": _set_mode_scope,
    "set_mood": _set_mood,
    "set_mood_auto": _set_mood_auto,
}


def apply_panel_command(mode_master: Any, command: Dict[str, Any]) -> bool:
    """Apply a desktop control panel command; marks the state dirty when it was applied."""
    handler = _HANDLERS.get(command.get("type"))
    if handler is None or not handler(mode_master, command):
        return False
    mode_master._state_dirty = True
    return True
