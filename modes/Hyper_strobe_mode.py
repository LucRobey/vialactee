"""
Hyper Strobe Mode
Kinetic strobe and pulse effect gated on verified acoustic beats when rhythm-locked,
with smooth fallback to spectral flux peaks and continuous breathing glow when the beat tracker is lost.
Never branches on ctx.scene (eliminating the 1.5s DROP_IMPACT whiteout and fake BUILDUP auto-strobe).
Zero runtime heap allocations.
"""
from typing import List, Dict, Any
import math
import numpy as np
import modes.Mode as Mode


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
        self.pulse_phase: float = 2.0 * math.pi * self.segment_phase_offset

        # Pre-allocated scratch color vectors (ZERO runtime heap allocation)
        self.strobe_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.glow_color: np.ndarray = np.zeros(3, dtype=np.float64)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        mood = self.mood_colors
        effective_decay = float(np.clip(self.decay_ratio / max(0.5, self.mood_trail), 0.02, 0.95))

        band_flux = getattr(self.listener, "band_flux", None)
        flux_val = 0.0
        if band_flux is not None and 0 <= self.listen_band < len(band_flux):
            flux_val = float(band_flux[self.listen_band])

        if ctx is not None:
            if ctx.is_silent:
                self.fade_to_black_segment_vectorized(effective_decay, 0, self.nb_of_leds - 1)
                return

            is_real = bool(ctx.is_real_beat)
            trust = float(ctx.beat_trust)
            energy = float(ctx.energy)
            tension = float(ctx.tension)
            lock = self.rhythm_lock

            # 1. Gate hard strobe flash on verified real beat (or 1-frame drop_hit / strong flux peak)
            beat_trigger = (is_real and (trust > 0.35 or lock > 0.35)) or self.drop_hit
            flux_trigger = flux_val > (self.flux_threshold * (0.45 + 0.55 * lock))
            trigger = beat_trigger or flux_trigger

            if trigger:
                accent_blend = float(np.clip(0.6 * tension + self.mood_accent, 0.0, 1.0))
                hi = self.highlight_color
                beat_tag = str(getattr(self.listener, "beat_tag", "Bass/Kick"))
                if beat_tag == "Snare/Mid":
                    tag_col = mood[1]
                    tag_w = max(0.45, accent_blend)
                elif beat_tag == "Hi-hat/Cymbal":
                    tag_col = mood[2]
                    tag_w = max(0.55, accent_blend)
                else:
                    tag_col = mood[2]
                    tag_w = accent_blend
                for c in range(3):
                    self.strobe_color[c] = (1.0 - tag_w) * float(hi[c]) + tag_w * float(tag_col[c])
                self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, self.strobe_color)
            elif lock < 0.45 and energy > 0.05:
                # 2. When the flywheel is lost, breathe smoothly with acoustic energy so the mode never dies
                self.pulse_phase = (self.pulse_phase + self.dt * 3.0 * self.mood_pace) % (2.0 * math.pi)
                breath = 0.5 + 0.5 * math.sin(self.pulse_phase)
                glow_level = (1.0 - lock) * energy * (0.12 + 0.25 * breath)
                m0 = mood[0]
                for c in range(3):
                    self.glow_color[c] = float(m0[c]) * glow_level
                self.smooth_segment_vectorized(0.35, 0, self.nb_of_leds - 1, self.glow_color)
            else:
                self.fade_to_black_segment_vectorized(effective_decay, 0, self.nb_of_leds - 1)
        else:
            if flux_val > self.flux_threshold:
                self.smooth_segment_vectorized(1.0, 0, self.nb_of_leds - 1, self.highlight_color)
            else:
                self.fade_to_black_segment_vectorized(effective_decay, 0, self.nb_of_leds - 1)
