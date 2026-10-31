"""
transitions/api.py - THE DOORS of the sealed transition sector.

This is the only module the rest of the project may import from `transitions`.
It defines plain, immutable data shapes (what crosses the wall) and the
front-door class `TransitionService` (how the wall is crossed).

Rules (enforced by tests/governance/test_transition_isolation.py):
- Nothing in `transitions/` imports from core/, modes/, connectors/ or hardware/.
- Nothing outside `transitions/` imports from it except `transitions.api`.
- Only standard library + numpy appear here, so any side can import it freely.

Doors (see docs/contracts/transition_contract.md):
  IN : MusicSnapshot, InstallationSnapshot, requests (request_*, set_*), OrderAck
  OUT: TransitionOrders (one entry per segment, optional palette request),
       blend() in place, TransitionStatus (state + progress)

Guarantees:
- AXIOM-01/02: blend() mutates the destination buffer in place, zero allocation.
- Every shape has defaults for optional fields, so the doors can GROW
  (new music fields, new order fields) without breaking either side.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np


class PolicyError(Exception):
    """Raised when a coherence policy fails structural or semantic validation."""


# =============================================================================
# DOOR: MUSIC (in)
# =============================================================================

@dataclass(frozen=True)
class MusicSnapshot:
    """Read-only picture of what the music is doing at this frame (speaker time)."""
    beat_phase: float = 0.0
    is_beat: bool = False
    energy: float = 0.0
    salience: float = 0.0
    beat_trust: float = 0.0
    novelty: float = 0.0
    tension: float = 0.0
    power: float = 0.0
    scene: str = "CHILL"
    is_drop_impact: bool = False
    is_syncopated: bool = False
    is_locked: bool = False
    is_rhythmic: bool = False
    is_silent: bool = False
    is_song_change: bool = False
    is_verse_chorus_change: bool = False
    live_is_song_change: bool = False
    live_is_verse_chorus_change: bool = False
    lookahead_seconds: float = 5.0
    drop_countdown: float = 0.0
    is_drop_imminent: bool = False


# =============================================================================
# DOOR: MODE PROFILES (in)
# =============================================================================

@dataclass(frozen=True)
class ModeProfile:
    """Read-only profile of one mode: its name, 4D DNA, and tags."""
    name: str
    dna: Tuple[float, float, float, float] = (0.5, 0.5, 0.5, 0.5)
    tags: Tuple[str, ...] = ()


# =============================================================================
# DOOR: INSTALLATION (in)
# =============================================================================

@dataclass(frozen=True)
class SegmentDescriptor:
    """Read-only description of one physical segment."""
    name: str
    orientation: str = "vertical"                  # "vertical" | "horizontal"
    available_modes: Tuple[str, ...] = ()
    active_mode: str = ""
    is_blocked: bool = False
    id: str = ""
    tags: Tuple[str, ...] = ()


@dataclass(frozen=True)
class InstallationSnapshot:
    """Read-only description of the whole installation layout."""
    segments: Tuple[SegmentDescriptor, ...] = ()
    modes: Tuple[ModeProfile, ...] = ()
    room_bounds: Optional[Tuple[float, float]] = None   # (max_x, max_y) from the layout, None if unknown


# =============================================================================
# DOORS: ORDERS (out), ACKNOWLEDGEMENT (in), PALETTE REQUEST (out)
# =============================================================================

@dataclass(frozen=True)
class SegmentOrder:
    """One segment's instruction. Entries may differ per segment."""
    segment: str
    target_mode: str
    technique: str
    duration: float
    direction: Optional[str] = None                # "UP" | "DOWN" | None = leave unchanged
    start_offset: float = 0.0                      # seconds after the common start (0 = together)
    mode_handshake: bool = False                   # True if transition uses MODE_COOPERATIVE physics


@dataclass(frozen=True)
class PaletteRequest:
    """Optional request to the (outside) palette manager."""
    palette: str
    duration: Optional[float] = None


@dataclass(frozen=True)
class TransitionOrders:
    """Everything the sector asks the installation to do for one transition."""
    orders: Tuple[SegmentOrder, ...] = ()
    reason: str = ""                               # why it fired, for logs/telemetry
    palette: Optional[PaletteRequest] = None


@dataclass(frozen=True)
class OrderAck:
    """Caller's answer: which segments accepted the orders (others refused or are blocked)."""
    accepted: Tuple[str, ...] = ()
    refused: Tuple[str, ...] = ()


# =============================================================================
# DOOR: STATUS + PROGRESS (out)
# =============================================================================

@dataclass(frozen=True)
class TransitionStatus:
    """Read-only state of the sector, for the web UI, connector throttle and mode hooks."""
    state: str = "PASSATION"                       # "PASSATION" (idle) | "TRANSITION_DUAL"
    progress: float = 0.0                          # 0.0 .. 1.0
    is_in_transition: bool = False
    is_cooling_down: bool = False
    is_locked: bool = False
    auto_interval: float = 20.0
    technique: Optional[str] = None
    cooldown_remaining: float = 0.0
    is_pending: bool = False


AVAILABLE_TRANSITIONS: Tuple[str, ...] = (
    "AUTO",
    "silk_wipe",
    "silk_wipe_reverse",
    "iris_open",
    "iris_close",
    "zipper_merge",
    "ember_dissolve",
    "luma_melt",
    "breath_dip",
    "collider",
    "prism_sweep",
    "staccato_shutter",
    "transformer_cut",
    "flash_cut",
    "explosion",
    "vertical_wipe",
    "wipe_left_to_right",
    "wipe_right_to_left",
    "box_wipe",
    "spiral",
    "fade_in_out",
    "gravity_drop",
    "weird_glitch",
    "global_change",
)


# =============================================================================
# FRONT DOOR
# =============================================================================

class TransitionService:
    """
    The single entry point to the transition sector. Synchronous.
    Phase 1: contract only; the implementation is wired in later phases.
    """

    def __init__(self, infos: Optional[Dict[str, Any]] = None) -> None:
        self._policy: Optional[Dict[str, Any]] = None
        self._installation: Optional[InstallationSnapshot] = None

    @property
    def policy(self) -> Optional[Dict[str, Any]]:
        """Current declarative coherence policy dict, if configured."""
        return self._policy

    # --- configuration & allocation ------------------------------------------

    def configure(self, policy_raw: Dict[str, Any]) -> None:
        """Tell the sector about the coherence policy. Call at startup and on change."""
        self._policy = policy_raw

    def allocate_initial(self, music: Optional[MusicSnapshot] = None) -> Dict[str, str]:
        """
        Allocate coherent initial modes across all configured segments at boot.
        Returns a mapping from segment_name to mode_name.
        """
        if self._installation is None:
            return {}
        result: Dict[str, str] = {}
        for s in self._installation.segments:
            chosen = s.active_mode if s.active_mode else (s.available_modes[0] if s.available_modes else "Rainbow")
            result[s.name] = chosen
        return result

    # --- inputs --------------------------------------------------------------

    def set_installation(self, installation: InstallationSnapshot) -> None:
        """Tell the sector about the segments and layout. Call at startup and on change."""
        self._installation = installation

    def set_installation_snapshot(self, installation: InstallationSnapshot) -> None:
        """Alias for set_installation to ensure front door contract parity."""
        self.set_installation(installation)

    def update(self, dt: float, music: MusicSnapshot) -> Optional[TransitionOrders]:
        """
        Advance timers by dt seconds. Returns orders on the frame a transition
        fires, otherwise None. Hot path: no heap allocation when idle.
        """
        raise NotImplementedError

    def acknowledge(self, ack: OrderAck) -> None:
        """Report which segments accepted the last orders."""
        raise NotImplementedError

    # --- requests ------------------------------------------------------------

    def request_next(
        self,
        technique: Optional[str] = None,
        staggered: bool = False,
        stagger_pattern: Optional[Any] = None,
        duration: Optional[float] = None,
    ) -> None:
        """Ask for the next transition (beat-aligned). Technique None = sector decides."""
        raise NotImplementedError

    def request_drop(self) -> None:
        """Ask for an immediate high-impact transition."""
        raise NotImplementedError

    def set_locked(self, locked: bool) -> None:
        """While locked the sector never fires automatic transitions."""
        raise NotImplementedError

    def set_auto_interval(self, seconds: float) -> None:
        """Time between automatic transitions."""
        raise NotImplementedError

    # --- outputs -------------------------------------------------------------

    def blend(
        self,
        dest_buffer: np.ndarray,
        incoming_buffer: np.ndarray,
        progress: float,
        technique: str,
        coords: Optional[np.ndarray] = None,
    ) -> None:
        """
        Blend `incoming_buffer` over `dest_buffer` IN PLACE at `progress` (0..1).
        Returns nothing. Zero heap allocation (AXIOM-01 / AXIOM-02).
        """
        raise NotImplementedError

    def get_status(self) -> TransitionStatus:
        """Current state and progress."""
        raise NotImplementedError


_default_service: Optional[TransitionService] = None


def get_default_service() -> TransitionService:
    """Return the active default TransitionService instance, creating one if needed."""
    global _default_service
    if _default_service is None:
        from transitions.service import DefaultTransitionService
        _default_service = DefaultTransitionService()
    return _default_service


def configure(policy_raw: Dict[str, Any]) -> None:
    """Module-level convenience front door to configure the transition sector policy."""
    get_default_service().configure(policy_raw)


def allocate_initial(music: Optional[MusicSnapshot] = None) -> Dict[str, str]:
    """Module-level convenience front door to allocate initial segment modes."""
    return get_default_service().allocate_initial(music)


def create_transition_service(
    infos: Optional[Dict[str, Any]] = None,
) -> TransitionService:
    """
    Build the default front door. The only way outside code obtains the sector.

    Args:
        infos: Plain configuration dict (auto_transition_time, silence settings...).
    """
    from transitions.service import DefaultTransitionService
    return DefaultTransitionService(infos)


__all__ = [
    "AVAILABLE_TRANSITIONS",
    "PolicyError",
    "MusicSnapshot",
    "ModeProfile",
    "SegmentDescriptor",
    "InstallationSnapshot",
    "SegmentOrder",
    "PaletteRequest",
    "TransitionOrders",
    "OrderAck",
    "TransitionStatus",
    "TransitionService",
    "create_transition_service",
    "configure",
    "allocate_initial",
    "get_default_service",
]
