"""
Base Mode Class
Defines the core interface and execution lifecycle for all visual animation modes.
Provides standardized buffer rendering, vectorized color conversions, smoothing, and fading utilities.
Manages dynamic settings schemas and catalogs exposed to the React web interface.
Subclasses implement render() or run() to generate 30 FPS LED visualizations.
"""
import utils.rgb_hsv as RGB_HSV
import math
import time
import zlib
import numpy as np
from typing import List, Dict, Any, Tuple, Union, Optional
import logging

ModeSettingValue = Union[str, int, float, bool]

# Resolution of the shared 3-colour palette gradient (see Mode.palette_lut).
PALETTE_LUT_SIZE = 256

# Fallback palette (Cyberpunk) for modes used without Mode_master, e.g. in tests.
_FALLBACK_MOOD_COLORS = np.array(
    [(0, 240, 255), (255, 0, 128), (60, 0, 180), (0, 100, 255)], dtype=np.int32
)
_FALLBACK_MOOD_COLORS.flags.writeable = False

# Fallback scene modifiers (GROOVE neutral: pace=1, sharpness=1, trail=1, accent_mix=0)
_FALLBACK_MOOD_MODIFIERS = np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32)
_FALLBACK_MOOD_MODIFIERS.flags.writeable = False

class Mode:
    listener = None
    white = (255, 255, 255)
    _mood_colors: np.ndarray = _FALLBACK_MOOD_COLORS
    _mood_modifiers: np.ndarray = _FALLBACK_MOOD_MODIFIERS

    @classmethod
    def bind_mood_colors(cls, colors: np.ndarray) -> None:
        """Bind the live (4, 3) int32 mood colour view, shared by every mode."""
        Mode._mood_colors = colors

    @classmethod
    def reset_mood_colors(cls) -> None:
        """Testing utility: restore the static fallback palette."""
        Mode._mood_colors = _FALLBACK_MOOD_COLORS
        Mode._mood_modifiers = _FALLBACK_MOOD_MODIFIERS

    @classmethod
    def bind_mood_modifiers(cls, modifiers: np.ndarray) -> None:
        """Bind the live (4,) float32 mood modifier view, shared by every mode."""
        Mode._mood_modifiers = modifiers

    @classmethod
    def reset_mood_modifiers(cls) -> None:
        """Testing utility: restore the static neutral fallback modifiers."""
        Mode._mood_modifiers = _FALLBACK_MOOD_MODIFIERS

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        self.name = name
        self.segment_name = segment_name
        self.infos = infos
        self.logger = logging.getLogger(f"Mode.{self.name}")
        if self.listener is None:
            self.listener = listener
        self.rgb_list = rgb_list
        self.leds = leds
        self.indexes = indexes
        self.nb_of_leds = len(indexes)
        self.isActiv = False
        self.has_custom_transition = False
        self._exit_progress: float = 0.0
        self._enter_progress: float = 1.0

        # Stable [0, 1) offset derived from the segment name: lets identical modes on
        # different segments stagger their phase (travelling effects across the chandelier).
        self.segment_phase_offset: float = (zlib.crc32(str(segment_name).encode("utf-8")) % 1000) / 1000.0

        # Scratch buffers so the shared blenders never allocate per frame.
        n = max(1, self.nb_of_leds)
        self._scratch_rgb = np.zeros((n, 3), dtype=np.float64)
        self._scratch_color = np.zeros(3, dtype=np.float64)
        self._sample_f = np.zeros(n + 1, dtype=np.float64)
        self._sample_idx = np.zeros(n + 1, dtype=np.intp)

        # Shared palette gradient (primary -> secondary -> accent), refreshed in place.
        self._palette_lut = np.zeros((PALETTE_LUT_SIZE, 3), dtype=np.int32)
        self._palette_src = np.full((3, 3), -1, dtype=np.int32)
        _t = np.linspace(0.0, 1.0, PALETTE_LUT_SIZE)
        self._lut_a = np.clip(_t * 2.0, 0.0, 1.0)[:, None]
        self._lut_b = np.clip(_t * 2.0 - 1.0, 0.0, 1.0)[:, None]
        self._lut_f = np.zeros((PALETTE_LUT_SIZE, 3), dtype=np.float64)
        self._lut_tmp = np.zeros((PALETTE_LUT_SIZE, 3), dtype=np.float64)
        self._highlight = np.zeros(3, dtype=np.int32)

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return []

    def get_settings_catalog(self) -> Dict[str, Any]:
        schema = self.get_settings_schema()
        if len(schema) == 0:
            return {}

        return {
            "mode": self.name,
            "label": self.name,
            "settings": [self._public_setting_descriptor(descriptor) for descriptor in schema],
        }

    def export_settings(self) -> Dict[str, ModeSettingValue]:
        exported: Dict[str, ModeSettingValue] = {}
        for descriptor in self.get_settings_schema():
            key = descriptor.get("key")
            if not isinstance(key, str):
                continue

            attr_name = self._setting_attr_name(descriptor)
            current_value = getattr(self, attr_name, descriptor.get("default"))
            normalized_value, ok = self.normalize_setting_value(descriptor, current_value)
            if ok:
                exported[key] = normalized_value
            elif "default" in descriptor:
                exported[key] = descriptor["default"]
        return exported

    def apply_settings(self, settings: Dict[str, Any]) -> Dict[str, ModeSettingValue]:
        if not isinstance(settings, dict):
            return {}

        descriptors_by_key: Dict[str, Dict[str, Any]] = {}
        for descriptor in self.get_settings_schema():
            key = descriptor.get("key")
            if isinstance(key, str):
                descriptors_by_key[key] = descriptor

        applied: Dict[str, ModeSettingValue] = {}
        for key, raw_value in settings.items():
            descriptor = descriptors_by_key.get(key)
            if descriptor is None:
                continue

            normalized_value, ok = self.normalize_setting_value(descriptor, raw_value)
            if not ok:
                continue

            setattr(self, self._setting_attr_name(descriptor), normalized_value)
            applied[key] = normalized_value

        if len(applied) > 0:
            self.on_settings_applied(applied)

        return applied

    def on_settings_applied(self, applied_settings: Dict[str, ModeSettingValue]) -> None:
        return None

    @staticmethod
    def normalize_setting_value(descriptor: Dict[str, Any], value: Any) -> Tuple[ModeSettingValue, bool]:
        value_type = descriptor.get("valueType")

        if value_type == "boolean":
            if not isinstance(value, bool):
                return False, False
            normalized_value: ModeSettingValue = value
        elif value_type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return 0.0, False
            normalized_number = float(value)
            min_value = descriptor.get("min")
            max_value = descriptor.get("max")
            if isinstance(min_value, (int, float)):
                normalized_number = max(float(min_value), normalized_number)
            if isinstance(max_value, (int, float)):
                normalized_number = min(float(max_value), normalized_number)
            if descriptor.get("integer", False):
                normalized_value = int(round(normalized_number))
            else:
                normalized_value = normalized_number
        else:
            if not isinstance(value, str):
                return "", False
            normalized_value = value

        options = descriptor.get("options")
        if isinstance(options, list) and len(options) > 0:
            allowed_values = [
                option.get("value")
                for option in options
                if isinstance(option, dict) and "value" in option
            ]
            if len(allowed_values) > 0 and normalized_value not in allowed_values:
                return normalized_value, False

        return normalized_value, True

    def _public_setting_descriptor(self, descriptor: Dict[str, Any]) -> Dict[str, Any]:
        public_descriptor = {}
        for key, value in descriptor.items():
            if key != "attr":
                public_descriptor[key] = value

        if "default" in public_descriptor:
            normalized_default, ok = self.normalize_setting_value(descriptor, public_descriptor["default"])
            if ok:
                public_descriptor["default"] = normalized_default

        return public_descriptor

    def _setting_attr_name(self, descriptor: Dict[str, Any]) -> str:
        attr_name = descriptor.get("attr")
        if isinstance(attr_name, str) and len(attr_name) > 0:
            return attr_name
        return str(descriptor.get("key", ""))


    def smooth(self, ratio_new: float, led_index: int, new_color: List[int]):
        target = np.array(new_color)
        view = self.rgb_list[led_index:led_index+1]
        np.multiply(view, 1.0 - ratio_new, out=view, casting='unsafe')
        np.add(view, target * ratio_new, out=view, casting='unsafe')

    def _blend_into(self, view: np.ndarray, ratio_new: float, target) -> None:
        """view = view * (1 - ratio_new) + target * ratio_new, using scratch (no per-frame allocation).

        `target` may be a colour tuple/(3,) array broadcast over `view`, or an (k, 3) matrix matching it.
        During cooperative mode transitions, `target` is scaled by `self.transition_scale`.
        """
        np.multiply(view, 1.0 - ratio_new, out=view, casting='unsafe')
        eff_ratio = (
            ratio_new * self.transition_scale
            if (self._exit_progress > 0.0 or self._enter_progress < 1.0)
            else ratio_new
        )
        if isinstance(target, np.ndarray):
            if target.ndim == 1 and target.shape[0] == 3:
                scaled = self._scratch_color
                np.multiply(target, eff_ratio, out=scaled)
            elif target.ndim == 2 and target.shape[1] == 3 and target.shape[0] <= self._scratch_rgb.shape[0]:
                scaled = self._scratch_rgb[:target.shape[0]]
                np.multiply(target, eff_ratio, out=scaled)
            else:
                scaled = target * eff_ratio
        else:
            if len(target) == 3 and not hasattr(target[0], "__len__"):
                scaled = self._scratch_color
                scaled[:] = target
                np.multiply(scaled, eff_ratio, out=scaled)
            else:
                scaled = np.asarray(target) * eff_ratio
        np.add(view, scaled, out=view, casting='unsafe')

    def smooth_vectorized(self, ratio_new: float, target_rgb_matrix: np.ndarray):
        """
        Vectorized smoothing running entirely in numpy.
        Blends the new colors with the internal rgb_list correctly avoiding hardware-dimming bugs.
        """
        self._blend_into(self.rgb_list, ratio_new, target_rgb_matrix)

    def smooth_segment(self, ratio_new: float, start_index: int, stop_index: int, new_color):
        self.smooth_segment_vectorized(ratio_new, start_index, stop_index, new_color)

    def fade_to_black(self, ratio_black: float):
        if self._exit_progress > 0.0:
            ratio_black = min(1.0, ratio_black + (1.0 - ratio_black) * (self._exit_progress * self._exit_progress) * 0.45)
        np.multiply(self.rgb_list, 1.0 - ratio_black, out=self.rgb_list, casting='unsafe')

    def fade_to_black_led(self, ratio_black: float, led_index: int):
        view = self.rgb_list[led_index:led_index+1]
        np.multiply(view, 1.0 - ratio_black, out=view, casting='unsafe')

    def fade_to_black_segment(self, ratio_black: float, start_index: int, stop_index: int):
        self.fade_to_black_segment_vectorized(ratio_black, start_index, stop_index)

    def smooth_segment_vectorized(self, ratio_new: float, start_index: int, stop_index: int, new_color):
        if start_index <= stop_index and start_index >= 0 and stop_index < self.nb_of_leds:
            self._blend_into(self.rgb_list[start_index:stop_index+1], ratio_new, new_color)
            
    def fade_to_black_segment_vectorized(self, ratio_black: float, start_index: int, stop_index: int):
        if start_index <= stop_index and start_index >= 0 and stop_index < self.nb_of_leds:
            if self._exit_progress > 0.0:
                ratio_black = min(1.0, ratio_black + (1.0 - ratio_black) * (self._exit_progress * self._exit_progress) * 0.45)
            view = self.rgb_list[start_index:stop_index+1]
            np.multiply(view, 1.0 - ratio_black, out=view, casting='unsafe')

    def fill(self, color):
        self.rgb_list[:] = color

    # ------------------------------------------------------------------
    # Shared authoring helpers (see docs/contracts/mode_contract.md)
    # ------------------------------------------------------------------

    @property
    def drop_hit(self) -> bool:
        """True for exactly ONE frame when a drop lands. Use this to spawn/trigger things."""
        ctx = getattr(self.listener, "context", None)
        return bool(ctx.is_drop_impact) if ctx is not None else False

    @property
    def drop_decay(self) -> float:
        """Envelope 1.0 -> 0.0 across the DROP_IMPACT dwell (0.0 outside a drop). Use this to animate."""
        ctx = getattr(self.listener, "context", None)
        if ctx is None:
            return 0.0
        if ctx.is_drop_impact or ctx.scene == "DROP_IMPACT":
            return max(0.0, min(1.0, float(ctx.drop_progress)))
        return 0.0

    @property
    def dt(self) -> float:
        """Seconds since the previous frame (falls back to 1/60 when unavailable)."""
        try:
            value = float(getattr(self.listener, "dt", 1.0 / 60.0))
        except (TypeError, ValueError):
            return 1.0 / 60.0
        return value if value > 0.0 else 1.0 / 60.0

    @property
    def fps_ratio(self) -> float:
        """Frame duration relative to 60 FPS (1.0 at 60 FPS, 2.0 at 30 FPS)."""
        return self.dt * 60.0

    def alpha(self, rate_hz: float) -> float:
        """Frame-rate independent smoothing ratio: 1 - exp(-dt * rate_hz). Replaces fixed per-frame ratios."""
        return 1.0 - math.exp(-self.dt * max(0.0, rate_hz))

    @property
    def palette_lut(self) -> np.ndarray:
        """(256, 3) int32 gradient primary -> secondary -> accent, refreshed in place when the mood changes.

        Treat as read-only. Colour many LEDs at once without per-channel loops:
            idx = (t * 255).astype(np.intp);  np.take(self.palette_lut, idx, axis=0, out=rgb, mode='clip')
        or use `palette_sample`.
        """
        mood = self.mood_colors
        if not np.array_equal(self._palette_src, mood[:3]):
            self._palette_src[:] = mood[:3]
            c0, d01, d12 = mood[0], mood[1] - mood[0], mood[2] - mood[1]
            np.multiply(self._lut_a, d01, out=self._lut_f)
            np.add(self._lut_f, c0, out=self._lut_f)
            np.multiply(self._lut_b, d12, out=self._lut_tmp)
            np.add(self._lut_f, self._lut_tmp, out=self._lut_f)
            np.clip(self._lut_f, 0.0, 255.0, out=self._lut_f)
            self._palette_lut[:] = self._lut_f
        return self._palette_lut

    def palette_sample(self, t: np.ndarray, out: np.ndarray) -> np.ndarray:
        """out[i] = palette colour at t[i] in [0, 1] (len(t) <= nb_of_leds + 1). Allocation-free."""
        n = t.shape[0]
        scratch = self._sample_f[:n]
        np.multiply(t, PALETTE_LUT_SIZE - 1, out=scratch)
        np.clip(scratch, 0.0, PALETTE_LUT_SIZE - 1, out=scratch)
        idx = self._sample_idx[:n]
        idx[:] = scratch
        np.take(self.palette_lut, idx, axis=0, out=out, mode='clip')
        return out

    @property
    def highlight_color(self) -> np.ndarray:
        """Luminance-safe 'flash' colour: the brightest palette slot pushed 40% toward white.

        Palette slot 3 is documented as Background/Highlight and is dark on some palettes
        (e.g. Deep Ocean), so a flash built from it can be dimmer than the normal state.
        Returns a (3,) int32 array valid until the next call.
        """
        mood = self.mood_colors
        best = 0
        best_lum = -1.0
        for i in range(mood.shape[0]):
            lum = 0.2126 * float(mood[i, 0]) + 0.7152 * float(mood[i, 1]) + 0.0722 * float(mood[i, 2])
            if lum > best_lum:
                best_lum, best = lum, i
        for c in range(3):
            self._highlight[c] = int(mood[best, c] + 0.4 * (255.0 - float(mood[best, c])))
        return self._highlight

    def beat_pulse(self, sharpness: float = 2.2) -> float:
        """Confidence-blended beat envelope in [0, 1] (docs/contracts/mode_contract.md, shared).

        Locked tempo -> punchy `(1 - phase) ** k` pump; lost tempo -> smooth acoustic breathing from
        energy. Tension sharpens the decay. Silence returns 0. Gate hard flashes separately on is_real_beat.
        """
        listener = self.listener
        ctx = getattr(listener, "context", None)
        phase = float(getattr(listener, "beat_phase", 0.0))
        if ctx is not None:
            energy = float(getattr(ctx, "energy", 0.0))
            confidence = float(getattr(ctx, "beat_trust", getattr(listener, "beat_confidence", 0.0)))
            tension = float(getattr(ctx, "tension", 0.0))
            silent = bool(getattr(ctx, "is_silent", False))
        else:
            energy = float(getattr(listener, "asserved_total_power", 0.0))
            confidence = float(getattr(listener, "beat_confidence", 0.0))
            tension = 0.0
            silent = False
        if silent:
            return 0.0
        confidence = max(0.0, min(1.0, confidence))
        effective_sharpness = sharpness * self.mood_sharpness + 1.2 * tension
        rhythmic = max(0.0, 1.0 - phase) ** effective_sharpness
        breath = 0.5 * (1.0 + math.sin(2.0 * math.pi * phase - 0.5 * math.pi))
        acoustic = energy * (0.6 + 0.4 * breath)
        return max(0.0, min(1.0, confidence * rhythmic + (1.0 - confidence) * acoustic))


    def terminate(self):
        self.isActiv = False
        self._exit_progress = 0.0
        self._enter_progress = 1.0
        self.logger.debug("  on désactive le "+self.name+" du "+self.segment_name)

    def start(self):
        self.isActiv = True
        self._exit_progress = 0.0
        self._enter_progress = 1.0
        self.logger.debug("  on active le "+self.name+" du "+self.segment_name)

    def render(self, buffer: Optional[np.ndarray] = None, audio_ctx: Any = None, frame_info: Any = None) -> None:
        """
        Unified rendering interface for visual modes.
        If a buffer is supplied, self.rgb_list is temporarily redirected to it.
        Calls self.run() for backward compatibility with existing modes.
        """
        old_buffer = self.rgb_list
        if buffer is not None:
            self.rgb_list = buffer
        try:
            self.run()
        finally:
            if buffer is not None:
                self.rgb_list = old_buffer

    def update(self) -> None:
        self.render()

    def run(self) -> None:
        pass

    @property
    def mood_colors(self) -> np.ndarray:
        """
        Global curated palette colors provided by the mood sector (bound via bind_mood_colors).
        Shape: (4, 3) np.ndarray of dtype np.int32, read-only.
        """
        return Mode._mood_colors

    @property
    def mood_modifiers(self) -> np.ndarray:
        """Read-only (4,) float32 cosine-smoothed scene modifiers [pace, sharpness, trail, accent_mix]."""
        return Mode._mood_modifiers

    @property
    def mood_pace(self) -> float:
        return float(Mode._mood_modifiers[0])

    @property
    def mood_sharpness(self) -> float:
        return float(Mode._mood_modifiers[1])

    @property
    def mood_trail(self) -> float:
        return float(Mode._mood_modifiers[2])

    @property
    def mood_accent(self) -> float:
        return float(Mode._mood_modifiers[3])

    @property
    def rhythm_lock(self) -> float:
        """Continuous flywheel lock confidence in [0.0, 1.0] combining beat_trust and rhythm_salience."""
        listener = self.listener
        ctx = getattr(listener, "context", None)
        if ctx is not None:
            trust = float(getattr(ctx, "beat_trust", 0.0))
            salience = float(getattr(ctx, "salience", 0.0))
            if salience <= 0.0 and not bool(getattr(ctx, "is_silent", False)):
                salience = float(getattr(listener, "rhythm_salience", 1.0))
        else:
            trust = float(getattr(listener, "beat_confidence", getattr(listener, "beat_trust", 0.0)))
            salience = float(getattr(listener, "rhythm_salience", 1.0))
        return max(0.0, min(1.0, max(0.0, min(1.0, trust)) * (0.4 + 0.6 * max(0.0, min(1.0, salience)))))

    @property
    def transition_scale(self) -> float:
        """Combined physical energy envelope for mode-cooperative exit wind-down and enter bloom-in."""
        exit_gain = 1.0 - 0.75 * (self._exit_progress * self._exit_progress)
        enter_gain = 0.15 + 0.85 * (self._enter_progress * (2.0 - self._enter_progress))
        return exit_gain * enter_gain

    def on_transition_exit(self, progress: float) -> None:
        """Lifecycle hook called while this mode is transitioning out (progress in [0.0, 1.0])."""
        self._exit_progress = max(0.0, min(1.0, float(progress)))

    def on_transition_enter(self, progress: float) -> None:
        """Lifecycle hook called while this mode is transitioning in (progress in [0.0, 1.0])."""
        self._enter_progress = max(0.0, min(1.0, float(progress)))

    def on_transition_reset(self) -> None:
        """Reset transition lifecycle progress to steady state."""
        self._exit_progress = 0.0
        self._enter_progress = 1.0