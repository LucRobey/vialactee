"""
Opposite Sides Mode
Bass-vs-treble tug-of-war: two VU bars growing outward from a fixed solid core.
Per-wing band energy (normalised by a slow-peak AGC) sets fractional anti-aliased reach,
and ctx.spectral_tilt sets the competitive push. Discrete white sparks spawn on
ctx.is_real_beat, self.drop_hit, and band_flux onsets.
Harmonized with mood_colors and mood_modifiers with zero runtime heap allocations.
"""
from typing import List, Dict, Any
import math
import zlib
import numpy as np
import modes.Mode as Mode


class Opposite_sides_mode(Mode.Mode):
    """Bass-vs-treble tug-of-war with two VU bars growing outward from a fixed solid core.

    Lead: spectrum (per-wing band energy reach and spectral_tilt competitive push). Secondary: transient (white sparks on is_real_beat, drop_hit, and band_flux onsets). Macro: mood_colors, mood_pace/sharpness/trail/accent, bounded max(tension, drop_decay) boost.
    """
    LEAD = "spectrum"
    SECONDARY = ("transient",)

    SPARK_COLOR = (255.0, 255.0, 255.0)
    spark_count_default: int = 5

    _AGC_FLOOR: float = 0.08
    _PEAK_DECAY_RATE: float = 0.15
    _FLUX_COOLDOWN_S: float = 0.12
    _SPARK_PEAK_CAP: float = 1.00
    _SPARK_DEPOP_FLOOR: float = 0.18

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "sparkCount",
                "label": "Spark Count",
                "control": "slider",
                "valueType": "number",
                "integer": True,
                "min": 0,
                "max": 12,
                "step": 1,
                "default": self.spark_count_default,
                "attr": "spark_count",
            },
        ]

    def __init__(
        self,
        name: str,
        segment_name: str,
        listener: Any,
        leds: Any,
        indexes: List[int],
        rgb_list: np.ndarray,
        infos: Dict[str, Any],
    ):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)

        self.spark_count: int = int(
            infos.get("opposite_sides_spark_count", infos.get("sparkCount", self.spark_count_default))
        )
        self.spark_color: np.ndarray = np.array(self.SPARK_COLOR, dtype=np.float64)

        n = self.nb_of_leds
        if n <= 0:
            self.core_width: int = 0
            self.mid_start: int = 0
            self.mid_end: int = -1
            self._wing_len_l: int = 0
            self._wing_len_r: int = 0
            return

        w = min(n, max(2, int(round(0.08 * n)))) if n >= 2 else n
        c = n // 2
        self.core_width = w
        self.mid_start = max(0, min(n - w, c - (w // 2)))
        self.mid_end = self.mid_start + w - 1
        self._wing_len_l = self.mid_start
        self._wing_len_r = max(0, n - (self.mid_end + 1))

        # Precomputed distance from core edge (0.0 for the adjacent LED on each wing)
        self._dist_left: np.ndarray = np.arange(self._wing_len_l - 1, -1, -1, dtype=np.float64)
        self._dist_right: np.ndarray = np.arange(self._wing_len_r, dtype=np.float64)

        # Preallocated coverage buffers and 2D column views (cached on mode buffers, never on rgb_list)
        self._cov_l: np.ndarray = np.zeros(self._wing_len_l, dtype=np.float64)
        self._cov_r: np.ndarray = np.zeros(self._wing_len_r, dtype=np.float64)
        self._cov_l_2d: np.ndarray = self._cov_l[:, None]
        self._cov_r_2d: np.ndarray = self._cov_r[:, None]

        # Preallocated target and scratch buffers
        self._tgt: np.ndarray = np.zeros((n, 3), dtype=np.float64)
        self._tgt_l: np.ndarray = self._tgt[: self.mid_start]
        self._tgt_core: np.ndarray = self._tgt[self.mid_start : self.mid_end + 1]
        self._tgt_r: np.ndarray = self._tgt[self.mid_end + 1 :]

        self._spark: np.ndarray = np.zeros(n, dtype=np.float64)
        self._spark_clamped: np.ndarray = np.zeros(n, dtype=np.float64)
        self._spark_2d: np.ndarray = self._spark_clamped[:, None]
        self._tmp: np.ndarray = np.zeros((n, 3), dtype=np.float64)

        self.bass_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.high_color: np.ndarray = np.zeros(3, dtype=np.float64)
        self.mid_color: np.ndarray = np.zeros(3, dtype=np.float64)

        # Deterministic 64-entry golden-ratio spark table (well-separated, never clumped),
        # wing-flip mask, and inter-pop stagger delays (in frames) for firework crackle.
        seed = zlib.crc32(f"{name}:{segment_name}".encode("utf-8")) & 0xFFFFFFFF
        rng = np.random.RandomState(seed)
        phase0 = float(rng.uniform(0.0, 1.0))
        golden = 0.6180339887498949
        self._spawn_tbl: np.ndarray = np.array(
            [0.06 + 0.92 * ((phase0 + i * golden) % 1.0) for i in range(64)],
            dtype=np.float64,
        )
        self._spawn_flip: np.ndarray = rng.uniform(0.0, 1.0, size=64) < 0.30
        self._stagger_tbl: np.ndarray = rng.choice(np.array([1, 1, 2, 1, 2, 3], dtype=np.int32), size=64)
        self._spawn_cursor: int = 0
        self._crackle_queue: int = 0
        self._crackle_timer: int = 0

        # Per-wing envelopes, slow-peak AGC, phase wrap tracker, and flux onset state
        self._env_low: float = 0.0
        self._env_high: float = 0.0
        self._peak_low: float = 0.45
        self._peak_high: float = 0.45
        self._prev_phase: float = 0.0
        self._flux_peak: float = 1.0
        self._flux_cooldown: float = 0.0

    def _spawn_spark(self, on_left: bool, reach_l: float, reach_r: float) -> None:
        """Stamp a single 1-LED ultra-bright pinpoint spark, avoiding adjacent active sparks."""
        idx = self._spawn_cursor
        self._spawn_cursor = (idx + 1) & 63
        f = float(self._spawn_tbl[idx])

        if on_left and self._wing_len_l > 0 and reach_l > 0.05:
            w_end = self.mid_start - 1
            span = max(1.0, min(float(self._wing_len_l - 1), reach_l * 1.05))
            pos = int(round(w_end - f * span))
            pos = max(0, min(w_end, pos))
            # Keep sparkles isolated (never a multi-LED group)
            if (pos > 0 and self._spark[pos - 1] > 0.1) or (pos < w_end and self._spark[pos + 1] > 0.1):
                alt = pos - 2 if pos >= 2 else min(w_end, pos + 2)
                pos = max(0, min(w_end, alt))
            self._spark[pos] = 1.80
        elif (not on_left) and self._wing_len_r > 0 and reach_r > 0.05:
            w_start = self.mid_end + 1
            w_end = self.nb_of_leds - 1
            span = max(1.0, min(float(self._wing_len_r - 1), reach_r * 1.05))
            pos = int(round(w_start + f * span))
            pos = max(w_start, min(w_end, pos))
            if (pos > w_start and self._spark[pos - 1] > 0.1) or (pos < w_end and self._spark[pos + 1] > 0.1):
                alt = pos + 2 if pos + 2 <= w_end else max(w_start, pos - 2)
                pos = max(w_start, min(w_end, alt))
            self._spark[pos] = 1.80

    def _emit_one_crackle(self, win_left: bool, reach_l: float, reach_r: float) -> None:
        flip = bool(self._spawn_flip[self._spawn_cursor])
        side_left = (not win_left) if flip else win_left
        if side_left and reach_l <= 0.05 and reach_r > 0.05:
            side_left = False
        elif (not side_left) and reach_r <= 0.05 and reach_l > 0.05:
            side_left = True
        self._spawn_spark(side_left, reach_l, reach_r)

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return

        ctx = getattr(self.listener, "context", None)
        is_silent = bool(ctx.is_silent if ctx is not None else False)
        if is_silent:
            self._env_low *= 0.65
            self._env_high *= 0.65
            self._spark *= 0.50
            self.fade_to_black_segment_vectorized(0.35, 0, self.nb_of_leds - 1)
            return

        dt = self.dt

        # 2. Band groups: low = mean(bands[:low_cut]), high = mean(bands[high_start:])
        bands = getattr(self.listener, "asserved_fft_band", None)
        low = 0.0
        high = 0.0
        if bands is not None and len(bands) > 0:
            nb = len(bands)
            low_cut = max(1, int(round(3 * nb / 8)))
            high_start = min(nb - 1, int(round(5 * nb / 8)))
            s_low = 0.0
            for i in range(low_cut):
                s_low += float(bands[i])
            low = max(0.0, s_low / float(low_cut))

            s_high = 0.0
            n_high = max(1, nb - high_start)
            for i in range(high_start, nb):
                s_high += float(bands[i])
            high = max(0.0, s_high / float(n_high))

        # 3 & 4. Per-wing slow-peak AGC normalisation and asymmetric attack/recoil envelopes
        a_atk = self.alpha(22.0 * self.mood_pace)
        a_rec = self.alpha(6.5 * self.mood_sharpness / max(0.5, self.mood_trail))
        self._env_low += (a_atk if low > self._env_low else a_rec) * (low - self._env_low)
        self._env_high += (a_atk if high > self._env_high else a_rec) * (high - self._env_high)

        peak_decay = math.exp(-dt * self._PEAK_DECAY_RATE)
        self._peak_low = max(self._AGC_FLOOR, low, self._peak_low * peak_decay)
        self._peak_high = max(self._AGC_FLOOR, high, self._peak_high * peak_decay)
        level_low = self._env_low / self._peak_low
        level_high = self._env_high / self._peak_high

        # 5. Competitive push from spectral_tilt (loser stays at 1.0)
        tilt = float(ctx.spectral_tilt if ctx is not None else 0.0)
        tension = float(ctx.tension if ctx is not None else 0.0)
        push_low = 1.0 + 0.20 * max(0.0, -tilt)
        push_high = 1.0 + 0.20 * max(0.0, tilt)

        # 6. Soft-knee fractional reach with bounded macro gain (+10% max)
        macro_gain = 1.0 + 0.10 * max(tension, self.drop_decay)
        drive_low = max(0.0, level_low * push_low * macro_gain)
        drive_high = max(0.0, level_high * push_high * macro_gain)
        reach_l = float(self._wing_len_l) * (1.0 - math.exp(-2.0 * drive_low))
        reach_r = float(self._wing_len_r) * (1.0 - math.exp(-2.0 * drive_high))

        # 7. Anti-aliased coverage per wing
        if self._wing_len_l > 0:
            np.subtract(reach_l, self._dist_left, out=self._cov_l)
            np.clip(self._cov_l, 0.0, 1.0, out=self._cov_l)
        if self._wing_len_r > 0:
            np.subtract(reach_r, self._dist_right, out=self._cov_r)
            np.clip(self._cov_r, 0.0, 1.0, out=self._cov_r)

        # 8 & 9. Wing colours and luminance-safe solid core colour
        mood = self.mood_colors
        m0, m1, m2 = mood[0], mood[1], mood[2]
        hi = self.highlight_color
        accent = self.mood_accent
        inv_acc = 1.0 - accent
        for c in range(3):
            self.bass_color[c] = inv_acc * float(m0[c]) + accent * float(hi[c])
            self.high_color[c] = inv_acc * float(m1[c]) + accent * float(hi[c])

        lum = 0.299 * float(m2[0]) + 0.587 * float(m2[1]) + 0.114 * float(m2[2])
        if lum < 90.0:
            for c in range(3):
                self.mid_color[c] = 0.5 * float(m2[c]) + 0.5 * float(hi[c])
        else:
            for c in range(3):
                self.mid_color[c] = float(m2[c])

        if self._wing_len_l > 0:
            np.multiply(self._cov_l_2d, self.bass_color, out=self._tgt_l)
        self._tgt_core[:] = self.mid_color
        if self._wing_len_r > 0:
            np.multiply(self._cov_r_2d, self.high_color, out=self._tgt_r)

        # 10. Secondary (transient): firework crackle of 1-LED pinpoint sparks outside the core.
        # Fast decay + crisp depop floor so each pinpoint pops bright white and snaps off quickly,
        # while a burst queues staggered pops across subsequent frames ("pop de pop pop depop").
        self._spark *= math.exp(-dt * 20.0 / max(0.5, self.mood_trail))
        self._flux_cooldown = max(0.0, self._flux_cooldown - dt)
        base_sparks = max(0, int(self.spark_count))
        if base_sparks == 0:
            self._crackle_queue = 0

        phase = float(getattr(self.listener, "beat_phase", 0.0))
        phase_wrapped = (phase < self._prev_phase) and (self._prev_phase > 0.5)
        self._prev_phase = phase

        is_locked = (
            bool(ctx.is_locked)
            if ctx is not None
            else (float(getattr(self.listener, "beat_confidence", 0.0)) >= 0.5)
        )
        is_real_beat = (
            bool(ctx.is_real_beat)
            if ctx is not None
            else bool(getattr(self.listener, "is_real_beat", False))
        )
        beat_trigger = phase_wrapped if is_locked else is_real_beat

        win_left = (tilt < 0.0) if abs(tilt) > 1e-6 else (level_low >= level_high)
        if base_sparks > 0 and (beat_trigger or self.drop_hit):
            # Pop 1 pinpoint immediately on the beat/drop frame and queue the rest to crackle over ~150-220ms
            self._emit_one_crackle(win_left, reach_l, reach_r)
            burst_total = (base_sparks if beat_trigger else 0) + ((base_sparks + 2) if self.drop_hit else 0)
            self._crackle_queue = min(16, self._crackle_queue + max(0, burst_total - 1))
            self._crackle_timer = int(self._stagger_tbl[self._spawn_cursor])

        flux = getattr(self.listener, "band_flux", None)
        if (not is_locked) and base_sparks > 0 and flux is not None and len(flux) > 0:
            nf = len(flux)
            f_max = 0.0
            f_arg = 0
            for i in range(nf):
                fv = float(flux[i])
                if fv > f_max:
                    f_max = fv
                    f_arg = i
            self._flux_peak = max(1.0, f_max, self._flux_peak * math.exp(-dt * 1.5))
            thr = 0.22 + 0.5 * self.rhythm_lock
            if (f_max / self._flux_peak) > thr and self._flux_cooldown <= 0.0:
                self._flux_cooldown = self._FLUX_COOLDOWN_S
                f_left = f_arg < (nf / 2.0)
                if f_left and reach_l <= 0.05 and reach_r > 0.05:
                    f_left = False
                elif (not f_left) and reach_r <= 0.05 and reach_l > 0.05:
                    f_left = True
                self._spawn_spark(f_left, reach_l, reach_r)
                self._crackle_queue = min(16, self._crackle_queue + max(0, (base_sparks // 2)))
                if self._crackle_timer <= 0:
                    self._crackle_timer = int(self._stagger_tbl[self._spawn_cursor])

        # Staggered firework crackle: pop 1 pinpoint when the inter-pop frame timer expires
        if self._crackle_queue > 0 and base_sparks > 0:
            self._crackle_timer -= 1
            if self._crackle_timer <= 0:
                self._emit_one_crackle(win_left, reach_l, reach_r)
                self._crackle_queue -= 1
                if self._crackle_queue > 0:
                    self._crackle_timer = int(self._stagger_tbl[self._spawn_cursor])

        self._spark[self.mid_start : self.mid_end + 1] = 0.0
        np.subtract(self._spark, self._SPARK_DEPOP_FLOOR, out=self._spark_clamped)
        np.clip(self._spark_clamped, 0.0, self._SPARK_PEAK_CAP, out=self._spark_clamped)
        np.subtract(self.spark_color, self._tgt, out=self._tmp)
        np.multiply(self._tmp, self._spark_2d, out=self._tmp)
        np.add(self._tgt, self._tmp, out=self._tgt)

        if self._exit_progress > 0.0 or self._enter_progress < 1.0:
            np.multiply(self._tgt, self.transition_scale, out=self._tgt)

        np.clip(self._tgt, 0.0, 255.0, out=self._tgt)
        self.rgb_list[:] = self._tgt
