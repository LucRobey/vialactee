from typing import Dict, Any, Optional
import logging


class Transition_Director:
    """
    Clock and trigger of the transition sector.

    Tracks the global transition state machine (PASSATION <-> TRANSITION_DUAL and its
    0..1 progress), the live lookahead countdowns, and the auto-transition timer.
    It never commands anyone: update() only reports whether a trigger or timer fired.
    """

    def __init__(self, infos: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the Transition_Director.

        Args:
            infos (dict, optional): Configuration dictionary containing timer settings.
        """
        infos = infos or {}
        self.infos = infos
        self.logger = logging.getLogger("Transition_Director")

        self.locked = False
        self.configuration_duration = float(infos.get("auto_transition_time", 20.0))
        self._clock: float = 0.0
        self.next_change_time: Optional[float] = None  # armed on the first update()
        self.min_time_between_transitions = float(infos.get("min_time_between_transitions", 5.0))
        self.cooldown_remaining = max(0.0, float(infos.get("startup_grace_period", 0.0)))
        self.is_pending = False

        self.state = "PASSATION"
        self.transition_progress = 0.0
        self.transition_duration = 0.0
        self.transition_type = None

        self.upcoming_song_change_countdown = 0.0
        self.upcoming_structural_change_countdown = 0.0
        self._song_change_armed = False
        self._structural_change_armed = False
        self._drop_buildup_armed = False
        self.last_trigger_reason = ""
        self.pending_transition_config: Optional[Dict[str, Any]] = None
        self.pending_quantize_downbeat = True

    @property
    def is_in_transition(self) -> bool:
        """True if currently interpolating between dual mode buffers."""
        return self.state == "TRANSITION_DUAL"

    @property
    def is_cooling_down(self) -> bool:
        """True if currently within the post-transition cooldown period."""
        return self.cooldown_remaining > 0.0

    def reset_cooldown(self) -> None:
        """Clear active cooldown immediately (used by urgent drop impacts or manual overrides)."""
        self.cooldown_remaining = 0.0

    def arm_cooldown(self, seconds: Optional[float] = None) -> None:
        """Arm or reset security cooldown (defaults to min_time_between_transitions)."""
        self.cooldown_remaining = self.min_time_between_transitions if seconds is None else max(0.0, float(seconds))

    def set_min_time_between_transitions(self, seconds: float) -> None:
        """Configure the minimum security cooldown between transitions."""
        self.min_time_between_transitions = max(0.0, float(seconds))

    def start_transition(self, transition_config: Optional[Dict[str, Any]]) -> None:
        """ Start tracking a new global transition. """
        if transition_config is None:
            return
        self.state = "TRANSITION_DUAL"
        self.transition_progress = 0.0
        self.transition_type = transition_config["type"]
        duration = float(transition_config.get("total_duration", transition_config.get("duration", 2.0)))
        self.transition_duration = duration
        self.cooldown_remaining = 0.0
        self.is_pending = False

    def set_duration(self, duration: float) -> None:
        """Update active transition duration to accommodate staggered segments."""
        if duration > 0:
            self.transition_duration = max(self.transition_duration, float(duration))

    def cancel_transition(self) -> None:
        """ Abort a transition that no segment accepted: back to idle. """
        self.state = "PASSATION"
        self.transition_progress = 0.0
        self.transition_type = None
        self.cooldown_remaining = 0.0
        self.is_pending = False

    def update(self, dt: float, music: Optional[Any] = None) -> bool:
        """
        Advance the global transition progress and the countdowns by dt seconds.

        Args:
            dt (float): Elapsed time since the previous frame, in seconds.
            music: Optional MusicSnapshot, read for the live lookahead events.

        Returns:
            True when an audio trigger or the auto-transition timer fired and
            the director is not locked (the caller should schedule a transition).
        """
        dt = max(0.0, float(dt))
        if self.next_change_time is None:
            self.next_change_time = self._clock + self.configuration_duration
        self._clock += dt

        # Advance lookahead countdowns and cooldown timer
        if self.cooldown_remaining > 0.0:
            self.cooldown_remaining = max(0.0, self.cooldown_remaining - dt)
        self.upcoming_song_change_countdown = max(0.0, self.upcoming_song_change_countdown - dt)
        self.upcoming_structural_change_countdown = max(0.0, self.upcoming_structural_change_countdown - dt)

        # Lookahead: Check live audio feed for incoming events before they render
        if music is not None:
            lookahead = max(0.0, float(getattr(music, "lookahead_seconds", 5.0)))
            if getattr(music, "live_is_song_change", False):
                self.upcoming_song_change_countdown = lookahead
                self._song_change_armed = True
                self.logger.info(f"(TD) Live Song Change detected! Visual impact in {lookahead}s.")

            if getattr(music, "live_is_verse_chorus_change", False):
                self.upcoming_structural_change_countdown = lookahead
                self._structural_change_armed = True
                self.logger.info(f"(TD) Live Structural Change detected! Visual impact in {lookahead}s.")

        # Advance active transition progress
        if self.state == "TRANSITION_DUAL":
            duration = self.transition_duration
            step = (dt / duration) if duration > 0 else 1.0
            self.transition_progress += step
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                self.state = "PASSATION"
                self.transition_type = None
                self.cooldown_remaining = self.min_time_between_transitions
                self.next_change_time = max(self.next_change_time or 0.0, self._clock + self.configuration_duration)

        # 1. Real-time Drop Impact (speaker time) - urgent bypass
        is_drop_impact = bool(music is not None and getattr(music, "is_drop_impact", False))
        if is_drop_impact:
            self._drop_buildup_armed = False
            if self.is_in_transition:
                # If buildup explosion was running, snap to explosion climax (progress >= 0.80)
                if self.transition_type == "explosion":
                    if self.transition_progress < 0.80:
                        self.transition_progress = 0.80
                elif not self.locked:
                    self.is_pending = False
                    self.transition_progress = 1.0
                    self.state = "PASSATION"
                    self.last_trigger_reason = "drop_impact"
                    self.pending_transition_config = {"type": "explosion", "duration": 0.4}
                    self.pending_quantize_downbeat = False
                    self.next_change_time = self._clock + self.configuration_duration
                    self.cooldown_remaining = 0.0
                    self.logger.info("(TD) Drop impact interrupted non-explosion transition -> immediate explosion")
                    return True
            elif not self.locked:
                self.is_pending = False
                self.last_trigger_reason = "drop_impact"
                self.pending_transition_config = {"type": "explosion", "duration": 0.4}
                self.pending_quantize_downbeat = False
                self.next_change_time = self._clock + self.configuration_duration
                self.cooldown_remaining = 0.0
                self.logger.info("(TD) Real-time drop impact -> immediate explosion transition")
                return True

        # 2. Song change boundary (countdown reached 0.0 or real-time speaker event)
        if music is not None and getattr(music, "is_song_change", False):
            self._song_change_armed = True
            self.upcoming_song_change_countdown = 0.0

        if self._song_change_armed and self.upcoming_song_change_countdown <= 0.0:
            if not self.locked and not self.is_in_transition and not self.is_pending and self.cooldown_remaining <= 0.0:
                self._song_change_armed = False
                self.is_pending = True
                self.last_trigger_reason = "song_change"
                self.pending_transition_config = None
                self.pending_quantize_downbeat = False
                self.next_change_time = self._clock + self.configuration_duration
                self.logger.info("(TD) Song change boundary arrived at speakers -> triggering transition")
                return True

        # 3. Structural change boundary (countdown reached 0.0 or real-time speaker event)
        if music is not None and getattr(music, "is_verse_chorus_change", False):
            self._structural_change_armed = True
            self.upcoming_structural_change_countdown = 0.0

        if self._structural_change_armed and self.upcoming_structural_change_countdown <= 0.0:
            if not self.locked and not self.is_in_transition and not self.is_pending and self.cooldown_remaining <= 0.0:
                self._structural_change_armed = False
                self.is_pending = True
                self.last_trigger_reason = "structural_change"
                self.pending_transition_config = None
                self.pending_quantize_downbeat = False
                self.next_change_time = self._clock + self.configuration_duration
                self.logger.info("(TD) Structural change boundary arrived at speakers -> triggering transition")
                return True

        # 4. Pre-drop lookahead alignment (Drop predicted via lookahead)
        raw_scene = getattr(music, "scene", "") if music is not None else ""
        scene_str = str(getattr(raw_scene, "value", raw_scene) or "").upper()
        drop_countdown = float(getattr(music, "drop_countdown", 0.0)) if music is not None else 0.0
        is_drop_pred = bool(
            music is not None and (
                drop_countdown > 0.0
                or getattr(music, "is_drop_imminent", False)
                or scene_str == "BUILDUP"
                or getattr(music, "is_buildup", False)
                or getattr(music, "live_is_drop", False)
            )
        )

        if is_drop_pred:
            if not self._drop_buildup_armed and not self.is_in_transition and not self.is_pending and not self.locked and self.cooldown_remaining <= 0.0:
                lookahead = drop_countdown if drop_countdown > 0.0 else max(0.0, float(getattr(music, "lookahead_seconds", 5.0)))
                if lookahead > 0.4:
                    self._drop_buildup_armed = True
                    self.is_pending = True
                    # Explosion blackout ends at progress = 0.80. Setting duration = lookahead / 0.80
                    # ensures the climax/blast detonates exactly when the drop hits the speakers.
                    duration = round(lookahead / 0.80, 2)
                    self.last_trigger_reason = "pre_drop_buildup"
                    self.pending_transition_config = {"type": "explosion", "duration": duration}
                    self.pending_quantize_downbeat = False
                    self.next_change_time = self._clock + self.configuration_duration
                    self.logger.info(
                        f"(TD) Pre-drop lookahead detected! Scheduling buildup duration={duration}s for impact in {lookahead}s"
                    )
                    return True
        elif not is_drop_pred and drop_countdown <= 0.0:
            self._drop_buildup_armed = False

        # 5. Standard transitions based on the internal timer
        if self._clock > self.next_change_time:
            self.next_change_time = self._clock + self.configuration_duration
            if self.locked:
                return False
            # Defer periodic timer if a musical transition is already armed
            if self._song_change_armed or self._structural_change_armed or self._drop_buildup_armed:
                self.logger.info("(TD) Timer Expired but musical transition armed -> deferring timer")
                return False
            if self.is_in_transition or self.is_pending or self.cooldown_remaining > 0.0:
                self.logger.info("(TD) Timer Expired but transition active/pending/cooling -> deferring timer")
                return False
            self.is_pending = True
            self.last_trigger_reason = "timer"
            self.pending_transition_config = None
            self.pending_quantize_downbeat = True
            self.logger.info("(TD) Timer Expired")
            return True

        return False
