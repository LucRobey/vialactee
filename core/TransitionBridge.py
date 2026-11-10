"""
core/TransitionBridge.py - The only glue between the project and the transition sector.

Everything that translates between project objects (Listener, Segment, Mode_master)
and the doors of `transitions.api` lives here, so the sector itself never sees a
project object and the rest of the project never sees sector internals.

- build_music_snapshot:        Listener            -> MusicSnapshot        (Music door)
- build_mode_profiles:         modes.json dict     -> Tuple[ModeProfile]   (Mode profiles door)
- build_installation_snapshot: Segment list        -> InstallationSnapshot (Installation door)
- apply_orders:                TransitionOrders    -> OrderAck             (Orders + Acknowledgement doors;
                                                                            also forwards orders.palette to the mood sector)
"""
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import core.Segment as Segment
from mood.api import DEFAULT_MANUAL_HOLD
from transitions.api import (
    InstallationSnapshot,
    ModeProfile,
    MusicSnapshot,
    OrderAck,
    SegmentDescriptor,
    TransitionOrders,
)


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _scene_name(ctx: Any) -> str:
    raw = getattr(ctx, "scene", None)
    return str(getattr(raw, "value", raw) or "CHILL")


def build_music_snapshot(listener: Any) -> MusicSnapshot:
    """Freeze what the sector needs to know about the music this frame."""
    ctx = getattr(listener, "context", None)
    analyzer = getattr(listener, "analyzer", None)
    lookahead = _f(getattr(analyzer, "lookahead_seconds", 5.0), 5.0)

    if ctx is None:
        return MusicSnapshot(
            beat_phase=_f(getattr(listener, "beat_phase", 0.0)),
            is_beat=bool(getattr(listener, "is_beat", False)),
            energy=_f(getattr(listener, "asserved_total_power", 0.5), 0.5),
            salience=_f(getattr(listener, "rhythm_salience", 0.5), 0.5),
            beat_trust=_f(getattr(listener, "beat_trust", 0.5), 0.5),
            is_song_change=bool(getattr(listener, "is_song_change", False)),
            is_verse_chorus_change=bool(getattr(listener, "is_verse_chorus_change", False)),
            live_is_song_change=bool(getattr(listener, "live_is_song_change", False)),
            live_is_verse_chorus_change=bool(getattr(listener, "live_is_verse_chorus_change", False)),
            lookahead_seconds=lookahead,
            drop_countdown=_f(getattr(listener, "drop_countdown", 0.0)),
            is_drop_imminent=bool(getattr(listener, "is_drop_imminent", False)),
        )

    return MusicSnapshot(
        beat_phase=_f(getattr(listener, "beat_phase", 0.0)),
        is_beat=bool(getattr(listener, "is_beat", False)),
        energy=_f(getattr(ctx, "energy", 0.5), 0.5),
        salience=_f(getattr(ctx, "salience", 0.5), 0.5),
        beat_trust=_f(getattr(ctx, "beat_trust", 0.5), 0.5),
        novelty=_f(getattr(ctx, "novelty", 0.4), 0.4),
        tension=_f(getattr(ctx, "tension", 0.3), 0.3),
        power=_f(getattr(ctx, "power", 0.0)),
        scene=_scene_name(ctx),
        is_drop_impact=bool(getattr(ctx, "is_drop_impact", False)),
        is_syncopated=bool(getattr(ctx, "is_syncopated", False)),
        is_locked=bool(getattr(ctx, "is_locked", False)),
        is_rhythmic=bool(getattr(ctx, "is_rhythmic", False)),
        is_silent=bool(getattr(ctx, "is_silent", False)),
        is_song_change=bool(getattr(listener, "is_song_change", getattr(ctx, "is_song_change", False))),
        is_verse_chorus_change=bool(getattr(listener, "is_verse_chorus_change", getattr(ctx, "is_verse_chorus_change", False))),
        live_is_song_change=bool(getattr(listener, "live_is_song_change", False)),
        live_is_verse_chorus_change=bool(getattr(listener, "live_is_verse_chorus_change", False)),
        lookahead_seconds=lookahead,
        drop_countdown=_f(getattr(ctx, "drop_countdown", 0.0)),
        is_drop_imminent=bool(getattr(ctx, "is_drop_imminent", False)),
    )


def build_mode_profiles(
    modes_config: Optional[Dict[str, Any]] = None,
    global_only: bool = False,
) -> Tuple[ModeProfile, ...]:
    """Build frozen ModeProfile objects from config/modes.json (or cached Segment config)."""
    cfg = modes_config
    if cfg is None:
        if Segment.Segment._MODES_CONFIG_CACHE:
            cfg = next(iter(Segment.Segment._MODES_CONFIG_CACHE.values()))
        else:
            config_path = os.path.join(os.path.dirname(__file__), "..", "config", "modes.json")
            try:
                key = (os.path.abspath(config_path), os.stat(config_path).st_mtime_ns)
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                Segment.Segment._MODES_CONFIG_CACHE.clear()
                Segment.Segment._MODES_CONFIG_CACHE[key] = cfg
            except Exception:
                cfg = {}

    section = "global_modes" if global_only else "standard_modes"
    profiles: List[ModeProfile] = []
    for entry in (cfg or {}).get(section, []):
        if not isinstance(entry, dict) or not entry.get("name"):
            continue
        dna_raw = entry.get("dna") or {}
        dna = (
            _f(dna_raw.get("energy", 0.5), 0.5),
            _f(dna_raw.get("punch", 0.5), 0.5),
            _f(dna_raw.get("rhythm", 0.5), 0.5),
            _f(dna_raw.get("complexity", 0.5), 0.5),
        )
        tags = tuple(str(t) for t in (entry.get("tags") or ()))
        profiles.append(ModeProfile(name=str(entry["name"]), dna=dna, tags=tags))
    return tuple(profiles)


def _segment_descriptor(seg: Any) -> SegmentDescriptor:
    name = str(getattr(seg, "name", ""))
    ori = str(getattr(seg, "orientation", "vertical"))
    sid = str(getattr(seg, "id", "") or (name[8:].strip() if name.startswith("Segment ") else name))
    raw_tags = tuple(str(t) for t in (getattr(seg, "tags", ()) or ()) if t)
    tags = tuple(dict.fromkeys([*raw_tags, f"orientation:{ori}"]))
    return SegmentDescriptor(
        name=name,
        orientation=ori,
        available_modes=tuple(getattr(seg, "modes", {}).keys()),
        active_mode=str(getattr(seg, "activ_mode", "")),
        is_blocked=bool(getattr(seg, "isBlocked", False)),
        id=sid,
        tags=tags,
    )


def build_installation_snapshot(
    segments: List[Any],
    room_bounds: Optional[Tuple[float, float]] = None,
    modes: Optional[Tuple[ModeProfile, ...]] = None,
    global_only: bool = False,
) -> InstallationSnapshot:
    """Describe the physical segments and mode profiles to the sector."""
    mode_profiles = modes if modes is not None else build_mode_profiles(global_only=global_only)
    return InstallationSnapshot(
        segments=tuple(_segment_descriptor(seg) for seg in segments),
        modes=mode_profiles,
        room_bounds=room_bounds,
    )


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


def apply_panel_command(mode_master: Any, command: Dict[str, Any]) -> bool:
    """Apply a desktop control panel command (`set_locked`, `set_segment_mode`, `set_global_mode`, `set_mode_scope`)."""
    ctype = command.get("type")
    if ctype == "set_locked":
        mode_master.transitions.set_locked(bool(command.get("locked")))
        mode_master._state_dirty = True
        return True
    if ctype == "set_segment_mode":
        segment_ref = command.get("segment")
        mode_name = command.get("mode")
        if not isinstance(segment_ref, str) or not isinstance(mode_name, str):
            return False
        segment = mode_master._find_segment_by_name(segment_ref)
        if segment is None or segment._normalize_mode_name(mode_name) not in segment.modes:
            return False
        norm_name = segment._normalize_mode_name(mode_name)
        is_global = bool(getattr(segment.modes[norm_name], "IS_GLOBAL", False))
        for seg in (mode_master.segments_list if is_global else [segment]):
            seg.execute_mode_swap(norm_name)
        if is_global != bool(getattr(mode_master, "_use_global_modes", False)):
            sync_mode_scope(mode_master, is_global)
        else:
            mode_master._push_installation()
        mode_master._state_dirty = True
        return True
    if ctype == "set_global_mode":
        mode_name = command.get("mode")
        if not isinstance(mode_name, str) or not mode_master.segments_list:
            return False
        seg0 = mode_master.segments_list[0]
        norm_name = seg0._normalize_mode_name(mode_name)
        if norm_name not in seg0.modes or not getattr(seg0.modes[norm_name], "IS_GLOBAL", False):
            return False
        for seg in mode_master.segments_list:
            seg.execute_mode_swap(norm_name)
        sync_mode_scope(mode_master, True)
        mode_master._state_dirty = True
        return True
    if ctype == "set_mode_scope":
        scope = command.get("scope")
        if scope == "global" and mode_master.segments_list:
            seg0 = mode_master.segments_list[0]
            req = command.get("mode")
            norm_name = seg0._normalize_mode_name(req) if isinstance(req, str) else ""
            if norm_name not in seg0.modes or not getattr(seg0.modes[norm_name], "IS_GLOBAL", False):
                gmodes = sorted(k for k, m in seg0.modes.items() if getattr(m, "IS_GLOBAL", False))
                if not gmodes:
                    return False
                norm_name = gmodes[0]
            for seg in mode_master.segments_list:
                seg.execute_mode_swap(norm_name)
            sync_mode_scope(mode_master, True)
            mode_master._state_dirty = True
            return True
        if scope == "local" and mode_master.segments_list:
            sync_mode_scope(mode_master, False)
            music = build_music_snapshot(mode_master.listener)
            alloc = mode_master.transitions.allocate_initial(music) if hasattr(mode_master.transitions, "allocate_initial") else {}
            for seg in mode_master.segments_list:
                local_modes = sorted(k for k, m in seg.modes.items() if not getattr(m, "IS_GLOBAL", False))
                target = alloc.get(seg.name) or alloc.get(getattr(seg, "id", "")) or (local_modes[0] if local_modes else seg.get_current_mode())
                if target in seg.modes:
                    seg.execute_mode_swap(target)
            mode_master._push_installation()
            mode_master._state_dirty = True
            return True
    if ctype == "set_mood":
        mood = getattr(mode_master, "mood", None)
        palette = command.get("palette") or command.get("mood")
        if mood is None or not isinstance(palette, str) or not mood.request_palette(palette, hold=DEFAULT_MANUAL_HOLD):
            return False
        mode_master._state_dirty = True
        return True
    if ctype == "set_mood_auto":
        mood = getattr(mode_master, "mood", None)
        auto_scene = command.get("auto_scene")
        if mood is None or not isinstance(auto_scene, bool):
            return False
        mood.set_auto_scene(auto_scene)
        mode_master._state_dirty = True
        return True
    return False


def apply_orders(mode_master: Any, orders: TransitionOrders) -> OrderAck:
    """
    Execute the sector's orders on the real segments and report who accepted.
    A segment accepts when it actually started a transition (blocked segments,
    segments already transitioning and same-mode targets refuse).
    """
    accepted: List[str] = []
    refused: List[str] = []

    for order in orders.orders:
        segment = mode_master._find_segment_by_name(order.segment)
        if segment is None or getattr(segment, "isBlocked", False) is True:
            refused.append(order.segment)
            continue
        cfg = {
            "type": order.technique,
            "duration": order.duration,
            "mode_handshake": bool(getattr(order, "mode_handshake", True)),
        }
        if getattr(order, "start_offset", 0.0):
            cfg["start_offset"] = order.start_offset
        if orders.reason in ("drop_impact", "request_drop"):
            cfg["force"] = True
        segment.change_mode(order.target_mode, cfg)
        if order.direction is not None:
            segment.change_way(order.direction)
        (accepted if getattr(segment, "is_in_transition", False) else refused).append(order.segment)

    if hasattr(mode_master, "_state_dirty"):
        mode_master._state_dirty = True
    mood = getattr(mode_master, "mood", None)
    if orders.palette is not None and mood is not None:
        mood.request_palette(orders.palette.palette, orders.palette.duration)
    return OrderAck(accepted=tuple(accepted), refused=tuple(refused))
