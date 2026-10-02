"""
Hyper Strobe Mode
High-energy kinetic strobe effect gated strictly on verified acoustic beats.
Strobe accelerates with drop_progress during BUILDUP and pinches toward center on drop_imminent.
Full bloom explosion on DROP_IMPACT, and gentle sleep/glow during CHILL.
Harmonized with GlobalMoodManager mood_colors with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import numpy as np
import modes.Mode as Mode
import utils.colors as colors


class Hyper_strobe_mode(Mode.Mode):
    def get_settings_schema(self) -> List[Dict[str, Any]]:
        band_count = getattr(self.listener, "nb_of_fft_band", 8) if self.listener is not None else 8
        band_options = [
            {"label": f"Band {band_index + 1}", "value": band_index}
            for band_index in range(band_count)
        ]
        return [
            {
                "key": "fluxThreshold",
                "label": "Trigger Threshold",
                "control": "slider",
                "valueType": "number",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.7,
                "attr": "flux_threshold",
            },
            {
                "key": "decayRatio",
                "label": "Decay",
                "control": "slider",
                "valueType": "number",
                "min": 0.01,
                "max": 1.0,
                "step": 0.05,
                "default": 0.3,
                "attr": "decay_ratio",
            },
            {
                "key": "listenBand",
                "label": "Trigger Band",
                "control": "list",
                "valueType": "number",
                "integer": True,
                "default": 1,
                "options": band_options,
                "attr": "listen_band",
            },
        ]

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.flux_threshold = float(infos.get("strobe_flux_threshold", infos.get("fluxThreshold", 0.7)))
        self.decay_ratio = float(infos.get("strobe_decay_ratio", infos.get("decayRatio", 0.3)))
        self.listen_band = int(infos.get("strobe_listen_band", infos.get("listenBand", 1)))

        # Pre-allocated scratch color vectors (ZERO runtime heap allocation)
        self.strobe_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.glow_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        phase = float(getattr(self.listener, "beat_phase", 0.0))
        is_beat = bool(getattr(self.listener, "is_beat", False))
        mood = self.mood_colors

        if ctx is not None:
            is_real = bool(ctx.is_real_beat)
            trust = float(ctx.beat_trust)
            drop_prog = float(ctx.drop_progress)
            imminent = bool(ctx.is_drop_imminent)
            scene = getattr(ctx, "scene", None)
            is_drop = bool(ctx.is_drop_impact or scene == "DROP_IMPACT")
            is_buildup = bool(scene == "BUILDUP")
            is_chill = bool(scene == "CHILL" or (ctx.is_silent and scene not in ("GROOVE", "BUILDUP", "DROP_IMPACT")))
            energy = float(ctx.energy)
            tension = float(ctx.tension)

            # 1. Full bloom on DROP_IMPACT: pure highlight whiteout across full segment
            if is_drop:
                self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, mood[3])
                return

            # 2. Gate on ctx.is_real_beat and ctx.beat_trust > 0.4
            beat_trigger = is_real and (trust > 0.4)

            # Strobe accelerates with ctx.drop_progress in BUILDUP
            if is_buildup:
                rate = 1.0 + 3.0 * drop_prog
                strobe_active = (phase * rate) % 1.0 < 0.25
                trigger = beat_trigger or strobe_active
            else:
                trigger = beat_trigger

            # 3. Pinch on is_drop_imminent: contract light inward to center, fade outer edges
            if imminent:
                center = self.nb_of_leds // 2
                pinch_width = max(1, int(float(self.nb_of_leds) * 0.15 * max(0.1, 1.0 - drop_prog)))
                start_p = max(0, center - pinch_width)
                end_p = min(self.nb_of_leds - 1, center + pinch_width)
                if start_p > 0:
                    self.fade_to_black_segment_vectorized(1.0, 0, start_p - 1)
                if end_p < self.nb_of_leds - 1:
                    self.fade_to_black_segment_vectorized(1.0, end_p + 1, self.nb_of_leds - 1)

                if trigger:
                    self.smooth_segment_vectorized(1.0, start_p, end_p, mood[3])
                else:
                    self.fade_to_black_segment_vectorized(self.decay_ratio, start_p, end_p)
                return

            # 4. Standard Strobe vs Chill Glow
            if trigger:
                accent_blend = float(np.clip(tension, 0.0, 1.0))
                m3, m2 = mood[3], mood[2]
                self.strobe_color[0] = (1.0 - accent_blend) * float(m3[0]) + accent_blend * float(m2[0])
                self.strobe_color[1] = (1.0 - accent_blend) * float(m3[1]) + accent_blend * float(m2[1])
                self.strobe_color[2] = (1.0 - accent_blend) * float(m3[2]) + accent_blend * float(m2[2])
                self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, self.strobe_color)
            elif is_chill:
                # Sleep/glow in CHILL
                sine_breath = 0.5 * (1.0 + np.sin(2.0 * np.pi * phase))
                glow_level = (0.05 + 0.12 * energy) * (0.6 + 0.4 * sine_breath)
                m0 = mood[0]
                self.glow_color[0] = float(m0[0]) * glow_level
                self.glow_color[1] = float(m0[1]) * glow_level
                self.glow_color[2] = float(m0[2]) * glow_level
                self.smooth_segment_vectorized(0.3, 0, self.nb_of_leds - 1, self.glow_color)
            else:
                self.fade_to_black_segment_vectorized(self.decay_ratio, 0, self.nb_of_leds - 1)
        else:
            # Fallback when ctx is not available
            band_flux = getattr(self.listener, "band_flux", None)
            if band_flux is not None and len(band_flux) > self.listen_band and band_flux[self.listen_band] > self.flux_threshold:
                self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, mood[3])
            else:
                self.fade_to_black_segment_vectorized(self.decay_ratio, 0, self.nb_of_leds - 1)
