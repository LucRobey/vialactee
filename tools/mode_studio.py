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
import glob
import inspect
import importlib
import traceback
import argparse
from typing import Dict, Any, List, Optional, Tuple, Type

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
from modes.Mode import Mode


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

        # Playback cursor (speaker time in samples)
        self.speaker_sample_pos = 0
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
        self.prime_analyzer(sync_offset_seconds)

    def prime_analyzer(self, sync_offset_seconds: float = 0.0) -> None:
        """
        Fast-forwards 300 frames (~5s lookahead) leading up to current speaker position.
        Ensures ODF lookahead buffer, template bank, and delay ring buffer are primed immediately.
        """
        hop = int(self.sample_rate / 60.0)
        start_ingest = self.get_actual_speaker_sample() + int(sync_offset_seconds * self.sample_rate)
        now = time.time()

        for i in range(300):
            ingest_center = start_ingest + i * hop
            s_start = max(0, ingest_center - 2048)
            s_end = ingest_center + 2048
            chunk = np.zeros(4096, dtype=np.float32)
            if s_start < self.total_samples:
                sl = self.mono_data[s_start:min(s_end, self.total_samples)]
                chunk[:len(sl)] = sl
            self.listener.process_raw_audio(chunk)
            self.listener.update()

        # Space out timestamps across ring buffer so they drain frame-by-frame starting now
        count = self.listener._ring_count
        read_idx = self.listener._ring_read
        capacity = self.listener._ring_capacity
        for i in range(count):
            r = (read_idx + i) % capacity
            self.listener._ring_timestamps[r] = now - self.lookahead_seconds + (i / 60.0)

    def advance_ingest_frame(self, sync_offset_seconds: float = 0.0) -> None:
        """Feed current 4096-sample lookahead window into Listener before frame update."""
        actual_pos = self.get_actual_speaker_sample()
        ingest_sample = actual_pos + self.lookahead_samples + int(sync_offset_seconds * self.sample_rate)
        s_start = max(0, ingest_sample - 2048)
        s_end = ingest_sample + 2048
        chunk = np.zeros(4096, dtype=np.float32)
        if s_start < self.total_samples:
            sl = self.mono_data[s_start:min(s_end, self.total_samples)]
            chunk[:len(sl)] = sl
        self.listener.process_raw_audio(chunk)


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
    ACCENT_CYAN = (0, 220, 255)
    ACCENT_GREEN = (40, 240, 120)
    ACCENT_ORANGE = (255, 160, 20)
    ACCENT_RED = (255, 60, 80)
    ACCENT_PURPLE = (180, 80, 255)

    def __init__(self, song_path: str, initial_mode_name: Optional[str] = None, nb_leds: int = 80):
        pygame.init()
        pygame.font.init()

        self.width = 1180
        self.height = 720
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

        # 1. Initialize Listener with exact production config
        listener_infos = {
            "useMicrophone": True,
            "fakeDelay": 5.0,
            "latency": 0.0,
            "luminosity": 100,
            "sensibility": 100,
        }
        self.listener = Listener(listener_infos)
        # In mode_studio (direct digital audio feed), zero out the 69ms artificial microphone ADC buffer delay
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
        self.streamer = AudioStreamer(new_path, self.listener)
        self.streamer.prime_analyzer()
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

            # Advance audio analysis pipeline
            if self.streamer.is_playing:
                self.streamer.advance_ingest_frame(self.sync_offset_ms / 1000.0)

            self.listener.update()
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
        title_surf = self.font_title.render(disp_name.upper(), True, self.ACCENT_CYAN)
        self.screen.blit(title_surf, (40, 18))

        mode_num = f"Mode {self.mode_mgr.current_idx + 1}/{len(self.mode_mgr.mode_catalog)}"
        num_surf = self.font_main.render(mode_num, True, self.TEXT_DIM)
        self.screen.blit(num_surf, (title_surf.get_width() + 55, 23))

        # Song Title & Status Badge
        song_name = os.path.basename(self.streamer.file_path)
        song_surf = self.font_main.render(f"Track: {song_name}", True, self.TEXT_MAIN)
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
        time_surf = self.font_small.render(time_str, True, self.TEXT_DIM)
        self.screen.blit(time_surf, (bar_x, bar_y + 14))

        # A/V Sync Calibration Readout
        sync_color = self.ACCENT_CYAN if self.sync_offset_ms != 0 else self.TEXT_DIM
        sync_label = f"A/V Sync: {self.sync_offset_ms:+.0f} ms (K / L to tune)"
        sync_surf = self.font_small.render(sync_label, True, sync_color)
        self.screen.blit(sync_surf, (bar_x + time_surf.get_width() + 25, bar_y + 14))

        # Toast notification message
        if time.time() - self.status_msg_time < 3.0:
            msg_surf = self.font_main.render(self.status_msg, True, self.status_color)
            self.screen.blit(msg_surf, (self.width - msg_surf.get_width() - 40, bar_y + 13))

    def _draw_led_bar(self) -> None:
        """Renders the physical LED strip with realistic round pixels, dark grid, and bloom."""
        panel_rect = pygame.Rect(40, 98, self.width - 80, 160)
        pygame.draw.rect(self.screen, self.PANEL_BG, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, panel_rect, width=1, border_radius=12)

        tag_surf = self.font_small.render(
            f"VIRTUAL CHANDELIER SEGMENT ({self.nb_leds} LEDs) — {'VERTICAL' if self.is_vertical else 'HORIZONTAL'}",
            True, self.TEXT_DIM
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
        """Renders the 4 Oracle telemetry cards: Flywheel, Beat Badges, FFT Equalizer, Chroma."""
        hud_y = 272
        hud_h = 365
        card_w = (self.width - 80 - 45) // 4

        # Card 1: Anticipation Flywheel
        self._draw_flywheel_card(40, hud_y, card_w, hud_h)

        # Card 2: Beat & Transient Tagging
        self._draw_beat_card(40 + card_w + 15, hud_y, card_w, hud_h)

        # Card 3: 8-Band Equalizer & Power
        self._draw_fft_card(40 + (card_w + 15) * 2, hud_y, card_w, hud_h)

        # Card 4: Harmonic Chromagram & Novelty
        self._draw_chroma_card(40 + (card_w + 15) * 3, hud_y, card_w, hud_h)

    def _draw_flywheel_card(self, x: int, y: int, w: int, h: int) -> None:
        """Card 1: Continuous Flywheel Phase Dial, BPM, Confidence, Status."""
        card_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, self.PANEL_BG, card_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card_rect, width=1, border_radius=12)

        header = self.font_main.render("ORACLE FLYWHEEL", True, self.ACCENT_CYAN)
        self.screen.blit(header, (x + 16, y + 14))

        # Circular Phase Dial
        center_x = x + w // 2
        center_y = y + 105
        radius = 48

        pygame.draw.circle(self.screen, (14, 16, 22), (center_x, center_y), radius)
        pygame.draw.circle(self.screen, self.PANEL_BORDER, (center_x, center_y), radius, width=2)

        # Draw downbeat tick mark (12 o'clock)
        pygame.draw.line(self.screen, (255, 255, 255), (center_x, center_y - radius), (center_x, center_y - radius + 8), 2)

        # Rotating Phase Hand
        phase = self.listener.beat_phase
        angle_rad = phase * 2.0 * np.pi - (np.pi / 2.0)
        hand_x = center_x + int((radius - 8) * np.cos(angle_rad))
        hand_y = center_y + int((radius - 8) * np.sin(angle_rad))

        hand_color = self.ACCENT_CYAN if not self.listener.is_dropped_beat else self.ACCENT_ORANGE
        pygame.draw.line(self.screen, hand_color, (center_x, center_y), (hand_x, hand_y), 3)
        pygame.draw.circle(self.screen, hand_color, (hand_x, hand_y), 5)

        phase_lbl = self.font_mono.render(f"Phase: {phase:.2f}", True, self.TEXT_MAIN)
        self.screen.blit(phase_lbl, (center_x - phase_lbl.get_width() // 2, center_y + radius + 12))

        # Metrics Readouts
        my = center_y + radius + 40
        bpm_val = getattr(self.listener.analyzer, 'bpm', 120.0)
        conf_val = getattr(self.listener.analyzer, 'confidence_score', 0.0)
        status_val = getattr(self.listener.analyzer, 'flywheel_status', 'coasting')

        self.screen.blit(self.font_small.render("TEMPO CONSENSUS", True, self.TEXT_DIM), (x + 18, my))
        bpm_surf = self.font_title.render(f"{bpm_val:.1f} BPM", True, self.TEXT_MAIN)
        self.screen.blit(bpm_surf, (x + 18, my + 14))

        my += 55
        self.screen.blit(self.font_small.render("FLYWHEEL LOCK", True, self.TEXT_DIM), (x + 18, my))
        status_color = self.ACCENT_GREEN if status_val == "locked" else self.ACCENT_ORANGE
        status_surf = self.font_main.render(f"{status_val.upper()} ({int(conf_val * 100)}%)", True, status_color)
        self.screen.blit(status_surf, (x + 18, my + 15))

        my += 45
        beat_cnt = getattr(self.listener.analyzer, 'beat_count', 0)
        cnt_surf = self.font_small.render(f"Total Beats: {beat_cnt}", True, self.TEXT_DIM)
        self.screen.blit(cnt_surf, (x + 18, my))

    def _draw_beat_card(self, x: int, y: int, w: int, h: int) -> None:
        """Card 2: Real vs Dropped Beat Badges, Instrument Tag Dispatcher."""
        card_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, self.PANEL_BG, card_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card_rect, width=1, border_radius=12)

        header = self.font_main.render("BEAT & TRANSIENTS", True, self.ACCENT_GREEN)
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
        badge_surf = self.font_main.render(b_text, True, text_col)
        self.screen.blit(badge_surf, (badge_rect.centerx - badge_surf.get_width() // 2, badge_rect.centery - badge_surf.get_height() // 2))

        # Beat Tag (Bass/Kick, Snare/Mid, Hi-hat/Cymbal)
        my = y + 130
        self.screen.blit(self.font_small.render("CLASSIFIED TRANSIENT TAG", True, self.TEXT_DIM), (x + 18, my))

        tag = self.listener.beat_tag
        tag_color = self.ACCENT_RED if "Bass" in tag else (self.ACCENT_GREEN if "Snare" in tag else self.ACCENT_CYAN)

        tag_rect = pygame.Rect(x + 18, my + 18, w - 36, 42)
        pygame.draw.rect(self.screen, (15, 18, 26), tag_rect, border_radius=8)
        pygame.draw.rect(self.screen, tag_color, tag_rect, width=2, border_radius=8)

        tag_surf = self.font_title.render(f"[{tag}]", True, tag_color)
        self.screen.blit(tag_surf, (tag_rect.centerx - tag_surf.get_width() // 2, tag_rect.centery - tag_surf.get_height() // 2))

        # Rhythmic Guide & Hints
        my += 80
        self.screen.blit(self.font_small.render("MODE CODING RECIPE", True, self.TEXT_DIM), (x + 18, my))

        recipes = [
            "• is_real_beat -> Kick shockwave",
            "• is_dropped_beat -> Build suspense",
            "• tag=='Bass/Kick' -> Center red",
            "• tag=='Snare/Mid' -> Blue ripple",
            "• tag=='Hi-hat' -> Edge sparkle"
        ]
        for idx, r in enumerate(recipes):
            self.screen.blit(self.font_tiny.render(r, True, self.TEXT_MAIN), (x + 18, my + 20 + idx * 17))

    def _draw_fft_card(self, x: int, y: int, w: int, h: int) -> None:
        """Card 3: 8-Band Asserved Equalizer & Power Meter."""
        card_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, self.PANEL_BG, card_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card_rect, width=1, border_radius=12)

        header = self.font_main.render("SPECTRAL SPECTRUM (FFT)", True, self.ACCENT_ORANGE)
        self.screen.blit(header, (x + 16, y + 14))

        bands = self.listener.asserved_fft_band
        n_bands = min(8, len(bands))

        eq_x = x + 18
        eq_y = y + 55
        eq_w = w - 36
        eq_h = 160

        pygame.draw.rect(self.screen, (14, 16, 22), (eq_x, eq_y, eq_w, eq_h), border_radius=8)

        bar_w = int((eq_w - (n_bands + 1) * 4) / float(n_bands))
        palette = [
            (255, 60, 60), (255, 120, 40), (255, 200, 30), (100, 240, 60),
            (30, 220, 200), (40, 140, 255), (140, 80, 255), (220, 60, 255)
        ]

        for i in range(n_bands):
            val = float(np.clip(bands[i], 0.0, 1.0))
            bh = int(val * (eq_h - 10))
            bx = eq_x + 4 + i * (bar_w + 4)
            by = eq_y + eq_h - 5 - bh

            color = palette[i % len(palette)]
            if bh > 0:
                pygame.draw.rect(self.screen, color, (bx, by, bar_w, bh), border_radius=3)

            # Band number label
            lbl = self.font_tiny.render(str(i + 1), True, self.TEXT_DIM)
            self.screen.blit(lbl, (bx + bar_w // 2 - lbl.get_width() // 2, eq_y + eq_h + 3))

        # Total Audio Power Meter
        my = eq_y + eq_h + 30
        self.screen.blit(self.font_small.render("TOTAL ASSERVED POWER", True, self.TEXT_DIM), (x + 18, my))

        p_rect = pygame.Rect(x + 18, my + 18, w - 36, 16)
        pygame.draw.rect(self.screen, (14, 16, 22), p_rect, border_radius=4)

        power = float(np.clip(self.listener.asserved_total_power, 0.0, 1.0))
        if power > 0:
            fill_w = int((w - 36) * power)
            p_color = self.ACCENT_ORANGE if power < 0.8 else self.ACCENT_RED
            pygame.draw.rect(self.screen, p_color, (x + 18, my + 18, fill_w, 16), border_radius=4)

        p_lbl = self.font_mono.render(f"{power * 100:.1f}%", True, self.TEXT_MAIN)
        self.screen.blit(p_lbl, (x + 18, my + 40))

    def _draw_chroma_card(self, x: int, y: int, w: int, h: int) -> None:
        """Card 4: 12-Tone Chromagram Pitch Classes & Structural Novelty."""
        card_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, self.PANEL_BG, card_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, card_rect, width=1, border_radius=12)

        header = self.font_main.render("HARMONY & STRUCTURE", True, self.ACCENT_PURPLE)
        self.screen.blit(header, (x + 16, y + 14))

        # 12-Tone Chromagram
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        chroma = self.listener.smoothed_chroma_values
        c_max = max(1e-4, float(np.max(chroma)))

        ch_x = x + 18
        ch_y = y + 55
        ch_w = w - 36
        ch_h = 100

        pygame.draw.rect(self.screen, (14, 16, 22), (ch_x, ch_y, ch_w, ch_h), border_radius=8)

        n_bars = 12
        bar_w = int((ch_w - (n_bars + 1) * 2) / float(n_bars))
        best_note_idx = int(np.argmax(chroma)) if c_max > 0 else 0

        for i in range(n_bars):
            val = float(chroma[i]) / c_max if len(chroma) > i else 0.0
            bh = int(val * (ch_h - 10))
            bx = ch_x + 2 + i * (bar_w + 2)
            by = ch_y + ch_h - 5 - bh

            is_dom = (i == best_note_idx) and (c_max > 0.05)
            color = self.ACCENT_PURPLE if not is_dom else (255, 230, 80)
            if bh > 0:
                pygame.draw.rect(self.screen, color, (bx, by, bar_w, bh), border_radius=2)

        # Dominant Pitch Readout
        dom_note = notes[best_note_idx] if c_max > 0.05 else "—"
        note_lbl = self.font_small.render(f"Dominant Chord Pitch: {dom_note}", True, self.TEXT_MAIN)
        self.screen.blit(note_lbl, (x + 18, ch_y + ch_h + 8))

        # Structural Novelty & Drop Transition
        my = ch_y + ch_h + 38
        self.screen.blit(self.font_small.render("SONG STRUCTURE DETECTOR", True, self.TEXT_DIM), (x + 18, my))

        is_vc = self.listener.is_verse_chorus_change
        is_sc = self.listener.is_song_change

        vc_rect = pygame.Rect(x + 18, my + 18, w - 36, 32)
        if is_vc:
            pygame.draw.rect(self.screen, self.ACCENT_PURPLE, vc_rect, border_radius=6)
            vc_txt = "★ VERSE / CHORUS DROP!"
            vc_col = (10, 12, 18)
        elif is_sc:
            pygame.draw.rect(self.screen, self.ACCENT_CYAN, vc_rect, border_radius=6)
            vc_txt = "★ SONG CHANGE DETECTED"
            vc_col = (10, 12, 18)
        else:
            pygame.draw.rect(self.screen, (15, 18, 26), vc_rect, border_radius=6)
            pygame.draw.rect(self.screen, self.PANEL_BORDER, vc_rect, width=1, border_radius=6)
            vc_txt = "Steady Section"
            vc_col = self.TEXT_DIM

        vc_surf = self.font_main.render(vc_txt, True, vc_col)
        self.screen.blit(vc_surf, (vc_rect.centerx - vc_surf.get_width() // 2, vc_rect.centery - vc_surf.get_height() // 2))

        # Novelty Gauge
        my += 60
        nov = float(np.clip(self.listener.asserved_novelty, 0.0, 1.0))
        self.screen.blit(self.font_small.render(f"Novelty Index: {nov * 100:.0f}%", True, self.TEXT_DIM), (x + 18, my))
        nov_rect = pygame.Rect(x + 18, my + 18, w - 36, 12)
        pygame.draw.rect(self.screen, (14, 16, 22), nov_rect, border_radius=4)
        if nov > 0:
            pygame.draw.rect(self.screen, self.ACCENT_PURPLE, (x + 18, my + 18, int((w - 36) * nov), 12), border_radius=4)

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
        f_surf = self.font_small.render(total_str, True, self.TEXT_DIM)
        self.screen.blit(f_surf, (self.width // 2 - f_surf.get_width() // 2, footer_y))


# =====================================================================
# CLI ENTRY POINT
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Vialactée Mode Studio - Interactive Developer Visualizer")
    parser.add_argument("--song", "-s", type=str, default=None, help="Path to MP3 or WAV file")
    parser.add_argument("--mode", "-m", type=str, default=None, help="Initial mode name (e.g. 'Static_wave_mode')")
    parser.add_argument("--leds", "-l", type=int, default=80, help="Number of LEDs in the test bar (default: 80)")
    args = parser.parse_args()

    # Default fallback song
    song_path = args.song
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
    print(f"  LED Count: {args.leds}")
    print("  Initializing Audio Engine & Anticipation Flywheel...")

    app = StudioApp(song_path=song_path, initial_mode_name=args.mode, nb_leds=args.leds)
    app.run()


if __name__ == "__main__":
    main()
