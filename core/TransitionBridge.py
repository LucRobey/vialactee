"""
core/TransitionBridge.py - The only glue between the project and the transition sector.

Everything that translates between project objects (Listener, Segment, Mode_master)
and the doors of `transitions.api` lives here, so the sector itself never sees a
project object and the rest of the project never sees sector internals.

- build_music_snapshot:        Listener            -> MusicSnapshot   (Music door)
- build_installation_snapshot: Segment list        -> InstallationSnapshot (Installation door)
- apply_orders:                TransitionOrders    -> OrderAck        (Orders + Acknowledgement doors;
                                                                   also forwards orders.palette to the mood sector)
"""
from typing import Any, List, Optional, Tuple

from transitions.api import (
    InstallationSnapshot,
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


def build_installation_snapshot(
    segments: List[Any],
    room_bounds: Optional[Tuple[float, float]] = None,
) -> InstallationSnapshot:
    """Describe the physical segments to the sector."""
    return InstallationSnapshot(
        segments=tuple(
            SegmentDescriptor(
                name=seg.name,
                orientation=str(getattr(seg, "orientation", "vertical")),
                available_modes=tuple(getattr(seg, "modes", {}).keys()),
                active_mode=str(getattr(seg, "activ_mode", "")),
                is_blocked=bool(getattr(seg, "isBlocked", False)),
            )
            for seg in segments
        ),
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
    modes = None
    if isinstance(getattr(mode_master, "activ_configuration", None), dict):
        modes = mode_master.activ_configuration.setdefault("modes", {})

    for order in orders.orders:
        segment = mode_master._find_segment_by_name(order.segment)
        if segment is None or getattr(segment, "isBlocked", False) is True:
            refused.append(order.segment)
            continue
        cfg = {"type": order.technique, "duration": order.duration}
        if getattr(order, "start_offset", 0.0):
            cfg["start_offset"] = order.start_offset
        if orders.reason in ("drop_impact", "request_drop"):
            cfg["force"] = True
        segment.change_mode(order.target_mode, cfg)
        if order.direction is not None:
            segment.change_way(order.direction)
        if modes is not None:
            modes[order.segment] = order.target_mode
        (accepted if getattr(segment, "is_in_transition", False) else refused).append(order.segment)

    if hasattr(mode_master, "_state_dirty"):
        mode_master._state_dirty = True
    mood = getattr(mode_master, "mood", None)
    if orders.palette is not None and mood is not None:
        mood.request_palette(orders.palette.palette, orders.palette.duration)
    return OrderAck(accepted=tuple(accepted), refused=tuple(refused))
