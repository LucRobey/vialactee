import time
import logging
import random
import json
import os

class Transition_Director:
    def __init__(self, listener, infos):
        self.listener = listener
        self.logger = logging.getLogger("Transition_Director")
        self.silence_threshold = infos.get("silence_threshold", 150)
        self.silence_duration_trigger = infos.get("silence_duration_trigger", 10.0)
        
        self.silence_start_time = None
        self.is_in_standby = False

        # Discover segment geometry
        self.verticals = []
        self.horizontals = []
        self.all_segments = []
        self._load_segments()

    def _load_segments(self):
        """Reads the segments.json config directly to understand the hardware layout."""
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

    def choose_a_local_group(self):
        """Returns a list of segment names selected based on geometric logic."""
        if not self.all_segments:
            return []
            
        ideas = []
        
        # Idea 1: All Verticals
        if self.verticals:
            ideas.append(self.verticals)
            
        # Idea 2: All Horizontals
        if self.horizontals:
            ideas.append(self.horizontals)
            
        # Idea 3: Symmetrical pairs (v1 & v4, or v2 & v3)
        v_outer = [s for s in self.verticals if "v1" in s or "v4" in s]
        v_inner = [s for s in self.verticals if "v2" in s or "v3" in s]
        if v_outer: ideas.append(v_outer)
        if v_inner: ideas.append(v_inner)
        
        # Idea 4: Small random subset (e.g. 2 to 4 random segments)
        random_count = random.randint(2, min(4, len(self.all_segments)))
        random_subset = random.sample(self.all_segments, random_count)
        ideas.append(random_subset)
        
        # Return a randomly selected logic group
        chosen = random.choice(ideas)
        self.logger.debug(f"(TD) Selected Local Group: {chosen}")
        return chosen

    def evaluate_context(self, current_time, next_change_time):
        """
        Analyzes the audio state from the Listener and dictates if we should change modes.
        Returns a tuple: (action_string, transition_config_dict)
        Valid actions: "force_standby", "allow_change", "delay_change", "none"
        """
        is_silence = self.listener.smoothed_total_power < self.silence_threshold
        
        # 1. Evaluate Silence
        if is_silence:
            if self.silence_start_time is None:
                self.silence_start_time = current_time
            elif current_time - self.silence_start_time > self.silence_duration_trigger:
                if not self.is_in_standby:
                    return "force_standby", {"type": "global_change", "duration": 2.0} # Fades out fully
                return "none", None
        else:
            self.silence_start_time = None
            self.is_in_standby = False

        # 2. Evaluate Audio Event Triggers natively mapped
        # if getattr(self.listener, "is_song_change", False):
        #     self.logger.info("(TD) Massive Audio Event: SONG CHANGE DETECTED -> GLOBAL")
        #     chosen_effect = random.choice(["global_change", "radar_scan", "gravity_drop"])
        #     return "allow_change", {"type": chosen_effect, "duration": 4.0}

        # if getattr(self.listener, "is_verse_chorus_change", False):
        #     self.logger.info("(TD) Audio Event: VERSE/CHORUS BOUNDARY DETECTED -> LOCAL")
        #     targeted_segs = self.choose_a_local_group()
        #     return "allow_change", {
        #         "type": "local_change", 
        #         "duration": 2.0,
        #         "segments": targeted_segs
        #     }

        # 3. Evaluate Standard Transitions based on internal timers -> Fallback LOCAL
        if current_time > next_change_time:
            self.logger.info(f"(TD) Timer Expired")
            
            # Temporary override for testing!
            self.logger.info("(TD) TEST OVERRIDE: Forcing spatial global transition via timer!")
            chosen_effect = "explosion"
            return "allow_change", {
                "type": chosen_effect, 
                "duration": 5.0
            }
                
        return "none", None
