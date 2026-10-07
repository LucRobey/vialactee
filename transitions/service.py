"""
transitions/service.py - Default implementation of the front door (TransitionService).

Wires the sector's internals (director clock, manager decisions, engine blending)
behind the doors defined in transitions/api.py. The manager still reads its world
through duck-typed views; this module builds those views from the door snapshots,
so nothing outside the room is ever touched.
"""
from typing import Any, Dict, List, Optional

import numpy as np

from transitions import engine
from transitions.api import (
    InstallationSnapshot,
    MusicSnapshot,
    OrderAck,
    SegmentOrder,
    TransitionOrders,
    TransitionService,
    TransitionStatus,
)
from transitions.director import Transition_Director
from transitions.manager import LocalTransitionManager, TRANSITION_TECHNIQUES

DROP_TECHNIQUE: Dict[str, Any] = {"type": "explosion", "duration": 0.4}


class _MusicView:
    """What the manager reads as its 'listener': the latest MusicSnapshot, no allocation per frame."""
    __slots__ = ("beat_phase", "is_beat", "context")

    def __init__(self) -> None:
        self.context = MusicSnapshot()
        self.beat_phase = 0.0
        self.is_beat = False

    def set(self, music: MusicSnapshot) -> None:
        self.context = music
        self.beat_phase = music.beat_phase
        self.is_beat = music.is_beat


class _SegmentView:
    """A segment as the manager sees it. change_mode() records an order instead of acting."""
    __slots__ = ("name", "orientation", "modes", "activ_mode", "isBlocked", "_host")

    def __init__(self, host: "_Host", name: str, orientation: str, modes: Dict[str, None],
                 activ_mode: str, blocked: bool) -> None:
        self._host = host
        self.name = name
        self.orientation = orientation
        self.modes = modes
        self.activ_mode = activ_mode
        self.isBlocked = blocked

    def change_mode(self, mode_name: str, transition_config: Optional[Dict[str, Any]] = None) -> None:
        self._host.recorded.append((self.name, mode_name, transition_config))


class _Host:
    """The installation as the manager sees it, built from an InstallationSnapshot."""

    def __init__(self, director: Transition_Director) -> None:
        self.segments_list: List[_SegmentView] = []
        self._by_name: Dict[str, _SegmentView] = {}
        self.activ_configuration: Dict[str, Any] = {"modes": {}}
        self._state_dirty = False
        self.transition_director = director
        self.recorded: List[Any] = []

    def _find_segment_by_name(self, name: str) -> Optional[_SegmentView]:
        return self._by_name.get(name)

    def load(self, installation: InstallationSnapshot) -> None:
        self.segments_list = []
        self._by_name = {}
        for d in installation.segments:
            view = _SegmentView(self, d.name, d.orientation, {m: None for m in d.available_modes},
                                d.active_mode, d.is_blocked)
            self.segments_list.append(view)
            self._by_name[d.name] = view


class DefaultTransitionService(TransitionService):
    """Synchronous front door of the transition sector."""

    def __init__(self, infos: Optional[Dict[str, Any]] = None, segments_path: Optional[str] = None) -> None:
        self._director = Transition_Director(infos or {}, segments_path)
        self._host = _Host(self._director)
        self._music = _MusicView()
        self._manager = LocalTransitionManager(self._host, self._music)
        self._clock = 0.0
        self._reason = ""
        self._last_orders: Dict[str, str] = {}

    # --- inputs --------------------------------------------------------------

    def set_installation(self, installation: InstallationSnapshot) -> None:
        self._host.load(installation)
        if installation.room_bounds is not None:
            engine.set_room_bounds(*installation.room_bounds)

    def update(self, dt: float, music: MusicSnapshot) -> Optional[TransitionOrders]:
        self._clock += dt
        self._music.set(music)
        if self._director.update(self._clock, music):
            self._reason = "timer"
            self._manager.schedule_transition(quantize_downbeat=True)
        self._manager.update(dt)
        return self._drain()

    def acknowledge(self, ack: OrderAck) -> None:
        for name in ack.accepted:
            view = self._host._find_segment_by_name(name)
            target = self._last_orders.get(name)
            if view and target:
                view.activ_mode = target
        if not ack.accepted and self._director.is_in_transition:
            self._director.cancel_transition()
        self._last_orders = {}

    # --- requests ------------------------------------------------------------

    def request_next(self, technique: Optional[str] = None) -> None:
        self._reason = "request_next"
        self._manager.schedule_transition(transition_config=self._resolve(technique), quantize_downbeat=True)

    def request_drop(self) -> None:
        self._reason = "request_drop"
        self._manager.schedule_transition(transition_config=dict(DROP_TECHNIQUE), quantize_downbeat=False)

    def set_locked(self, locked: bool) -> None:
        self._director.locked = bool(locked)

    def set_auto_interval(self, seconds: float) -> None:
        self._director.configuration_duration = float(seconds)

    # --- outputs -------------------------------------------------------------

    def blend(
        self,
        dest_buffer: np.ndarray,
        incoming_buffer: np.ndarray,
        progress: float,
        technique: str,
        coords: Optional[np.ndarray] = None,
    ) -> None:
        engine.apply_transition(dest_buffer, incoming_buffer, progress, technique, coords)

    def get_status(self) -> TransitionStatus:
        d = self._director
        return TransitionStatus(
            state=d.state,
            progress=float(d.transition_progress),
            is_in_transition=d.is_in_transition,
            is_locked=d.locked,
            auto_interval=float(d.configuration_duration),
            technique=d.transition_type,
        )

    # --- internals -----------------------------------------------------------

    @staticmethod
    def _resolve(technique: Optional[str]) -> Optional[Dict[str, Any]]:
        if technique is None:
            return None
        if technique in TRANSITION_TECHNIQUES:
            return dict(TRANSITION_TECHNIQUES[technique])
        return {"type": technique, "duration": 2.0}

    def _drain(self) -> Optional[TransitionOrders]:
        if not self._host.recorded:
            return None
        orders = []
        for seg, mode, cfg in self._host.recorded:
            cfg = cfg or {}
            orders.append(SegmentOrder(
                segment=seg,
                target_mode=mode,
                technique=str(cfg.get("type", "fade_in_out")),
                duration=float(cfg.get("duration", 2.0)),
            ))
            self._last_orders[seg] = mode
        self._host.recorded = []
        return TransitionOrders(orders=tuple(orders), reason=self._reason)
