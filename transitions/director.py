from typing import Dict, Any, Optional
import logging
import json


class Transition_Director:
    """
    Clock and trigger of the transition sector.

    Tracks the global transition state machine (PASSATION <-> TRANSITION_DUAL and its
    0..1 progress), the live lookahead countdowns, and the auto-transition timer.
    It never commands anyone: update() only reports whether the auto timer expired.
    """

    def __init__(self, infos: Dict[str, Any], segments_path: Optional[str] = None) -> None:
        """
        Initialize the Transition_Director.

        Args:
            infos (dict): Configuration dictionary containing settings like
                silence thresholds.
            segments_path (str, optional): Path of the segments layout file,
                provided by the caller. None leaves the geometry maps empty.
        """
        self.infos = infos
        self.logger = logging.getLogger("Transition_Director")
        self.silence_threshold = infos.get("silence_threshold", 150)
        self.silence_duration_trigger = infos.get("silence_duration_trigger", 10.0)

        self.silence_start_time = None
        self.is_in_standby = False

        self.locked = False
        self.configuration_duration = float(infos.get("auto_transition_time", 20.0))
        self.next_change_time: Optional[float] = None  # armed on the first update()

        self.state = "PASSATION"
        self.transition_progress = 0.0
        self.transition_step = 0.0
        self.transition_type = None

        self.upcoming_song_change_countdown = 0.0
        self.upcoming_structural_change_countdown = 0.0
        self.last_update_time = None

        # Discover segment geometry
        self.verticals = []
        self.horizontals = []
        self.all_segments = []
        self.segments_path = segments_path
        self._load_segments()

    def _load_segments(self) -> None:
        """
        Read the segments configuration to understand the hardware layout.

        Parses the active segments file to classify available segments into
        vertical and horizontal groups for geometric-based logic.
        """
        if self.segments_path is None:
            return
        try:
            config_path = self.segments_path
            with open(config_path, "r") as f:
                data = json.load(f)
                if isinstance(data.get("segments"), list):
                    segment_lists = [data["segments"]]
                else:
                    segment_lists = [value for value in data.values() if isinstance(value, list)]

                for segment_list in segment_lists:
                    for seg in segment_list:
                        if not isinstance(seg, dict) or "name" not in seg:
                            continue
                        name = seg["name"]
                        self.all_segments.append(name)
                        if seg.get("orientation") == "vertical":
                            self.verticals.append(name)
                        else:
                            self.horizontals.append(name)
            self.logger.info(f"(TD) Instantiated geometry maps: {len(self.verticals)} Verticals, {len(self.horizontals)} Horizontals")
        except Exception as e:
            self.logger.error(f"(TD) Failed to load segments configuration: {e}")

    @property
    def is_in_transition(self) -> bool:
        """True if currently interpolating between dual mode buffers."""
        return self.state == "TRANSITION_DUAL"

    def start_transition(self, transition_config: Optional[Dict[str, Any]]) -> None:
        """ Start tracking a new global transition. """
        if transition_config is None:
            return
        self.state = "TRANSITION_DUAL"
        self.transition_progress = 0.0
        self.transition_type = transition_config["type"]
        duration = float(transition_config.get("duration", 2.0))
        self.transition_duration = duration
        self.transition_step = (1.0 / 30.0) / duration if duration > 0 else 1.0

    def cancel_transition(self) -> None:
        """ Abort a transition that no segment accepted: back to idle. """
        self.state = "PASSATION"
        self.transition_progress = 0.0

    def update(self, current_time: float, music: Optional[Any] = None) -> bool:
        """
        Advance the global transition progress and the countdowns.

        Args:
            current_time (float): Monotonic clock of the sector, in seconds.
            music: Optional MusicSnapshot, read for the live lookahead events.

        Returns:
            True when the auto-transition timer expired and the director is not
            locked (the caller should then schedule a transition).
        """
        if self.next_change_time is None:
            self.next_change_time = current_time + self.configuration_duration

        if self.last_update_time is None:
            dt = 1.0 / 30.0
        else:
            dt = max(0.0, current_time - self.last_update_time)
        self.last_update_time = current_time

        self.upcoming_song_change_countdown = max(0.0, self.upcoming_song_change_countdown - dt)
        self.upcoming_structural_change_countdown = max(0.0, self.upcoming_structural_change_countdown - dt)

        # Lookahead: Check live audio feed for incoming events 5 seconds before they render
        if music is not None:
            lookahead = getattr(music, "lookahead_seconds", 5.0)
            if getattr(music, "live_is_song_change", False):
                self.upcoming_song_change_countdown = lookahead
                self.logger.info(f"(TD) Live Song Change detected! Visual impact in {lookahead}s.")

            if getattr(music, "live_is_verse_chorus_change", False):
                self.upcoming_structural_change_countdown = lookahead
                self.logger.info(f"(TD) Live Structural Change detected! Visual impact in {lookahead}s.")

        if self.state == "TRANSITION_DUAL":
            duration = getattr(self, "transition_duration", 2.0)
            step = (dt / duration) if duration > 0 else 1.0
            self.transition_progress += step
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                self.state = "PASSATION"

        # 2. Evaluate Audio Event Triggers natively mapped
        # if getattr(self.listener, "is_song_change", False):
        #     self.logger.info("(TD) Massive Audio Event: SONG CHANGE DETECTED -> GLOBAL")
        #     chosen_effect = random.choice(["global_change", "radar_scan", "gravity_drop"])
        #     await self.mode_master.change_configuration({"type": chosen_effect, "duration": 4.0})
        #     self.next_change_time = current_time + self.configuration_duration

        # 3. Standard transitions based on the internal timer
        if current_time > self.next_change_time:
            self.next_change_time = current_time + self.configuration_duration
            if self.locked:
                return False
            self.logger.info("(TD) Timer Expired")
            return True
        return False
