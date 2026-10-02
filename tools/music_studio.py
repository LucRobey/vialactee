"""
music_studio.py - Interactive DSP & Music Analysis Laboratory

Provides bit-for-bit hardware-parity music analysis inspection and tuning for the
Vialactée LED chandelier. Evaluates production Listener, AudioAnalyzer (Oracle Flywheel),
AudioIngestion, and StructuralNoveltyDetector in real time with synchronized sounddevice playback,
sample-accurate lookahead oscilloscope, 8-band FFT dynamics, 12-tone chromagram,
structural drop scope, and live parameter tuning.
"""

from __future__ import annotations
import os
import sys
import time
import glob
import math
import json
import argparse
import importlib.util
from typing import Dict, Any, List, Optional, Tuple, Type, Callable

# Ensure repository root is on sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import soundfile as sf
import sounddevice as sd
import pygame

from core.Listener import Listener
from core.RhythmConfig import RhythmConfig
from core.BaseAudioAnalyzer import BaseAudioAnalyzer
from core.AudioAnalyzer import AudioAnalyzer, bpm_to_class
from core.MusicalContextEngine import MusicalScene, MusicalRegime


def load_studio_model_class(model_name: str, repo_root: str) -> Type[BaseAudioAnalyzer]:
    """
    Dynamically loads any model subclassing BaseAudioAnalyzer without importing heavy
    offline MIR benchmarking packages (torchaudio, mir_eval, matplotlib, etc.).
    """
    if model_name in ("AudioAnalyzer", "baseline"):
        return AudioAnalyzer
    if model_name in ("MultiBandOnsetAudioAnalyzer", "production", "default"):
        from core.MultiBandOnsetAudioAnalyzer import MultiBandOnsetAudioAnalyzer
        return MultiBandOnsetAudioAnalyzer

    models_dir = os.path.join(repo_root, "research", "experiments", "models")
    discovered_classes: Dict[str, Type[BaseAudioAnalyzer]] = {}

    if os.path.exists(models_dir):
        for fname in sorted(os.listdir(models_dir)):
            if fname.endswith(".py") and not fname.startswith("__"):
                fpath = os.path.join(models_dir, fname)
                mod_name = f"research.experiments.models.{fname[:-3]}"
                try:
                    spec = importlib.util.spec_from_file_location(mod_name, fpath)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[mod_name] = module
                        spec.loader.exec_module(module)
                        for attr_name in dir(module):
                            obj = getattr(module, attr_name)
                            if (
                                isinstance(obj, type)
                                and issubclass(obj, BaseAudioAnalyzer)
                                and obj is not BaseAudioAnalyzer
                            ):
                                discovered_classes[attr_name.lower()] = obj
                                discovered_classes[attr_name] = obj
                except Exception as e:
                    print(f"[Warning] Failed to import model module {fname}: {e}")

    if model_name in discovered_classes:
        return discovered_classes[model_name]
    elif model_name.lower() in discovered_classes:
        return discovered_classes[model_name.lower()]

    available = sorted(set([k for k in discovered_classes.keys() if not k.islower()] + ["AudioAnalyzer"]))
    raise ValueError(
        f"Model '{model_name}' not found. Available models: {available}"
    )


# =====================================================================
# AUDIO STREAMER (Hardware DAC Compensation & Predictive Lookahead)
# =====================================================================

class AudioStreamer:
    """
    Sample-accurate audio streamer using sounddevice with 5.0s predictive lookahead.
    Feeds future audio chunks to Listener in strict 735-sample increments (60 FPS parity)
    while streaming speaker-time audio to physical speakers in perfect synchronization.
    """

    def __init__(self, audio_file_path: str, listener: Listener, sample_rate: int = 44100):
        self.file_path = audio_file_path
        self.listener = listener
        self.sample_rate = sample_rate
        self.lookahead_seconds = getattr(listener.analyzer, 'lookahead_seconds', 5.0)
        self.lookahead_samples = int(self.lookahead_seconds * self.sample_rate)
        self.hop_samples = int(round(self.sample_rate / 60.0))  # Exactly 735 samples at 44100 Hz

        print(f"Loading audio: {os.path.basename(audio_file_path)}...")
        raw_data, sr = sf.read(audio_file_path, dtype='float32')
        if sr != self.sample_rate:
            print(f"Resampling audio from {sr} Hz to {self.sample_rate} Hz...")
            import scipy.signal as signal
            gcd = math.gcd(int(sr), int(self.sample_rate))
            up = self.sample_rate // gcd
            down = sr // gcd
            raw_data = signal.resample_poly(raw_data, up, down, axis=0).astype(np.float32)

        if raw_data.ndim == 1:
            self.stereo_data = np.column_stack((raw_data, raw_data))
            self.mono_data = raw_data
        else:
            self.stereo_data = raw_data[:, :2]
            self.mono_data = np.mean(raw_data, axis=1).astype(np.float32)

        self.total_samples = len(self.mono_data)
        self.total_duration = self.total_samples / float(self.sample_rate)

        self.speaker_sample_pos = 0
        self.ingest_sample_pos = 0
        self.dac_latency = 0.0
        self.is_playing = False
        self.is_finished = False

        self.stream: Optional[sd.OutputStream] = None

    def start_stream(self) -> None:
        if self.stream is None:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=2,
                blocksize=1024,
                callback=self._audio_callback
            )
            self.stream.start()

    def stop_stream(self) -> None:
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        if not self.is_playing:
            outdata.fill(0)
            return

        self.dac_latency = max(0.0, time_info.outputBufferDacTime - time_info.currentTime)
        pos = self.speaker_sample_pos
        end = pos + frames

        if pos >= self.total_samples:
            outdata.fill(0)
            self.is_finished = True
            return

        if end <= self.total_samples:
            outdata[:] = self.stereo_data[pos:end]
        else:
            available = self.total_samples - pos
            outdata[:available] = self.stereo_data[pos:self.total_samples]
            outdata[available:].fill(0)
            self.is_finished = True

        self.speaker_sample_pos += frames

    def get_actual_speaker_sample(self) -> int:
        dac_frames = int(self.dac_latency * self.sample_rate)
        return max(0, self.speaker_sample_pos - dac_frames)

    def get_current_time(self) -> float:
        return float(self.get_actual_speaker_sample()) / float(self.sample_rate)

    def seek(self, target_seconds: float, sync_offset_seconds: float = 0.0) -> None:
        target_sample = int(np.clip(target_seconds * self.sample_rate, 0, max(0, self.total_samples - 1024)))
        self.speaker_sample_pos = target_sample
        if hasattr(self.listener, 'reset'):
            self.listener.reset()
        elif hasattr(self.listener.analyzer, 'reset'):
            self.listener.analyzer.reset()
        self.prime_analyzer(sync_offset_seconds)

    def prime_analyzer(self, sync_offset_seconds: float = 0.0) -> None:
        start_ingest = self.get_actual_speaker_sample() + int(sync_offset_seconds * self.sample_rate)
        now = time.time()

        for i in range(300):
            ingest_center = start_ingest + i * self.hop_samples
            s_start = max(0, ingest_center - 2048)
            s_end = min(self.total_samples, ingest_center + 2048)
            chunk = np.zeros(4096, dtype=np.float32)
            if s_start < self.total_samples and s_end > s_start:
                chunk[:s_end - s_start] = self.mono_data[s_start:s_end]
            self.listener.process_raw_audio(chunk)
            self.listener.update(fixed_dt=1/60.0)

        self.ingest_sample_pos = start_ingest + 300 * self.hop_samples

        count = self.listener._ring_count
        read_idx = self.listener._ring_read
        capacity = self.listener._ring_capacity
        for i in range(count):
            r = (read_idx + i) % capacity
            self.listener._ring_timestamps[r] = now - self.lookahead_seconds + (i / 60.0)
        self.listener.last_env_time = now

    def advance_ingest_frame(
        self,
        sync_offset_seconds: float = 0.0,
        on_frame_step: Optional[Callable[[], None]] = None
    ) -> int:
        """
        Advances ingestion in exact 735-sample increments to catch up with actual speaker playback.
        Invokes on_frame_step() on each 60 FPS sub-frame to guarantee no beat triggers or events are dropped.
        Returns the number of 60 FPS frames processed.
        """
        actual_speaker = self.get_actual_speaker_sample()
        target_ingest = (
            actual_speaker
            + self.lookahead_samples
            + int(sync_offset_seconds * self.sample_rate)
        )

        # Handle seeking or massive pause catchup (> 2.0s behind)
        if self.ingest_sample_pos > target_ingest + 10 * self.hop_samples:
            self.ingest_sample_pos = target_ingest
        elif target_ingest - self.ingest_sample_pos > 120 * self.hop_samples:
            self.ingest_sample_pos = target_ingest - 4 * self.hop_samples

        frames_stepped = 0
        max_frames_per_tick = 6
        while (
            self.ingest_sample_pos + self.hop_samples <= target_ingest
            and frames_stepped < max_frames_per_tick
        ):
            chunk_center = self.ingest_sample_pos
            s_start = max(0, chunk_center - 2048)
            s_end = min(self.total_samples, chunk_center + 2048)
            chunk = np.zeros(4096, dtype=np.float32)
            if s_start < self.total_samples and s_end > s_start:
                chunk[:s_end - s_start] = self.mono_data[s_start:s_end]
            self.listener.process_raw_audio(chunk)
            self.listener.update(fixed_dt=1/60.0)
            self.ingest_sample_pos += self.hop_samples
            frames_stepped += 1
            if on_frame_step is not None:
                on_frame_step()

        return frames_stepped


# =====================================================================
# MUSIC STUDIO GUI APPLICATION
# =====================================================================

class MusicStudioApp:
    """
    Main interactive laboratory GUI for testing, visualizing, and calibrating
    Vialactée music analysis capabilities.
    """

    # Modern Cyber-Lab Color Palette
    BG_COLOR = (11, 13, 18)
    PANEL_BG = (18, 22, 31)
    PANEL_BORDER = (38, 46, 64)
    TEXT_MAIN = (235, 240, 248)
    TEXT_DIM = (120, 134, 158)
    TEXT_MUTED = (75, 86, 105)

    ACCENT_CYAN = (0, 229, 255)
    ACCENT_GREEN = (0, 230, 118)
    ACCENT_RED = (255, 50, 80)
    ACCENT_ORANGE = (255, 145, 0)
    ACCENT_PURPLE = (170, 0, 255)
    ACCENT_BLUE = (41, 121, 255)
    ACCENT_GOLD = (255, 214, 0)
    ACCENT_MAGENTA = (255, 40, 130)

    SCENE_COLORS = {
        MusicalScene.CHILL: (70, 130, 240),       # Slate Blue / Cyan
        MusicalScene.GROOVE: (40, 240, 120),      # Emerald Green
        MusicalScene.BUILDUP: (255, 40, 130),     # Vivid Crimson
        MusicalScene.DROP_IMPACT: (255, 230, 80), # Blinding White/Gold
    }

    SCENE_BG_COLORS = {
        MusicalScene.CHILL: (18, 28, 55),
        MusicalScene.GROOVE: (16, 55, 32),
        MusicalScene.BUILDUP: (65, 15, 35),
        MusicalScene.DROP_IMPACT: (70, 60, 20),
    }

    SCENE_ICONS = {
        MusicalScene.CHILL: "≋",
        MusicalScene.GROOVE: "●",
        MusicalScene.BUILDUP: "▲",
        MusicalScene.DROP_IMPACT: "💥",
    }

    REGIME_COLORS = SCENE_COLORS
    REGIME_BG_COLORS = SCENE_BG_COLORS
    REGIME_ICONS = SCENE_ICONS

    CHROMA_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    BAND_NAMES = ["Sub-Bass", "Bass", "Low-Mid", "Mid", "High-Mid", "Presence", "Brilliance", "Air"]

    def __init__(self, song_path: str, nb_leds: int = 80, model_name: str = "MultiBandOnsetAudioAnalyzer"):
        pygame.init()
        pygame.font.init()

        self.width = 1440
        self.height = 960
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF)
        pygame.display.set_caption("Vialactée Music Studio — Real-Time DSP & Music Analysis Laboratory")

        # Fonts
        self.font_title = pygame.font.SysFont("Trebuchet MS", 20, bold=True)
        self.font_main = pygame.font.SysFont("Trebuchet MS", 14, bold=True)
        self.font_small = pygame.font.SysFont("Trebuchet MS", 11)
        self.font_mono = pygame.font.SysFont("Consolas", 12, bold=True)
        self.font_big_num = pygame.font.SysFont("Trebuchet MS", 28, bold=True)
        self.font_tiny = pygame.font.SysFont("Trebuchet MS", 9)

        self.clock = pygame.time.Clock()
        self.nb_leds = nb_leds

        # Persistent A/V Sync calibration
        self.sync_config_file = os.path.join(_HERE, "studio_sync.json")
        self.sync_offset_ms = 0.0
        self.load_sync_config()

        # Playlist setup
        self.song_list = sorted(glob.glob(os.path.join(_REPO_ROOT, "assets", "musics", "mp3_files", "*.mp3")))
        try:
            self.song_index = self.song_list.index(os.path.abspath(song_path))
        except (ValueError, IndexError):
            self.song_index = 0
            if self.song_list:
                song_path = self.song_list[0]

        # Rhythm Model Resolution & Dynamic Band Configuration
        self.model_class = load_studio_model_class(model_name, _REPO_ROOT)
        self.model_name = self.model_class.__name__
        self.nb_bands = int(getattr(self.model_class, "NB_AUDIO_BANDS", 8))

        dummy_infos = {
            "sensi": 1.0,
            "luminosite": 1.0,
            "fakeDelay": 5.0,
            "latency": 0.0,
            "useMicrophone": True,
            "nb_of_fft_band": self.nb_bands,
            "nb_of_chroma": 12,
            "sample_rate": 44100,
            "buffer_size": 4096
        }
        self.listener = Listener(dummy_infos, analyzer_class=self.model_class)
        # Zero out microphone ADC delay for local file playback
        self.listener.dynamic_audio_latency = 0.0

        # Audio Streamer setup
        self.streamer = AudioStreamer(song_path, self.listener)
        self.streamer.prime_analyzer(self.sync_offset_ms / 1000.0)

        # Status & Flash timers
        self.status_msg = "Ready. Press [Space] to pause/play."
        self.status_msg_time = time.time()
        self.status_color = self.ACCENT_CYAN

        self.last_beat_visual_time = 0.0
        self.last_beat_visual_color = self.ACCENT_RED
        self.last_beat_visual_tag = "Bass/Kick"
        self.last_beat_was_real = True

        self.last_drop_time = 0.0
        self.last_song_change_time = 0.0

        # Text rendering cache (avoids 4000+ surface allocations per sec)
        self._text_cache: Dict[Tuple[int, str, Tuple[int, int, int]], pygame.Surface] = {}

        # Rolling history buffers for plotting (time-synchronized at speaker playback)
        self.history_size = 240
        self.history_novelty = np.zeros(self.history_size)
        self.history_lm = np.zeros(self.history_size)
        self.history_gm = np.zeros(self.history_size)
        self.history_cursor = 0

        # Virtual LED strip buffer
        self.led_rgb = np.zeros((self.nb_leds, 3), dtype=np.uint8)

        # Tuning drawer state with dynamic property bindings
        self.tuning_open = False
        self.tuning_params = [
            {"name": "sensi", "label": "Audio Sensitivity", "get": lambda: self.listener.sensi, "set": lambda v: setattr(self.listener, "sensi", v), "min": 0.1, "max": 3.0, "step": 0.05, "fmt": "{:.2f}"},
            {"name": "mod_conf", "label": "Moderate Lock Conf", "get": lambda: self.listener.analyzer.config.moderate_confidence_threshold, "set": lambda v: setattr(self.listener.analyzer.config, "moderate_confidence_threshold", v), "min": 0.05, "max": 0.50, "step": 0.01, "fmt": "{:.2f}"},
            {"name": "high_conf", "label": "High Lock Conf", "get": lambda: self.listener.analyzer.config.high_confidence_threshold, "set": lambda v: setattr(self.listener.analyzer.config, "high_confidence_threshold", v), "min": 0.10, "max": 0.60, "step": 0.01, "fmt": "{:.2f}"},
            {"name": "strong_peak", "label": "Strong Peak Mult", "get": lambda: self.listener.analyzer.config.strong_peak_multiplier, "set": lambda v: setattr(self.listener.analyzer.config, "strong_peak_multiplier", v), "min": 1.0, "max": 3.5, "step": 0.1, "fmt": "{:.1f}"},
            {"name": "real_beat_ratio", "label": "Real Beat Ratio", "get": lambda: self.listener.analyzer.config.real_beat_baseline_ratio, "set": lambda v: setattr(self.listener.analyzer.config, "real_beat_baseline_ratio", v), "min": 0.1, "max": 1.5, "step": 0.05, "fmt": "{:.2f}"},
            {"name": "novelty_th", "label": "Song Novelty Drop Th", "get": lambda: self.listener.analyzer.config.song_novelty_asserved_th, "set": lambda v: setattr(self.listener.analyzer.config, "song_novelty_asserved_th", v), "min": 0.4, "max": 1.2, "step": 0.02, "fmt": "{:.2f}"},
            {"name": "silence_th", "label": "Silence Power Floor", "get": lambda: self.listener.analyzer.config.silence_power_threshold, "set": lambda v: setattr(self.listener.analyzer.config, "silence_power_threshold", v), "min": 1.0, "max": 20.0, "step": 0.5, "fmt": "{:.1f}"},
            {"name": "drop_buildup", "label": "Pre-Drop Gradient Th", "get": lambda: getattr(self.listener.context, "drop_buildup_threshold", 0.40), "set": lambda v: setattr(self.listener.context, "drop_buildup_threshold", v), "min": 0.10, "max": 0.80, "step": 0.02, "fmt": "{:.2f}"},
            {"name": "salience_low", "label": "Salience Low Th", "get": lambda: getattr(self.listener.context, "salience_low", 0.35), "set": lambda v: setattr(self.listener.context, "salience_low", v), "min": 0.10, "max": 0.60, "step": 0.02, "fmt": "{:.2f}"},
            {"name": "salience_high", "label": "Salience High Th", "get": lambda: getattr(self.listener.context, "salience_high", 0.45), "set": lambda v: setattr(self.listener.context, "salience_high", v), "min": 0.20, "max": 0.85, "step": 0.02, "fmt": "{:.2f}"},
            {"name": "trust_low", "label": "Beat Trust Low Th", "get": lambda: getattr(self.listener.context, "trust_low", 0.35), "set": lambda v: setattr(self.listener.context, "trust_low", v), "min": 0.10, "max": 0.60, "step": 0.02, "fmt": "{:.2f}"},
            {"name": "trust_high", "label": "Beat Trust High Th", "get": lambda: getattr(self.listener.context, "trust_high", 0.50), "set": lambda v: setattr(self.listener.context, "trust_high", v), "min": 0.20, "max": 0.85, "step": 0.02, "fmt": "{:.2f}"},
        ]
        self.tuning_selected_idx = 0
        self.tuning_dragging = False

        # Surface caches for zero heap allocation hot rendering (AXIOM-02)
        self._drawer_overlay_surf: Optional[pygame.Surface] = None
        self._scope_buildup_surf: Optional[pygame.Surface] = None

    def get_text(self, font: pygame.font.Font, text: str, color: Tuple[int, int, int]) -> pygame.Surface:
        """Cached font renderer avoiding heap thrashing at 60 FPS."""
        key = (id(font), text, color)
        surf = self._text_cache.get(key)
        if surf is None:
            if len(self._text_cache) > 2000:
                self._text_cache.clear()
            surf = font.render(text, True, color)
            self._text_cache[key] = surf
        return surf

    # =================================================================
    # CONFIG & PLAYLIST MANAGEMENT
    # =================================================================

    def load_sync_config(self) -> None:
        try:
            if os.path.exists(self.sync_config_file):
                with open(self.sync_config_file, "r") as f:
                    data = json.load(f)
                    self.sync_offset_ms = float(data.get("sync_offset_ms", 0.0))
        except Exception:
            self.sync_offset_ms = 0.0

    def save_sync_config(self) -> None:
        try:
            with open(self.sync_config_file, "w") as f:
                json.dump({"sync_offset_ms": self.sync_offset_ms}, f, indent=2)
        except Exception:
            pass

    def change_song(self, new_index: int) -> None:
        if not self.song_list:
            return
        self.song_index = new_index % len(self.song_list)
        new_path = self.song_list[self.song_index]

        was_playing = self.streamer.is_playing
        self.streamer.stop_stream()
        if hasattr(self.listener, 'reset'):
            self.listener.reset()
        elif hasattr(self.listener.analyzer, 'reset'):
            self.listener.analyzer.reset()
        self.streamer = AudioStreamer(new_path, self.listener)
        self.streamer.prime_analyzer(self.sync_offset_ms / 1000.0)
        if was_playing:
            self.streamer.start_stream()
            self.streamer.is_playing = True

        self.set_status(f"Track: {os.path.basename(new_path)}", self.ACCENT_CYAN)

    def set_status(self, msg: str, color: Tuple[int, int, int]) -> None:
        self.status_msg = msg
        self.status_msg_time = time.time()
        self.status_color = color

    # =================================================================
    # RUN LOOP
    # =================================================================

    def run(self) -> None:
        self.streamer.start_stream()
        self.streamer.is_playing = True
        running = True

        while running:
            # Event processing
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.streamer.is_playing = not self.streamer.is_playing
                        self.set_status("PAUSED" if not self.streamer.is_playing else "PLAYING", self.TEXT_MAIN)
                    elif event.key == pygame.K_RIGHT:
                        self.streamer.seek(self.streamer.get_current_time() + 5.0, self.sync_offset_ms / 1000.0)
                        self.set_status("+5s Seek", self.TEXT_MAIN)
                    elif event.key == pygame.K_LEFT:
                        self.streamer.seek(self.streamer.get_current_time() - 5.0, self.sync_offset_ms / 1000.0)
                        self.set_status("-5s Seek", self.TEXT_MAIN)
                    elif event.key == pygame.K_k:
                        self.sync_offset_ms -= 10.0
                        self.save_sync_config()
                        self.set_status(f"A/V Sync: {self.sync_offset_ms:+.0f} ms (Visuals earlier)", self.ACCENT_CYAN)
                    elif event.key == pygame.K_l:
                        self.sync_offset_ms += 10.0
                        self.save_sync_config()
                        self.set_status(f"A/V Sync: {self.sync_offset_ms:+.0f} ms (Visuals later)", self.ACCENT_CYAN)
                    elif event.key == pygame.K_BACKSLASH:
                        self.sync_offset_ms = 0.0
                        self.save_sync_config()
                        self.set_status("A/V Sync: 0 ms (Reset)", self.TEXT_MAIN)
                    elif event.key == pygame.K_n:
                        self.change_song(self.song_index + 1)
                    elif event.key == pygame.K_p:
                        self.change_song(self.song_index - 1)
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        target_track = event.key - pygame.K_1
                        if target_track < len(self.song_list):
                            self.change_song(target_track)
                    elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                        self.listener.sensi = min(3.0, self.listener.sensi + 0.1)
                        self.set_status(f"Sensibility: {int(self.listener.sensi * 100)}%", self.ACCENT_ORANGE)
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.listener.sensi = max(0.1, self.listener.sensi - 0.1)
                        self.set_status(f"Sensibility: {int(self.listener.sensi * 100)}%", self.ACCENT_ORANGE)
                    elif event.key == pygame.K_t:
                        self.tuning_open = not self.tuning_open
                        self.set_status(f"Live Parameter Drawer {'OPEN' if self.tuning_open else 'CLOSED'}", self.ACCENT_GOLD)
                    # Tuning Drawer controls
                    elif self.tuning_open:
                        if event.key == pygame.K_UP:
                            self.tuning_selected_idx = (self.tuning_selected_idx - 1) % len(self.tuning_params)
                        elif event.key == pygame.K_DOWN:
                            self.tuning_selected_idx = (self.tuning_selected_idx + 1) % len(self.tuning_params)
                        elif event.key == pygame.K_LEFT:
                            self._adjust_param(-1)
                        elif event.key == pygame.K_RIGHT:
                            self._adjust_param(1)
                        elif event.key == pygame.K_d:
                            # Reset default RhythmConfig & MusicalContextEngine
                            self.listener.analyzer.config = RhythmConfig()
                            if hasattr(self.listener.analyzer, 'novelty_detector'):
                                self.listener.analyzer.novelty_detector.config = self.listener.analyzer.config
                            if hasattr(self.listener, 'context'):
                                self.listener.context.reset()
                                self.listener.context.drop_buildup_threshold = 0.40
                                self.listener.context.salience_low = 0.35
                                self.listener.context.salience_high = 0.45
                                self.listener.context.trust_low = 0.35
                                self.listener.context.trust_high = 0.50
                            self.listener.sensi = 1.0
                            self.set_status("Reset DSP & Context parameters to default", self.ACCENT_GREEN)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    # Check if tuning drawer is open and clicked inside
                    if self.tuning_open:
                        dw = 400
                        row_h = 40
                        row_gap = 4
                        item_step = row_h + row_gap
                        dh = 66 + len(self.tuning_params) * item_step + 14
                        dx = self.width - dw - 40
                        dy = max(40, (self.height - 35 - dh) // 2)
                        drawer_rect = pygame.Rect(dx, dy, dw, dh)
                        if drawer_rect.collidepoint(mx, my):
                            row_idx = (my - (dy + 58)) // item_step
                            if 0 <= row_idx < len(self.tuning_params):
                                self.tuning_selected_idx = row_idx
                                self.tuning_dragging = True
                                self._handle_tuning_slider_mouse(mx)
                            continue

                    # Interactive timeline scrubber click
                    if 40 <= mx <= self.width - 40 and 42 <= my <= 62:
                        progress = (mx - 40) / float(self.width - 80)
                        target_sec = progress * self.streamer.total_duration
                        self.streamer.seek(target_sec, self.sync_offset_ms / 1000.0)

                elif event.type == pygame.MOUSEMOTION:
                    if self.tuning_open and self.tuning_dragging:
                        self._handle_tuning_slider_mouse(event.pos[0])

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.tuning_dragging = False

            # Audio Ingestion & Analysis step (Strict 735-Sample Ingestion Accumulator)
            if self.streamer.is_playing:
                frames_stepped = self.streamer.advance_ingest_frame(
                    self.sync_offset_ms / 1000.0,
                    on_frame_step=self._on_audio_frame
                )
                if frames_stepped > 0:
                    self._update_reference_leds()

            # Render Frame
            self.screen.fill(self.BG_COLOR)
            self._draw_header()
            self._draw_reference_led_strip()
            self._draw_panel_1_lookahead_oscilloscope()
            self._draw_panel_2_flywheel_and_beats()
            self._draw_panel_3_fft_dynamics()
            self._draw_panel_4_chromagram()
            self._draw_panel_5_structural_novelty()
            self._draw_footer()

            if self.tuning_open:
                self._draw_tuning_drawer()

            pygame.display.flip()
            self.clock.tick(60)

        self.streamer.stop_stream()
        pygame.quit()

    def _on_audio_frame(self) -> None:
        """Called every 735-sample ingestion step for sample-accurate trigger handling."""
        if self.listener.is_beat:
            self.last_beat_visual_time = time.time()
            tag = self.listener.beat_tag
            self.last_beat_visual_tag = tag
            self.last_beat_was_real = self.listener.is_real_beat
            if tag == "Bass/Kick":
                self.last_beat_visual_color = self.ACCENT_RED
            elif tag == "Snare/Mid":
                self.last_beat_visual_color = self.ACCENT_GREEN
            else:
                self.last_beat_visual_color = self.ACCENT_BLUE

        if self.listener.is_verse_chorus_change:
            self.last_drop_time = time.time()
        if self.listener.is_song_change:
            self.last_song_change_time = time.time()

        self.history_novelty[self.history_cursor] = self.listener.combined_novelty
        self.history_lm[self.history_cursor] = self.listener.novelty_lm
        self.history_gm[self.history_cursor] = self.listener.novelty_gm
        self.history_cursor = (self.history_cursor + 1) % self.history_size

    def _handle_tuning_slider_mouse(self, mx: int) -> None:
        if not (0 <= self.tuning_selected_idx < len(self.tuning_params)):
            return
        p = self.tuning_params[self.tuning_selected_idx]
        dw = 400
        dx = self.width - dw - 40
        s_bar_x = dx + 20
        s_bar_w = dw - 45
        ratio = min(1.0, max(0.0, (mx - s_bar_x) / float(max(1, s_bar_w))))
        raw_val = p["min"] + ratio * (p["max"] - p["min"])
        steps = round((raw_val - p["min"]) / p["step"])
        new_val = float(np.clip(p["min"] + steps * p["step"], p["min"], p["max"]))

        # Guard against hysteresis inversion
        context = getattr(self.listener, 'context', None)
        if context is not None:
            if p["name"] == "salience_low":
                new_val = min(new_val, getattr(context, "salience_high", 0.45) - 0.02)
            elif p["name"] == "salience_high":
                new_val = max(new_val, getattr(context, "salience_low", 0.35) + 0.02)
            elif p["name"] == "trust_low":
                new_val = min(new_val, getattr(context, "trust_high", 0.50) - 0.02)
            elif p["name"] == "trust_high":
                new_val = max(new_val, getattr(context, "trust_low", 0.35) + 0.02)

        p["set"](new_val)
        self.set_status(f"{p['label']}: {p['fmt'].format(new_val)}", self.ACCENT_GOLD)

    def _adjust_param(self, direction: int) -> None:
        p = self.tuning_params[self.tuning_selected_idx]
        cur_val = p["get"]()
        new_val = float(np.clip(cur_val + direction * p["step"], p["min"], p["max"]))

        # Guard against hysteresis inversion
        context = getattr(self.listener, 'context', None)
        if context is not None:
            if p["name"] == "salience_low":
                new_val = min(new_val, getattr(context, "salience_high", 0.45) - 0.02)
            elif p["name"] == "salience_high":
                new_val = max(new_val, getattr(context, "salience_low", 0.35) + 0.02)
            elif p["name"] == "trust_low":
                new_val = min(new_val, getattr(context, "trust_high", 0.50) - 0.02)
            elif p["name"] == "trust_high":
                new_val = max(new_val, getattr(context, "trust_low", 0.35) + 0.02)

        p["set"](new_val)
        self.set_status(f"{p['label']}: {p['fmt'].format(new_val)}", self.ACCENT_GOLD)

    def _update_reference_leds(self) -> None:
        """Simulate real-time chandelier response across 80 LEDs using delayed production data."""
        self.led_rgb.fill(0)
        power = float(np.clip(self.listener.asserved_total_power, 0.0, 1.0))
        chroma = self.listener.smoothed_chroma_values
        dom_pitch = int(np.argmax(chroma)) if len(chroma) > 0 else 0

        # Map dominant pitch to hue
        hue = (dom_pitch / 12.0)
        # Convert HSV to RGB
        r_f, g_f, b_f = self._hsv_to_rgb(hue, 0.85, power)

        # Center-expanding power pulse
        center = self.nb_leds // 2
        spread = int(power * (self.nb_leds // 2))

        for i in range(spread):
            decay = 1.0 - (i / max(1, spread))
            r = int(r_f * decay * 255)
            g = int(g_f * decay * 255)
            b = int(b_f * decay * 255)
            if center - i >= 0:
                self.led_rgb[center - i] = (r, g, b)
            if center + i < self.nb_leds:
                self.led_rgb[center + i] = (r, g, b)

        # Flash kick pulses at tips
        t_since_beat = time.time() - self.last_beat_visual_time
        if t_since_beat < 0.20 and self.last_beat_was_real:
            beat_intensity = 1.0 - (t_since_beat / 0.20)
            col = self.last_beat_visual_color
            flash_rgb = (int(col[0] * beat_intensity), int(col[1] * beat_intensity), int(col[2] * beat_intensity))
            self.led_rgb[0] = flash_rgb
            self.led_rgb[-1] = flash_rgb

    @staticmethod
    def _hsv_to_rgb(h: float, s: float, v: float) -> Tuple[float, float, float]:
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i %= 6
        if i == 0: return v, t, p
        if i == 1: return q, v, p
        if i == 2: return p, v, t
        if i == 3: return p, q, v
        if i == 4: return t, p, v
        return v, p, q

    # =================================================================
    # DRAWING ROUTINES: HEADER & REFERENCE STRIP
    # =================================================================

    def _draw_header(self) -> None:
        title_surf = self.get_text(self.font_title, "VIALACTÉE MUSIC STUDIO", self.ACCENT_CYAN)
        self.screen.blit(title_surf, (40, 15))

        model_info = f"Model: {self.model_name} [{self.nb_bands} bands]"
        sub_surf = self.get_text(self.font_small, f"Predictive Flywheel & Real-Time DSP Lab │ {model_info}", self.TEXT_DIM)
        self.screen.blit(sub_surf, (title_surf.get_width() + 55, 18))

        # Track name
        song_name = os.path.basename(self.streamer.file_path)
        track_surf = self.get_text(self.font_main, f"Track [{self.song_index + 1}/{len(self.song_list)}]: {song_name}", self.TEXT_MAIN)
        self.screen.blit(track_surf, (self.width - track_surf.get_width() - 40, 16))

        # Interactive Progress Scrubber
        bar_x = 40
        bar_y = 48
        bar_w = self.width - 80
        bar_h = 8
        pygame.draw.rect(self.screen, self.PANEL_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        cur_time = self.streamer.get_current_time()
        tot_time = max(1.0, self.streamer.total_duration)
        progress = min(1.0, cur_time / tot_time)
        fill_w = int(bar_w * progress)

        if fill_w > 0:
            pygame.draw.rect(self.screen, self.ACCENT_CYAN, (bar_x, bar_y, fill_w, bar_h), border_radius=4)
        pygame.draw.circle(self.screen, (255, 255, 255), (bar_x + fill_w, bar_y + bar_h // 2), 5)

        # Scrubber Sub-labels
        cur_min, cur_sec = divmod(int(cur_time), 60)
        tot_min, tot_sec = divmod(int(tot_time), 60)
        time_str = f"{cur_min:02d}:{cur_sec:02d} / {tot_min:02d}:{tot_sec:02d}"
        time_surf = self.get_text(self.font_small, time_str, self.TEXT_DIM)
        hx = bar_x
        self.screen.blit(time_surf, (hx, bar_y + 12))
        hx += time_surf.get_width() + 18

        # A/V Sync readout
        sync_color = self.ACCENT_CYAN if self.sync_offset_ms != 0 else self.TEXT_DIM
        sync_label = f"A/V Sync: {self.sync_offset_ms:+.0f} ms"
        sync_surf = self.get_text(self.font_small, sync_label, sync_color)
        self.screen.blit(sync_surf, (hx, bar_y + 12))
        hx += sync_surf.get_width() + 18

        # Beat Trust (T, speaker-delayed) & Live Trust
        t_val = float(getattr(self.listener, 'beat_trust', 0.0))
        t_live = float(getattr(self.listener, 'live_beat_trust', t_val))
        t_color = self.ACCENT_GREEN if t_val >= 0.50 else (self.ACCENT_ORANGE if t_val >= 0.35 else self.ACCENT_RED)
        t_surf = self.get_text(self.font_small, f"Trust (T): {int(t_val * 100)}% (Live: {int(t_live * 100)}%)", t_color)
        self.screen.blit(t_surf, (hx, bar_y + 12))
        hx += t_surf.get_width() + 18

        # Rhythmic Salience (S, speaker-delayed) & Live Salience
        s_val = float(getattr(self.listener, 'rhythm_salience', 0.0))
        s_live = float(getattr(self.listener, 'live_rhythm_salience', s_val))
        s_color = self.ACCENT_GREEN if s_val >= 0.45 else (self.ACCENT_CYAN if s_val < 0.35 else self.ACCENT_ORANGE)
        s_surf = self.get_text(self.font_small, f"Salience (S): {int(s_val * 100)}% (Live: {int(s_live * 100)}%)", s_color)
        self.screen.blit(s_surf, (hx, bar_y + 12))
        hx += s_surf.get_width() + 18

        # Salience Gradient (ΔR)
        grad_val = float(getattr(self.listener, 'salience_gradient', 0.0))
        grad_color = self.ACCENT_MAGENTA if grad_val >= 0.40 else (self.ACCENT_CYAN if grad_val > 0.05 else self.TEXT_DIM)
        grad_surf = self.get_text(self.font_small, f"ΔR: {grad_val:+.2f}", grad_color)
        self.screen.blit(grad_surf, (hx, bar_y + 12))
        hx += grad_surf.get_width() + 18

        # Canonical Musical Regime Badge
        context = getattr(self.listener, 'context', None)
        if context is not None:
            curr_reg = context.current_regime
            reg_col = self.REGIME_COLORS.get(curr_reg, self.TEXT_MAIN)
            reg_icon = self.REGIME_ICONS.get(curr_reg, "●")
            reg_surf = self.get_text(self.font_small, f"[{reg_icon} {curr_reg.value}]", reg_col)
            self.screen.blit(reg_surf, (hx, bar_y + 12))
            hx += reg_surf.get_width() + 18

            countdown = float(context.drop_countdown)
            if countdown > 0.0 or curr_reg == MusicalRegime.PRE_DROP_BUILDUP:
                alert_surf = self.get_text(self.font_main, f"⚠️ DROP IN {countdown:.1f}s!", self.ACCENT_MAGENTA)
                self.screen.blit(alert_surf, (hx, bar_y + 10))

        # Toast notification
        if time.time() - self.status_msg_time < 3.0:
            msg_surf = self.get_text(self.font_main, self.status_msg, self.status_color)
            self.screen.blit(msg_surf, (self.width - msg_surf.get_width() - 40, bar_y + 10))

    def _draw_reference_led_strip(self) -> None:
        """Draws miniature horizontal reference strip of 80 LEDs."""
        strip_y = 78
        strip_h = 16
        strip_w = self.width - 80
        led_w = strip_w / float(self.nb_leds)

        # Background slot
        pygame.draw.rect(self.screen, (14, 16, 22), (40, strip_y, strip_w, strip_h), border_radius=3)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (40, strip_y, strip_w, strip_h), width=1, border_radius=3)

        for i in range(self.nb_leds):
            r, g, b = self.led_rgb[i]
            if r > 0 or g > 0 or b > 0:
                cx = int(40 + i * led_w + led_w / 2)
                cy = strip_y + strip_h // 2
                rad = max(2, int(led_w / 2) - 1)
                pygame.draw.circle(self.screen, (r, g, b), (cx, cy), rad)

    # =================================================================
    # PANEL 1: 5.0-SECOND ODF LOOKAHEAD OSCILLOSCOPE
    # =================================================================

    def _draw_panel_1_lookahead_oscilloscope(self) -> None:
        px = 40
        py = 104
        pw = self.width - 80
        ph = 175

        # Background & Header
        pygame.draw.rect(self.screen, self.PANEL_BG, (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (px, py, pw, ph), width=1, border_radius=8)

        head_surf = self.get_text(self.font_main, "PREDICTIVE ONSET DETECTION (ODF) & 5.0-SECOND LOOKAHEAD OSCILLOSCOPE", self.ACCENT_CYAN)
        self.screen.blit(head_surf, (px + 16, py + 10))

        sub_surf = self.get_text(self.font_small, "Future audio chunks streamed 5.0s ahead of speaker playback time — Wave travels RIGHT (Future) to LEFT (Speaker Now)", self.TEXT_DIM)
        self.screen.blit(sub_surf, (px + 16, py + 30))

        # Salience & Gradient telemetry in top-right of Panel 1
        s_val = float(getattr(self.listener, 'rhythm_salience', 0.0))
        s_live = float(getattr(self.listener, 'live_rhythm_salience', s_val))
        t_val = float(getattr(self.listener, 'beat_trust', 0.0))
        t_live = float(getattr(self.listener, 'live_beat_trust', t_val))
        grad_val = float(getattr(self.listener, 'salience_gradient', 0.0))
        scope_info = f"Spk S: {int(s_val*100)}% (Trust {int(t_val*100)}%) │ Live S: {int(s_live*100)}% (Trust {int(t_live*100)}%) │ ΔR: {grad_val:+.2f}"
        scope_surf = self.get_text(self.font_small, scope_info, self.ACCENT_MAGENTA if grad_val >= 0.40 else self.ACCENT_CYAN)
        self.screen.blit(scope_surf, (px + pw - scope_surf.get_width() - 16, py + 10))

        # Scope display area
        gx = px + 16
        gy = py + 52
        gw = pw - 32
        gh = ph - 64
        pygame.draw.rect(self.screen, (12, 14, 19), (gx, gy, gw, gh), border_radius=6)
        pygame.draw.rect(self.screen, (26, 32, 44), (gx, gy, gw, gh), width=1, border_radius=6)

        odf_buf = self.listener.analyzer.odf_buffer
        total_len = len(odf_buf)
        if total_len < 2:
            return

        lookahead_frames = int(self.listener.analyzer.lookahead_seconds * self.listener.analyzer.odf_fps)
        speaker_idx = max(0, min(total_len - 1, total_len - 1 - lookahead_frames))
        cursor_ratio = float(speaker_idx) / float(max(1, total_len - 1))
        cursor_x = gx + int(gw * cursor_ratio)

        # Highlight incoming drop buildup zone on the scope if active
        context = getattr(self.listener, 'context', None)
        countdown = float(getattr(context, 'drop_countdown', 0.0)) if context is not None else 0.0
        if countdown > 0.0 or (context and getattr(context, 'is_buildup', False)):
            drop_frame = speaker_idx + int(countdown * self.listener.analyzer.odf_fps)
            drop_frame = max(speaker_idx + 1, min(total_len - 1, drop_frame))
            drop_x = gx + int(gw * (drop_frame / float(max(1, total_len - 1))))
            buildup_w = max(4, drop_x - cursor_x)
            max_surf_w = min(buildup_w, gx + gw - cursor_x)
            if self._scope_buildup_surf is None or self._scope_buildup_surf.get_size() != (gw, gh):
                self._scope_buildup_surf = pygame.Surface((gw, gh), pygame.SRCALPHA)
            self._scope_buildup_surf.fill((0, 0, 0, 0))
            pulse_a = int(35 + 25 * math.sin(time.time() * 8.0))
            self._scope_buildup_surf.fill((255, 40, 130, pulse_a), rect=pygame.Rect(0, 0, max_surf_w, gh))
            self.screen.blit(self._scope_buildup_surf, (cursor_x, gy), area=pygame.Rect(0, 0, max_surf_w, gh))
            pygame.draw.line(self.screen, self.ACCENT_MAGENTA, (drop_x, gy), (drop_x, gy + gh), 2)
            drop_tag = self.get_text(self.font_small, f"▲ DROP IN {countdown:.1f}s", self.ACCENT_MAGENTA)
            self.screen.blit(drop_tag, (drop_x - drop_tag.get_width() // 2, gy + gh - 18))

        # Grid lines
        pygame.draw.line(self.screen, (22, 28, 38), (gx, gy + gh // 2), (gx + gw, gy + gh // 2), 1)
        for s in range(1, 6):
            sec_frame = speaker_idx + int(s * self.listener.analyzer.odf_fps)
            if sec_frame < total_len:
                sec_x = gx + int(gw * (sec_frame / float(max(1, total_len - 1))))
                pygame.draw.line(self.screen, (22, 28, 38), (sec_x, gy), (sec_x, gy + gh), 1)
                t_lbl = self.get_text(self.font_small, f"+{s}s", self.TEXT_MUTED)
                self.screen.blit(t_lbl, (sec_x - t_lbl.get_width() // 2, gy + 4))

        # Speaker Line (NOW)
        pygame.draw.line(self.screen, self.ACCENT_GOLD, (cursor_x, gy), (cursor_x, gy + gh), 2)
        speaker_lbl = self.get_text(self.font_small, "▼ SPEAKER NOW", self.ACCENT_GOLD)
        self.screen.blit(speaker_lbl, (cursor_x - speaker_lbl.get_width() // 2, gy - 14))

        max_val = max(15.0, float(np.max(odf_buf)))
        scale_y = (gh - 16) / max_val

        # Draw Baseline and Strong Peak threshold lines
        baseline = float(self.listener.analyzer.rolling_flux_baseline)
        strong_th = baseline * float(self.listener.analyzer.config.strong_peak_multiplier) + 0.1

        base_y = int(gy + gh - 8 - baseline * scale_y)
        th_y = int(gy + gh - 8 - strong_th * scale_y)

        if gy <= base_y <= gy + gh:
            pygame.draw.line(self.screen, (40, 70, 90), (gx, base_y), (gx + gw, base_y), 1)
        if gy <= th_y <= gy + gh:
            pygame.draw.line(self.screen, (90, 40, 40), (gx, th_y), (gx + gw, th_y), 1)

        # Plot ODF curve
        points = []
        for i in range(total_len):
            x = gx + int(gw * (i / float(max(1, total_len - 1))))
            val = odf_buf[i]
            y = int(gy + gh - 8 - val * scale_y)
            y = max(gy + 4, min(gy + gh - 4, y))
            points.append((x, y))

        if len(points) > 1:
            pygame.draw.lines(self.screen, (0, 180, 210), False, points, 2)

        # Overlay Pearson Template Pulse Wave for estimated BPM
        bpm = self.listener.bpm
        if bpm > 0:
            tau_frames = 60.0 * 60.0 / bpm  # frames per beat at 60 fps
            template_pts = []
            cur_phase = self.listener.beat_phase
            phase_offset = cur_phase * tau_frames

            for i in range(total_len):
                x = gx + int(gw * (i / float(max(1, total_len - 1))))
                delta_frames = i - speaker_idx
                phi = ((delta_frames + phase_offset) % tau_frames) / tau_frames
                dist = min(phi, 1.0 - phi)
                pulse = max(0.0, 1.0 - (dist / 0.1)) if dist < 0.1 else 0.0

                py_val = int(gy + gh - 8 - pulse * (gh * 0.4))
                template_pts.append((x, py_val))

            if len(template_pts) > 1:
                pygame.draw.lines(self.screen, (170, 0, 255), False, template_pts, 1)

        # Legend tags
        leg_odf = self.get_text(self.font_small, "● Spectral Flux (ODF)", self.ACCENT_CYAN)
        leg_tpl = self.get_text(self.font_small, "--- Oracle Template Pulse", self.ACCENT_PURPLE)
        self.screen.blit(leg_odf, (gx + gw - leg_odf.get_width() - 180, gy + 8))
        self.screen.blit(leg_tpl, (gx + gw - leg_tpl.get_width() - 10, gy + 8))

    # =================================================================
    # PANEL 2: ANTICIPATION FLYWHEEL & BEAT TRACKER CORE
    # =================================================================

    def _draw_panel_2_flywheel_and_beats(self) -> None:
        px = 40
        py = 290
        pw = 430
        ph = 280

        pygame.draw.rect(self.screen, self.PANEL_BG, (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (px, py, pw, ph), width=1, border_radius=8)

        # Header
        head_surf = self.get_text(self.font_main, "ANTICIPATION FLYWHEEL & BEAT TRACKER", self.ACCENT_CYAN)
        self.screen.blit(head_surf, (px + 16, py + 12))

        # Circular Flywheel Gauge
        cx = px + 85
        cy = py + 105
        radius = 56

        # Outer ring
        is_locked = self.listener.flywheel_status == "locked"
        ring_color = self.ACCENT_GREEN if is_locked else self.ACCENT_ORANGE
        pygame.draw.circle(self.screen, (22, 26, 36), (cx, cy), radius)
        pygame.draw.circle(self.screen, ring_color, (cx, cy), radius, 3)

        # Beat ticks (12, 3, 6, 9 o'clock)
        for angle_deg in [0, 90, 180, 270]:
            rad = math.radians(angle_deg - 90)
            tx1 = cx + int((radius - 7) * math.cos(rad))
            ty1 = cy + int((radius - 7) * math.sin(rad))
            tx2 = cx + int(radius * math.cos(rad))
            ty2 = cy + int(radius * math.sin(rad))
            col = (255, 255, 255) if angle_deg == 0 else (100, 115, 135)
            pygame.draw.line(self.screen, col, (tx1, ty1), (tx2, ty2), 2)

        # Continuous spinning phase needle
        phase = self.listener.beat_phase
        needle_angle = phase * 2 * math.pi - math.pi / 2
        nx = cx + int((radius - 12) * math.cos(needle_angle))
        ny = cy + int((radius - 12) * math.sin(needle_angle))
        pygame.draw.line(self.screen, (255, 255, 255), (cx, cy), (nx, ny), 3)
        pygame.draw.circle(self.screen, ring_color, (cx, cy), 6)

        # Center Status Text
        stat_txt = "LOCKED" if is_locked else "COASTING"
        stat_surf = self.get_text(self.font_mono, stat_txt, ring_color)
        self.screen.blit(stat_surf, (cx - stat_surf.get_width() // 2, cy + radius + 12))

        # Readout details on right side of gauge
        rx = px + 175
        ry = py + 48

        # BPM
        bpm_val = self.listener.bpm
        bpm_surf = self.get_text(self.font_big_num, f"{bpm_val:.1f}", self.TEXT_MAIN)
        self.screen.blit(bpm_surf, (rx, ry))
        bpm_lbl = self.get_text(self.font_small, "BPM", self.TEXT_DIM)
        self.screen.blit(bpm_lbl, (rx + bpm_surf.get_width() + 8, ry + 12))

        # 1. Beat Trust (Speaker Now)
        t_val = float(getattr(self.listener, 'beat_trust', 0.0))
        t_clamped = min(1.0, max(0.0, t_val))
        ry += 38
        context = getattr(self.listener, 'context', None)
        t_low = float(getattr(context, 'trust_low', 0.35)) if context else 0.35
        t_high = float(getattr(context, 'trust_high', 0.50)) if context else 0.50
        t_col = self.ACCENT_GREEN if t_clamped >= t_high else (self.ACCENT_ORANGE if t_clamped >= t_low else self.ACCENT_RED)
        t_tag = "LOCKED" if t_clamped >= t_high else ("COAST" if t_clamped >= t_low else "DRIFT")
        t_lbl = self.get_text(self.font_small, f"Beat Trust (T): {int(t_clamped * 100)}% [{t_tag}]", t_col)
        self.screen.blit(t_lbl, (rx, ry))

        bar_w = pw - (rx - px) - 20
        bar_h = 8
        pygame.draw.rect(self.screen, (14, 16, 22), (rx, ry + 15, bar_w, bar_h), border_radius=3)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (rx, ry + 15, bar_w, bar_h), width=1, border_radius=3)

        # Schmitt deadband [t_low, t_high]
        db_start = rx + int(bar_w * t_low)
        db_end = rx + int(bar_w * t_high)
        pygame.draw.rect(self.screen, (35, 30, 20), (db_start, ry + 15, max(1, db_end - db_start), bar_h))

        t_fill = int(bar_w * t_clamped)
        if t_fill > 0:
            pygame.draw.rect(self.screen, t_col, (rx, ry + 15, t_fill, bar_h), border_radius=3)

        # Threshold ticks at 35% and 50%
        pygame.draw.line(self.screen, (160, 160, 160), (db_start, ry + 13), (db_start, ry + 25), 1)
        pygame.draw.line(self.screen, (220, 220, 220), (db_end, ry + 13), (db_end, ry + 25), 1)

        # 2. Lookahead Beat Trust & Pearson Confidence
        ry += 26
        conf = float(np.clip(self.listener.beat_confidence, 0.0, 1.0))
        t_live = float(getattr(self.listener, 'live_beat_trust', conf))
        conf_lbl2 = self.get_text(self.font_small, f"Live Trust (+5s): {int(t_live * 100)}% │ r = {conf:+.2f}", self.TEXT_DIM)
        self.screen.blit(conf_lbl2, (rx, ry))

        pygame.draw.rect(self.screen, (14, 16, 22), (rx, ry + 15, bar_w, bar_h), border_radius=3)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (rx, ry + 15, bar_w, bar_h), width=1, border_radius=3)
        conf_fill = int(bar_w * conf)
        if conf_fill > 0:
            c_color = self.ACCENT_GREEN if conf >= 0.30 else (self.ACCENT_ORANGE if conf >= 0.15 else self.ACCENT_RED)
            pygame.draw.rect(self.screen, c_color, (rx, ry + 15, conf_fill, bar_h), border_radius=3)

        t15 = rx + int(bar_w * 0.15)
        t30 = rx + int(bar_w * 0.30)
        pygame.draw.line(self.screen, (160, 160, 160), (t15, ry + 13), (t15, ry + 25), 1)
        pygame.draw.line(self.screen, (220, 220, 220), (t30, ry + 13), (t30, ry + 25), 1)

        # Logarithmic Tempo Class (Octave Ring) & Harmonics
        ry += 26
        lbt_class = bpm_to_class(bpm_val)
        base_b = 60.0 * (2.0 ** lbt_class)
        class_str = f"Octave: {lbt_class:.3f} │ Harm: {base_b*0.5:.0f}/{base_b:.0f}/{base_b*1.5:.0f}"
        class_surf = self.get_text(self.font_small, class_str, self.TEXT_MUTED)
        self.screen.blit(class_surf, (rx, ry))

        # High-Impact Beat Strobe Flash Box (Bottom of Panel 2)
        strobe_y = py + 195
        strobe_w = pw - 32
        strobe_h = 70
        strobe_rect = pygame.Rect(px + 16, strobe_y, strobe_w, strobe_h)

        t_since_beat = time.time() - self.last_beat_visual_time
        flash_duration = 0.22

        if t_since_beat < flash_duration and t_since_beat >= 0:
            intensity = 1.0 - (t_since_beat / flash_duration)
            col = self.last_beat_visual_color
            bg_col = (int(col[0] * intensity * 0.4), int(col[1] * intensity * 0.4), int(col[2] * intensity * 0.4))
            pygame.draw.rect(self.screen, bg_col, strobe_rect, border_radius=6)
            pygame.draw.rect(self.screen, col, strobe_rect, width=2, border_radius=6)

            tag_txt = f"{'● REAL BEAT' if self.last_beat_was_real else '◐ DROPPED BEAT'} — {self.last_beat_visual_tag.upper()}"
            t_surf = self.get_text(self.font_title, tag_txt, (255, 255, 255))
            self.screen.blit(t_surf, (strobe_rect.centerx - t_surf.get_width() // 2, strobe_rect.centery - t_surf.get_height() // 2))
        else:
            pygame.draw.rect(self.screen, (14, 16, 22), strobe_rect, border_radius=6)
            pygame.draw.rect(self.screen, (28, 34, 46), strobe_rect, width=1, border_radius=6)
            idle_surf = self.get_text(self.font_mono, "WAITING FOR BEAT IMPULSE", (70, 80, 95))
            self.screen.blit(idle_surf, (strobe_rect.centerx - idle_surf.get_width() // 2, strobe_rect.centery - idle_surf.get_height() // 2))

    # =================================================================
    # PANEL 3: 8-BAND FFT DYNAMICS & FLUX
    # =================================================================

    def _draw_panel_3_fft_dynamics(self) -> None:
        px = 490
        py = 290
        pw = 510
        ph = 280

        pygame.draw.rect(self.screen, self.PANEL_BG, (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (px, py, pw, ph), width=1, border_radius=8)

        raw_fft = self.listener.fft_band_values
        smooth_fft = self.listener.smoothed_fft_band_values
        asserved_fft = self.listener.asserved_fft_band
        band_flux = self.listener.band_flux

        num_bands = len(smooth_fft) if len(smooth_fft) > 0 else self.nb_bands
        head_surf = self.get_text(self.font_main, f"{num_bands}-BAND FREQUENCY DYNAMICS & TRANSIENT FLUX", self.ACCENT_CYAN)
        self.screen.blit(head_surf, (px + 16, py + 12))

        # Equalizer Bars Area
        gx = px + 16
        gy = py + 42
        gw = pw - 32
        gh = 175

        spacing = 4 if num_bands <= 8 else (2 if num_bands <= 16 else 1)
        col_w = max(2.0, (gw - spacing * (num_bands - 1)) / float(num_bands))

        max_raw = max(50.0, float(np.max(smooth_fft)) if len(smooth_fft) > 0 else 50.0)

        for i in range(num_bands):
            bx = int(gx + i * (col_w + spacing))
            bw = max(2, int(col_w))

            # Background slot
            pygame.draw.rect(self.screen, (14, 16, 22), (bx, gy, bw, gh), border_radius=3 if num_bands <= 16 else 1)

            # Transient flux LED indicator at top of each column
            has_peak = len(band_flux) > i and band_flux[i] > 5.0
            led_col = self.ACCENT_RED if has_peak else (40, 48, 64)
            led_h = 4 if num_bands > 16 else 6
            pygame.draw.rect(self.screen, led_col, (bx + 1, gy + 4, max(1, bw - 2), led_h), border_radius=1)

            # Raw energy ghost bar
            r_val = raw_fft[i] if i < len(raw_fft) else 0.0
            r_h = min(gh - 20, int((r_val / max_raw) * (gh - 20)))
            if r_h > 0:
                pygame.draw.rect(self.screen, (30, 45, 60), (bx + 1, gy + gh - 6 - r_h, max(1, bw - 2), r_h), border_radius=1)

            # Smoothed energy solid bar
            s_val = smooth_fft[i] if i < len(smooth_fft) else 0.0
            s_h = min(gh - 20, int((s_val / max_raw) * (gh - 20)))
            if s_h > 0:
                # Continuous color gradient from cyan/blue to green/yellow
                frac = i / float(max(1, num_bands - 1))
                bar_color = self.ACCENT_CYAN if frac < 0.25 else (self.ACCENT_GREEN if frac < 0.65 else self.ACCENT_GOLD)
                pad = 2 if bw >= 12 else 0
                pygame.draw.rect(self.screen, bar_color, (bx + pad, gy + gh - 6 - s_h, max(1, bw - 2 * pad), s_h), border_radius=1)

            # Asserved floating peak cap
            a_val = asserved_fft[i] if i < len(asserved_fft) else 0.0
            a_y = gy + gh - 6 - int(a_val * (gh - 24))
            pygame.draw.rect(self.screen, (255, 255, 255), (bx + 1, a_y, max(1, bw - 2), 2))

            # Band short label
            show_label = (num_bands <= 8) or (num_bands <= 16 and i % 2 == 0) or (num_bands > 16 and (i % 4 == 0 or i == num_bands - 1))
            if show_label:
                b_lbl = self.get_text(self.font_small, f"B{i}" if num_bands <= 8 else f"{i}", self.TEXT_DIM)
                self.screen.blit(b_lbl, (bx + bw // 2 - b_lbl.get_width() // 2, gy + gh + 4))

        # Total Power Asservation footer within panel 3
        tp_y = py + 242
        tp_rect = pygame.Rect(px + 16, tp_y, pw - 32, 26)
        pygame.draw.rect(self.screen, (14, 16, 22), tp_rect, border_radius=4)

        tot_p = float(self.listener.asserved_total_power)
        p_fill = int(tp_rect.width * min(1.0, tot_p))
        if p_fill > 0:
            pygame.draw.rect(self.screen, self.ACCENT_PURPLE, (tp_rect.x, tp_rect.y, p_fill, tp_rect.height), border_radius=4)

        p_lbl = self.get_text(self.font_small, f"Total Power Asserved: {tot_p * 100:.0f}%", self.TEXT_MAIN)
        self.screen.blit(p_lbl, (tp_rect.x + 10, tp_rect.y + 6))

    # =================================================================
    # PANEL 4: 12-TONE CHROMAGRAM & KEY ANALYZER
    # =================================================================

    def _draw_panel_4_chromagram(self) -> None:
        px = 1020
        py = 290
        pw = 380
        ph = 280

        pygame.draw.rect(self.screen, self.PANEL_BG, (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (px, py, pw, ph), width=1, border_radius=8)

        head_surf = self.get_text(self.font_main, "12-TONE CHROMAGRAM & HARMONY", self.ACCENT_CYAN)
        self.screen.blit(head_surf, (px + 16, py + 12))

        chroma = self.listener.smoothed_chroma_values
        raw_chroma = self.listener.chroma_values
        dom_pitch = int(np.argmax(chroma)) if len(chroma) > 0 else 0
        dom_note = self.CHROMA_NAMES[dom_pitch]

        # Dominant pitch badge
        badge_surf = self.get_text(self.font_mono, f"KEY: {dom_note}", self.ACCENT_GOLD)
        self.screen.blit(badge_surf, (px + pw - badge_surf.get_width() - 16, py + 12))

        # Draw 12 vertical chroma bars
        gx = px + 16
        gy = py + 45
        gw = pw - 32
        gh = 175
        col_w = (gw - 22) / 12.0

        max_c = max(10.0, float(np.max(chroma)) if len(chroma) > 0 else 10.0)

        for i in range(12):
            bx = int(gx + i * (col_w + 2))
            bw = int(col_w)

            # Background slot
            pygame.draw.rect(self.screen, (14, 16, 22), (bx, gy, bw, gh), border_radius=3)

            val = chroma[i] if i < len(chroma) else 0.0
            bh = min(gh - 8, int((val / max_c) * (gh - 8)))

            if bh > 0:
                is_dom = (i == dom_pitch)
                c_col = self.ACCENT_GOLD if is_dom else self.ACCENT_BLUE
                pygame.draw.rect(self.screen, c_col, (bx + 2, gy + gh - 4 - bh, bw - 4, bh), border_radius=2)

            # Note label
            lbl_color = self.ACCENT_GOLD if (i == dom_pitch) else self.TEXT_DIM
            n_lbl = self.get_text(self.font_small, self.CHROMA_NAMES[i], lbl_color)
            self.screen.blit(n_lbl, (bx + bw // 2 - n_lbl.get_width() // 2, gy + gh + 4))

        # Circular note summary
        summary_y = py + 242
        note_text = f"Dominant Pitch Class: {dom_note} (Bin {dom_pitch})"
        s_surf = self.get_text(self.font_small, note_text, self.TEXT_MAIN)
        self.screen.blit(s_surf, (px + 16, summary_y + 4))

    # =================================================================
    # PANEL 5: STRUCTURAL NOVELTY & DROP SCOPE
    # =================================================================

    def _draw_panel_5_structural_novelty(self) -> None:
        px = 40
        py = 590
        pw = self.width - 80
        ph = 320

        pygame.draw.rect(self.screen, self.PANEL_BG, (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (px, py, pw, ph), width=1, border_radius=8)

        # Context state extraction
        context = getattr(self.listener, 'context', None)
        if context is not None:
            curr_reg = context.current_regime
            prev_reg = context.previous_regime
            blend = float(context.regime_blend)
            dwell = float(context.regime_dwell_time)
            countdown = float(context.drop_countdown)
            dwell_min = getattr(context, 'min_dwell_time', 1.0)
            is_locked = dwell < dwell_min
            is_rhythmic = bool(context.is_rhythmic)
            is_in_pocket = bool(context.is_in_pocket)
            is_buildup = bool(context.is_buildup)
            is_structural_change = bool(context.is_structural_change)
        else:
            curr_reg = MusicalRegime.DEEP_AMBIENT
            prev_reg = MusicalRegime.DEEP_AMBIENT
            blend = 1.0
            dwell = 0.0
            countdown = 0.0
            dwell_min = 1.0
            is_locked = False
            is_rhythmic = False
            is_in_pocket = False
            is_buildup = False
            is_structural_change = False

        reg_col = self.REGIME_COLORS.get(curr_reg, self.TEXT_MAIN)
        reg_bg = self.REGIME_BG_COLORS.get(curr_reg, (20, 24, 34))
        reg_icon = self.REGIME_ICONS.get(curr_reg, "●")

        # Header Title
        head_surf = self.get_text(self.font_main, "STRUCTURAL NOVELTY & REGIME STATE", self.ACCENT_CYAN)
        self.screen.blit(head_surf, (px + 16, py + 12))

        # Event Badges in Header
        bx = px + head_surf.get_width() + 25

        # Canonical Musical Scene Badge
        reg_badge_txt = f"{reg_icon} {getattr(curr_reg, 'value', str(curr_reg))}"
        reg_badge_surf = self.get_text(self.font_mono, reg_badge_txt, (255, 255, 255))
        reg_badge_w = reg_badge_surf.get_width() + 18
        reg_badge_rect = pygame.Rect(bx, py + 9, reg_badge_w, 22)
        pygame.draw.rect(self.screen, reg_bg, reg_badge_rect, border_radius=4)
        pygame.draw.rect(self.screen, reg_col, reg_badge_rect, width=1, border_radius=4)
        self.screen.blit(reg_badge_surf, (bx + 9, py + 12))
        bx += reg_badge_w + 10

        # Tier 3 Badges: [LOCKED], [SYNCOPATED], [SILENT], [IMMINENT], [IMPACT]
        b_locked = bool(getattr(context, 'is_locked', False))
        b_synco = bool(getattr(context, 'is_syncopated', False))
        b_silent = bool(getattr(context, 'is_silent', False))
        b_imminent = bool(getattr(context, 'is_drop_imminent', False))
        b_impact = bool(getattr(context, 'is_drop_impact', False) or curr_reg == MusicalScene.DROP_IMPACT)

        tier3_list = [
            ("LOCKED", b_locked, (40, 240, 120), (16, 50, 28)),
            ("SYNCOPATED", b_synco, (255, 160, 20), (55, 35, 12)),
            ("SILENT", b_silent, (70, 130, 240), (20, 28, 55)),
            ("IMMINENT", b_imminent, (255, 40, 130), (60, 15, 30)),
            ("IMPACT", b_impact, (255, 230, 80), (65, 55, 18)),
        ]
        for t_name, t_val, t_fg, t_bg in tier3_list:
            if t_val:
                t_surf = self.get_text(self.font_tiny, f"[{t_name}]", t_fg)
                tw = t_surf.get_width() + 10
                t_rect = pygame.Rect(bx, py + 9, tw, 22)
                pygame.draw.rect(self.screen, t_bg, t_rect, border_radius=4)
                pygame.draw.rect(self.screen, t_fg, t_rect, width=1, border_radius=4)
                self.screen.blit(t_surf, (bx + 5, py + 13))
                bx += tw + 6

        # Pre-drop countdown alert in header
        if curr_reg == MusicalScene.BUILDUP or countdown > 0.0:
            c_surf = self.get_text(self.font_mono, f"⚠️ DROP IN {countdown:.2f}s", (255, 255, 255))
            c_w = c_surf.get_width() + 16
            c_rect = pygame.Rect(bx, py + 9, c_w, 22)
            pygame.draw.rect(self.screen, (70, 15, 35), c_rect, border_radius=4)
            pygame.draw.rect(self.screen, self.ACCENT_MAGENTA, c_rect, width=1, border_radius=4)
            self.screen.blit(c_surf, (bx + 8, py + 12))
            bx += c_w + 10

        # Verse / Chorus Drop Badge
        t_since_drop = time.time() - self.last_drop_time
        if t_since_drop < 1.5:
            d_surf = self.get_text(self.font_mono, "★ VERSE / CHORUS DROP", self.ACCENT_PURPLE)
            pygame.draw.rect(self.screen, (60, 20, 90), (bx, py + 9, d_surf.get_width() + 16, 22), border_radius=4)
            pygame.draw.rect(self.screen, self.ACCENT_PURPLE, (bx, py + 9, d_surf.get_width() + 16, 22), width=1, border_radius=4)
            self.screen.blit(d_surf, (bx + 8, py + 12))
            bx += d_surf.get_width() + 14

        # Song Cut / Transition Badge
        t_since_song = time.time() - self.last_song_change_time
        if t_since_song < 2.0:
            s_surf = self.get_text(self.font_mono, "⚡ SONG TRANSITION", self.ACCENT_ORANGE)
            pygame.draw.rect(self.screen, (90, 50, 20), (bx, py + 9, s_surf.get_width() + 16, 22), border_radius=4)
            pygame.draw.rect(self.screen, self.ACCENT_ORANGE, (bx, py + 9, s_surf.get_width() + 16, 22), width=1, border_radius=4)
            self.screen.blit(s_surf, (bx + 8, py + 12))

        # Real-time Graph Area
        gx = px + 16
        gy = py + 42
        gw = 710
        gh = ph - 54

        pygame.draw.rect(self.screen, (12, 14, 19), (gx, gy, gw, gh), border_radius=6)
        pygame.draw.rect(self.screen, (26, 32, 44), (gx, gy, gw, gh), width=1, border_radius=6)

        # Plot STM vs LTM Timbral Divergence (Cyan), LM (Orange), GM (Purple)
        n_pts = self.history_size
        idx_order = [(self.history_cursor + i) % n_pts for i in range(n_pts)]

        nov_arr = self.history_novelty[idx_order]
        lm_arr = self.history_lm[idx_order]
        gm_arr = self.history_gm[idx_order]

        max_val = max(1.0, float(np.max(gm_arr)), float(np.max(nov_arr)))
        scale_y = (gh - 16) / max_val

        nov_pts = []
        lm_pts = []
        gm_pts = []

        for i in range(n_pts):
            x = gx + int(gw * (i / float(n_pts - 1)))
            y_nov = int(gy + gh - 8 - nov_arr[i] * scale_y)
            y_lm = int(gy + gh - 8 - lm_arr[i] * scale_y)
            y_gm = int(gy + gh - 8 - gm_arr[i] * scale_y)

            nov_pts.append((x, max(gy + 4, min(gy + gh - 4, y_nov))))
            lm_pts.append((x, max(gy + 4, min(gy + gh - 4, y_lm))))
            gm_pts.append((x, max(gy + 4, min(gy + gh - 4, y_gm))))

        if len(nov_pts) > 1:
            pygame.draw.lines(self.screen, (170, 0, 255), False, gm_pts, 2)
            pygame.draw.lines(self.screen, self.ACCENT_ORANGE, False, lm_pts, 1)
            pygame.draw.lines(self.screen, self.ACCENT_CYAN, False, nov_pts, 2)

        # Legend
        leg_nov = self.get_text(self.font_small, "● Novelty (STM vs LTM)", self.ACCENT_CYAN)
        leg_lm = self.get_text(self.font_small, "--- Local Max (LM)", self.ACCENT_ORANGE)
        leg_gm = self.get_text(self.font_small, "--- Global Max (GM Macro Threshold)", self.ACCENT_PURPLE)

        self.screen.blit(leg_nov, (gx + 12, gy + 8))
        self.screen.blit(leg_lm, (gx + 12, gy + 22))
        self.screen.blit(leg_gm, (gx + 12, gy + 36))

        # Right sidebar layout
        rx = gx + gw + 14
        col1_x = rx
        col1_w = 275
        col2_x = col1_x + col1_w + 14
        col2_w = (px + pw - 16) - col2_x

        # Telemetry signals
        s_val = float(getattr(self.listener, 'rhythm_salience', 0.0))
        s_live = float(getattr(self.listener, 'live_rhythm_salience', s_val))
        t_val = float(getattr(self.listener, 'beat_trust', 0.0))
        t_live = float(getattr(self.listener, 'live_beat_trust', t_val))
        grad_val = float(getattr(self.listener, 'salience_gradient', 0.0))
        s_low = float(getattr(context, 'salience_low', 0.35)) if context else 0.35
        s_high = float(getattr(context, 'salience_high', 0.45)) if context else 0.45
        t_low = float(getattr(context, 'trust_low', 0.35)) if context else 0.35
        t_high = float(getattr(context, 'trust_high', 0.50)) if context else 0.50
        drop_th = float(getattr(context, 'drop_buildup_threshold', 0.40)) if context else 0.40

        # =============================================================
        # COLUMN 1: NOVELTY, SALIENCE & SALIENCE GRADIENT (ΔR)
        # =============================================================
        y1 = gy + 2

        # 1. Asserved Novelty Meter
        asserv_nov = float(self.listener.asserved_novelty)
        an_lbl = self.get_text(self.font_small, f"Asserved Novelty: {asserv_nov * 100:.0f}%", self.TEXT_MAIN)
        self.screen.blit(an_lbl, (col1_x, y1))
        y1 += 17

        an_rect = pygame.Rect(col1_x, y1, col1_w, 10)
        pygame.draw.rect(self.screen, (14, 16, 22), an_rect, border_radius=3)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, an_rect, width=1, border_radius=3)
        an_fill = int(an_rect.width * min(1.0, max(0.0, asserv_nov)))
        if an_fill > 0:
            an_col = self.ACCENT_PURPLE if asserv_nov >= 0.8 else self.ACCENT_CYAN
            pygame.draw.rect(self.screen, an_col, (an_rect.x, an_rect.y, an_fill, an_rect.height), border_radius=3)

        # Song cut threshold tick
        th_val = self.listener.analyzer.config.song_novelty_asserved_th
        th_x = col1_x + int(an_rect.width * min(1.0, th_val))
        pygame.draw.line(self.screen, self.ACCENT_RED, (th_x, y1 - 2), (th_x, y1 + 12), 2)
        th_lbl = self.get_text(self.font_tiny, f"Drop Th: {th_val:.2f}", self.TEXT_MUTED)
        self.screen.blit(th_lbl, (th_x - 22, y1 + 12))
        y1 += 26

        # 2. Memory Envelope Readouts
        detector = getattr(self.listener.analyzer, 'novelty_detector', None)
        stm_power = getattr(detector, 'stm_power', 0.0)
        ltm_power = getattr(detector, 'ltm_power', 0.0)
        novelty_lm = self.listener.novelty_lm
        novelty_gm = self.listener.novelty_gm
        sil_frames = getattr(detector, 'silence_frames', 0)
        sil_th = getattr(detector, 'silence_threshold_frames', 1)

        stm_lbl = self.get_text(self.font_tiny, f"STM: {stm_power:.2f}   LTM: {ltm_power:.2f}", self.TEXT_DIM)
        self.screen.blit(stm_lbl, (col1_x, y1))
        y1 += 13
        lm_lbl = self.get_text(self.font_tiny, f"LM: {novelty_lm:.3f}   GM: {novelty_gm:.3f}", self.ACCENT_ORANGE)
        self.screen.blit(lm_lbl, (col1_x, y1))
        y1 += 13
        sil_lbl = self.get_text(self.font_tiny, f"Silence: {sil_frames}/{sil_th} frames", self.TEXT_MUTED)
        self.screen.blit(sil_lbl, (col1_x, y1))
        y1 += 18

        # 3. Rhythmic Salience (S) with Schmitt deadband [s_low, s_high]
        s_col = self.ACCENT_GREEN if s_val >= s_high else (self.ACCENT_CYAN if s_val < s_low else self.ACCENT_ORANGE)
        s_tag = "POCKET" if s_val >= s_high else ("AMBIENT" if s_val < s_low else "HYST")
        s_lbl = self.get_text(self.font_small, f"Salience (S): {int(s_val * 100)}% [{s_tag}]", s_col)
        self.screen.blit(s_lbl, (col1_x, y1))

        live_s = self.get_text(self.font_tiny, f"Live: {int(s_live * 100)}%", self.TEXT_DIM)
        self.screen.blit(live_s, (col1_x + col1_w - live_s.get_width(), y1 + 1))
        y1 += 16

        # Salience meter bar
        s_bar = pygame.Rect(col1_x, y1, col1_w, 10)
        pygame.draw.rect(self.screen, (14, 16, 22), s_bar, border_radius=3)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, s_bar, width=1, border_radius=3)

        # Schmitt deadband [s_low, s_high] shaded
        db_s_start = col1_x + int(col1_w * s_low)
        db_s_end = col1_x + int(col1_w * s_high)
        pygame.draw.rect(self.screen, (35, 30, 20), (db_s_start, y1, max(1, db_s_end - db_s_start), 10))

        fill_s = int(col1_w * min(1.0, max(0.0, s_val)))
        if fill_s > 0:
            pygame.draw.rect(self.screen, s_col, (col1_x, y1, fill_s, 10), border_radius=3)

        # Deadband ticks
        pygame.draw.line(self.screen, (160, 160, 170), (db_s_start, y1 - 2), (db_s_start, y1 + 12), 1)
        pygame.draw.line(self.screen, (220, 220, 230), (db_s_end, y1 - 2), (db_s_end, y1 + 12), 1)

        leg_s = self.get_text(self.font_tiny, f"0%       {int(s_low*100)}% [Deadband] {int(s_high*100)}%     100%", self.TEXT_MUTED)
        self.screen.blit(leg_s, (col1_x, y1 + 12))
        y1 += 26

        # 4. Salience Gradient (ΔR) Bipolar Gauge
        g_col = self.ACCENT_MAGENTA if grad_val >= drop_th else (self.ACCENT_CYAN if grad_val > 0.05 else (self.ACCENT_ORANGE if grad_val < -0.05 else self.TEXT_DIM))
        g_arrow = "▲" if grad_val > 0.05 else ("▼" if grad_val < -0.05 else "●")
        g_lbl = self.get_text(self.font_small, f"Gradient (ΔR): {g_arrow} {grad_val:+.2f}", g_col)
        self.screen.blit(g_lbl, (col1_x, y1))

        trig_txt = "⚠️ BUILDUP!" if grad_val >= drop_th else ("Rising" if grad_val > 0.10 else "Stable")
        trig_surf = self.get_text(self.font_tiny, trig_txt, g_col)
        self.screen.blit(trig_surf, (col1_x + col1_w - trig_surf.get_width(), y1 + 1))
        y1 += 16

        # Bipolar gauge [-0.5, +0.5]
        g_bar = pygame.Rect(col1_x, y1, col1_w, 10)
        pygame.draw.rect(self.screen, (14, 16, 22), g_bar, border_radius=3)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, g_bar, width=1, border_radius=3)

        # Center line (0.0)
        cx_grad = col1_x + col1_w // 2
        pygame.draw.line(self.screen, (100, 110, 130), (cx_grad, y1 - 2), (cx_grad, y1 + 12), 1)

        # Pre-drop threshold tick (+drop_th)
        th_ratio = min(1.0, max(0.0, drop_th / 0.50))
        th_grad_x = cx_grad + int((col1_w // 2) * th_ratio)
        pygame.draw.line(self.screen, self.ACCENT_MAGENTA, (th_grad_x, y1 - 2), (th_grad_x, y1 + 12), 2)

        # Bipolar fill
        clamped_g = min(0.5, max(-0.5, grad_val))
        g_fill = int((col1_w // 2) * (clamped_g / 0.5))
        if g_fill > 0:
            pygame.draw.rect(self.screen, g_col, (cx_grad, y1, g_fill, 10), border_radius=2)
        elif g_fill < 0:
            pygame.draw.rect(self.screen, g_col, (cx_grad + g_fill, y1, -g_fill, 10), border_radius=2)

        leg_g = self.get_text(self.font_tiny, f"-0.50        0.00       +{drop_th:.2f} (Drop) +0.50", self.TEXT_MUTED)
        self.screen.blit(leg_g, (col1_x, y1 + 12))
        y1 += 26

        # 5. Semantic Context Flags Mini-Card
        flags_box = pygame.Rect(col1_x, y1, col1_w, max(28, gy + gh - y1 - 2))
        pygame.draw.rect(self.screen, (14, 16, 22), flags_box, border_radius=4)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, flags_box, width=1, border_radius=4)

        f1 = "● RHYTHMIC" if is_rhythmic else "○ AMBIENT"
        c1 = self.ACCENT_GREEN if is_rhythmic else self.ACCENT_CYAN
        self.screen.blit(self.get_text(self.font_tiny, f1, c1), (col1_x + 8, y1 + 5))

        f2 = "● IN POCKET" if is_in_pocket else "○ OFF POCKET"
        c2 = self.ACCENT_GREEN if is_in_pocket else self.TEXT_DIM
        self.screen.blit(self.get_text(self.font_tiny, f2, c2), (col1_x + 8, y1 + 18))

        f3 = "● BUILDUP" if is_buildup else "○ STEADY"
        c3 = self.ACCENT_MAGENTA if is_buildup else self.TEXT_MUTED
        self.screen.blit(self.get_text(self.font_tiny, f3, c3), (col1_x + 130, y1 + 5))

        f4 = "● STRUCT CUT" if is_structural_change else "○ NO CUT"
        c4 = self.ACCENT_PURPLE if is_structural_change else self.TEXT_MUTED
        self.screen.blit(self.get_text(self.font_tiny, f4, c4), (col1_x + 130, y1 + 18))

        # =============================================================
        # COLUMN 2: REGIME BLEND & 2x2 REGIME STATE MATRIX (T x S)
        # =============================================================
        y2 = gy + 2

        # Header & Dwell / Crossfade Row
        reg_title = self.get_text(self.font_small, "CANONICAL REGIME & PHASE PLANE", self.ACCENT_GOLD)
        self.screen.blit(reg_title, (col2_x, y2))
        y2 += 18

        # Large Active Regime Badge
        badge_w = 160
        badge_h = 24
        b_rect = pygame.Rect(col2_x, y2, badge_w, badge_h)
        pygame.draw.rect(self.screen, reg_bg, b_rect, border_radius=4)
        pygame.draw.rect(self.screen, reg_col, b_rect, width=1, border_radius=4)
        b_txt_surf = self.get_text(self.font_small, f"{reg_icon} {getattr(curr_reg, 'value', str(curr_reg))}", (255, 255, 255))
        self.screen.blit(b_txt_surf, (col2_x + 8, y2 + 4))

        # Dwell Time
        dwell_txt = f"Dwell: {dwell:.1f}s [{'🔒 LOCKED' if is_locked else '✓ STEADY'}]"
        dwell_col = self.ACCENT_ORANGE if is_locked else self.ACCENT_GREEN
        dwell_surf = self.get_text(self.font_tiny, dwell_txt, dwell_col)
        self.screen.blit(dwell_surf, (col2_x + col2_w - dwell_surf.get_width(), y2 + 6))
        y2 += 28

        # Transition Crossfade Progress
        pct_lbl = f"Crossfade: {int(blend * 100)}%" if blend < 1.0 else "Crossfade: 100% (Settled)"
        pct_col = self.ACCENT_GREEN if blend >= 0.99 else self.ACCENT_CYAN
        cf_surf = self.get_text(self.font_tiny, pct_lbl, pct_col)
        self.screen.blit(cf_surf, (col2_x, y2))

        if blend < 1.0:
            from_surf = self.get_text(self.font_tiny, f"From: {getattr(prev_reg, 'value', str(prev_reg))}", self.TEXT_MUTED)
            self.screen.blit(from_surf, (col2_x + col2_w - from_surf.get_width(), y2))
        y2 += 13

        cf_bar = pygame.Rect(col2_x, y2, col2_w, 6)
        pygame.draw.rect(self.screen, (14, 16, 22), cf_bar, border_radius=3)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, cf_bar, width=1, border_radius=3)
        fill_cf = int(col2_w * min(1.0, max(0.0, blend)))
        if fill_cf > 0:
            pygame.draw.rect(self.screen, pct_col, (col2_x, y2, fill_cf, 6), border_radius=3)
        y2 += 11

        # -------------------------------------------------------------
        # 2x2 Regime State Matrix (T x S) Phase Plane Mini-Grid
        # -------------------------------------------------------------
        grid_x = col2_x
        grid_y = y2
        grid_w = col2_w
        grid_h = max(110, gy + gh - y2 - 4)

        pygame.draw.rect(self.screen, (12, 14, 20), (grid_x, grid_y, grid_w, grid_h), border_radius=6)
        pygame.draw.rect(self.screen, (35, 42, 58), (grid_x, grid_y, grid_w, grid_h), width=1, border_radius=6)

        # Thresholds: T in [t_low, t_high], S in [s_low, s_high]
        # X mapping: Beat Trust T in [0, 1]
        x_t_low = grid_x + int(grid_w * t_low)
        x_t_high = grid_x + int(grid_w * t_high)
        # Y mapping: Salience S in [0, 1] (inverted: top is S=1.0, bottom is S=0.0)
        y_s_high = grid_y + int(grid_h * (1.0 - s_high))
        y_s_low = grid_y + int(grid_h * (1.0 - s_low))

        # Deadband shaded strips
        pygame.draw.rect(self.screen, (20, 24, 34), (x_t_low, grid_y, max(1, x_t_high - x_t_low), grid_h))
        pygame.draw.rect(self.screen, (20, 24, 34), (grid_x, y_s_high, grid_w, max(1, y_s_low - y_s_high)))

        # Active Quadrant Highlight
        b_synco_flag = bool(getattr(context, 'is_syncopated', False))
        b_locked_flag = bool(getattr(context, 'is_locked', False))
        if curr_reg == MusicalScene.GROOVE:
            if b_synco_flag:
                pygame.draw.rect(self.screen, (50, 30, 12), (grid_x, grid_y, max(1, x_t_low - grid_x), max(1, y_s_high - grid_y)))
            else:
                pygame.draw.rect(self.screen, (14, 45, 26), (x_t_high, grid_y, max(1, grid_x + grid_w - x_t_high), max(1, y_s_high - grid_y)))
        elif curr_reg == MusicalScene.CHILL:
            pygame.draw.rect(self.screen, (16, 24, 45), (grid_x, y_s_low, max(1, x_t_low - grid_x), max(1, grid_y + grid_h - y_s_low)))

        # Threshold lines
        pygame.draw.line(self.screen, (40, 48, 65), (x_t_low, grid_y), (x_t_low, grid_y + grid_h), 1)
        pygame.draw.line(self.screen, (40, 48, 65), (x_t_high, grid_y), (x_t_high, grid_y + grid_h), 1)
        pygame.draw.line(self.screen, (40, 48, 65), (grid_x, y_s_low), (grid_x + grid_w, y_s_low), 1)
        pygame.draw.line(self.screen, (40, 48, 65), (grid_x, y_s_high), (grid_x + grid_w, y_s_high), 1)

        # Quadrant Labels
        # Top-Left: GROOVE (SYNCO)
        cf_surf = self.get_text(self.font_tiny, "GROOVE (SYNCO)", (255, 160, 20) if (curr_reg == MusicalScene.GROOVE and b_synco_flag) else self.TEXT_MUTED)
        self.screen.blit(cf_surf, (grid_x + 6, grid_y + 4))

        # Top-Right: GROOVE (LOCKED)
        poc_surf = self.get_text(self.font_tiny, "GROOVE (LOCKED)", self.ACCENT_GREEN if (curr_reg == MusicalScene.GROOVE and b_locked_flag) else self.TEXT_MUTED)
        self.screen.blit(poc_surf, (x_t_high + 6, grid_y + 4))

        # Bottom-Left: CHILL
        amb_surf = self.get_text(self.font_tiny, "CHILL", self.ACCENT_BLUE if curr_reg == MusicalScene.CHILL else self.TEXT_MUTED)
        self.screen.blit(amb_surf, (grid_x + 6, y_s_low + 4))

        # Bottom-Right: GROOVE (PULSE)
        fp_surf = self.get_text(self.font_tiny, "GROOVE (PULSE)", self.ACCENT_GREEN if (curr_reg == MusicalScene.GROOVE and not b_synco_flag) else self.TEXT_MUTED)
        self.screen.blit(fp_surf, (x_t_high + 6, y_s_low + 4))

        # Center Hysteresis Label
        cx_db = (x_t_low + x_t_high) // 2
        cy_db = (y_s_low + y_s_high) // 2
        db_lbl = self.get_text(self.font_tiny, "HYST", self.TEXT_MUTED)
        self.screen.blit(db_lbl, (cx_db - db_lbl.get_width() // 2, cy_db - db_lbl.get_height() // 2))

        # Current (T, S) Point & Crosshairs
        pt_x = grid_x + int(grid_w * min(1.0, max(0.0, t_val)))
        pt_y = grid_y + int(grid_h * (1.0 - min(1.0, max(0.0, s_val))))

        # Crosshair lines
        pygame.draw.line(self.screen, (55, 65, 85), (grid_x, pt_y), (grid_x + grid_w, pt_y), 1)
        pygame.draw.line(self.screen, (55, 65, 85), (pt_x, grid_y), (pt_x, grid_y + grid_h), 1)

        # Glowing point
        pygame.draw.circle(self.screen, reg_col, (pt_x, pt_y), 5)
        pygame.draw.circle(self.screen, (255, 255, 255), (pt_x, pt_y), 2)

        # Coordinates label near point
        coord_txt = f"({t_val:.2f}, {s_val:.2f})"
        coord_surf = self.get_text(self.font_tiny, coord_txt, (255, 255, 255))
        coord_x = pt_x + 6 if pt_x + 6 + coord_surf.get_width() < grid_x + grid_w else pt_x - 6 - coord_surf.get_width()
        coord_y = pt_y - 11 if pt_y - 11 > grid_y else pt_y + 4
        self.screen.blit(coord_surf, (coord_x, coord_y))

        # Override Alert Banner for BUILDUP or DROP_IMPACT
        if curr_reg in (MusicalScene.BUILDUP, MusicalScene.DROP_IMPACT):
            banner_w = grid_w - 24
            banner_h = 22
            banner_x = grid_x + 12
            banner_y = grid_y + grid_h // 2 - banner_h // 2
            b_bg = self.REGIME_BG_COLORS.get(curr_reg, (65, 15, 35))
            b_border = self.REGIME_COLORS.get(curr_reg, self.ACCENT_MAGENTA)
            pygame.draw.rect(self.screen, b_bg, (banner_x, banner_y, banner_w, banner_h), border_radius=4)
            pygame.draw.rect(self.screen, b_border, (banner_x, banner_y, banner_w, banner_h), width=1, border_radius=4)

            b_msg = f"OVERRIDE: {getattr(curr_reg, 'value', str(curr_reg))}"
            if curr_reg == MusicalScene.BUILDUP and countdown > 0.0:
                b_msg += f" ({countdown:.2f}s)"
            ov_surf = self.get_text(self.font_tiny, b_msg, b_border)
            self.screen.blit(ov_surf, (banner_x + banner_w // 2 - ov_surf.get_width() // 2, banner_y + banner_h // 2 - ov_surf.get_height() // 2))

        # Axis Indicators
        axis_t = self.get_text(self.font_tiny, "Trust (T) →", self.TEXT_DIM)
        self.screen.blit(axis_t, (grid_x + grid_w - axis_t.get_width() - 4, grid_y + grid_h - 13))
        axis_s = self.get_text(self.font_tiny, "↑ Salience (S)", self.TEXT_DIM)
        self.screen.blit(axis_s, (grid_x + 4, grid_y + grid_h - 13))

    # =================================================================
    # PANEL 6: LIVE PARAMETER TUNING DRAWER ([T] KEY)
    # =================================================================

    def _draw_tuning_drawer(self) -> None:
        dw = 400
        row_h = 40
        row_gap = 4
        item_step = row_h + row_gap
        dh = 66 + len(self.tuning_params) * item_step + 14
        dx = self.width - dw - 40
        dy = max(40, (self.height - 35 - dh) // 2)

        # Semi-transparent backdrop surface (cached, zero heap allocation)
        if self._drawer_overlay_surf is None or self._drawer_overlay_surf.get_size() != (dw, dh):
            self._drawer_overlay_surf = pygame.Surface((dw, dh), pygame.SRCALPHA)
            self._drawer_overlay_surf.fill((16, 20, 28, 245))
        self.screen.blit(self._drawer_overlay_surf, (dx, dy))

        pygame.draw.rect(self.screen, self.ACCENT_GOLD, (dx, dy, dw, dh), width=2, border_radius=8)

        # Header
        t_head = self.get_text(self.font_main, "LIVE DSP PARAMETER TUNER [T]", self.ACCENT_GOLD)
        self.screen.blit(t_head, (dx + 16, dy + 14))

        t_sub = self.get_text(self.font_small, "Use [↑/↓] to select, [←/→] to adjust, [D] default", self.TEXT_DIM)
        self.screen.blit(t_sub, (dx + 16, dy + 34))

        # Parameters List
        py = dy + 58
        for i, p in enumerate(self.tuning_params):
            is_sel = (i == self.tuning_selected_idx)
            val = p["get"]()

            row_rect = pygame.Rect(dx + 12, py, dw - 24, row_h)
            if is_sel:
                pygame.draw.rect(self.screen, (32, 40, 56), row_rect, border_radius=4)
                pygame.draw.rect(self.screen, self.ACCENT_CYAN, row_rect, width=1, border_radius=4)

            name_color = self.ACCENT_CYAN if is_sel else self.TEXT_MAIN
            lbl_surf = self.get_text(self.font_small, p["label"], name_color)
            val_surf = self.get_text(self.font_mono, p["fmt"].format(val), self.ACCENT_GOLD if is_sel else self.TEXT_MAIN)

            self.screen.blit(lbl_surf, (dx + 20, py + 5))
            self.screen.blit(val_surf, (dx + dw - val_surf.get_width() - 25, py + 5))

            # Slider bar
            s_bar_w = dw - 45
            pygame.draw.rect(self.screen, (10, 12, 16), (dx + 20, py + 24, s_bar_w, 6), border_radius=3)
            ratio = (val - p["min"]) / max(1e-6, p["max"] - p["min"])
            fill_w = int(s_bar_w * np.clip(ratio, 0.0, 1.0))
            if fill_w > 0:
                pygame.draw.rect(self.screen, self.ACCENT_CYAN if is_sel else self.TEXT_DIM, (dx + 20, py + 24, fill_w, 6), border_radius=3)

            py += item_step

    # =================================================================
    # FOOTER BAR
    # =================================================================

    def _draw_footer(self) -> None:
        footer_y = self.height - 35
        shortcuts = [
            "[Space] Play/Pause",
            "[←/→] Seek ±5s",
            "[N/P] Next/Prev Song",
            "[1-9] Track Direct",
            "[K/L] A/V Sync (±10ms)",
            "[T] Parameter Tuner",
            "[+/-] Sensibility",
            "[Esc] Exit"
        ]
        total_str = "    │    ".join(shortcuts)
        f_surf = self.get_text(self.font_small, total_str, self.TEXT_DIM)
        self.screen.blit(f_surf, (self.width // 2 - f_surf.get_width() // 2, footer_y))


# =====================================================================
# CLI ENTRY POINT
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Vialactée Music Studio - Real-Time DSP & Music Analysis Laboratory")
    parser.add_argument("--song", "-s", type=str, default=None, help="Path to MP3 or WAV file")
    parser.add_argument("--leds", "-l", type=int, default=80, help="Number of LEDs in reference segment (default: 80)")
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="MultiBandOnsetAudioAnalyzer",
        help="Rhythm analyzer model class (e.g. MultiBandOnsetAudioAnalyzer, AudioAnalyzer, CostasLoopAudioAnalyzer, DualFlywheelAudioAnalyzer)"
    )
    args = parser.parse_args()

    song_path = args.song
    if song_path and not os.path.isabs(song_path) and not os.path.exists(song_path):
        repo_relative = os.path.join(_REPO_ROOT, song_path)
        if os.path.exists(repo_relative):
            song_path = repo_relative

    if not song_path:
        default_song = os.path.join(_REPO_ROOT, "assets", "musics", "mp3_files", "Palladium.mp3")
        if os.path.exists(default_song):
            song_path = default_song
        else:
            candidates = glob.glob(os.path.join(_REPO_ROOT, "assets", "musics", "mp3_files", "*.mp3"))
            song_path = candidates[0] if candidates else ""

    if not song_path or not os.path.exists(song_path):
        print(f"Error: No audio song found at '{song_path}'. Please provide --song <path>.")
        sys.exit(1)

    is_win = (sys.platform == "win32")
    if is_win:
        try:
            import ctypes
            ctypes.windll.winmm.timeBeginPeriod(1)
        except Exception:
            pass

    try:
        app = MusicStudioApp(song_path=song_path, nb_leds=args.leds, model_name=args.model)
        app.run()
    finally:
        if is_win:
            try:
                import ctypes
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass


if __name__ == "__main__":
    main()
