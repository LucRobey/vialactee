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


def build_mode_profiles(modes_config: Optional[Dict[str, Any]] = None) -> Tuple[ModeProfile, ...]:
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

    profiles: List[ModeProfile] = []
    for entry in (cfg or {}).get("standard_modes", []):
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
) -> InstallationSnapshot:
    """Describe the physical segments and mode profiles to the sector."""
    mode_profiles = modes if modes is not None else build_mode_profiles()
    return InstallationSnapshot(
        segments=tuple(_segment_descriptor(seg) for seg in segments),
        modes=mode_profiles,
        room_bounds=room_bounds,
    )


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
