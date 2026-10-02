"""
Matrix Rain Mode
Classic digital rain effect designed for vertical chandelier strips.
Spawns raindrops on ctx.is_syncopated or verified transient hits.
Fall velocity scaled to listener.bpm. Freezes on is_drop_imminent and flashes on DROP_IMPACT.
Harmonized with GlobalMoodManager mood_colors with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode


class Matrix_rain_mode(Mode.Mode):
    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.flux_threshold: float = float(infos.get("rain_flux_threshold", 0.5))
        self.fade_ratio: float = float(infos.get("rain_fade_ratio", 0.15))
        self.listen_band: int = int(infos.get("rain_listen_band", -1))
        self.sub_step: float = 0.0

        # Pre-allocated scratch color vector (ZERO runtime heap allocation)
        self.drop_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        dt = getattr(self.listener, "dt", 1.0 / 60.0)
        fps_ratio = dt * 60.0
        bpm = max(60.0, min(200.0, float(getattr(self.listener, "bpm", 120.0))))
        mood = self.mood_colors

        scene = getattr(ctx, "scene", None)
        drop_prog = float(getattr(ctx, "drop_progress", 0.0))
        is_imminent = bool(ctx.is_drop_imminent if ctx is not None else False)
        is_drop = bool(ctx.is_drop_impact if ctx is not None else False) or scene == "DROP_IMPACT"
        is_sync = bool(ctx.is_syncopated if ctx is not None else False)
        is_real = bool(ctx.is_real_beat if ctx is not None else getattr(self.listener, "is_real_beat", False))
        is_beat = bool(getattr(self.listener, "is_beat", False))

        # 1. Flash on DROP_IMPACT: pure highlight whiteout across full segment
        if is_drop:
            self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, mood[3])
            return

        # 2. Fall velocity scaled to listener.bpm (Freeze on is_drop_imminent)
        if not is_imminent:
            speed = (bpm / 120.0) * fps_ratio
            self.sub_step += speed
            while self.sub_step >= 1.0:
                if self.nb_of_leds > 1:
                    self.rgb_list[1:] = self.rgb_list[:-1]
                    self.rgb_list[0] = 0
                self.sub_step -= 1.0

        # 3. Decay the entire strip proportionally to create falling tails
        self.fade_to_black_segment_vectorized(self.fade_ratio, 0, self.nb_of_leds - 1)

        # 4. Check for transient hits or syncopation to spawn new raindrops
        band_flux = getattr(self.listener, "band_flux", None)
        flux_hit = False
        if band_flux is not None and len(band_flux) > 0:
            listen_idx = self.listen_band if (0 <= self.listen_band < len(band_flux)) else (len(band_flux) - 1)
            flux_hit = bool(band_flux[listen_idx] > self.flux_threshold)

        transient_hit = (is_beat and is_real) or flux_hit
        should_spawn = (is_sync or transient_hit) and not is_imminent

        if should_spawn:
            if is_sync:
                self.drop_color[:] = mood[2]  # Neon accent on syncopation
            elif is_real:
                self.drop_color[:] = mood[3]  # Highlight on verified acoustic beat
            else:
                self.drop_color[:] = mood[0]  # Primary rain color

            self.smooth_segment_vectorized(1.0, 0, 0, self.drop_color)
