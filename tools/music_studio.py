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
from typing import Dict, Any, List, Optional, Tuple

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
from core.AudioAnalyzer import bpm_to_class


# =====================================================================
# AUDIO STREAMER (Hardware DAC Compensation & Predictive Lookahead)
# =====================================================================

class AudioStreamer:
    """
    Sample-accurate audio streamer using sounddevice with 5.0s predictive lookahead.
    Feeds future audio chunks to Listener while streaming speaker-time audio
    to physical speakers in perfect synchronization.
    """

    def __init__(self, audio_file_path: str, listener: Listener, sample_rate: int = 44100):
        self.file_path = audio_file_path
        self.listener = listener
        self.sample_rate = sample_rate
        self.lookahead_seconds = getattr(listener.analyzer, 'lookahead_seconds', 5.0)
        self.lookahead_samples = int(self.lookahead_seconds * self.sample_rate)

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
        self.prime_analyzer(sync_offset_seconds)

    def prime_analyzer(self, sync_offset_seconds: float = 0.0) -> None:
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

        count = self.listener._ring_count
        read_idx = self.listener._ring_read
        capacity = self.listener._ring_capacity
        for i in range(count):
            r = (read_idx + i) % capacity
            self.listener._ring_timestamps[r] = now - self.lookahead_seconds + (i / 60.0)

    def advance_ingest_frame(self, sync_offset_seconds: float = 0.0) -> None:
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

    CHROMA_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    BAND_NAMES = ["Sub-Bass", "Bass", "Low-Mid", "Mid", "High-Mid", "Presence", "Brilliance", "Air"]

    def __init__(self, song_path: str, nb_leds: int = 80):
        pygame.init()
        pygame.font.init()

        self.width = 1440
        self.height = 920
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF)
        pygame.display.set_caption("Vialactée Music Studio — Real-Time DSP & Music Analysis Laboratory")

        # Fonts
        self.font_title = pygame.font.SysFont("Trebuchet MS", 20, bold=True)
        self.font_main = pygame.font.SysFont("Trebuchet MS", 14, bold=True)
        self.font_small = pygame.font.SysFont("Trebuchet MS", 11)
        self.font_mono = pygame.font.SysFont("Consolas", 12, bold=True)
        self.font_big_num = pygame.font.SysFont("Trebuchet MS", 28, bold=True)

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

        # Production Listener initialization
        dummy_infos = {
            "sensi": 1.0,
            "luminosite": 1.0,
            "fakeDelay": 5.0,
            "latency": 0.0,
            "useMicrophone": True,
            "nb_of_fft_band": 8,
            "nb_of_chroma": 12,
            "sample_rate": 44100,
            "buffer_size": 4096
        }
        self.listener = Listener(dummy_infos)
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

        # Rolling history buffers for plotting
        self.history_size = 240
        self.history_novelty = np.zeros(self.history_size)
        self.history_lm = np.zeros(self.history_size)
        self.history_gm = np.zeros(self.history_size)
        self.history_cursor = 0

        # Past ODF buffer (shows past 1.0s before speaker time)
        self.past_odf_len = 60
        self.past_odf = np.zeros(self.past_odf_len)

        # Virtual LED strip buffer
        self.led_rgb = np.zeros((self.nb_leds, 3), dtype=np.uint8)

        # Tuning drawer state
        self.tuning_open = False
        self.tuning_params = [
            {"name": "sensi", "label": "Audio Sensitivity", "obj": self.listener, "attr": "sensi", "min": 0.1, "max": 3.0, "step": 0.05, "fmt": "{:.2f}"},
            {"name": "mod_conf", "label": "Moderate Lock Conf", "obj": self.listener.analyzer.config, "attr": "moderate_confidence_threshold", "min": 0.05, "max": 0.50, "step": 0.01, "fmt": "{:.2f}"},
            {"name": "high_conf", "label": "High Lock Conf", "obj": self.listener.analyzer.config, "attr": "high_confidence_threshold", "min": 0.10, "max": 0.60, "step": 0.01, "fmt": "{:.2f}"},
            {"name": "strong_peak", "label": "Strong Peak Mult", "obj": self.listener.analyzer.config, "attr": "strong_peak_multiplier", "min": 1.0, "max": 3.5, "step": 0.1, "fmt": "{:.1f}"},
            {"name": "real_beat_ratio", "label": "Real Beat Ratio", "obj": self.listener.analyzer.config, "attr": "real_beat_baseline_ratio", "min": 0.1, "max": 1.5, "step": 0.05, "fmt": "{:.2f}"},
            {"name": "novelty_th", "label": "Song Novelty Drop Th", "obj": self.listener.analyzer.config, "attr": "song_novelty_asserved_th", "min": 0.4, "max": 1.2, "step": 0.02, "fmt": "{:.2f}"},
            {"name": "silence_th", "label": "Silence Power Floor", "obj": self.listener.analyzer.config, "attr": "silence_power_threshold", "min": 1.0, "max": 20.0, "step": 0.5, "fmt": "{:.1f}"},
        ]
        self.tuning_selected_idx = 0

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
                            # Reset default RhythmConfig
                            self.listener.analyzer.config = RhythmConfig()
                            self.listener.analyzer.novelty_detector.config = self.listener.analyzer.config
                            self.listener.sensi = 1.0
                            self.set_status("Reset DSP parameters to default", self.ACCENT_GREEN)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Interactive timeline scrubber click
                    mx, my = event.pos
                    if 40 <= mx <= self.width - 40 and 42 <= my <= 62:
                        progress = (mx - 40) / float(self.width - 80)
                        target_sec = progress * self.streamer.total_duration
                        self.streamer.seek(target_sec, self.sync_offset_ms / 1000.0)

            # Audio Ingestion & Analysis step
            if self.streamer.is_playing:
                self.streamer.advance_ingest_frame(self.sync_offset_ms / 1000.0)
                self.listener.update()

                # Shift past ODF buffer
                speaker_offset = int(self.listener.analyzer.lookahead_seconds * self.listener.analyzer.odf_fps)
                odf_buf = self.listener.analyzer.odf_buffer
                speaker_idx = max(0, min(len(odf_buf) - 1, (len(odf_buf) - 1) - speaker_offset))
                current_speaker_odf = odf_buf[speaker_idx]
                self.past_odf[:-1] = self.past_odf[1:]
                self.past_odf[-1] = current_speaker_odf

                # Capture beat triggers
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

                # Capture structural triggers
                if self.listener.is_verse_chorus_change:
                    self.last_drop_time = time.time()
                if self.listener.is_song_change:
                    self.last_song_change_time = time.time()

                # Record rolling structural history
                self.history_novelty[self.history_cursor] = self.listener.combined_novelty
                self.history_lm[self.history_cursor] = self.listener.analyzer.novelty_detector.novelty_lm
                self.history_gm[self.history_cursor] = self.listener.analyzer.novelty_detector.novelty_gm
                self.history_cursor = (self.history_cursor + 1) % self.history_size

                # Update virtual reference LED strip
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

    def _adjust_param(self, direction: int) -> None:
        p = self.tuning_params[self.tuning_selected_idx]
        obj = p["obj"]
        attr = p["attr"]
        cur_val = getattr(obj, attr)
        new_val = float(np.clip(cur_val + direction * p["step"], p["min"], p["max"]))
        setattr(obj, attr, new_val)
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
        title_surf = self.font_title.render("VIALACTÉE MUSIC STUDIO", True, self.ACCENT_CYAN)
        self.screen.blit(title_surf, (40, 15))

        sub_surf = self.font_small.render("Predictive Flywheel & Real-Time DSP Analysis Lab", True, self.TEXT_DIM)
        self.screen.blit(sub_surf, (title_surf.get_width() + 55, 18))

        # Track name
        song_name = os.path.basename(self.streamer.file_path)
        track_surf = self.font_main.render(f"Track [{self.song_index + 1}/{len(self.song_list)}]: {song_name}", True, self.TEXT_MAIN)
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
        time_surf = self.font_small.render(time_str, True, self.TEXT_DIM)
        self.screen.blit(time_surf, (bar_x, bar_y + 12))

        # A/V Sync readout
        sync_color = self.ACCENT_CYAN if self.sync_offset_ms != 0 else self.TEXT_DIM
        sync_label = f"A/V Sync: {self.sync_offset_ms:+.0f} ms (K / L to tune)"
        sync_surf = self.font_small.render(sync_label, True, sync_color)
        self.screen.blit(sync_surf, (bar_x + time_surf.get_width() + 25, bar_y + 12))

        # Toast notification
        if time.time() - self.status_msg_time < 3.0:
            msg_surf = self.font_main.render(self.status_msg, True, self.status_color)
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

        head_surf = self.font_main.render("PREDICTIVE ONSET DETECTION (ODF) & 5.0-SECOND LOOKAHEAD OSCILLOSCOPE", True, self.ACCENT_CYAN)
        self.screen.blit(head_surf, (px + 16, py + 10))

        sub_surf = self.font_small.render("Future audio chunks streamed 5.0s ahead of speaker playback time — Wave travels RIGHT (Future) to LEFT (Speaker Now)", True, self.TEXT_DIM)
        self.screen.blit(sub_surf, (px + 16, py + 30))

        # Scope display area
        gx = px + 16
        gy = py + 52
        gw = pw - 32
        gh = ph - 64
        pygame.draw.rect(self.screen, (12, 14, 19), (gx, gy, gw, gh), border_radius=6)
        pygame.draw.rect(self.screen, (26, 32, 44), (gx, gy, gw, gh), width=1, border_radius=6)

        # Speaker cursor sits at ~15% from left (representing T_speaker)
        # Left 15% represents past 1.0s (60 frames). Right 85% represents future 5.0s (300 frames).
        cursor_ratio = 0.15
        cursor_x = gx + int(gw * cursor_ratio)

        # Grid lines
        pygame.draw.line(self.screen, (22, 28, 38), (gx, gy + gh // 2), (gx + gw, gy + gh // 2), 1)
        for s in range(1, 6):
            sec_x = cursor_x + int((gw - int(gw * cursor_ratio)) * (s / 5.0))
            if sec_x < gx + gw:
                pygame.draw.line(self.screen, (22, 28, 38), (sec_x, gy), (sec_x, gy + gh), 1)
                t_lbl = self.font_small.render(f"+{s}s", True, self.TEXT_MUTED)
                self.screen.blit(t_lbl, (sec_x - t_lbl.get_width() // 2, gy + 4))

        # Speaker Line (NOW)
        pygame.draw.line(self.screen, self.ACCENT_GOLD, (cursor_x, gy), (cursor_x, gy + gh), 2)
        speaker_lbl = self.font_small.render("▼ SPEAKER NOW", True, self.ACCENT_GOLD)
        self.screen.blit(speaker_lbl, (cursor_x - speaker_lbl.get_width() // 2, gy - 14))

        # Concatenate past ODF and future ODF buffer
        odf_buf = self.listener.analyzer.odf_buffer
        total_stream = np.concatenate((self.past_odf, odf_buf))
        total_len = len(total_stream)

        max_val = max(15.0, float(np.max(total_stream)))
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
            if i < self.past_odf_len:
                # Past section (0 to cursor_x)
                x = gx + int(int(gw * cursor_ratio) * (i / float(self.past_odf_len)))
            else:
                # Future section (cursor_x to end)
                future_idx = i - self.past_odf_len
                x = cursor_x + int((gw - int(gw * cursor_ratio)) * (future_idx / float(len(odf_buf))))

            val = total_stream[i]
            y = int(gy + gh - 8 - val * scale_y)
            y = max(gy + 4, min(gy + gh - 4, y))
            points.append((x, y))

        if len(points) > 1:
            # Draw glow line
            pygame.draw.lines(self.screen, (0, 180, 210), False, points, 2)

        # Overlay Pearson Template Pulse Wave for estimated BPM
        bpm = self.listener.bpm
        if bpm > 0:
            tau_frames = 60.0 * 60.0 / bpm  # frames per beat at 60 fps
            template_pts = []
            cur_phase = self.listener.beat_phase
            phase_offset = cur_phase * tau_frames

            for i in range(len(odf_buf)):
                future_x = cursor_x + int((gw - int(gw * cursor_ratio)) * (i / float(len(odf_buf))))
                phi = ((i + phase_offset) % tau_frames) / tau_frames
                dist = min(phi, 1.0 - phi)
                pulse = max(0.0, 1.0 - (dist / 0.1)) if dist < 0.1 else 0.0

                py_val = int(gy + gh - 8 - pulse * (gh * 0.4))
                template_pts.append((future_x, py_val))

            if len(template_pts) > 1:
                pygame.draw.lines(self.screen, (170, 0, 255), False, template_pts, 1)

        # Legend tags
        leg_odf = self.font_small.render("● Spectral Flux (ODF)", True, self.ACCENT_CYAN)
        leg_tpl = self.font_small.render("--- Oracle Template Pulse", True, self.ACCENT_PURPLE)
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
        head_surf = self.font_main.render("ANTICIPATION FLYWHEEL & BEAT TRACKER", True, self.ACCENT_CYAN)
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
        stat_surf = self.font_mono.render(stat_txt, True, ring_color)
        self.screen.blit(stat_surf, (cx - stat_surf.get_width() // 2, cy + radius + 12))

        # Readout details on right side of gauge
        rx = px + 175
        ry = py + 50

        # BPM
        bpm_val = self.listener.bpm
        bpm_surf = self.font_big_num.render(f"{bpm_val:.1f}", True, self.TEXT_MAIN)
        self.screen.blit(bpm_surf, (rx, ry))
        bpm_lbl = self.font_small.render("BPM", True, self.TEXT_DIM)
        self.screen.blit(bpm_lbl, (rx + bpm_surf.get_width() + 8, ry + 12))

        # Pearson Confidence
        conf = float(np.clip(self.listener.beat_confidence, 0.0, 1.0))
        ry += 42
        conf_lbl = self.font_small.render(f"Pearson Conf: {conf * 100:.0f}%", True, self.TEXT_DIM)
        self.screen.blit(conf_lbl, (rx, ry))

        bar_w = pw - (rx - px) - 20
        pygame.draw.rect(self.screen, (14, 16, 22), (rx, ry + 16, bar_w, 10), border_radius=3)
        conf_fill = int(bar_w * conf)
        if conf_fill > 0:
            c_color = self.ACCENT_GREEN if conf >= 0.30 else (self.ACCENT_ORANGE if conf >= 0.15 else self.ACCENT_RED)
            pygame.draw.rect(self.screen, c_color, (rx, ry + 16, conf_fill, 10), border_radius=3)

        # Threshold tick lines at 0.15 and 0.30
        t15 = rx + int(bar_w * 0.15)
        t30 = rx + int(bar_w * 0.30)
        pygame.draw.line(self.screen, (160, 160, 160), (t15, ry + 14), (t15, ry + 28), 1)
        pygame.draw.line(self.screen, (220, 220, 220), (t30, ry + 14), (t30, ry + 28), 1)

        # Logarithmic Tempo Class (Octave Ring)
        ry += 36
        lbt_class = bpm_to_class(bpm_val)
        class_str = f"Octave Class: {lbt_class:.3f}"
        class_surf = self.font_small.render(class_str, True, self.TEXT_DIM)
        self.screen.blit(class_surf, (rx, ry))

        # Harmonic Candidates
        ry += 18
        base_b = 60.0 * (2.0 ** lbt_class)
        harm_str = f"Harmonics: {base_b*0.5:.0f} | {base_b:.0f} | {base_b*1.5:.0f}"
        harm_surf = self.font_small.render(harm_str, True, self.TEXT_MUTED)
        self.screen.blit(harm_surf, (rx, ry))

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
            t_surf = self.font_title.render(tag_txt, True, (255, 255, 255))
            self.screen.blit(t_surf, (strobe_rect.centerx - t_surf.get_width() // 2, strobe_rect.centery - t_surf.get_height() // 2))
        else:
            pygame.draw.rect(self.screen, (14, 16, 22), strobe_rect, border_radius=6)
            pygame.draw.rect(self.screen, (28, 34, 46), strobe_rect, width=1, border_radius=6)
            idle_surf = self.font_mono.render("WAITING FOR BEAT IMPULSE", True, (70, 80, 95))
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

        head_surf = self.font_main.render("8-BAND FREQUENCY DYNAMICS & SPECTRAL PEAKS", True, self.ACCENT_CYAN)
        self.screen.blit(head_surf, (px + 16, py + 12))

        # Equalizer Bars Area
        gx = px + 16
        gy = py + 42
        gw = pw - 32
        gh = 175

        col_w = (gw - 28) / 8.0

        raw_fft = self.listener.fft_band_values
        smooth_fft = self.listener.smoothed_fft_band_values
        asserved_fft = self.listener.asserved_fft_band
        band_peaks = self.listener.band_peak
        band_flux = self.listener.band_flux

        max_raw = max(50.0, float(np.max(smooth_fft)) if len(smooth_fft) > 0 else 50.0)

        for i in range(8):
            bx = int(gx + i * (col_w + 4))
            bw = int(col_w)

            # Background slot
            pygame.draw.rect(self.screen, (14, 16, 22), (bx, gy, bw, gh), border_radius=4)

            # Peak LED indicator at top of each column
            has_peak = len(band_peaks) > i and band_peaks[i] > 0
            led_col = self.ACCENT_RED if has_peak else (40, 48, 64)
            pygame.draw.rect(self.screen, led_col, (bx + 2, gy + 4, bw - 4, 6), border_radius=2)

            # Raw energy ghost bar
            r_val = raw_fft[i] if i < len(raw_fft) else 0.0
            r_h = min(gh - 20, int((r_val / max_raw) * (gh - 20)))
            if r_h > 0:
                pygame.draw.rect(self.screen, (30, 45, 60), (bx + 2, gy + gh - 6 - r_h, bw - 4, r_h), border_radius=2)

            # Smoothed energy solid bar
            s_val = smooth_fft[i] if i < len(smooth_fft) else 0.0
            s_h = min(gh - 20, int((s_val / max_raw) * (gh - 20)))
            if s_h > 0:
                # Color gradient from cyan/blue to green/yellow
                bar_color = self.ACCENT_CYAN if i < 2 else (self.ACCENT_GREEN if i < 5 else self.ACCENT_GOLD)
                pygame.draw.rect(self.screen, bar_color, (bx + 4, gy + gh - 6 - s_h, bw - 8, s_h), border_radius=2)

            # Asserved floating peak cap
            a_val = asserved_fft[i] if i < len(asserved_fft) else 0.0
            a_y = gy + gh - 6 - int(a_val * (gh - 24))
            pygame.draw.rect(self.screen, (255, 255, 255), (bx + 3, a_y, bw - 6, 2))

            # Band short label
            b_lbl = self.font_small.render(f"B{i}", True, self.TEXT_DIM)
            self.screen.blit(b_lbl, (bx + bw // 2 - b_lbl.get_width() // 2, gy + gh + 4))

        # Total Power Asservation footer within panel 3
        tp_y = py + 242
        tp_rect = pygame.Rect(px + 16, tp_y, pw - 32, 26)
        pygame.draw.rect(self.screen, (14, 16, 22), tp_rect, border_radius=4)

        tot_p = float(self.listener.asserved_total_power)
        p_fill = int(tp_rect.width * min(1.0, tot_p))
        if p_fill > 0:
            pygame.draw.rect(self.screen, self.ACCENT_PURPLE, (tp_rect.x, tp_rect.y, p_fill, tp_rect.height), border_radius=4)

        p_lbl = self.font_small.render(f"Total Power Asserved: {tot_p * 100:.0f}%", True, self.TEXT_MAIN)
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

        head_surf = self.font_main.render("12-TONE CHROMAGRAM & HARMONY", True, self.ACCENT_CYAN)
        self.screen.blit(head_surf, (px + 16, py + 12))

        chroma = self.listener.smoothed_chroma_values
        raw_chroma = self.listener.chroma_values
        dom_pitch = int(np.argmax(chroma)) if len(chroma) > 0 else 0
        dom_note = self.CHROMA_NAMES[dom_pitch]

        # Dominant pitch badge
        badge_surf = self.font_mono.render(f"KEY: {dom_note}", True, self.ACCENT_GOLD)
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
            n_lbl = self.font_small.render(self.CHROMA_NAMES[i], True, lbl_color)
            self.screen.blit(n_lbl, (bx + bw // 2 - n_lbl.get_width() // 2, gy + gh + 4))

        # Circular note summary
        summary_y = py + 242
        note_text = f"Dominant Pitch Class: {dom_note} (Bin {dom_pitch})"
        s_surf = self.font_small.render(note_text, True, self.TEXT_MAIN)
        self.screen.blit(s_surf, (px + 16, summary_y + 4))

    # =================================================================
    # PANEL 5: STRUCTURAL NOVELTY & DROP SCOPE
    # =================================================================

    def _draw_panel_5_structural_novelty(self) -> None:
        px = 40
        py = 590
        pw = self.width - 80
        ph = 250

        pygame.draw.rect(self.screen, self.PANEL_BG, (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, (px, py, pw, ph), width=1, border_radius=8)

        # Header & Badges
        head_surf = self.font_main.render("STRUCTURAL NOVELTY, MACRO TENSION & DROP DETECTION", True, self.ACCENT_CYAN)
        self.screen.blit(head_surf, (px + 16, py + 12))

        # Event Badges
        bx = px + head_surf.get_width() + 35

        # Verse / Chorus Drop Badge
        t_since_drop = time.time() - self.last_drop_time
        if t_since_drop < 1.5:
            d_alpha = 1.0 - (t_since_drop / 1.5)
            d_surf = self.font_mono.render("★ VERSE / CHORUS DROP", True, self.ACCENT_PURPLE)
            pygame.draw.rect(self.screen, (60, 20, 90), (bx, py + 10, d_surf.get_width() + 16, 22), border_radius=4)
            pygame.draw.rect(self.screen, self.ACCENT_PURPLE, (bx, py + 10, d_surf.get_width() + 16, 22), width=1, border_radius=4)
            self.screen.blit(d_surf, (bx + 8, py + 13))
            bx += d_surf.get_width() + 25

        # Song Cut / Transition Badge
        t_since_song = time.time() - self.last_song_change_time
        if t_since_song < 2.0:
            s_surf = self.font_mono.render("⚡ SONG TRANSITION", True, self.ACCENT_ORANGE)
            pygame.draw.rect(self.screen, (90, 50, 20), (bx, py + 10, s_surf.get_width() + 16, 22), border_radius=4)
            pygame.draw.rect(self.screen, self.ACCENT_ORANGE, (bx, py + 10, s_surf.get_width() + 16, 22), width=1, border_radius=4)
            self.screen.blit(s_surf, (bx + 8, py + 13))

        # Real-time Graph Area
        gx = px + 16
        gy = py + 44
        gw = pw - 340
        gh = ph - 60

        pygame.draw.rect(self.screen, (12, 14, 19), (gx, gy, gw, gh), border_radius=6)
        pygame.draw.rect(self.screen, (26, 32, 44), (gx, gy, gw, gh), width=1, border_radius=6)

        # Plot STM vs LTM Timbral Divergence (Cyan), LM (Orange), GM (Purple)
        # Unwrap circular history buffer
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
        leg_nov = self.font_small.render("● Combined Novelty (STM vs LTM)", True, self.ACCENT_CYAN)
        leg_lm = self.font_small.render("--- Local Max (LM)", True, self.ACCENT_ORANGE)
        leg_gm = self.font_small.render("--- Global Max (GM Macro Threshold)", True, self.ACCENT_PURPLE)

        self.screen.blit(leg_nov, (gx + 12, gy + 8))
        self.screen.blit(leg_lm, (gx + 12, gy + 24))
        self.screen.blit(leg_gm, (gx + 12, gy + 40))

        # Right sidebar inside Panel 5: Meters and Counters
        rx = gx + gw + 24
        ry = gy + 4

        # Asserved Novelty Meter
        asserv_nov = float(self.listener.asserved_novelty)
        self.screen.blit(self.font_small.render(f"Asserved Novelty: {asserv_nov * 100:.0f}%", True, self.TEXT_MAIN), (rx, ry))
        ry += 18
        an_rect = pygame.Rect(rx, ry, 280, 16)
        pygame.draw.rect(self.screen, (14, 16, 22), an_rect, border_radius=4)
        an_fill = int(an_rect.width * min(1.0, asserv_nov))
        if an_fill > 0:
            an_col = self.ACCENT_PURPLE if asserv_nov >= 0.8 else self.ACCENT_CYAN
            pygame.draw.rect(self.screen, an_col, (an_rect.x, an_rect.y, an_fill, an_rect.height), border_radius=4)

        # Song cut threshold tick
        th_val = self.listener.analyzer.config.song_novelty_asserved_th
        th_x = rx + int(an_rect.width * th_val)
        pygame.draw.line(self.screen, self.ACCENT_RED, (th_x, ry - 2), (th_x, ry + 18), 2)
        th_lbl = self.font_small.render(f"Drop Th: {th_val:.2f}", True, self.TEXT_MUTED)
        self.screen.blit(th_lbl, (th_x - 30, ry + 20))

        # Memory Envelope Readouts
        ry += 48
        detector = self.listener.analyzer.novelty_detector
        stm_lbl = self.font_small.render(f"STM Power: {detector.stm_power:.2f}", True, self.TEXT_DIM)
        ltm_lbl = self.font_small.render(f"LTM Power: {detector.ltm_power:.2f}", True, self.TEXT_DIM)
        self.screen.blit(stm_lbl, (rx, ry))
        self.screen.blit(ltm_lbl, (rx + 140, ry))

        ry += 22
        lm_lbl = self.font_small.render(f"Novelty LM: {detector.novelty_lm:.3f}", True, self.ACCENT_ORANGE)
        gm_lbl = self.font_small.render(f"Novelty GM: {detector.novelty_gm:.3f}", True, self.ACCENT_PURPLE)
        self.screen.blit(lm_lbl, (rx, ry))
        self.screen.blit(gm_lbl, (rx + 140, ry))

        ry += 24
        sil_lbl = self.font_small.render(f"Silence Frames: {detector.silence_frames} / {detector.silence_threshold_frames}", True, self.TEXT_MUTED)
        self.screen.blit(sil_lbl, (rx, ry))

    # =================================================================
    # PANEL 6: LIVE PARAMETER TUNING DRAWER ([T] KEY)
    # =================================================================

    def _draw_tuning_drawer(self) -> None:
        dw = 380
        dh = 420
        dx = self.width - dw - 40
        dy = 120

        # Semi-transparent backdrop surface
        overlay = pygame.Surface((dw, dh), pygame.SRCALPHA)
        overlay.fill((16, 20, 28, 240))
        self.screen.blit(overlay, (dx, dy))

        pygame.draw.rect(self.screen, self.ACCENT_GOLD, (dx, dy, dw, dh), width=2, border_radius=8)

        # Header
        t_head = self.font_main.render("LIVE DSP PARAMETER TUNER [T]", True, self.ACCENT_GOLD)
        self.screen.blit(t_head, (dx + 16, dy + 16))

        t_sub = self.font_small.render("Use [↑/↓] to select, [←/→] to adjust, [D] default", True, self.TEXT_DIM)
        self.screen.blit(t_sub, (dx + 16, dy + 38))

        # Parameters List
        py = dy + 68
        for i, p in enumerate(self.tuning_params):
            is_sel = (i == self.tuning_selected_idx)
            val = getattr(p["obj"], p["attr"])

            row_rect = pygame.Rect(dx + 12, py, dw - 24, 40)
            if is_sel:
                pygame.draw.rect(self.screen, (32, 40, 56), row_rect, border_radius=4)
                pygame.draw.rect(self.screen, self.ACCENT_CYAN, row_rect, width=1, border_radius=4)

            name_color = self.ACCENT_CYAN if is_sel else self.TEXT_MAIN
            lbl_surf = self.font_small.render(p["label"], True, name_color)
            val_surf = self.font_mono.render(p["fmt"].format(val), True, self.ACCENT_GOLD if is_sel else self.TEXT_MAIN)

            self.screen.blit(lbl_surf, (dx + 20, py + 6))
            self.screen.blit(val_surf, (dx + dw - val_surf.get_width() - 25, py + 6))

            # Slider bar
            s_bar_w = dw - 45
            pygame.draw.rect(self.screen, (10, 12, 16), (dx + 20, py + 24, s_bar_w, 6), border_radius=3)
            ratio = (val - p["min"]) / max(1e-6, p["max"] - p["min"])
            fill_w = int(s_bar_w * np.clip(ratio, 0.0, 1.0))
            if fill_w > 0:
                pygame.draw.rect(self.screen, self.ACCENT_CYAN if is_sel else self.TEXT_DIM, (dx + 20, py + 24, fill_w, 6), border_radius=3)

            py += 46

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
        f_surf = self.font_small.render(total_str, True, self.TEXT_DIM)
        self.screen.blit(f_surf, (self.width // 2 - f_surf.get_width() // 2, footer_y))


# =====================================================================
# CLI ENTRY POINT
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Vialactée Music Studio - Real-Time DSP & Music Analysis Laboratory")
    parser.add_argument("--song", "-s", type=str, default=None, help="Path to MP3 or WAV file")
    parser.add_argument("--leds", "-l", type=int, default=80, help="Number of LEDs in reference segment (default: 80)")
    args = parser.parse_args()

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

    app = MusicStudioApp(song_path=song_path, nb_leds=args.leds)
    app.run()


if __name__ == "__main__":
    main()
