"""
StructuralNoveltyDetector.py - Structural Music Event & Novelty Detection Engine.

Autonomously identifies Verse/Chorus boundaries, Seamless Crossfades, Hard Song Cuts,
and Silence Drops using Short-Term Memory (STM) vs Long-Term Memory (LTM) tension
wrapped in asserved self-adjusting mathematical envelopes.
"""

from typing import List, Optional
import numpy as np

from core.RhythmConfig import RhythmConfig


class StructuralNoveltyDetector:
    """
    Tracks timbral and energetic novelty across time, maintaining self-adjusting
    envelopes (Local Max & Global Max) to trigger structural musical events.
    """

    def __init__(self, nb_fft_bands: int = 8, config: Optional[RhythmConfig] = None) -> None:
        self.nb_fft_bands = nb_fft_bands
        self.config = config if config is not None else RhythmConfig()

        # Short-Term and Long-Term Memory (STM / LTM)
        self.stm_timbre = np.zeros(self.nb_fft_bands)
        self.ltm_timbre = np.zeros(self.nb_fft_bands)
        self.stm_power = 0.0
        self.ltm_power = 0.0

        # Asserved Envelopes
        self.novelty_lm = 0.5
        self.novelty_gm = 0.5
        self.asserved_novelty = 0.0
        self.combined_novelty = 0.0

        # Event History & Cooldowns
        self.song_changes_times: List[float] = []
        self.structural_changes_times: List[float] = []
        self.last_structural_change_time = 0.0

        # Silence Detection
        self.silence_frames = 0
        self.silence_threshold_frames = int(self.config.silence_threshold_seconds * 60)

        # Output Triggers (1-frame pulses)
        self.is_verse_chorus_change = False
        self.is_song_change = False

    def update(
        self,
        current_timbre: np.ndarray,
        current_power: float,
        current_time: float,
        dt: float,
        fps_ratio: float
    ) -> None:
        """
        Processes instantaneous timbre and power to update memory envelopes
        and detect structural events.
        """
        # 1. Reset per-frame triggers
        self.is_verse_chorus_change = False
        self.is_song_change = False

        # 2. Update Short-Term and Long-Term Memory (STM/LTM)
        stm_retention = self.config.stm_retention_base ** fps_ratio
        ltm_retention = self.config.ltm_retention_base ** fps_ratio

        self.stm_timbre = stm_retention * self.stm_timbre + (1 - stm_retention) * current_timbre
        self.ltm_timbre = ltm_retention * self.ltm_timbre + (1 - ltm_retention) * current_timbre

        self.stm_power = stm_retention * self.stm_power + (1 - stm_retention) * current_power
        self.ltm_power = ltm_retention * self.ltm_power + (1 - ltm_retention) * current_power

        # 3. Calculate Distance / Novelty Metrics
        timbral_novelty = float(np.linalg.norm(self.stm_timbre - self.ltm_timbre))
        power_novelty = float(np.abs(self.stm_power - self.ltm_power) / (self.ltm_power + 1.0))
        self.combined_novelty = timbral_novelty + (power_novelty * self.config.power_novelty_weight)

        # 4. Asserved Envelope Tracking
        if self.combined_novelty >= self.novelty_lm:
            self.novelty_lm = self.combined_novelty
        else:
            self.novelty_lm = max(
                self.config.novelty_lm_floor,
                self.novelty_lm * (self.config.novelty_lm_decay ** fps_ratio)
            )

        passed_gm = self.combined_novelty > self.novelty_gm
        if self.combined_novelty >= self.novelty_gm:
            self.novelty_gm = 1.01 * self.combined_novelty
        else:
            self.novelty_gm *= 1 + (0.005 * fps_ratio) * (
                (self.novelty_lm / max(0.001, self.novelty_gm)) - 0.9
            )

        safe_gm = max(0.01, self.novelty_gm)
        target_asserved = self.combined_novelty / safe_gm
        self.asserved_novelty += min(1.0, 0.4 * fps_ratio) * (target_asserved - self.asserved_novelty)

        # 5. Event Classification
        # A. Seamless Crossfade / Song Drop
        if self.asserved_novelty > self.config.song_novelty_asserved_th:
            if (
                len(self.song_changes_times) == 0
                or (current_time - self.song_changes_times[-1]) > self.config.structural_cooldown_seconds
            ):
                self.song_changes_times.append(current_time)
                self.is_song_change = True
                self.novelty_gm = self.combined_novelty * self.config.gm_shock_multiplier
                self.asserved_novelty = 0.0
                self.ltm_timbre = np.copy(self.stm_timbre)
                self.ltm_power = self.stm_power

        # B. Verse / Chorus Boundary
        elif passed_gm:
            if (current_time - self.last_structural_change_time) > self.config.structural_cooldown_seconds:
                self.structural_changes_times.append(current_time)
                self.last_structural_change_time = current_time
                self.is_verse_chorus_change = True
                self.asserved_novelty = 0.0
                self.ltm_timbre = np.copy(self.stm_timbre)
                self.ltm_power = self.stm_power

        # C. Silence Drop
        if current_power < self.config.silence_power_threshold:
            self.silence_frames += 1
        else:
            self.silence_frames = 0

        if self.silence_frames > self.silence_threshold_frames:
            if (
                len(self.song_changes_times) == 0
                or (current_time - self.song_changes_times[-1]) > self.config.silence_cooldown_seconds
            ):
                self.song_changes_times.append(current_time)
                self.is_song_change = True
                self.silence_frames = 0
