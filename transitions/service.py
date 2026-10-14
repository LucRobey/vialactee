"""
transitions/service.py - Default implementation of the front door (TransitionService).

Wires the sector's internals (director clock, manager decisions, engine blending)
directly behind the doors defined in transitions/api.py.
"""
from typing import Any, Dict, Optional

import numpy as np

from transitions import engine
from transitions.api import (
    InstallationSnapshot,
    MusicSnapshot,
    OrderAck,
    TransitionOrders,
    TransitionService,
    TransitionStatus,
)
from transitions.director import Transition_Director
from transitions.manager import LocalTransitionManager, TRANSITION_TECHNIQUES

DROP_TECHNIQUE: Dict[str, Any] = {"type": "explosion", "duration": 0.4}

# Automatic (director-fired) triggers that ripple across the installation per segment.
# Drop triggers (`drop_impact`, `pre_drop_buildup`) are deliberately NOT staggered: their
# duration is scaled so the climax lands exactly when the drop reaches the speakers, and
# per-segment start offsets would break that alignment. Manual requests (`request_next`,
# `request_drop`) stay instant unless the caller asks for `staggered=True`.
STAGGERED_AUTO_REASONS = frozenset(("timer", "song_change", "structural_change"))


class DefaultTransitionService(TransitionService):
    """Synchronous front door of the transition sector."""

    def __init__(self, infos: Optional[Dict[str, Any]] = None) -> None:
        service_infos = dict(infos or {})
        if "min_time_between_transitions" not in service_infos:
            service_infos["min_time_between_transitions"] = 5.0
        self._director = Transition_Director(service_infos)
        self._manager = LocalTransitionManager(self._director)
        self._reason = ""
        self._drop_requested = False
        self._last_orders: Dict[str, str] = {}

    # --- inputs --------------------------------------------------------------

    def set_installation(self, installation: InstallationSnapshot) -> None:
        self._manager.set_installation(installation.segments)
        if installation.room_bounds is not None:
            engine.set_room_bounds(*installation.room_bounds)

    def update(self, dt: float, music: MusicSnapshot) -> Optional[TransitionOrders]:
        self._manager.music = music
        director_fired = self._director.update(dt, music)
        if self._drop_requested:
            self._drop_requested = False
            self._reason = "request_drop"
            self._manager.schedule_transition(transition_config=dict(DROP_TECHNIQUE), quantize_downbeat=False)
        elif director_fired:
            self._reason = self._director.last_trigger_reason or "timer"
            self._manager.schedule_transition(
                transition_config=self._director.pending_transition_config,
                quantize_downbeat=self._director.pending_quantize_downbeat,
                staggered=self._reason in STAGGERED_AUTO_REASONS,
            )
        self._manager.update(dt, music)
        return self._drain()

    def acknowledge(self, ack: OrderAck) -> None:
        for name in ack.accepted:
            target = self._last_orders.get(name)
            if target:
                self._manager.set_active_mode(name, target)
        if not ack.accepted and self._director.is_in_transition:
            self._director.cancel_transition()
        self._last_orders = {}

    # --- requests ------------------------------------------------------------

    def request_next(
        self,
        technique: Optional[str] = None,
        staggered: bool = False,
        stagger_pattern: Optional[Any] = None,
    ) -> None:
        self._drop_requested = False
        self._reason = "request_next"
        self._director.reset_cooldown()
        self._director.is_pending = True
        self._manager.schedule_transition(
            transition_config=self._resolve(technique),
            quantize_downbeat=True,
            staggered=staggered,
            stagger_pattern=stagger_pattern,
        )

    def request_drop(self) -> None:
        self._drop_requested = True
        self._reason = "request_drop"
        self._director.reset_cooldown()
        self._director.is_pending = True
        self._manager._pending_transition = None

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
            is_cooling_down=d.is_cooling_down,
            is_locked=d.locked,
            auto_interval=float(d.configuration_duration),
            technique=d.transition_type,
            cooldown_remaining=float(d.cooldown_remaining),
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
        orders = self._manager.pop_orders()
        if not orders:
            if not self._director.is_pending and self._manager._pending_transition is None and not self._drop_requested:
                self._reason = ""
            return None
        for o in orders:
            self._last_orders[o.segment] = o.target_mode
        reason = self._reason
        self._reason = ""
        return TransitionOrders(orders=orders, reason=reason)
