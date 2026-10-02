"""
mode_studio.py - Interactive Visual Mode Authoring & Test Studio

Provides bit-for-bit hardware-parity mode development for the Vialactée LED chandelier.
Runs the exact production Listener, AudioAnalyzer (Oracle Anticipation Flywheel),
and AudioIngestion pipeline with real-time synchronized sounddevice playback,
interactive Pygame rendering, live Oracle telemetry HUD, and instant code hot-reloading.
"""

from __future__ import annotations
import os
import sys
import time
import math
import glob
import inspect
import importlib
import traceback
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
from core.BaseAudioAnalyzer import BaseAudioAnalyzer
from core.AudioAnalyzer import AudioAnalyzer, bpm_to_class
from core.MusicalContextEngine import MusicalRegime
from modes.Mode import Mode


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
# AUDIO STREAMER WITH ZERO-DELAY LOOKAHEAD PRE-ROLL
# =====================================================================

class AudioStreamer:
    """
    Sample-accurate audio streamer using sounddevice with 5.0s predictive lookahead.
    Feeds future audio chunks to Listener.process_raw_audio() while streaming
    speaker-time audio to physical speakers in perfect synchronization.
    """

    def __init__(self, audio_file_path: str, listener: Listener, sample_rate: int = 44100):
        self.file_path = audio_file_path
        self.listener = listener
        self.sample_rate = sample_rate
        self.lookahead_seconds = getattr(listener.analyzer, 'lookahead_seconds', 5.0)
        self.lookahead_samples = int(self.lookahead_seconds * self.sample_rate)

        # Load audio data via soundfile (supports fast MP3/WAV read)
        print(f"Loading audio: {os.path.basename(audio_file_path)}...")
        raw_data, sr = sf.read(audio_file_path, dtype='float32')
        if sr != self.sample_rate:
            print(f"Resampling audio from {sr} Hz to {self.sample_rate} Hz for hardware parity...")
            import math
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

        self.hop_samples = int(round(self.sample_rate / 60.0))  # Exactly 735 samples at 44100 Hz

        # Playback cursor (speaker time in samples)
        self.speaker_sample_pos = 0
        self.ingest_sample_pos = 0
        self.dac_latency = 0.0
        self.is_playing = False
        self.is_finished = False

        # Internal sounddevice output stream
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
        """Executed inside sounddevice C-thread to feed speakers."""
        if not self.is_playing:
            outdata.fill(0)
            return

        # Measure true DAC buffer latency reported by audio hardware
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
        """Returns the sample currently playing at the speaker cone, subtracting hardware DAC delay."""
        dac_frames = int(self.dac_latency * self.sample_rate)
        return max(0, self.speaker_sample_pos - dac_frames)

    def get_current_time(self) -> float:
        return float(self.get_actual_speaker_sample()) / float(self.sample_rate)

    def seek(self, target_seconds: float, sync_offset_seconds: float = 0.0) -> None:
        """Seek to a specific song timestamp and re-prime the 5s lookahead buffer."""
        target_sample = int(np.clip(target_seconds * self.sample_rate, 0, max(0, self.total_samples - 1024)))
        self.speaker_sample_pos = target_sample
        if hasattr(self.listener, 'reset'):
            self.listener.reset()
        elif hasattr(self.listener.analyzer, 'reset'):
            self.listener.analyzer.reset()
        self.prime_analyzer(sync_offset_seconds)

    def prime_analyzer(self, sync_offset_seconds: float = 0.0) -> None:
        """
        Fast-forwards 300 frames (~5s lookahead) leading up to current speaker position.
        Ensures ODF lookahead buffer, template bank, and delay ring buffer are primed immediately.
        """
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

        # Space out timestamps across ring buffer so they drain frame-by-frame starting now
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
# DYNAMIC MODE DISCOVERY & HOT-RELOAD MANAGER
# =====================================================================

class ModeManager:
    """Discovers, instantiates, and hot-reloads lighting modes from modes/."""

    def __init__(self, modes_dir: str, listener: Listener, nb_leds: int = 80):
        self.modes_dir = modes_dir
        self.listener = listener
        self.nb_leds = nb_leds

        self.mode_catalog: List[Tuple[str, str, str]] = [] # (display_name, module_name, class_name)
        self.current_idx = 0
        self.active_mode_instance: Optional[Mode] = None
        self.active_module = None

        self.rgb_buffer = np.zeros((self.nb_leds, 3), dtype=np.int32)
        self.indexes = list(range(self.nb_leds))

        self.discover_modes()

    def discover_modes(self) -> None:
        """Scans modes/ for all Python files implementing Mode subclasses."""
        self.mode_catalog.clear()
        py_files = sorted(glob.glob(os.path.join(self.modes_dir, "*.py")))

        for path in py_files:
            fname = os.path.basename(path)
            if fname in ("Mode.py", "__init__.py"):
                continue

            mod_name = os.path.splitext(fname)[0]
            try:
                mod = importlib.import_module(f"modes.{mod_name}")
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if inspect.isclass(attr) and issubclass(attr, Mode) and attr is not Mode:
                        display_name = mod_name.replace("_mode", "").replace("_", " ").title()
                        self.mode_catalog.append((display_name, mod_name, attr_name))
                        break
            except Exception as e:
                print(f"Warning: could not inspect mode module {mod_name}: {e}")

        print(f"Discovered {len(self.mode_catalog)} modes in {self.modes_dir}.")

    def load_mode(self, index: int) -> Tuple[bool, str]:
        """Instantiates mode at given catalog index."""
        if not self.mode_catalog:
            return False, "No modes found in catalog"

        self.current_idx = index % len(self.mode_catalog)
        disp_name, mod_name, cls_name = self.mode_catalog[self.current_idx]

        try:
            mod = importlib.import_module(f"modes.{mod_name}")
            mod = importlib.reload(mod)
            self.active_module = mod
            cls = getattr(mod, cls_name)

            self.rgb_buffer.fill(0)
            self.active_mode_instance = cls(
                name=disp_name,
                segment_name="studio_preview",
                listener=self.listener,
                leds=None,
                indexes=self.indexes,
                rgb_list=self.rgb_buffer,
                infos={"shot_base_speed": 2.0}
            )
            self.active_mode_instance.isActiv = True
            return True, f"Loaded {disp_name} ({cls_name})"
        except Exception as e:
            err_msg = traceback.format_exc()
            print(f"Error loading mode {disp_name}:\n{err_msg}")
            return False, f"Error: {e}"

    def reload_current(self) -> Tuple[bool, str]:
        """Hot-reloads current mode from disk."""
        return self.load_mode(self.current_idx)

    def next_mode(self) -> Tuple[bool, str]:
        return self.load_mode(self.current_idx + 1)

    def prev_mode(self) -> Tuple[bool, str]:
        return self.load_mode(self.current_idx - 1)

    def render(self) -> None:
        """Executes rendering of the active mode into self.rgb_buffer."""
        if self.active_mode_instance is not None:
            try:
                self.active_mode_instance.render(buffer=self.rgb_buffer)
            except Exception as e:
                pass


# =====================================================================
# PYGAME STUDIO GUI & ORACLE TELEMETRY HUD
# =====================================================================

class StudioApp:
    """Pygame interface rendering the LED bar, playback timeline, and Oracle HUD."""

    # UI Theme Palette
    BG_COLOR = (15, 17, 23)
    PANEL_BG = (24, 28, 38)
    PANEL_BORDER = (42, 48, 65)
    TEXT_MAIN = (230, 235, 245)
    TEXT_DIM = (130, 140, 160)
    TEXT_MUTED = (90, 100, 120)
    ACCENT_CYAN = (0, 220, 255)
    ACCENT_GREEN = (40, 240, 120)
    ACCENT_ORANGE = (255, 160, 20)
    ACCENT_RED = (255, 60, 80)
    ACCENT_PURPLE = (180, 80, 255)
    ACCENT_MAGENTA = (255, 40, 130)
    ACCENT_GOLD = (255, 215, 0)
    ACCENT_BLUE = (70, 130, 240)

    REGIME_COLORS = {
        MusicalRegime.DEEP_AMBIENT: (70, 130, 240),
        MusicalRegime.FLOATING_PULSE: (0, 220, 255),
        MusicalRegime.THE_POCKET: (40, 240, 120),
        MusicalRegime.CHAOTIC_FILL: (255, 160, 20),
        MusicalRegime.PRE_DROP_BUILDUP: (255, 40, 130),
        MusicalRegime.STRUCTURAL_CHANGE: (180, 80, 255),
    }

    REGIME_BG_COLORS = {
        MusicalRegime.DEEP_AMBIENT: (18, 28, 55),
        MusicalRegime.FLOATING_PULSE: (12, 45, 60),
        MusicalRegime.THE_POCKET: (16, 55, 32),
        MusicalRegime.CHAOTIC_FILL: (60, 35, 12),
        MusicalRegime.PRE_DROP_BUILDUP: (65, 15, 35),
        MusicalRegime.STRUCTURAL_CHANGE: (50, 20, 70),
    }

    REGIME_ICONS = {
        MusicalRegime.DEEP_AMBIENT: "≋",
        MusicalRegime.FLOATING_PULSE: "◌",
        MusicalRegime.THE_POCKET: "●",
        MusicalRegime.CHAOTIC_FILL: "⚡",
        MusicalRegime.PRE_DROP_BUILDUP: "▲",
        MusicalRegime.STRUCTURAL_CHANGE: "✦",
    }

    def __init__(self, song_path: str, initial_mode_name: Optional[str] = None, nb_leds: int = 80, model_name: str = "MultiBandOnsetAudioAnalyzer"):
        pygame.init()
        pygame.font.init()

        self.width = 1380
        self.height = 760
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Vialactée Mode Studio — Hardware-Parity Oracle Lab")

        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.font_main = pygame.font.SysFont("Segoe UI", 15, bold=True)
        self.font_mono = pygame.font.SysFont("Consolas", 14)
        self.font_small = pygame.font.SysFont("Segoe UI", 12)
        self.font_tiny = pygame.font.SysFont("Segoe UI", 11)

        self.nb_leds = nb_leds
        self.is_vertical = False

        # Text rendering cache (avoids heap thrashing at 60 FPS)
        self._text_cache: Dict[Tuple[int, str, Tuple[int, int, int]], pygame.Surface] = {}
        self._pulse_glow_surf: Optional[pygame.Surface] = None

        # Find all available songs in assets/musics/mp3_files
        self.assets_music_dir = os.path.join(_REPO_ROOT, "assets", "musics", "mp3_files")
        self.song_list = sorted(glob.glob(os.path.join(self.assets_music_dir, "*.mp3")))
        self.song_index = 0
        norm_song = os.path.normpath(os.path.abspath(song_path)) if song_path else ""
        song_base = os.path.basename(song_path).lower() if song_path else ""

        found = False
        for i, s in enumerate(self.song_list):
            if os.path.normpath(os.path.abspath(s)) == norm_song or os.path.basename(s).lower() == song_base:
                self.song_index = i
                found = True
                break
        if not found and self.song_list:
            for i, s in enumerate(self.song_list):
                if "palladium" in os.path.basename(s).lower():
                    self.song_index = i
                    break

        # Rhythm Model Resolution & Dynamic Band Configuration
        self.model_class = load_studio_model_class(model_name, _REPO_ROOT)
        self.model_name = self.model_class.__name__
        self.nb_bands = int(getattr(self.model_class, "NB_AUDIO_BANDS", 8))

        # 1. Initialize Listener with exact production config and injected analyzer
        listener_infos = {
            "useMicrophone": True,
            "fakeDelay": 5.0,
            "latency": 0.0,
            "luminosity": 100,
            "sensibility": 100,
            "nb_of_fft_band": self.nb_bands,
            "nb_of_chroma": 12,
            "sample_rate": 44100,
            "buffer_size": 4096
        }
        self.listener = Listener(listener_infos, analyzer_class=self.model_class)
        # In mode_studio (direct digital audio feed), zero out the artificial microphone ADC buffer delay
        self.listener.dynamic_audio_latency = 0.0

        # Load persisted A/V sync calibration offset (milliseconds)
        self.sync_config_file = os.path.join(_HERE, "studio_sync.json")
        self.sync_offset_ms = 0.0
        if os.path.exists(self.sync_config_file):
            try:
                import json
                with open(self.sync_config_file, "r") as f:
                    cfg = json.load(f)
                    self.sync_offset_ms = float(cfg.get("sync_offset_ms", 0.0))
            except Exception:
                pass

        # 2. Initialize Audio Streamer
        self.streamer = AudioStreamer(self.song_list[self.song_index] if self.song_list else song_path, self.listener)

        # 3. Initialize Mode Manager
        modes_dir = os.path.join(_REPO_ROOT, "modes")
        self.mode_mgr = ModeManager(modes_dir, self.listener, self.nb_leds)

        # Select initial mode (default to Static_wave_mode if none specified)
        target_mode = (initial_mode_name or "Static_wave").lower()
        for idx, (_, mod_name, _) in enumerate(self.mode_mgr.mode_catalog):
            if target_mode in mod_name.lower():
                self.mode_mgr.current_idx = idx
                break

        success, msg = self.mode_mgr.load_mode(self.mode_mgr.current_idx)
        self.status_msg = msg
        self.status_msg_time = time.time()
        self.status_color = self.ACCENT_GREEN if success else self.ACCENT_RED

        # Prime lookahead buffer so initial playback begins locked
        self.streamer.prime_analyzer(self.sync_offset_ms / 1000.0)

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

    def save_sync_config(self) -> None:
        try:
            import json
            with open(self.sync_config_file, "w") as f:
                json.dump({"sync_offset_ms": self.sync_offset_ms}, f, indent=2)
        except Exception:
            pass

    def change_song(self, new_index: int) -> None:
        """Switch to another song in assets/musics/mp3_files."""
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

    def run(self) -> None:
        """Main application loop running at 60 FPS."""
        self.streamer.start_stream()
        self.streamer.is_playing = True
        running = True

        while running:
            # Handle Pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.streamer.is_playing = not self.streamer.is_playing
                        self.set_status("PAUSED" if not self.streamer.is_playing else "PLAYING", self.TEXT_MAIN)
                    elif event.key == pygame.K_r:
                        ok, msg = self.mode_mgr.reload_current()
                        self.set_status(f"HOT-RELOAD: {msg}", self.ACCENT_GREEN if ok else self.ACCENT_RED)
                    elif event.key == pygame.K_UP:
                        ok, msg = self.mode_mgr.prev_mode()
                        self.set_status(msg, self.ACCENT_CYAN)
                    elif event.key == pygame.K_DOWN:
                        ok, msg = self.mode_mgr.next_mode()
                        self.set_status(msg, self.ACCENT_CYAN)
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
                    elif event.key == pygame.K_o:
                        self.is_vertical = not self.is_vertical
                        self.set_status("Orientation: " + ("Vertical" if self.is_vertical else "Horizontal"), self.ACCENT_PURPLE)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Check if clicked on seek progress bar
                    mx, my = event.pos
                    if 40 <= mx <= self.width - 40 and 65 <= my <= 80:
                        ratio = (mx - 40) / float(self.width - 80)
                        target_sec = ratio * self.streamer.total_duration
                        self.streamer.seek(target_sec, self.sync_offset_ms / 1000.0)

            # Advance audio analysis pipeline & step modes
            if self.streamer.is_playing:
                self.streamer.advance_ingest_frame(self.sync_offset_ms / 1000.0)

            self.mode_mgr.render()

            # Render GUI
            self.screen.fill(self.BG_COLOR)
            self._draw_header()
            self._draw_led_bar()
            self._draw_telemetry_hud()
            self._draw_footer()

            pygame.display.flip()
            self.clock.tick(60)

        self.streamer.stop_stream()
        pygame.quit()

    # =================================================================
    # DRAWING ROUTINES
    # =================================================================

    def _draw_header(self) -> None:
        """Draws top title, mode selection, and interactive progress scrubber."""
        disp_name, _, _ = self.mode_mgr.mode_catalog[self.mode_mgr.current_idx]
        title_surf = self.get_text(self.font_title, disp_name.upper(), self.ACCENT_CYAN)
        self.screen.blit(title_surf, (40, 18))

        mode_num = f"Mode {self.mode_mgr.current_idx + 1}/{len(self.mode_mgr.mode_catalog)} │ Model: {self.model_name} [{self.nb_bands} bands]"
        num_surf = self.get_text(self.font_main, mode_num, self.TEXT_DIM)
        self.screen.blit(num_surf, (title_surf.get_width() + 55, 23))

        # Song Title & Status Badge
        song_name = os.path.basename(self.streamer.file_path)
        song_surf = self.get_text(self.font_main, f"Track: {song_name}", self.TEXT_MAIN)
        self.screen.blit(song_surf, (self.width - song_surf.get_width() - 40, 22))

        # Interactive Progress Scrubber
        bar_x = 40
        bar_y = 65
        bar_w = self.width - 80
        bar_h = 10
        pygame.draw.rect(self.screen, self.PANEL_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=5)

        cur_time = self.streamer.get_current_time()
        tot_time = max(1.0, self.streamer.total_duration)
        progress = min(1.0, cur_time / tot_time)
        fill_w = int(bar_w * progress)

        if fill_w > 0:
            pygame.draw.rect(self.screen, self.ACCENT_CYAN, (bar_x, bar_y, fill_w, bar_h), border_radius=5)

        # Scrubber thumb
        pygame.draw.circle(self.screen, (255, 255, 255), (bar_x + fill_w, bar_y + bar_h // 2), 6)

        # Time Labels and Sync Offset Readout
        cur_min, cur_sec = divmod(int(cur_time), 60)
        tot_min, tot_sec = divmod(int(tot_time), 60)
        time_str = f"{cur_min:02d}:{cur_sec:02d} / {tot_min:02d}:{tot_sec:02d}"
        time_surf = self.get_text(self.font_small, time_str, self.TEXT_DIM)
        hx = bar_x
        self.screen.blit(time_surf, (hx, bar_y + 14))
        hx += time_surf.get_width() + 18

        # A/V Sync Calibration Readout
        sync_color = self.ACCENT_CYAN if self.sync_offset_ms != 0 else self.TEXT_DIM
        sync_label = f"A/V Sync: {self.sync_offset_ms:+.0f} ms"
        sync_surf = self.get_text(self.font_small, sync_label, sync_color)
        self.screen.blit(sync_surf, (hx, bar_y + 14))
        hx += sync_surf.get_width() + 18

        # Context thresholds
        context = getattr(self.listener, 'context', None)
        s_low = float(getattr(context, 'salience_low', 0.35)) if context else 0.35
        s_high = float(getattr(context, 'salience_high', 0.45)) if context else 0.45
        t_low = float(getattr(context, 'trust_low', 0.35)) if context else 0.35
        t_high = float(getattr(context, 'trust_high', 0.50)) if context else 0.50
        drop_th = float(getattr(context, 'drop_buildup_threshold', 0.40)) if context else 0.40

        # Beat Confidence Quick Readout in Header
        conf_val = float(getattr(self.listener, 'beat_confidence', 0.0))
        conf_clamped = min(1.0, max(0.0, conf_val))
        conf_color = self.ACCENT_GREEN if conf_clamped >= 0.30 else (self.ACCENT_ORANGE if conf_clamped >= 0.15 else self.ACCENT_RED)
        conf_surf = self.get_text(self.font_small, f"Conf: {int(conf_clamped * 100)}%", conf_color)
        self.screen.blit(conf_surf, (hx, bar_y + 14))
        hx += conf_surf.get_width() + 18

        # Beat Trust (T, speaker-delayed) & Live Trust
        t_val = float(getattr(self.listener, 'beat_trust', 0.0))
        t_live = float(getattr(self.listener, 'live_beat_trust', t_val))
        t_color = self.ACCENT_GREEN if t_val >= t_high else (self.ACCENT_ORANGE if t_val >= t_low else self.ACCENT_RED)
        t_surf = self.get_text(self.font_small, f"Trust (T): {int(t_val * 100)}% (Live: {int(t_live * 100)}%)", t_color)
        self.screen.blit(t_surf, (hx, bar_y + 14))
        hx += t_surf.get_width() + 18

        # Rhythmic Salience (S, speaker-delayed) & Live Salience
        s_val = float(getattr(self.listener, 'rhythm_salience', 0.0))
        s_live = float(getattr(self.listener, 'live_rhythm_salience', s_val))
        s_color = self.ACCENT_GREEN if s_val >= s_high else (self.ACCENT_CYAN if s_val < s_low else self.ACCENT_ORANGE)
        s_surf = self.get_text(self.font_small, f"Salience (S): {int(s_val * 100)}% (Live: {int(s_live * 100)}%)", s_color)
        self.screen.blit(s_surf, (hx, bar_y + 14))
        hx += s_surf.get_width() + 18

        # Salience Gradient (ΔR)
        grad_val = float(getattr(self.listener, 'salience_gradient', 0.0))
        grad_color = self.ACCENT_MAGENTA if grad_val >= drop_th else (self.ACCENT_CYAN if grad_val > 0.05 else self.TEXT_DIM)
        grad_surf = self.get_text(self.font_small, f"ΔR: {grad_val:+.2f}", grad_color)
        self.screen.blit(grad_surf, (hx, bar_y + 14))
        hx += grad_surf.get_width() + 18

        # Active Musical Regime Badge
        if context is not None:
            curr_reg = context.current_regime
            reg_col = self.REGIME_COLORS.get(curr_reg, self.TEXT_MAIN)
            reg_icon = self.REGIME_ICONS.get(curr_reg, "●")
            reg_name = getattr(curr_reg, 'value', str(curr_reg))
            reg_surf = self.get_text(self.font_small, f"[{reg_icon} {reg_name}]", reg_col)
            self.screen.blit(reg_surf, (hx, bar_y + 14))
            hx += reg_surf.get_width() + 18

            countdown = float(context.drop_countdown)
            if countdown > 0.0 or curr_reg == MusicalRegime.PRE_DROP_BUILDUP:
                alert_surf = self.get_text(self.font_main, f"⚠️ DROP IN {countdown:.1f}s!", self.ACCENT_MAGENTA)
                self.screen.blit(alert_surf, (hx, bar_y + 12))

        # Toast notification message
        if time.time() - self.status_msg_time < 3.0:
            msg_surf = self.get_text(self.font_main, self.status_msg, self.status_color)
            self.screen.blit(msg_surf, (self.width - msg_surf.get_width() - 40, bar_y + 13))

    def _draw_led_bar(self) -> None:
        """Renders the physical LED strip with realistic round pixels, dark grid, and bloom."""
        panel_rect = pygame.Rect(40, 98, self.width - 80, 160)
        pygame.draw.rect(self.screen, self.PANEL_BG, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, panel_rect, width=1, border_radius=12)

        tag_surf = self.get_text(
            self.font_small,
            f"VIRTUAL CHANDELIER SEGMENT ({self.nb_leds} LEDs) — {'VERTICAL' if self.is_vertical else 'HORIZONTAL'}",
            self.TEXT_DIM
        )
        self.screen.blit(tag_surf, (55, 108))

        rgb = self.mode_mgr.rgb_buffer
        n_leds = self.nb_leds

        if not self.is_vertical:
            track_x = 60
            track_w = panel_rect.width - 40
            track_y = panel_rect.centery + 10
            track_h = 36

            # Dark aluminum extrusion channel
            pygame.draw.rect(self.screen, (10, 12, 16), (track_x, track_y - track_h // 2, track_w, track_h), border_radius=6)

            step = track_w / float(n_leds)
            r_led = max(3, int(step * 0.42))

            for i in range(n_leds):
                cx = int(track_x + (i + 0.5) * step)
                cy = track_y
                r = int(np.clip(rgb[i, 0], 0, 255))
                g = int(np.clip(rgb[i, 1], 0, 255))
                b = int(np.clip(rgb[i, 2], 0, 255))

                # Subtle bloom glow
                if r > 30 or g > 30 or b > 30:
                    glow_color = (r // 4, g // 4, b // 4)
                    pygame.draw.circle(self.screen, glow_color, (cx, cy), r_led + 4)

                # Bright LED core
                pygame.draw.circle(self.screen, (r, g, b), (cx, cy), r_led)
        else:
            # Vertical orientation preview
            track_x = panel_rect.centerx
            track_y = panel_rect.top + 30
            track_h = panel_rect.height - 45
            track_w = 34

            pygame.draw.rect(self.screen, (10, 12, 16), (track_x - track_w // 2, track_y, track_w, track_h), border_radius=6)
            step = track_h / float(n_leds)
            r_led = max(3, int(step * 0.42))

            for i in range(n_leds):
                cx = track_x
                cy = int(track_y + (i + 0.5) * step)
                r = int(np.clip(rgb[i, 0], 0, 255))
                g = int(np.clip(rgb[i, 1], 0, 255))
                b = int(np.clip(rgb[i, 2], 0, 255))

                if r > 30 or g > 30 or b > 30:
                    pygame.draw.circle(self.screen, (r // 4, g // 4, b // 4), (cx, cy), r_led + 3)
                pygame.draw.circle(self.screen, (r, g, b), (cx, cy), r_led)

    def _draw_telemetry_hud(self) -> None:
        """Renders the 5 Oracle telemetry cards: Flywheel, Regime & Context, Salience & Trust, Beat Badges, Spectral/Harmony."""
        hud_y = 272
        hud_h = 425
        n_cards = 5
        card_w = (self.width - 80 - (n_cards - 1) * 15) // n_cards
        spacing = 15

        # Card 1: Anticipation Flywheel & BPM
        self._draw_flywheel_card(40, hud_y, card_w, hud_h)

        # Card 2: Musical Context & Canonical Regime Engine
        self._draw_context_card(40 + (card_w + spacing) * 1, hud_y, card_w, hud_h)

        # Card 3: Rhythmic Salience (S), Beat Trust (T) & Salience Gradient (ΔR)
        self._draw_salience_trust_card(40 + (card_w + spacing) * 2, hud_y, card_w, hud_h)

        # Card 4: Beat & Transient Tagging
        self._draw_beat_card(40 + (card_w + spacing) * 3, hud_y, card_w, hud_h)

        # Card 5: Spectral Dynamics, Total Power & Chromagram Harmony
        self._draw_spectral_card(40 + (card_w + spacing) * 4, hud_y, card_w, hud_h)

    def _draw_context_card(self, x: int, y: int, w: int, h: int) -> None:
        """Card 2: Real-time Musical Context Engine, Canonical Regimes, Transition Crossfade & 2x2 State Matrix."""
        card_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, self.PANEL_BG, card_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card_rect, width=1, border_radius=12)

        header = self.get_text(self.font_main, "MUSICAL REGIME", self.ACCENT_GOLD)
        self.screen.blit(header, (x + 16, y + 14))

        context = getattr(self.listener, 'context', None)
        if context is None:
            no_ctx = self.get_text(self.font_small, "Musical Context Engine Inactive", self.TEXT_MUTED)
            self.screen.blit(no_ctx, (x + 16, y + 46))
            return

        curr_reg = context.current_regime
        prev_reg = context.previous_regime
        blend = float(context.regime_blend)
        dwell = float(context.regime_dwell_time)
        countdown = float(context.drop_countdown)

        reg_col = self.REGIME_COLORS.get(curr_reg, self.TEXT_MAIN)
        reg_bg = self.REGIME_BG_COLORS.get(curr_reg, (20, 24, 34))
        reg_icon = self.REGIME_ICONS.get(curr_reg, "●")
        reg_name = getattr(curr_reg, 'value', str(curr_reg))

        # 1. Primary Regime Badge
        badge_rect = pygame.Rect(x + 16, y + 42, w - 32, 42)
        pygame.draw.rect(self.screen, reg_bg, badge_rect, border_radius=8)
        pygame.draw.rect(self.screen, reg_col, badge_rect, width=2, border_radius=8)

        # Pulse glow if in PRE_DROP_BUILDUP (cached surface, zero heap allocation)
        if curr_reg == MusicalRegime.PRE_DROP_BUILDUP:
            glow_w = w - 32
            glow_h = 42
            if self._pulse_glow_surf is None or self._pulse_glow_surf.get_size() != (glow_w, glow_h):
                self._pulse_glow_surf = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)
            pulse_alpha = int(128 + 127 * math.sin(time.time() * 8.0))
            self._pulse_glow_surf.fill((255, 40, 130, pulse_alpha // 3))
            self.screen.blit(self._pulse_glow_surf, badge_rect.topleft)

        badge_txt = f"{reg_icon} {reg_name}"
        badge_surf = self.get_text(self.font_main, badge_txt, (255, 255, 255))
        self.screen.blit(badge_surf, (badge_rect.centerx - badge_surf.get_width() // 2, badge_rect.centery - badge_surf.get_height() // 2))

        # Regime Description
        desc_map = {
            MusicalRegime.THE_POCKET: "Solid groove • High S & T",
            MusicalRegime.DEEP_AMBIENT: "Atmospheric drift • Low S & T",
            MusicalRegime.FLOATING_PULSE: "Metric pulse • Low S, High T",
            MusicalRegime.CHAOTIC_FILL: "Aperiodic fill • High S, Low T",
            MusicalRegime.PRE_DROP_BUILDUP: "Salience spike • Drop imminent!",
            MusicalRegime.STRUCTURAL_CHANGE: "Section / song boundary cut",
        }
        desc_txt = desc_map.get(curr_reg, "Active musical context state")
        desc_surf = self.get_text(self.font_tiny, desc_txt, self.TEXT_DIM)
        self.screen.blit(desc_surf, (x + 16, y + 88))

        # 2. Transition Crossfade (Blend Progress)
        cy = y + 108
        self.screen.blit(self.get_text(self.font_tiny, "CROSSFADE PROGRESS", self.TEXT_DIM), (x + 16, cy))

        pct_col = self.ACCENT_GREEN if blend >= 0.99 else self.ACCENT_CYAN
        pct_lbl = f"{int(blend * 100)}%" if blend < 0.99 else "100% (Settled)"
        pct_surf = self.get_text(self.font_mono, pct_lbl, pct_col)
        self.screen.blit(pct_surf, (x + w - pct_surf.get_width() - 16, cy))

        # Progress bar
        cy += 15
        bar_w = w - 32
        bar_h = 6
        pygame.draw.rect(self.screen, (14, 16, 22), (x + 16, cy, bar_w, bar_h), border_radius=3)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (x + 16, cy, bar_w, bar_h), width=1, border_radius=3)
        fill_w = int(bar_w * min(1.0, max(0.0, blend)))
        if fill_w > 0:
            pygame.draw.rect(self.screen, pct_col, (x + 16, cy, fill_w, bar_h), border_radius=3)

        # 3. Dwell Time & Stability Gate (Compact formatting avoids horizontal text overlap)
        cy += 14
        dwell_min = getattr(context, 'min_dwell_time', 1.0)
        is_locked = dwell < dwell_min
        dwell_txt = f"Dwell: {dwell:.1f}s [{'🔒' if is_locked else '✓'}]"
        dwell_col = self.ACCENT_ORANGE if is_locked else self.ACCENT_GREEN
        dwell_surf = self.get_text(self.font_tiny, dwell_txt, dwell_col)
        self.screen.blit(dwell_surf, (x + 16, cy))

        if blend < 1.0:
            reg_short = {
                MusicalRegime.THE_POCKET: "POCKET",
                MusicalRegime.DEEP_AMBIENT: "AMBIENT",
                MusicalRegime.FLOATING_PULSE: "PULSE",
                MusicalRegime.CHAOTIC_FILL: "FILL",
                MusicalRegime.PRE_DROP_BUILDUP: "BUILDUP",
                MusicalRegime.STRUCTURAL_CHANGE: "STRUCT",
            }
            from_name = reg_short.get(prev_reg, getattr(prev_reg, 'value', str(prev_reg)))
            from_surf = self.get_text(self.font_tiny, f"From: {from_name}", self.TEXT_MUTED)
            self.screen.blit(from_surf, (x + w - from_surf.get_width() - 16, cy))

        # 4. Drop Countdown Alert Box or Semantic Flags
        cy += 20
        if curr_reg == MusicalRegime.PRE_DROP_BUILDUP or countdown > 0.0:
            drop_box = pygame.Rect(x + 16, cy, w - 32, 54)
            pygame.draw.rect(self.screen, (60, 15, 30), drop_box, border_radius=6)
            pygame.draw.rect(self.screen, self.ACCENT_MAGENTA, drop_box, width=2, border_radius=6)

            c_lbl = self.get_text(self.font_tiny, "⚠️ INCOMING DROP COUNTDOWN", self.ACCENT_MAGENTA)
            self.screen.blit(c_lbl, (drop_box.centerx - c_lbl.get_width() // 2, drop_box.y + 6))

            c_num = self.get_text(self.font_main, f"{countdown:.2f} s", (255, 255, 255))
            self.screen.blit(c_num, (drop_box.centerx - c_num.get_width() // 2, drop_box.y + 22))

            # Shrinking countdown bar
            lookahead = getattr(self.listener.analyzer, 'lookahead_seconds', 5.0)
            c_ratio = min(1.0, max(0.0, countdown / max(0.1, lookahead)))
            c_bar_w = int((w - 48) * c_ratio)
            pygame.draw.rect(self.screen, (20, 24, 34), (x + 24, drop_box.bottom - 8, w - 48, 4), border_radius=2)
            if c_bar_w > 0:
                pygame.draw.rect(self.screen, self.ACCENT_MAGENTA, (x + 24, drop_box.bottom - 8, c_bar_w, 4), border_radius=2)
            box_bottom = drop_box.bottom
        else:
            # Semantic Flags Display
            flags_box = pygame.Rect(x + 16, cy, w - 32, 54)
            pygame.draw.rect(self.screen, (14, 16, 22), flags_box, border_radius=6)
            pygame.draw.rect(self.screen, self.PANEL_BORDER, flags_box, width=1, border_radius=6)

            self.screen.blit(self.get_text(self.font_tiny, "SEMANTIC CONTEXT FLAGS", self.TEXT_DIM), (x + 22, cy + 5))

            f1 = "● RHYTHMIC" if context.is_rhythmic else "○ AMBIENT"
            c1 = self.ACCENT_GREEN if context.is_rhythmic else self.ACCENT_CYAN
            self.screen.blit(self.get_text(self.font_tiny, f1, c1), (x + 22, cy + 20))

            f2 = "● IN POCKET" if context.is_in_pocket else "○ OFF POCKET"
            c2 = self.ACCENT_GREEN if context.is_in_pocket else self.TEXT_DIM
            self.screen.blit(self.get_text(self.font_tiny, f2, c2), (x + 22, cy + 34))

            f3 = "● BUILDUP" if context.is_buildup else "○ STEADY"
            c3 = self.ACCENT_MAGENTA if context.is_buildup else self.TEXT_MUTED
            self.screen.blit(self.get_text(self.font_tiny, f3, c3), (x + 120, cy + 20))

            f4 = "● STRUCT CUT" if context.is_structural_change else "○ NO CUT"
            c4 = self.ACCENT_PURPLE if context.is_structural_change else self.TEXT_MUTED
            self.screen.blit(self.get_text(self.font_tiny, f4, c4), (x + 120, cy + 34))
            box_bottom = flags_box.bottom

        # -------------------------------------------------------------
        # 5. 2x2 Canonical Regime State Matrix (T x S) Phase Plane Mini-Grid
        # -------------------------------------------------------------
        grid_x = x + 16
        grid_y = box_bottom + 8
        grid_w = w - 32
        grid_h = h - (grid_y - y) - 12

        pygame.draw.rect(self.screen, (12, 14, 20), (grid_x, grid_y, grid_w, grid_h), border_radius=6)
        pygame.draw.rect(self.screen, (35, 42, 58), (grid_x, grid_y, grid_w, grid_h), width=1, border_radius=6)

        t_low = float(getattr(context, "trust_low", 0.35))
        t_high = float(getattr(context, "trust_high", 0.50))
        s_low = float(getattr(context, "salience_low", 0.35))
        s_high = float(getattr(context, "salience_high", 0.45))

        t_val = float(getattr(self.listener, "beat_trust", 0.0))
        s_val = float(getattr(self.listener, "rhythm_salience", 0.0))

        # Thresholds: T in [t_low, t_high], S in [s_low, s_high]
        x_t_low = grid_x + int(grid_w * t_low)
        x_t_high = grid_x + int(grid_w * t_high)
        y_s_high = grid_y + int(grid_h * (1.0 - s_high))
        y_s_low = grid_y + int(grid_h * (1.0 - s_low))

        # Deadband shaded strips
        pygame.draw.rect(self.screen, (20, 24, 34), (x_t_low, grid_y, max(1, x_t_high - x_t_low), grid_h))
        pygame.draw.rect(self.screen, (20, 24, 34), (grid_x, y_s_high, grid_w, max(1, y_s_low - y_s_high)))

        # Active Quadrant Highlight
        if curr_reg == MusicalRegime.CHAOTIC_FILL:
            pygame.draw.rect(self.screen, (50, 30, 12), (grid_x, grid_y, max(1, x_t_low - grid_x), max(1, y_s_high - grid_y)))
        elif curr_reg == MusicalRegime.THE_POCKET:
            pygame.draw.rect(self.screen, (14, 45, 26), (x_t_high, grid_y, max(1, grid_x + grid_w - x_t_high), max(1, y_s_high - grid_y)))
        elif curr_reg == MusicalRegime.DEEP_AMBIENT:
            pygame.draw.rect(self.screen, (16, 24, 45), (grid_x, y_s_low, max(1, x_t_low - grid_x), max(1, grid_y + grid_h - y_s_low)))
        elif curr_reg == MusicalRegime.FLOATING_PULSE:
            pygame.draw.rect(self.screen, (10, 38, 50), (x_t_high, y_s_low, max(1, grid_x + grid_w - x_t_high), max(1, grid_y + grid_h - y_s_low)))

        # Threshold lines
        pygame.draw.line(self.screen, (40, 48, 65), (x_t_low, grid_y), (x_t_low, grid_y + grid_h), 1)
        pygame.draw.line(self.screen, (40, 48, 65), (x_t_high, grid_y), (x_t_high, grid_y + grid_h), 1)
        pygame.draw.line(self.screen, (40, 48, 65), (grid_x, y_s_low), (grid_x + grid_w, y_s_low), 1)
        pygame.draw.line(self.screen, (40, 48, 65), (grid_x, y_s_high), (grid_x + grid_w, y_s_high), 1)

        # Quadrant labels (tiny font)
        cf_col = self.REGIME_COLORS[MusicalRegime.CHAOTIC_FILL] if curr_reg == MusicalRegime.CHAOTIC_FILL else self.TEXT_MUTED
        cf_surf = self.get_text(self.font_tiny, "FILL", cf_col)
        self.screen.blit(cf_surf, (grid_x + 5, grid_y + 4))

        poc_col = self.REGIME_COLORS[MusicalRegime.THE_POCKET] if curr_reg == MusicalRegime.THE_POCKET else self.TEXT_MUTED
        poc_surf = self.get_text(self.font_tiny, "POCKET", poc_col)
        self.screen.blit(poc_surf, (x_t_high + 5, grid_y + 4))

        amb_col = self.REGIME_COLORS[MusicalRegime.DEEP_AMBIENT] if curr_reg == MusicalRegime.DEEP_AMBIENT else self.TEXT_MUTED
        amb_surf = self.get_text(self.font_tiny, "AMBIENT", amb_col)
        self.screen.blit(amb_surf, (grid_x + 5, y_s_low + 4))

        fp_col = self.REGIME_COLORS[MusicalRegime.FLOATING_PULSE] if curr_reg == MusicalRegime.FLOATING_PULSE else self.TEXT_MUTED
        fp_surf = self.get_text(self.font_tiny, "PULSE", fp_col)
        self.screen.blit(fp_surf, (x_t_high + 5, y_s_low + 4))

        # Center Hysteresis Label
        cx_db = (x_t_low + x_t_high) // 2
        cy_db = (y_s_low + y_s_high) // 2
        db_lbl = self.get_text(self.font_tiny, "HYST", self.TEXT_MUTED)
        self.screen.blit(db_lbl, (cx_db - db_lbl.get_width() // 2, cy_db - db_lbl.get_height() // 2))

        # Current (T, S) Point & Crosshairs
        pt_x = grid_x + int(grid_w * min(1.0, max(0.0, t_val)))
        pt_y = grid_y + int(grid_h * (1.0 - min(1.0, max(0.0, s_val))))

        pygame.draw.line(self.screen, (55, 65, 85), (grid_x, pt_y), (grid_x + grid_w, pt_y), 1)
        pygame.draw.line(self.screen, (55, 65, 85), (pt_x, grid_y), (pt_x, grid_y + grid_h), 1)

        pygame.draw.circle(self.screen, reg_col, (pt_x, pt_y), 4)
        pygame.draw.circle(self.screen, (255, 255, 255), (pt_x, pt_y), 2)

        # Coordinate label
        coord_txt = f"({t_val:.2f}, {s_val:.2f})"
        coord_surf = self.get_text(self.font_tiny, coord_txt, (255, 255, 255))
        coord_x = pt_x + 5 if pt_x + 5 + coord_surf.get_width() < grid_x + grid_w else pt_x - 5 - coord_surf.get_width()
        coord_y = pt_y - 11 if pt_y - 11 > grid_y else pt_y + 3
        self.screen.blit(coord_surf, (coord_x, coord_y))

        # Override Alert Banner for PRE_DROP_BUILDUP or STRUCTURAL_CHANGE
        if curr_reg in (MusicalRegime.PRE_DROP_BUILDUP, MusicalRegime.STRUCTURAL_CHANGE):
            banner_w = grid_w - 20
            banner_h = 20
            banner_x = grid_x + 10
            banner_y = grid_y + grid_h // 2 - banner_h // 2
            b_bg = self.REGIME_BG_COLORS.get(curr_reg, (65, 15, 35))
            b_border = self.REGIME_COLORS.get(curr_reg, self.ACCENT_MAGENTA)
            pygame.draw.rect(self.screen, b_bg, (banner_x, banner_y, banner_w, banner_h), border_radius=4)
            pygame.draw.rect(self.screen, b_border, (banner_x, banner_y, banner_w, banner_h), width=1, border_radius=4)

            b_msg = f"OVERRIDE: {reg_name}"
            if curr_reg == MusicalRegime.PRE_DROP_BUILDUP and countdown > 0.0:
                b_msg += f" ({countdown:.2f}s)"
            ov_surf = self.get_text(self.font_tiny, b_msg, b_border)
            self.screen.blit(ov_surf, (banner_x + banner_w // 2 - ov_surf.get_width() // 2, banner_y + banner_h // 2 - ov_surf.get_height() // 2))

        # Axis indicators
        axis_t = self.get_text(self.font_tiny, "T →", self.TEXT_DIM)
        self.screen.blit(axis_t, (grid_x + grid_w - axis_t.get_width() - 3, grid_y + grid_h - 12))
        axis_s = self.get_text(self.font_tiny, "↑ S", self.TEXT_DIM)
        self.screen.blit(axis_s, (grid_x + 3, grid_y + grid_h - 12))

    def _draw_salience_trust_card(self, x: int, y: int, w: int, h: int) -> None:
        """Card 3: Rhythmic Salience (S), Beat Trust (T), Schmitt Deadbands & Salience Gradient (ΔR)."""
        card_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, self.PANEL_BG, card_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card_rect, width=1, border_radius=12)

        header = self.get_text(self.font_main, "SALIENCE & TRUST", self.ACCENT_CYAN)
        self.screen.blit(header, (x + 16, y + 14))

        context = getattr(self.listener, 'context', None)
        s_low = float(getattr(context, 'salience_low', 0.35)) if context else 0.35
        s_high = float(getattr(context, 'salience_high', 0.45)) if context else 0.45
        t_low = float(getattr(context, 'trust_low', 0.35)) if context else 0.35
        t_high = float(getattr(context, 'trust_high', 0.50)) if context else 0.50
        drop_th = float(getattr(context, 'drop_buildup_threshold', 0.40)) if context else 0.40

        s_val = float(getattr(self.listener, 'rhythm_salience', 0.0))
        s_live = float(getattr(self.listener, 'live_rhythm_salience', s_val))
        t_val = float(getattr(self.listener, 'beat_trust', 0.0))
        t_live = float(getattr(self.listener, 'live_beat_trust', t_val))
        grad_val = float(getattr(self.listener, 'salience_gradient', 0.0))

        # -------------------------------------------------------------
        # 1. RHYTHMIC SALIENCE (S)
        # -------------------------------------------------------------
        sy = y + 46
        self.screen.blit(self.get_text(self.font_small, "RHYTHMIC SALIENCE (S)", self.TEXT_DIM), (x + 16, sy))

        s_col = self.ACCENT_GREEN if s_val >= s_high else (self.ACCENT_CYAN if s_val < s_low else self.ACCENT_ORANGE)
        s_tag = "POCKET" if s_val >= s_high else ("AMBIENT" if s_val < s_low else "HYSTERESIS")
        s_surf = self.get_text(self.font_title, f"{int(s_val * 100)}%", s_col)
        self.screen.blit(s_surf, (x + 16, sy + 16))

        tag_surf = self.get_text(self.font_mono, f"[{s_tag}]", s_col)
        self.screen.blit(tag_surf, (x + 22 + s_surf.get_width(), sy + 20))

        live_s_surf = self.get_text(self.font_tiny, f"Live (+5s): {int(s_live * 100)}%", self.TEXT_DIM)
        self.screen.blit(live_s_surf, (x + w - live_s_surf.get_width() - 16, sy + 22))

        # Meter with Schmitt deadband [s_low, s_high]
        bar_x = x + 16
        bar_y = sy + 44
        bar_w = w - 32
        bar_h = 10
        pygame.draw.rect(self.screen, (14, 16, 22), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=4)

        # Deadband background highlight [s_low, s_high]
        db_s_start = bar_x + int(bar_w * s_low)
        db_s_end = bar_x + int(bar_w * s_high)
        pygame.draw.rect(self.screen, (35, 30, 20), (db_s_start, bar_y, max(1, db_s_end - db_s_start), bar_h))

        fill_s = int(bar_w * min(1.0, max(0.0, s_val)))
        if fill_s > 0:
            pygame.draw.rect(self.screen, s_col, (bar_x, bar_y, fill_s, bar_h), border_radius=4)

        # Threshold ticks at s_low and s_high
        pygame.draw.line(self.screen, (160, 160, 170), (db_s_start, bar_y - 2), (db_s_start, bar_y + bar_h + 2), 1)
        pygame.draw.line(self.screen, (220, 220, 230), (db_s_end, bar_y - 2), (db_s_end, bar_y + bar_h + 2), 1)

        leg_s = self.get_text(self.font_tiny, f"0%       {int(s_low*100)}% [Deadband] {int(s_high*100)}%     100%", self.TEXT_MUTED)
        self.screen.blit(leg_s, (bar_x, bar_y + 12))

        # -------------------------------------------------------------
        # 2. BEAT TRUST (T)
        # -------------------------------------------------------------
        ty = bar_y + 34
        self.screen.blit(self.get_text(self.font_small, "BEAT TRUST (T)", self.TEXT_DIM), (x + 16, ty))

        t_col = self.ACCENT_GREEN if t_val >= t_high else (self.ACCENT_ORANGE if t_val >= t_low else self.ACCENT_RED)
        t_tag = "TRUSTED" if t_val >= t_high else ("COASTING" if t_val >= t_low else "DRIFTING")
        t_surf = self.get_text(self.font_title, f"{int(t_val * 100)}%", t_col)
        self.screen.blit(t_surf, (x + 16, ty + 16))

        t_tag_surf = self.get_text(self.font_mono, f"[{t_tag}]", t_col)
        self.screen.blit(t_tag_surf, (x + 22 + t_surf.get_width(), ty + 20))

        live_t_surf = self.get_text(self.font_tiny, f"Live (+5s): {int(t_live * 100)}%", self.TEXT_DIM)
        self.screen.blit(live_t_surf, (x + w - live_t_surf.get_width() - 16, ty + 22))

        # Meter with Schmitt deadband [t_low, t_high]
        bar_y = ty + 44
        pygame.draw.rect(self.screen, (14, 16, 22), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=4)

        db_t_start = bar_x + int(bar_w * t_low)
        db_t_end = bar_x + int(bar_w * t_high)
        pygame.draw.rect(self.screen, (35, 30, 20), (db_t_start, bar_y, max(1, db_t_end - db_t_start), bar_h))

        fill_t = int(bar_w * min(1.0, max(0.0, t_val)))
        if fill_t > 0:
            pygame.draw.rect(self.screen, t_col, (bar_x, bar_y, fill_t, bar_h), border_radius=4)

        # Threshold ticks at t_low and t_high
        pygame.draw.line(self.screen, (160, 160, 170), (db_t_start, bar_y - 2), (db_t_start, bar_y + bar_h + 2), 1)
        pygame.draw.line(self.screen, (220, 220, 230), (db_t_end, bar_y - 2), (db_t_end, bar_y + bar_h + 2), 1)

        leg_t = self.get_text(self.font_tiny, f"0%       {int(t_low*100)}% [Deadband] {int(t_high*100)}%     100%", self.TEXT_MUTED)
        self.screen.blit(leg_t, (bar_x, bar_y + 12))

        # -------------------------------------------------------------
        # 3. SALIENCE GRADIENT (ΔR) & PRE-DROP TRIGGER
        # -------------------------------------------------------------
        gy = bar_y + 34
        self.screen.blit(self.get_text(self.font_small, "SALIENCE GRADIENT (ΔR = R_live - R_spk)", self.TEXT_DIM), (x + 16, gy))

        g_col = self.ACCENT_MAGENTA if grad_val >= drop_th else (self.ACCENT_CYAN if grad_val > 0.05 else (self.ACCENT_ORANGE if grad_val < -0.05 else self.TEXT_DIM))
        g_arrow = "▲" if grad_val > 0.05 else ("▼" if grad_val < -0.05 else "●")
        g_surf = self.get_text(self.font_title, f"{g_arrow} {grad_val:+.2f}", g_col)
        self.screen.blit(g_surf, (x + 16, gy + 16))

        if grad_val >= drop_th:
            trig_surf = self.get_text(self.font_small, "⚠️ BUILDUP TRIGGER!", self.ACCENT_MAGENTA)
            self.screen.blit(trig_surf, (x + w - trig_surf.get_width() - 16, gy + 20))
        elif grad_val > 0.10:
            trig_surf = self.get_text(self.font_small, "Rising Influx", self.ACCENT_CYAN)
            self.screen.blit(trig_surf, (x + w - trig_surf.get_width() - 16, gy + 20))
        else:
            trig_surf = self.get_text(self.font_small, "Stable Flow", self.TEXT_MUTED)
            self.screen.blit(trig_surf, (x + w - trig_surf.get_width() - 16, gy + 20))

        # Bipolar gauge [-0.5, +0.5]
        bar_y = gy + 44
        pygame.draw.rect(self.screen, (14, 16, 22), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=4)

        # Center line (0.0)
        cx_grad = bar_x + bar_w // 2
        pygame.draw.line(self.screen, (100, 110, 130), (cx_grad, bar_y - 2), (cx_grad, bar_y + bar_h + 2), 1)

        # Pre-drop threshold tick (+drop_th)
        th_ratio = min(1.0, max(0.0, drop_th / 0.50))
        th_grad_x = cx_grad + int((bar_w // 2) * th_ratio)
        pygame.draw.line(self.screen, self.ACCENT_MAGENTA, (th_grad_x, bar_y - 2), (th_grad_x, bar_y + bar_h + 2), 2)

        # Fill bi-directional from center
        clamped_g = min(0.5, max(-0.5, grad_val))
        g_fill = int((bar_w // 2) * (clamped_g / 0.5))
        if g_fill > 0:
            pygame.draw.rect(self.screen, g_col, (cx_grad, bar_y, g_fill, bar_h), border_radius=2)
        elif g_fill < 0:
            pygame.draw.rect(self.screen, g_col, (cx_grad + g_fill, bar_y, -g_fill, bar_h), border_radius=2)

        leg_g = self.get_text(self.font_tiny, f"-0.50             0.00        +{drop_th:.2f} [Drop] +0.50", self.TEXT_MUTED)
        self.screen.blit(leg_g, (bar_x, bar_y + 12))

        # 4. Telemetry Alignment & Flywheel Coupling Summary Box
        sy_box = bar_y + 30
        sh_box = h - (sy_box - y) - 12
        if sh_box >= 40:
            box_rect = pygame.Rect(bar_x, sy_box, bar_w, sh_box)
            pygame.draw.rect(self.screen, (14, 16, 22), box_rect, border_radius=6)
            pygame.draw.rect(self.screen, self.PANEL_BORDER, box_rect, width=1, border_radius=6)

            self.screen.blit(self.get_text(self.font_tiny, "TELEMETRY DYNAMICS", self.TEXT_DIM), (bar_x + 8, sy_box + 5))

            delta_s = s_live - s_val
            ds_col = self.ACCENT_CYAN if delta_s >= 0 else self.ACCENT_ORANGE
            ds_txt = f"Salience Lead: {delta_s:+.2f} (+5.0s)"
            self.screen.blit(self.get_text(self.font_tiny, ds_txt, ds_col), (bar_x + 8, sy_box + 20))

            delta_t = t_live - t_val
            dt_col = self.ACCENT_GREEN if delta_t >= 0 else self.ACCENT_ORANGE
            dt_txt = f"Trust Lead:    {delta_t:+.2f} (+5.0s)"
            self.screen.blit(self.get_text(self.font_tiny, dt_txt, dt_col), (bar_x + 8, sy_box + 34))

            is_s_lock = s_val >= s_high
            is_t_lock = t_val >= t_high
            lock_str = "DUAL LOCK" if (is_s_lock and is_t_lock) else ("RHYTHM ONLY" if is_s_lock else ("BEAT ONLY" if is_t_lock else "AMBIENT DRIFT"))
            lock_col = self.ACCENT_GREEN if (is_s_lock and is_t_lock) else (self.ACCENT_CYAN if (is_s_lock or is_t_lock) else self.TEXT_MUTED)
            self.screen.blit(self.get_text(self.font_tiny, f"State: {lock_str}", lock_col), (bar_x + 8, sy_box + 48))

    def _draw_spectral_card(self, x: int, y: int, w: int, h: int) -> None:
        """Card 5: Multi-Band Equalizer, Total Power, Chromagram Harmony & Novelty."""
        card_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, self.PANEL_BG, card_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card_rect, width=1, border_radius=12)

        header = self.get_text(self.font_main, "SPECTRAL & HARMONY", self.ACCENT_PURPLE)
        self.screen.blit(header, (x + 16, y + 14))

        # 1. Multi-band Equalizer
        bands = self.listener.asserved_fft_band
        n_bands = len(bands) if len(bands) > 0 else self.nb_bands

        eq_x = x + 16
        eq_y = y + 46
        eq_w = w - 32
        eq_h = 100
        pygame.draw.rect(self.screen, (14, 16, 22), (eq_x, eq_y, eq_w, eq_h), border_radius=6)

        spacing = 2 if n_bands <= 16 else 1
        bar_w = max(2.0, (eq_w - spacing * (n_bands - 1)) / float(n_bands))

        for i in range(n_bands):
            val = float(min(1.0, max(0.0, bands[i]))) if i < len(bands) else 0.0
            bh = int(val * (eq_h - 8))
            bx = int(eq_x + i * (bar_w + spacing))
            by = eq_y + eq_h - 4 - bh

            frac = i / float(max(1, n_bands - 1))
            color = self.ACCENT_CYAN if frac < 0.25 else (self.ACCENT_GREEN if frac < 0.65 else self.ACCENT_ORANGE)
            if bh > 0:
                pygame.draw.rect(self.screen, color, (bx, by, max(1, int(bar_w)), bh), border_radius=1)

        # Total Power readout
        power = float(min(1.0, max(0.0, self.listener.asserved_total_power)))
        p_surf = self.get_text(self.font_tiny, f"Total Power: {power * 100:.0f}%", self.TEXT_DIM)
        self.screen.blit(p_surf, (x + 16, eq_y + eq_h + 6))

        # 2. 12-Tone Chromagram Pitch Classes
        cy = eq_y + eq_h + 28
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        chroma = self.listener.smoothed_chroma_values
        c_max = max(1e-4, float(np.max(chroma))) if len(chroma) > 0 else 1.0

        ch_x = x + 16
        ch_y = cy
        ch_w = w - 32
        ch_h = 65
        pygame.draw.rect(self.screen, (14, 16, 22), (ch_x, ch_y, ch_w, ch_h), border_radius=6)

        n_chroma = 12
        c_col_w = int((ch_w - (n_chroma + 1) * 2) / float(n_chroma))
        best_note_idx = int(np.argmax(chroma)) if len(chroma) > 0 and c_max > 0.05 else 0

        for i in range(n_chroma):
            val = float(chroma[i]) / c_max if len(chroma) > i else 0.0
            bh = int(val * (ch_h - 8))
            bx = ch_x + 2 + i * (c_col_w + 2)
            by = ch_y + ch_h - 4 - bh
            is_dom = (i == best_note_idx) and (c_max > 0.05)
            color = (255, 230, 80) if is_dom else self.ACCENT_PURPLE
            if bh > 0:
                pygame.draw.rect(self.screen, color, (bx, by, c_col_w, bh), border_radius=1)

        dom_note = notes[best_note_idx] if c_max > 0.05 else "—"
        key_lbl = self.get_text(self.font_small, f"Dominant Key: {dom_note}", self.TEXT_MAIN)
        self.screen.blit(key_lbl, (x + 16, ch_y + ch_h + 6))

        # 3. Structural Novelty & Drop Transition
        ny = ch_y + ch_h + 28
        is_vc = self.listener.is_verse_chorus_change
        is_sc = self.listener.is_song_change

        vc_rect = pygame.Rect(x + 16, ny, w - 32, 28)
        if is_vc:
            pygame.draw.rect(self.screen, self.ACCENT_PURPLE, vc_rect, border_radius=6)
            vc_txt = "★ VERSE / CHORUS DROP!"
            vc_col = (10, 12, 18)
        elif is_sc:
            pygame.draw.rect(self.screen, self.ACCENT_CYAN, vc_rect, border_radius=6)
            vc_txt = "★ SONG CHANGE DETECTED"
            vc_col = (10, 12, 18)
        else:
            pygame.draw.rect(self.screen, (14, 16, 22), vc_rect, border_radius=6)
            pygame.draw.rect(self.screen, self.PANEL_BORDER, vc_rect, width=1, border_radius=6)
            vc_txt = "Steady Macro Structure"
            vc_col = self.TEXT_MUTED

        vc_surf = self.get_text(self.font_small, vc_txt, vc_col)
        self.screen.blit(vc_surf, (vc_rect.centerx - vc_surf.get_width() // 2, vc_rect.centery - vc_surf.get_height() // 2))

        # Novelty meter
        ny += 36
        nov = float(min(1.0, max(0.0, self.listener.asserved_novelty)))
        self.screen.blit(self.get_text(self.font_tiny, f"Novelty Index: {nov * 100:.0f}%", self.TEXT_DIM), (x + 16, ny))
        nov_rect = pygame.Rect(x + 16, ny + 16, w - 32, 8)
        pygame.draw.rect(self.screen, (14, 16, 22), nov_rect, border_radius=4)
        if nov > 0:
            pygame.draw.rect(self.screen, self.ACCENT_PURPLE, (x + 16, ny + 16, int((w - 32) * nov), 8), border_radius=4)


    def _draw_flywheel_card(self, x: int, y: int, w: int, h: int) -> None:
        """Card 1: Continuous Flywheel Phase Dial, BPM, Confidence Meter, Status."""
        card_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, self.PANEL_BG, card_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card_rect, width=1, border_radius=12)

        header = self.get_text(self.font_main, "ORACLE FLYWHEEL", self.ACCENT_CYAN)
        self.screen.blit(header, (x + 16, y + 14))

        # Circular Phase Dial
        center_x = x + w // 2
        center_y = y + 84
        radius = 36

        pygame.draw.circle(self.screen, (14, 16, 22), (center_x, center_y), radius)
        pygame.draw.circle(self.screen, self.PANEL_BORDER, (center_x, center_y), radius, width=2)

        # Draw downbeat tick mark (12 o'clock)
        pygame.draw.line(self.screen, (255, 255, 255), (center_x, center_y - radius), (center_x, center_y - radius + 7), 2)

        # Rotating Phase Hand
        phase = self.listener.beat_phase
        angle_rad = phase * 2.0 * np.pi - (np.pi / 2.0)
        hand_x = center_x + int((radius - 7) * np.cos(angle_rad))
        hand_y = center_y + int((radius - 7) * np.sin(angle_rad))

        hand_color = self.ACCENT_CYAN if not self.listener.is_dropped_beat else self.ACCENT_ORANGE
        pygame.draw.line(self.screen, hand_color, (center_x, center_y), (hand_x, hand_y), 3)
        pygame.draw.circle(self.screen, hand_color, (hand_x, hand_y), 4)

        phase_lbl = self.get_text(self.font_mono, f"Phase: {phase:.2f}", self.TEXT_MAIN)
        self.screen.blit(phase_lbl, (center_x - phase_lbl.get_width() // 2, center_y + radius + 7))

        # Row 1: Tempo Consensus & Flywheel Status (Two columns)
        bpm_val = getattr(self.listener.analyzer, 'bpm', 120.0)
        status_val = getattr(self.listener.analyzer, 'flywheel_status', 'coasting')

        r1_y = center_y + radius + 28
        self.screen.blit(self.get_text(self.font_small, "TEMPO", self.TEXT_DIM), (x + 18, r1_y))
        bpm_surf = self.get_text(self.font_main, f"{bpm_val:.1f} BPM", self.TEXT_MAIN)
        self.screen.blit(bpm_surf, (x + 18, r1_y + 14))

        self.screen.blit(self.get_text(self.font_small, "STATUS", self.TEXT_DIM), (x + 130, r1_y))
        status_color = self.ACCENT_GREEN if status_val == "locked" else self.ACCENT_ORANGE
        status_surf = self.get_text(self.font_main, status_val.upper(), status_color)
        self.screen.blit(status_surf, (x + 130, r1_y + 14))

        # Row 2: Prominent Beat Confidence Meter & Thresholds
        conf_val = float(getattr(self.listener, 'beat_confidence', 0.0))
        conf_clamped = float(np.clip(conf_val, 0.0, 1.0))
        conf_pct = int(conf_clamped * 100)

        if conf_clamped >= 0.30:
            tier_str = "HIGH"
            c_color = self.ACCENT_GREEN
        elif conf_clamped >= 0.15:
            tier_str = "MOD"
            c_color = self.ACCENT_ORANGE
        else:
            tier_str = "LOW"
            c_color = self.ACCENT_RED

        r2_y = r1_y + 40
        self.screen.blit(self.get_text(self.font_small, "BEAT CONFIDENCE", self.TEXT_DIM), (x + 18, r2_y))

        # Confidence percentage & score badge
        conf_surf = self.get_text(self.font_title, f"{conf_pct}%", c_color)
        self.screen.blit(conf_surf, (x + 18, r2_y + 14))

        score_label = f"[{tier_str}]  r = {conf_val:+.2f}"
        score_surf = self.get_text(self.font_mono, score_label, self.TEXT_DIM)
        self.screen.blit(score_surf, (x + 22 + conf_surf.get_width(), r2_y + 18))

        # Progress bar
        bar_x = x + 18
        bar_y = r2_y + 43
        bar_w = w - 36
        bar_h = 10
        pygame.draw.rect(self.screen, (14, 16, 22), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=4)

        fill_w = int(bar_w * conf_clamped)
        if fill_w > 0:
            pygame.draw.rect(self.screen, c_color, (bar_x, bar_y, fill_w, bar_h), border_radius=4)

        # Threshold tick marks (15% moderate, 30% high)
        t15 = bar_x + int(bar_w * 0.15)
        t30 = bar_x + int(bar_w * 0.30)
        pygame.draw.line(self.screen, (140, 140, 150), (t15, bar_y - 2), (t15, bar_y + bar_h + 2), 1)
        pygame.draw.line(self.screen, (220, 220, 230), (t30, bar_y - 2), (t30, bar_y + bar_h + 2), 1)

        # Threshold legend
        legend_surf = self.get_text(self.font_tiny, "0%       15% (Mod)   30% (High)     100%", self.TEXT_DIM)
        self.screen.blit(legend_surf, (bar_x, bar_y + 13))

        # Row 3: Total Beats & Mode Blending Preview
        r3_y = bar_y + 28
        beat_cnt = getattr(self.listener.analyzer, 'beat_count', 0)
        cnt_surf = self.get_text(self.font_small, f"Total Beats: {beat_cnt}", self.TEXT_DIM)
        self.screen.blit(cnt_surf, (x + 18, r3_y))

        blend_txt = f"Blend: {conf_clamped*100:.0f}% rhythm / {(1.0-conf_clamped)*100:.0f}% ambient"
        blend_color = self.ACCENT_CYAN if conf_clamped >= 0.15 else self.TEXT_DIM
        blend_surf = self.get_text(self.font_tiny, blend_txt, blend_color)
        self.screen.blit(blend_surf, (x + 18, r3_y + 16))

    def _draw_beat_card(self, x: int, y: int, w: int, h: int) -> None:
        """Card 2: Real vs Dropped Beat Badges, Instrument Tag Dispatcher."""
        card_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, self.PANEL_BG, card_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card_rect, width=1, border_radius=12)

        header = self.get_text(self.font_main, "BEAT & TRANSIENTS", self.ACCENT_GREEN)
        self.screen.blit(header, (x + 16, y + 14))

        # Primary Beat Status Badge
        badge_rect = pygame.Rect(x + 18, y + 55, w - 36, 52)
        is_real = self.listener.is_real_beat
        is_drop = self.listener.is_dropped_beat
        is_beat = self.listener.is_beat

        if is_real:
            b_color = self.ACCENT_GREEN
            b_text = "● REAL BEAT HIT"
        elif is_drop:
            b_color = self.ACCENT_ORANGE
            b_text = "◐ DROPPED / BREAKDOWN"
        elif is_beat:
            b_color = (255, 255, 255)
            b_text = "○ FLYWHEEL TICK"
        else:
            b_color = (35, 40, 52)
            b_text = "IDLE TICK"

        pygame.draw.rect(self.screen, b_color, badge_rect, border_radius=8)
        text_col = (10, 15, 20) if (is_real or is_drop or is_beat) else self.TEXT_DIM
        badge_surf = self.get_text(self.font_main, b_text, text_col)
        self.screen.blit(badge_surf, (badge_rect.centerx - badge_surf.get_width() // 2, badge_rect.centery - badge_surf.get_height() // 2))

        # Beat Tag (Bass/Kick, Snare/Mid, Hi-hat/Cymbal)
        my = y + 130
        self.screen.blit(self.get_text(self.font_small, "CLASSIFIED TRANSIENT TAG", self.TEXT_DIM), (x + 18, my))

        tag = self.listener.beat_tag
        tag_color = self.ACCENT_RED if "Bass" in tag else (self.ACCENT_GREEN if "Snare" in tag else self.ACCENT_CYAN)

        tag_rect = pygame.Rect(x + 18, my + 18, w - 36, 42)
        pygame.draw.rect(self.screen, (15, 18, 26), tag_rect, border_radius=8)
        pygame.draw.rect(self.screen, tag_color, tag_rect, width=2, border_radius=8)

        tag_surf = self.get_text(self.font_title, f"[{tag}]", tag_color)
        self.screen.blit(tag_surf, (tag_rect.centerx - tag_surf.get_width() // 2, tag_rect.centery - tag_surf.get_height() // 2))

        # Rhythmic Guide & Hints
        my += 80
        self.screen.blit(self.get_text(self.font_small, "MODE CODING RECIPE", self.TEXT_DIM), (x + 18, my))

        recipes = [
            "• is_real_beat -> Kick shockwave",
            "• is_dropped_beat -> Build suspense",
            "• beat_confidence -> Blend fallback",
            "• tag=='Bass/Kick' -> Center red",
            "• tag=='Snare/Mid' -> Blue ripple"
        ]
        for idx, r in enumerate(recipes):
            self.screen.blit(self.get_text(self.font_tiny, r, self.TEXT_MAIN), (x + 18, my + 20 + idx * 17))



    def _draw_footer(self) -> None:
        """Renders keyboard shortcut reference bar at the bottom."""
        footer_y = self.height - 40
        shortcuts = [
            "[R] Hot-Reload Code",
            "[Space] Pause/Play",
            "[↑/↓] Switch Mode",
            "[←/→] Seek ±5s",
            "[N/P] Next/Prev Song",
            "[K/L] A/V Sync (±10ms)",
            "[O] Toggle Orientation",
            "[Esc] Exit"
        ]
        total_str = "    │    ".join(shortcuts)
        f_surf = self.get_text(self.font_small, total_str, self.TEXT_DIM)
        self.screen.blit(f_surf, (self.width // 2 - f_surf.get_width() // 2, footer_y))


# =====================================================================
# CLI ENTRY POINT
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Vialactée Mode Studio - Interactive Developer Visualizer")
    parser.add_argument("--song", "-s", type=str, default=None, help="Path to MP3 or WAV file")
    parser.add_argument("--mode", "-m", type=str, default=None, help="Initial mode name (e.g. 'Static_wave_mode')")
    parser.add_argument("--leds", "-l", type=int, default=80, help="Number of LEDs in the test bar (default: 80)")
    parser.add_argument(
        "--model",
        type=str,
        default="MultiBandOnsetAudioAnalyzer",
        help="Rhythm analyzer model class (e.g. MultiBandOnsetAudioAnalyzer, AudioAnalyzer, CostasLoopAudioAnalyzer, DualFlywheelAudioAnalyzer)"
    )
    args = parser.parse_args()

    # Default fallback song
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

    print("=" * 70)
    print("  VIALACTÉE MODE STUDIO — HARDWARE PARITY LAB")
    print("=" * 70)
    print(f"  Song: {os.path.basename(song_path)}")
    print(f"  Model: {args.model}")
    print(f"  LED Count: {args.leds}")
    print("  Initializing Audio Engine & Anticipation Flywheel...")

    is_win = (sys.platform == "win32")
    if is_win:
        try:
            import ctypes
            ctypes.windll.winmm.timeBeginPeriod(1)
        except Exception:
            pass

    try:
        app = StudioApp(song_path=song_path, initial_mode_name=args.mode, nb_leds=args.leds, model_name=args.model)
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
