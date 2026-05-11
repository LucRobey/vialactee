from typing import Dict, Any, Optional
import time
import logging
import random
import json
import os

class Transition_Director:
    """
    Directs transitions between visual modes based on audio context and timers.
    
    This class evaluates the current audio state (via the Listener) and geometry 
    to decide when and how to transition between different display modes.
    """

    def __init__(self, mode_master: Any, listener: Any, infos: Dict[str, Any]) -> None:
        """
        Initialize the Transition_Director.

        Args:
            mode_master: The orchestrator to command for transitions.
            listener: The listener object providing audio analysis data.
            infos (dict): Configuration dictionary containing settings like 
                silence thresholds.
        """
        self.mode_master = mode_master
        self.listener = listener
        self.logger = logging.getLogger("Transition_Director")
        self.silence_threshold = infos.get("silence_threshold", 150)
        self.silence_duration_trigger = infos.get("silence_duration_trigger", 10.0)
        
        self.silence_start_time = None
        self.is_in_standby = False

        self.configuration_duration = 20.0
        self.next_change_time = time.time() + self.configuration_duration

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
        self._load_segments()

    def _load_segments(self) -> None:
        """
        Read the segments configuration to understand the hardware layout.

        Parses the segments.json file to classify available segments into 
        vertical and horizontal groups for geometric-based logic.
        """
        try:
            config_path = os.path.join(os.path.dirname(__file__), "..", "config", "segments.json")
            with open(config_path, "r") as f:
                data = json.load(f)
                if isinstance(data.get("segments"), list):
                    segment_lists = [data["segments"]]
                else:
                    segment_lists = [value for value in data.values() if isinstance(value, list)]

                for segment_list in segment_lists:
                    for seg in segment_list:
                        name = seg["name"]
                        self.all_segments.append(name)
                        if seg.get("orientation") == "vertical":
                            self.verticals.append(name)
                        else:
                            self.horizontals.append(name)
            self.logger.info(f"(TD) Instantiated geometry maps: {len(self.verticals)} Verticals, {len(self.horizontals)} Horizontals")
        except Exception as e:
            self.logger.error(f"(TD) Failed to load segments.json: {e}")

    def start_transition(self, transition_config: Optional[Dict[str, Any]]) -> None:
        """ Start tracking a new global transition. """
        if transition_config is None:
            return
        self.state = "TRANSITION_DUAL"
        self.transition_progress = 0.0
        self.transition_type = transition_config["type"]
        duration = transition_config.get("duration", 2.0)
        if duration > 0:
            self.transition_step = (1.0 / 30.0) / duration
        else:
            self.transition_step = 1.0

    async def update(self, current_time: float) -> None:
        """
        Advance the global transition progress and analyze audio context.
        If a transition is needed, it directly commands the mode_master.
        
        Args:
            current_time (float): The current system time.
        """
        if self.last_update_time is None:
            self.last_update_time = current_time
        dt = current_time - self.last_update_time
        self.last_update_time = current_time
        
        self.upcoming_song_change_countdown = max(0.0, self.upcoming_song_change_countdown - dt)
        self.upcoming_structural_change_countdown = max(0.0, self.upcoming_structural_change_countdown - dt)

        # Lookahead: Check live audio feed for incoming events 5 seconds before they render
        if getattr(self.listener, "live_is_song_change", False):
            lookahead = getattr(self.listener.analyzer, 'lookahead_seconds', 5.0) if hasattr(self.listener, 'analyzer') else 5.0
            self.upcoming_song_change_countdown = lookahead
            self.logger.info(f"(TD) Live Song Change detected! Visual impact in {lookahead}s.")

        if getattr(self.listener, "live_is_verse_chorus_change", False):
            lookahead = getattr(self.listener.analyzer, 'lookahead_seconds', 5.0) if hasattr(self.listener, 'analyzer') else 5.0
            self.upcoming_structural_change_countdown = lookahead
            self.logger.info(f"(TD) Live Structural Change detected! Visual impact in {lookahead}s.")

        if self.state == "TRANSITION_DUAL":
            self.transition_progress += self.transition_step
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                self.state = "PASSATION"

        # 2. Evaluate Audio Event Triggers natively mapped
        # if getattr(self.listener, "is_song_change", False):
        #     self.logger.info("(TD) Massive Audio Event: SONG CHANGE DETECTED -> GLOBAL")
        #     chosen_effect = random.choice(["global_change", "radar_scan", "gravity_drop"])
        #     await self.mode_master.change_configuration({"type": chosen_effect, "duration": 4.0})
        #     self.next_change_time = current_time + self.configuration_duration

        # 3. Evaluate Standard Transitions based on internal timers -> Fallback LOCAL
        if current_time > self.next_change_time:
            self.logger.info(f"(TD) Timer Expired")
            
            # Temporary override for testing!
            self.logger.info("(TD) TEST OVERRIDE: Forcing spatial global transition via timer!")
            chosen_effect = "explosion"
            transition_config = {
                "type": chosen_effect, 
                "duration": 4.0
            }
            await self.mode_master.change_configuration(transition_config)
            self.next_change_time = current_time + self.configuration_duration
