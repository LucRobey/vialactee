"""
tools/structural_annotator.py - Dedicated Interactive Structural Music Annotator.

Human-in-the-loop listening and ground-truth annotation across the 10 neural-core
benchmark tracks (and arbitrary audio files).

Features:
- Standalone interactive Pygame + sounddevice application.
- Sample-accurate audio clock using sounddevice output stream callback frames consumed
  minus output DAC latency (zero wall-clock drift).
- Pre-cached audio array loading (.npz) with fallbacks (soundfile / librosa).
- Vectorized waveform envelope calculation (instant rendering at 60 FPS).
- BeatNet downbeat overlay from neural/<Track>.downbeats.txt showing measure boundaries.
- One-key event tagging:
    [D] -> CLIMAX_OR_DROP (Red)
    [B] -> BUILDUP_OR_RISER (Yellow)
    [X] -> BREAKDOWN_OR_SOLO (Blue)
    [S] -> SECTION_CHANGE (Green)
- Reflex compensation: -100ms offset on live taps while playing; 0ms when paused.
- Marker editing: click to select, nudge +/-10ms ([,] / [.]), snap to downbeat ([G]),
  delete ([Delete]/[Backspace]), undo/redo ([Ctrl+Z] / [Ctrl+Y]).
- Buildup-to-drop linking (pair_id) for anticipation lead-time analysis.
- Clean, atomic JSON persistence to research/benchmarks/ground_truth/structural_annotations.json.
- Track navigation: [N] / [P] across the 10 neural-core tracks.
- Minimalist, ergonomic, and aesthetic dark-theme UI with on-screen event table and hotkey guide.
"""

from __future__ import annotations
import os
import sys
import time
import math
import json
import copy
import argparse
from typing import Dict, Any, List, Optional, Tuple, Set

# Ensure repository root is on sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import sounddevice as sd
import pygame


# =====================================================================
# CONSTANTS & COLOR PALETTE
# =====================================================================

EVENT_CLIMAX = "CLIMAX_OR_DROP"
EVENT_BUILDUP = "BUILDUP_OR_RISER"
EVENT_BREAKDOWN = "BREAKDOWN_OR_SOLO"
EVENT_SECTION = "SECTION_CHANGE"

EVENT_TYPES = [EVENT_CLIMAX, EVENT_BUILDUP, EVENT_BREAKDOWN, EVENT_SECTION]

EVENT_COLORS = {
    EVENT_CLIMAX: (239, 68, 68),      # Crisp Red
    EVENT_BUILDUP: (245, 158, 11),     # Amber / Gold
    EVENT_BREAKDOWN: (59, 130, 246),   # Royal Blue
    EVENT_SECTION: (34, 197, 94),      # Emerald Green
}

EVENT_ICONS = {
    EVENT_CLIMAX: "DROP",
    EVENT_BUILDUP: "RISE",
    EVENT_BREAKDOWN: "BREAK",
    EVENT_SECTION: "SECT",
}

# Theme Colors (Deep Charcoal / Modern Obsidian)
COLOR_BG = (17, 19, 24)
COLOR_PANEL = (24, 27, 34)
COLOR_PANEL_HEADER = (30, 34, 44)
COLOR_BORDER = (46, 52, 66)
COLOR_BORDER_LIGHT = (68, 77, 98)

COLOR_TIMELINE_BG = (13, 15, 19)
COLOR_WAVE_CENTER = (35, 42, 54)
COLOR_WAVE_FILL = (55, 95, 145)
COLOR_WAVE_PEAK = (90, 160, 235)
COLOR_WAVE_OVERVIEW = (65, 110, 160)

COLOR_DOWNBEAT = (40, 150, 175)
COLOR_DOWNBEAT_LINE = (28, 65, 80)
COLOR_PLAYHEAD = (255, 255, 255)
COLOR_SELECTION = (251, 191, 36)

COLOR_TEXT_MAIN = (240, 243, 246)
COLOR_TEXT_MUTED = (145, 155, 170)
COLOR_TEXT_DIM = (85, 95, 110)
COLOR_ACCENT_CYAN = (56, 189, 248)
COLOR_ACCENT_GREEN = (34, 197, 94)
COLOR_ACCENT_AMBER = (245, 158, 11)
COLOR_ACCENT_RED = (239, 68, 68)


# =====================================================================
# AUDIO STREAMER (Sample-Accurate Audio Clock)
# =====================================================================

class AudioStreamer:
    """
    Sample-accurate audio streamer using sounddevice output stream callback frames
    consumed minus output DAC latency (borrowed/adapted from tools/music_studio.py).
    Guarantees 100% zero drift between audio output and visual playhead.
    Gracefully falls back to a software timer in headless / soundcard-less environments.
    """

    def __init__(self, mono_data: np.ndarray, sample_rate: int = 44100):
        self.mono_data = mono_data.astype(np.float32)
        self.sample_rate = sample_rate
        self.stereo_data = np.column_stack((self.mono_data, self.mono_data))
        self.total_samples = len(self.mono_data)
        self.total_duration = float(self.total_samples) / float(self.sample_rate)

        self.speaker_sample_pos = 0
        self.dac_latency = 0.0
        self.is_playing = False
        self.is_finished = False
        self.volume = 1.0

        # Software clock fallback state
        self._fallback_mode = False
        self._fallback_time = 0.0
        self._fallback_last_tick = time.perf_counter()

        self.stream: Optional[sd.OutputStream] = None
        self._init_stream()

    def _init_stream(self) -> None:
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=2,
                blocksize=1024,
                callback=self._audio_callback
            )
            self.stream.start()
            self._fallback_mode = False
        except Exception as e:
            # Fallback for headless / CI systems without audio devices
            self.stream = None
            self._fallback_mode = True

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
            self.is_playing = False
            return

        if end <= self.total_samples:
            outdata[:] = self.stereo_data[pos:end] * self.volume
        else:
            avail = self.total_samples - pos
            outdata[:avail] = self.stereo_data[pos:self.total_samples] * self.volume
            outdata[avail:].fill(0)
            self.is_finished = True
            self.is_playing = False

        self.speaker_sample_pos += frames

    def get_actual_speaker_sample(self) -> int:
        if self._fallback_mode:
            return int(self._fallback_time * self.sample_rate)
        if not self.is_playing:
            return self.speaker_sample_pos
        dac_frames = int(self.dac_latency * self.sample_rate)
        return max(0, min(self.total_samples, self.speaker_sample_pos - dac_frames))

    def get_current_time(self) -> float:
        if self._fallback_mode:
            now = time.perf_counter()
            if self.is_playing:
                dt = now - self._fallback_last_tick
                self._fallback_time = min(self.total_duration, self._fallback_time + dt)
                if self._fallback_time >= self.total_duration:
                    self.is_finished = True
            self._fallback_last_tick = now
            return self._fallback_time

        return float(self.get_actual_speaker_sample()) / float(self.sample_rate)

    def seek(self, target_seconds: float) -> None:
        target_seconds = max(0.0, min(self.total_duration, target_seconds))
        if self._fallback_mode:
            self._fallback_time = target_seconds
            self._fallback_last_tick = time.perf_counter()
        else:
            target_sample = int(target_seconds * self.sample_rate)
            self.speaker_sample_pos = min(self.total_samples, target_sample)
        self.is_finished = False

    def play(self) -> None:
        self.is_playing = True
        self.is_finished = False
        if self._fallback_mode:
            self._fallback_last_tick = time.perf_counter()

    def pause(self) -> None:
        self.is_playing = False

    def toggle_play(self) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def stop(self) -> None:
        self.is_playing = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None


# =====================================================================
# WAVEFORM ENVELOPE PRE-COMPUTATION
# =====================================================================

class WaveformEnvelope:
    """
    Computes and caches multi-scale audio waveform peak envelopes for zero-lag
    rendering at 60 FPS across both overview and zoomed timeline viewports.
    """

    def __init__(self, mono_data: np.ndarray, sample_rate: int = 44100, overview_bins: int = 1600):
        self.sample_rate = sample_rate
        self.total_samples = len(mono_data)
        self.total_duration = float(self.total_samples) / float(self.sample_rate)

        # 1. Overview Envelope (Fixed number of bins across entire track)
        overview_bins = max(200, overview_bins)
        chunk = max(1, self.total_samples // overview_bins)
        valid_len = overview_bins * chunk
        if valid_len > 0 and valid_len <= self.total_samples:
            reshaped = mono_data[:valid_len].reshape(overview_bins, chunk)
            self.overview_min = np.amin(reshaped, axis=1)
            self.overview_max = np.amax(reshaped, axis=1)
        else:
            self.overview_min = np.zeros(overview_bins, dtype=np.float32)
            self.overview_max = np.zeros(overview_bins, dtype=np.float32)

        # 2. Fine Timeline Envelope (Chunk size = 256 samples, ~5.8ms resolution)
        self.fine_chunk_size = 256
        n_fine = self.total_samples // self.fine_chunk_size
        fine_valid = n_fine * self.fine_chunk_size
        if fine_valid > 0:
            fine_reshaped = mono_data[:fine_valid].reshape(n_fine, self.fine_chunk_size)
            self.fine_min = np.amin(fine_reshaped, axis=1)
            self.fine_max = np.amax(fine_reshaped, axis=1)
        else:
            self.fine_min = np.zeros(1, dtype=np.float32)
            self.fine_max = np.zeros(1, dtype=np.float32)
        self.fine_step_sec = float(self.fine_chunk_size) / float(self.sample_rate)

    def get_timeline_slice(self, t_start: float, t_end: float, target_pixels: int) -> Tuple[np.ndarray, np.ndarray]:
        """Returns min and max envelope arrays resampled to target_pixels for [t_start, t_end]."""
        target_pixels = max(10, target_pixels)
        out_min = np.zeros(target_pixels, dtype=np.float32)
        out_max = np.zeros(target_pixels, dtype=np.float32)

        if len(self.fine_min) == 0 or t_end <= t_start or self.total_duration <= 0:
            return out_min, out_max

        dur = t_end - t_start
        # Time corresponding to each horizontal pixel column
        px_times = t_start + (np.arange(target_pixels, dtype=np.float32) / float(target_pixels)) * dur

        valid_mask = (px_times >= 0.0) & (px_times < self.total_duration)
        if not np.any(valid_mask):
            return out_min, out_max

        valid_indices = np.where(valid_mask)[0]
        fine_indices = np.clip((px_times[valid_mask] / self.fine_step_sec).astype(int), 0, len(self.fine_min) - 1)

        out_min[valid_indices] = self.fine_min[fine_indices]
        out_max[valid_indices] = self.fine_max[fine_indices]
        return out_min, out_max


# =====================================================================
# AUDIO & DOWNBEAT ASSET LOADERS
# =====================================================================

def resolve_audio_file(track_name: str, repo_root: str) -> Optional[Tuple[np.ndarray, int]]:
    """
    Loads raw mono audio for a track by checking direct file paths, pre-cached .npz arrays,
    then falling back to soundfile / librosa if needed.
    """
    # 0. Direct file path check
    if os.path.isfile(track_name):
        return _load_audio_fallback(track_name)
    repo_rel = os.path.join(repo_root, track_name)
    if os.path.isfile(repo_rel):
        return _load_audio_fallback(repo_rel)

    clean_name = os.path.splitext(os.path.basename(track_name))[0]
    names_to_try = [track_name] if clean_name == track_name else [clean_name, track_name]

    candidates = []
    for name in names_to_try:
        candidates.extend([
            os.path.join(repo_root, "assets", "musics", "mp3_files", "librosa", f"{name}.mp3.npz"),
            os.path.join(repo_root, "assets", "musics", "mp3_files", "librosa", f"{name}.npz"),
            os.path.join(repo_root, "research", "benchmarks", "ground_truth", f"{name}.npz"),
        ])

    for c in candidates:
        if os.path.exists(c):
            try:
                data = np.load(c, allow_pickle=True)
                if "y" in data:
                    sr = int(data.get("sr", 44100))
                    return data["y"].astype(np.float32), sr
            except Exception:
                pass

    # Fallback: search in mp3_files
    mp3_dir = os.path.join(repo_root, "assets", "musics", "mp3_files")
    if os.path.exists(mp3_dir):
        for name in names_to_try:
            exact_mp3 = os.path.join(mp3_dir, f"{name}.mp3")
            if os.path.exists(exact_mp3):
                return _load_audio_fallback(exact_mp3)

        for f in os.listdir(mp3_dir):
            for name in names_to_try:
                if f.lower().startswith(name.lower()) and f.endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac")):
                    return _load_audio_fallback(os.path.join(mp3_dir, f))

    return None


def _load_audio_fallback(file_path: str, target_sr: int = 44100) -> Optional[Tuple[np.ndarray, int]]:
    """Loads audio file with soundfile or librosa."""
    try:
        import soundfile as sf
        data, sr = sf.read(file_path, dtype="float32")
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        if sr != target_sr:
            import scipy.signal as signal
            gcd = math.gcd(int(sr), int(target_sr))
            up = target_sr // gcd
            down = sr // gcd
            data = signal.resample_poly(data, up, down, axis=0).astype(np.float32)
        return data, target_sr
    except Exception:
        pass

    try:
        import librosa
        y, sr = librosa.load(file_path, sr=target_sr, mono=True)
        return y.astype(np.float32), target_sr
    except Exception:
        pass

    return None


def load_downbeats(track_name: str, repo_root: str) -> np.ndarray:
    """Loads BeatNet downbeat timestamps from neural ground truth."""
    clean_name = os.path.splitext(os.path.basename(track_name))[0]
    names_to_try = [track_name] if clean_name == track_name else [clean_name, track_name]
    for name in names_to_try:
        downbeats_file = os.path.join(
            repo_root, "research", "benchmarks", "ground_truth", "neural", f"{name}.downbeats.txt"
        )
        if os.path.exists(downbeats_file):
            timestamps = []
            try:
                with open(downbeats_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        try:
                            val = float(line.split()[0])
                            timestamps.append(val)
                        except ValueError:
                            continue
                return np.array(sorted(timestamps), dtype=np.float64)
            except Exception:
                pass
    return np.array([], dtype=np.float64)

    timestamps = []
    try:
        with open(downbeats_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    val = float(line.split()[0])
                    timestamps.append(val)
                except ValueError:
                    continue
    except Exception:
        pass
    return np.array(sorted(timestamps), dtype=np.float64)


def load_catalog_meta(repo_root: str) -> Dict[str, Any]:
    """Loads music catalog metadata (genres, artists, tempos) if available."""
    catalog_path = os.path.join(repo_root, "research", "benchmarks", "ground_truth", "music_catalog.json")
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# =====================================================================
# ANNOTATION MANAGER & PERSISTENCE
# =====================================================================

class AnnotationManager:
    """
    Manages structural event annotations, undo/redo history, and atomic
    JSON file persistence matching the plan_structural_annotator.md schema.
    """

    def __init__(self, json_path: str):
        self.json_path = json_path
        self.schema_version = "1.0"
        self.annotator = "human_expert"
        self.tracks: Dict[str, Dict[str, Any]] = {}
        self.undo_stack: Dict[str, List[List[Dict[str, Any]]]] = {}
        self.redo_stack: Dict[str, List[List[Dict[str, Any]]]] = {}
        self.is_dirty = False
        self.load()

    def load(self) -> None:
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.schema_version = data.get("schema_version", "1.0")
                    self.annotator = data.get("annotator", "human_expert")
                    self.tracks = data.get("tracks", {})
                    self.is_dirty = False
                    return
            except Exception as e:
                print(f"[Warning] Failed to parse existing {self.json_path}: {e}")
        self.tracks = {}
        self.is_dirty = False

    def save(self) -> bool:
        """Atomically saves annotations to JSON file via a temporary file."""
        os.makedirs(os.path.dirname(os.path.abspath(self.json_path)), exist_ok=True)
        tmp_path = f"{self.json_path}.tmp"
        payload = {
            "schema_version": self.schema_version,
            "annotator": self.annotator,
            "tracks": self.tracks,
        }
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.json_path)
            self.is_dirty = False
            return True
        except Exception as e:
            print(f"[Error] Failed to save {self.json_path}: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            return False

    def ensure_track(self, track_name: str, duration_sec: float) -> Dict[str, Any]:
        if track_name not in self.tracks:
            # Conservative default: tracks known without climaxes (e.g. Bohemian Rhapsody) default has_climaxes=False
            has_climaxes = not ("Bohemian Rhapsody" in track_name)
            self.tracks[track_name] = {
                "duration_sec": round(duration_sec, 3),
                "status": "unreviewed",
                "has_climaxes": has_climaxes,
                "events": [],
            }
            self.is_dirty = True
        else:
            self.tracks[track_name]["duration_sec"] = round(duration_sec, 3)

        if track_name not in self.undo_stack:
            self.undo_stack[track_name] = []
            self.redo_stack[track_name] = []

        return self.tracks[track_name]

    def push_state(self, track_name: str) -> None:
        """Pushes current event list to undo stack and clears redo stack."""
        if track_name not in self.tracks:
            return
        if track_name not in self.undo_stack:
            self.undo_stack[track_name] = []
            self.redo_stack[track_name] = []

        current_events = copy.deepcopy(self.tracks[track_name].get("events", []))
        self.undo_stack[track_name].append(current_events)
        if len(self.undo_stack[track_name]) > 60:
            self.undo_stack[track_name].pop(0)
        self.redo_stack[track_name].clear()
        self.is_dirty = True

    def undo(self, track_name: str) -> bool:
        if track_name not in self.undo_stack or not self.undo_stack[track_name]:
            return False
        # Save current to redo
        current_events = copy.deepcopy(self.tracks[track_name].get("events", []))
        self.redo_stack[track_name].append(current_events)
        # Restore previous
        prev_events = self.undo_stack[track_name].pop()
        self.tracks[track_name]["events"] = prev_events
        self.is_dirty = True
        return True

    def redo(self, track_name: str) -> bool:
        if track_name not in self.redo_stack or not self.redo_stack[track_name]:
            return False
        current_events = copy.deepcopy(self.tracks[track_name].get("events", []))
        self.undo_stack[track_name].append(current_events)
        next_events = self.redo_stack[track_name].pop()
        self.tracks[track_name]["events"] = next_events
        self.is_dirty = True
        return True

    def generate_event_id(self, track_name: str) -> str:
        events = self.tracks.get(track_name, {}).get("events", [])
        existing_nums = set()
        for e in events:
            eid = e.get("id", "")
            if eid.startswith("evt_"):
                try:
                    existing_nums.add(int(eid[4:]))
                except ValueError:
                    pass
        num = 1
        while num in existing_nums:
            num += 1
        return f"evt_{num:03d}"

    def auto_link_pair(self, track_name: str, new_event: Dict[str, Any]) -> None:
        """
        Automatically links an unlinked BUILDUP_OR_RISER to a CLIMAX_OR_DROP if
        they occur within a natural musical proximity (<= 45s).
        """
        events = self.tracks.get(track_name, {}).get("events", [])
        evt_type = new_event["type"]
        evt_time = new_event["time_sec"]

        if evt_type == EVENT_CLIMAX:
            # Look backwards for the closest unlinked BUILDUP_OR_RISER
            candidates = [
                e for e in events
                if e["type"] == EVENT_BUILDUP
                and not e.get("pair_id")
                and (evt_time - e["time_sec"]) > 0.5
                and (evt_time - e["time_sec"]) <= 45.0
            ]
            if candidates:
                closest = max(candidates, key=lambda x: x["time_sec"])
                pair_id = f"drop_{new_event['id']}"
                closest["pair_id"] = pair_id
                new_event["pair_id"] = pair_id

        elif evt_type == EVENT_BUILDUP:
            # Look forwards for the closest unlinked CLIMAX_OR_DROP
            candidates = [
                e for e in events
                if e["type"] == EVENT_CLIMAX
                and not e.get("pair_id")
                and (e["time_sec"] - evt_time) > 0.5
                and (e["time_sec"] - evt_time) <= 45.0
            ]
            if candidates:
                closest = min(candidates, key=lambda x: x["time_sec"])
                pair_id = f"drop_{closest['id']}"
                closest["pair_id"] = pair_id
                new_event["pair_id"] = pair_id


# =====================================================================
# PYGAME INTERACTIVE APPLICATION
# =====================================================================

class StructuralAnnotatorApp:
    """
    Full-featured interactive desktop application for structural music annotation.
    """

    def __init__(
        self,
        repo_root: str,
        initial_track: Optional[str] = None,
        headless: bool = False
    ):
        self.repo_root = repo_root
        self.headless = headless
        self.width = 1420
        self.height = 860

        # Discover core tracks from neural_core.json
        core_json = os.path.join(self.repo_root, "research", "benchmarks", "ground_truth", "neural_core.json")
        if os.path.exists(core_json):
            with open(core_json, "r", encoding="utf-8") as f:
                self.track_list = json.load(f)
        if not self.track_list:
            self.track_list = ["Genesis"]

        self.track_index = 0
        if initial_track:
            clean_name = os.path.splitext(os.path.basename(initial_track))[0]
            if initial_track in self.track_list:
                self.track_index = self.track_list.index(initial_track)
            elif clean_name in self.track_list:
                self.track_index = self.track_list.index(clean_name)
            else:
                track_label = clean_name if os.path.isfile(initial_track) else initial_track
                self.track_list.append(track_label)
                self.track_index = len(self.track_list) - 1

        # Persistence Manager
        annotations_json = os.path.join(
            self.repo_root, "research", "benchmarks", "ground_truth", "structural_annotations.json"
        )
        self.manager = AnnotationManager(annotations_json)
        self.catalog = load_catalog_meta(self.repo_root)

        # Pygame initialization
        if not self.headless:
            pygame.init()
            pygame.font.init()
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE | pygame.DOUBLEBUF)
            pygame.display.set_caption("Vialactée — Structural Ground-Truth Annotator")

            # Fonts
            self.font_title = pygame.font.SysFont("Trebuchet MS", 22, bold=True)
            self.font_main = pygame.font.SysFont("Trebuchet MS", 14, bold=True)
            self.font_small = pygame.font.SysFont("Trebuchet MS", 12)
            self.font_mono = pygame.font.SysFont("Consolas", 12, bold=True)
            self.font_mono_small = pygame.font.SysFont("Consolas", 10)
            self.font_clock = pygame.font.SysFont("Trebuchet MS", 30, bold=True)
            self.font_tag = pygame.font.SysFont("Trebuchet MS", 11, bold=True)
        else:
            self.screen = None

        self.clock = pygame.time.Clock() if not self.headless else None
        self._text_cache: Dict[Tuple[int, str, Tuple[int, int, int]], pygame.Surface] = {}

        # Timeline Zoom / Viewport State
        self.timeline_zoom_sec = 16.0  # Total visible seconds in timeline (zoom range: 2.0 to 60.0s)
        self.timeline_scroll_center: Optional[float] = None
        self.selected_event_id: Optional[str] = None
        self.dragging_marker = False
        self.event_table_scroll = 0

        # Text editing modal state
        self.is_editing_note = False
        self.note_edit_buffer = ""

        # Status flash message
        self.status_text = "Ready. Tap [D], [B], [X], [S] to annotate. [Space] to play/pause."
        self.status_color = COLOR_TEXT_MAIN
        self.status_time = time.time()

        # Audio & Envelope state for current track
        self.streamer: Optional[AudioStreamer] = None
        self.envelope: Optional[WaveformEnvelope] = None
        self.downbeats: np.ndarray = np.array([], dtype=np.float64)

        # Load first track
        self.load_track(self.track_list[self.track_index])

    def get_text(self, font: pygame.font.Font, text: str, color: Tuple[int, int, int]) -> pygame.Surface:
        key = (id(font), text, color)
        surf = self._text_cache.get(key)
        if surf is None:
            if len(self._text_cache) > 2500:
                self._text_cache.clear()
            surf = font.render(text, True, color)
            self._text_cache[key] = surf
        return surf

    def set_status(self, msg: str, color: Tuple[int, int, int] = COLOR_TEXT_MAIN) -> None:
        self.status_text = msg
        self.status_color = color
        self.status_time = time.time()

    def current_track_name(self) -> str:
        return self.track_list[self.track_index]

    def current_track_data(self) -> Dict[str, Any]:
        t_name = self.current_track_name()
        duration = self.streamer.total_duration if self.streamer else 100.0
        return self.manager.ensure_track(t_name, duration)

    def load_track(self, track_name: str) -> None:
        """Loads audio, envelopes, downbeats, and annotations for the given track."""
        if self.streamer is not None:
            self.streamer.stop()

        self.selected_event_id = None
        self.timeline_scroll_center = None
        self.is_editing_note = False

        res = resolve_audio_file(track_name, self.repo_root)
        if res is None:
            # Create synthetic 60s silence fallback for headless / missing file testing
            dummy_sr = 44100
            dummy_y = np.zeros(dummy_sr * 60, dtype=np.float32)
            self.streamer = AudioStreamer(dummy_y, sample_rate=dummy_sr)
            self.set_status(f"[Warning] Audio not found for '{track_name}', using blank buffer.", COLOR_ACCENT_RED)
        else:
            y, sr = res
            self.streamer = AudioStreamer(y, sample_rate=sr)
            self.set_status(f"Loaded '{track_name}' ({self.streamer.total_duration:.1f}s)", COLOR_ACCENT_CYAN)

        self.envelope = WaveformEnvelope(self.streamer.mono_data, sample_rate=self.streamer.sample_rate)
        self.downbeats = load_downbeats(track_name, self.repo_root)
        self.manager.ensure_track(track_name, self.streamer.total_duration)

    def change_track(self, delta: int) -> None:
        """Cycles to the next or previous track in neural_core.json."""
        # Auto-save changes on track change
        if self.manager.is_dirty:
            self.manager.save()
        self.track_index = (self.track_index + delta) % len(self.track_list)
        self.load_track(self.track_list[self.track_index])

    # =================================================================
    # EVENT MANIPULATION & ANNOTATION LOGIC
    # =================================================================

    def add_event(self, event_type: str) -> None:
        """
        Adds a new structural event at the current playhead with reflex compensation.
        Live tap while playing: -100ms offset.
        Tap while paused: 0ms offset.
        """
        t_name = self.current_track_name()
        self.manager.push_state(t_name)

        current_playhead = self.streamer.get_current_time() if self.streamer else 0.0
        is_playing = self.streamer.is_playing if self.streamer else False

        # Reflex Compensation
        offset = -0.100 if is_playing else 0.0
        effective_time = max(0.0, current_playhead + offset)
        if self.streamer:
            effective_time = min(self.streamer.total_duration, effective_time)

        evt_id = self.manager.generate_event_id(t_name)
        new_event = {
            "id": evt_id,
            "type": event_type,
            "time_sec": round(effective_time, 3),
            "raw_tap_sec": round(current_playhead, 3),
            "snapped_to_downbeat": False,
            "snap_delta_ms": 0.0,
            "pair_id": None,
            "note": "",
        }

        # Auto-link buildup to drop if within temporal proximity
        self.manager.auto_link_pair(t_name, new_event)

        events = self.current_track_data()["events"]
        events.append(new_event)
        events.sort(key=lambda x: x["time_sec"])

        self.selected_event_id = evt_id
        tag_name = EVENT_ICONS.get(event_type, event_type)
        offset_info = "-100ms reflex offset" if is_playing else "0ms (paused)"
        self.set_status(f"Tagged [{tag_name}] at {effective_time:.3f}s ({offset_info})", EVENT_COLORS.get(event_type, COLOR_ACCENT_CYAN))

    def get_selected_event(self) -> Optional[Dict[str, Any]]:
        if not self.selected_event_id:
            return None
        events = self.current_track_data()["events"]
        for e in events:
            if e["id"] == self.selected_event_id:
                return e
        return None

    def nudge_selected(self, delta_sec: float) -> None:
        """Nudges selected event by +/- delta seconds."""
        evt = self.get_selected_event()
        if not evt:
            return
        t_name = self.current_track_name()
        self.manager.push_state(t_name)

        new_t = max(0.0, evt["time_sec"] + delta_sec)
        if self.streamer:
            new_t = min(self.streamer.total_duration, new_t)
        evt["time_sec"] = round(new_t, 3)
        evt["snapped_to_downbeat"] = False

        events = self.current_track_data()["events"]
        events.sort(key=lambda x: x["time_sec"])
        self.set_status(f"Nudged {evt['id']} to {evt['time_sec']:.3f}s ({delta_sec*1000:+.0f}ms)", COLOR_ACCENT_CYAN)

    def snap_selected_to_downbeat(self) -> None:
        """
        Snaps the selected event to the nearest BeatNet downbeat.
        If already snapped to that downbeat, toggles un-snap back to pre-snap time.
        """
        evt = self.get_selected_event()
        if not evt or len(self.downbeats) == 0:
            self.set_status("No downbeats available to snap.", COLOR_ACCENT_AMBER)
            return

        t_name = self.current_track_name()
        self.manager.push_state(t_name)

        cur_t = evt["time_sec"]
        # Find closest downbeat
        idx = int(np.argmin(np.abs(self.downbeats - cur_t)))
        nearest_db = float(self.downbeats[idx])

        # If already snapped to this exact downbeat, toggle un-snap
        if evt.get("snapped_to_downbeat") and abs(evt["time_sec"] - nearest_db) < 0.005:
            restored_t = evt.get("pre_snap_time_sec")
            if restored_t is None:
                restored_t = evt["time_sec"] - (evt.get("snap_delta_ms", 0.0) / 1000.0)
            evt["time_sec"] = round(float(restored_t), 3)
            evt["snapped_to_downbeat"] = False
            evt["snap_delta_ms"] = 0.0
            self.set_status(f"Un-snapped {evt['id']} back to {evt['time_sec']:.3f}s", COLOR_TEXT_MUTED)
        else:
            delta_ms = round((nearest_db - cur_t) * 1000.0, 1)
            evt["pre_snap_time_sec"] = cur_t
            evt["time_sec"] = round(nearest_db, 3)
            evt["snapped_to_downbeat"] = True
            evt["snap_delta_ms"] = delta_ms
            self.set_status(f"Snapped {evt['id']} to downbeat at {nearest_db:.3f}s ({delta_ms:+.1f}ms)", COLOR_ACCENT_CYAN)

        events = self.current_track_data()["events"]
        events.sort(key=lambda x: x["time_sec"])

    def delete_selected(self) -> None:
        """Deletes the currently selected event and unlinks any paired partner."""
        evt = self.get_selected_event()
        if not evt:
            return
        t_name = self.current_track_name()
        self.manager.push_state(t_name)

        pid = evt.get("pair_id")
        events = self.current_track_data()["events"]
        events[:] = [e for e in events if e["id"] != self.selected_event_id]
        if pid:
            for e in events:
                if e.get("pair_id") == pid:
                    e["pair_id"] = None
        self.set_status(f"Deleted event {self.selected_event_id}", COLOR_ACCENT_RED)
        self.selected_event_id = None

    def link_selected_pair(self) -> None:
        """Links selected event to complementary buildup or drop, unlinking previous partners."""
        evt = self.get_selected_event()
        if not evt:
            return
        t_name = self.current_track_name()
        self.manager.push_state(t_name)

        evt_type = evt["type"]
        events = self.current_track_data()["events"]

        partner = None
        pid = None
        if evt_type == EVENT_CLIMAX:
            # Link to closest preceding BUILDUP_OR_RISER
            candidates = [e for e in events if e["type"] == EVENT_BUILDUP and e["time_sec"] < evt["time_sec"]]
            if candidates:
                partner = max(candidates, key=lambda x: x["time_sec"])
                pid = f"drop_{evt['id']}"
        elif evt_type == EVENT_BUILDUP:
            # Link to closest following CLIMAX_OR_DROP
            candidates = [e for e in events if e["type"] == EVENT_CLIMAX and e["time_sec"] > evt["time_sec"]]
            if candidates:
                partner = min(candidates, key=lambda x: x["time_sec"])
                pid = f"drop_{partner['id']}"

        if partner and pid:
            # Clear old partner of evt if any
            if evt.get("pair_id"):
                old_pid = evt["pair_id"]
                for e in events:
                    if e.get("pair_id") == old_pid and e["id"] != evt["id"]:
                        e["pair_id"] = None
            # Clear old partner of partner if any
            if partner.get("pair_id"):
                old_partner_pid = partner["pair_id"]
                for e in events:
                    if e.get("pair_id") == old_partner_pid and e["id"] != partner["id"]:
                        e["pair_id"] = None

            evt["pair_id"] = pid
            partner["pair_id"] = pid
            self.set_status(f"Linked {partner['id']} <-> {evt['id']} (pair_id: {pid})", COLOR_ACCENT_AMBER)
            return

        self.set_status("No eligible complementary event found to link.", COLOR_ACCENT_AMBER)

    def unlink_selected(self) -> None:
        """Unlinks the pair_id on the selected event and its partner."""
        evt = self.get_selected_event()
        if not evt or not evt.get("pair_id"):
            return
        t_name = self.current_track_name()
        self.manager.push_state(t_name)

        pid = evt["pair_id"]
        events = self.current_track_data()["events"]
        for e in events:
            if e.get("pair_id") == pid:
                e["pair_id"] = None
        self.set_status(f"Cleared link pair {pid}", COLOR_TEXT_MUTED)

    def toggle_has_climaxes(self) -> None:
        td = self.current_track_data()
        td["has_climaxes"] = not td.get("has_climaxes", True)
        self.manager.is_dirty = True
        status_str = "YES" if td["has_climaxes"] else "NO"
        self.set_status(f"Track 'has_climaxes': {status_str}", COLOR_ACCENT_AMBER)

    def toggle_status(self) -> None:
        td = self.current_track_data()
        cur = td.get("status", "unreviewed")
        td["status"] = "reviewed" if cur != "reviewed" else "unreviewed"
        self.manager.is_dirty = True
        self.set_status(f"Track status: {td['status'].upper()}", COLOR_ACCENT_GREEN if td['status'] == 'reviewed' else COLOR_TEXT_MUTED)

    # =================================================================
    # RENDERING METHODS
    # =================================================================

    def render(self) -> None:
        if self.screen is None:
            return

        self.screen.fill(COLOR_BG)
        total_dur = self.streamer.total_duration if self.streamer else 1.0
        cur_time = self.streamer.get_current_time() if self.streamer else 0.0

        # Dynamic panel bounding boxes
        w, h = self.screen.get_size()
        self.width, self.height = w, h

        header_rect = pygame.Rect(0, 0, w, 68)
        overview_rect = pygame.Rect(20, 74, w - 40, 56)
        timeline_rect = pygame.Rect(20, 138, w - 40, 260)

        split_top = 408
        split_h = max(200, h - split_top - 36)
        table_w = int(w * 0.52)
        table_rect = pygame.Rect(20, split_top, table_w - 30, split_h)
        guide_rect = pygame.Rect(table_w, split_top, w - table_w - 20, split_h)

        footer_rect = pygame.Rect(0, h - 30, w, 30)

        # 1. Header
        self._render_header(header_rect, cur_time, total_dur)

        # 2. Overview Waveform Bar
        self._render_overview(overview_rect, cur_time, total_dur)

        # 3. Main Zoomed Timeline
        self._render_timeline(timeline_rect, cur_time, total_dur)

        # 4. Event Table
        self._render_event_table(table_rect)

        # 5. Hotkey Guide & Details Panel
        self._render_guide_panel(guide_rect)

        # 6. Status Footer
        self._render_footer(footer_rect)

        # 7. Modal Note Editing Dialog (if active)
        if self.is_editing_note:
            self._render_note_modal()

        pygame.display.flip()

    def _render_header(self, rect: pygame.Rect, cur_time: float, total_dur: float) -> None:
        pygame.draw.rect(self.screen, COLOR_PANEL_HEADER, rect)
        pygame.draw.line(self.screen, COLOR_BORDER, (rect.left, rect.bottom), (rect.right, rect.bottom))

        t_name = self.current_track_name()
        t_meta = self.catalog.get(t_name, {})
        artist = t_meta.get("artist", "Unknown Artist")
        genre = t_meta.get("genre", "Unknown Genre")

        # Track navigation & title
        idx_str = f"[{self.track_index + 1}/{len(self.track_list)}]"
        t_surf = self.get_text(self.font_title, f"{idx_str}  {t_name}", COLOR_TEXT_MAIN)
        self.screen.blit(t_surf, (24, 12))

        sub_text = f"{artist} • {genre} • Meter: {t_meta.get('meter', '4/4')}"
        sub_surf = self.get_text(self.font_small, sub_text, COLOR_TEXT_MUTED)
        self.screen.blit(sub_surf, (26, 42))

        # Right side: Badges and Playhead Clock
        rx = rect.right - 24

        # Save status pill
        save_col = COLOR_ACCENT_GREEN if not self.manager.is_dirty else COLOR_ACCENT_AMBER
        save_str = "SAVED [Ctrl+S]" if not self.manager.is_dirty else "UNSAVED [Ctrl+S]"
        save_surf = self.get_text(self.font_small, save_str, save_col)
        rx -= save_surf.get_width() + 16
        pygame.draw.rect(self.screen, COLOR_PANEL, (rx, 18, save_surf.get_width() + 16, 28), border_radius=4)
        pygame.draw.rect(self.screen, save_col, (rx, 18, save_surf.get_width() + 16, 28), width=1, border_radius=4)
        self.screen.blit(save_surf, (rx + 8, 24))

        # Status badge (Reviewed / Unreviewed)
        td = self.current_track_data()
        rev_status = td.get("status", "unreviewed")
        rev_col = COLOR_ACCENT_GREEN if rev_status == "reviewed" else COLOR_TEXT_MUTED
        rev_str = f"[{rev_status.upper()}] (R)"
        rev_surf = self.get_text(self.font_small, rev_str, rev_col)
        rx -= rev_surf.get_width() + 16
        pygame.draw.rect(self.screen, COLOR_PANEL, (rx, 18, rev_surf.get_width() + 16, 28), border_radius=4)
        pygame.draw.rect(self.screen, rev_col, (rx, 18, rev_surf.get_width() + 16, 28), width=1, border_radius=4)
        self.screen.blit(rev_surf, (rx + 8, 24))

        # Has Climaxes badge
        has_climax = td.get("has_climaxes", True)
        clim_col = COLOR_ACCENT_RED if has_climax else COLOR_TEXT_DIM
        clim_str = f"CLIMAXES: {'YES' if has_climax else 'NO'} (C)"
        clim_surf = self.get_text(self.font_small, clim_str, clim_col)
        rx -= clim_surf.get_width() + 16
        pygame.draw.rect(self.screen, COLOR_PANEL, (rx, 18, clim_surf.get_width() + 16, 28), border_radius=4)
        pygame.draw.rect(self.screen, clim_col, (rx, 18, clim_surf.get_width() + 16, 28), width=1, border_radius=4)
        self.screen.blit(clim_surf, (rx + 8, 24))

        # Audio Clock (Big numbers)
        disp_time = max(0.0, cur_time)
        cur_min = int(disp_time // 60)
        cur_sec = disp_time % 60
        tot_min = int(total_dur // 60)
        tot_sec = total_dur % 60
        clock_str = f"{cur_min:02d}:{cur_sec:06.3f} / {tot_min:02d}:{tot_sec:05.2f}"
        clock_surf = self.get_text(self.font_clock, clock_str, COLOR_PLAYHEAD)
        rx -= clock_surf.get_width() + 24
        self.screen.blit(clock_surf, (rx, 16))

    def _render_overview(self, rect: pygame.Rect, cur_time: float, total_dur: float) -> None:
        """Renders the full song waveform overview bar with all event markers."""
        pygame.draw.rect(self.screen, COLOR_TIMELINE_BG, rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, width=1, border_radius=6)

        if total_dur <= 0 or not self.envelope:
            return

        mid_y = rect.centery
        amp_scale = (rect.height / 2.0) * 0.90
        n_bins = len(self.envelope.overview_min)

        # Draw overview waveform
        pts_top = []
        pts_bot = []
        for i in range(n_bins):
            x = rect.left + int(i * rect.width / n_bins)
            y_top = mid_y - int(self.envelope.overview_max[i] * amp_scale)
            y_bot = mid_y - int(self.envelope.overview_min[i] * amp_scale)
            pts_top.append((x, y_top))
            pts_bot.append((x, y_bot))

        if len(pts_top) > 1:
            poly = pts_top + pts_bot[::-1]
            pygame.draw.polygon(self.screen, COLOR_WAVE_OVERVIEW, poly)

        # Center line
        pygame.draw.line(self.screen, COLOR_WAVE_CENTER, (rect.left, mid_y), (rect.right, mid_y), 1)

        # Draw event markers on overview
        events = self.current_track_data()["events"]
        for e in events:
            ex = rect.left + int((e["time_sec"] / total_dur) * rect.width)
            col = EVENT_COLORS.get(e["type"], COLOR_TEXT_MAIN)
            pygame.draw.line(self.screen, col, (ex, rect.top + 2), (ex, rect.bottom - 2), 2)

        # Zoom viewport box
        t_center = self.timeline_scroll_center if self.timeline_scroll_center is not None else cur_time
        half_win = self.timeline_zoom_sec / 2.0
        v_start = max(0.0, t_center - half_win)
        v_end = min(total_dur, t_center + half_win)
        vx1 = rect.left + int((v_start / total_dur) * rect.width)
        vx2 = rect.left + int((v_end / total_dur) * rect.width)
        vw = max(4, vx2 - vx1)
        pygame.draw.rect(self.screen, (255, 255, 255, 30), (vx1, rect.top, vw, rect.height), width=1, border_radius=2)

        # Playhead needle
        px = rect.left + int((cur_time / total_dur) * rect.width)
        pygame.draw.line(self.screen, COLOR_PLAYHEAD, (px, rect.top), (px, rect.bottom), 2)

    def _render_timeline(self, rect: pygame.Rect, cur_time: float, total_dur: float) -> None:
        """Renders the high-resolution, zoomable waveform timeline with downbeat grid and markers."""
        pygame.draw.rect(self.screen, COLOR_TIMELINE_BG, rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, width=1, border_radius=6)

        t_center = self.timeline_scroll_center if self.timeline_scroll_center is not None else cur_time
        half_win = self.timeline_zoom_sec / 2.0
        t_start = t_center - half_win
        t_end = t_center + half_win

        def time_to_x(t: float) -> int:
            return rect.left + int(((t - t_start) / (t_end - t_start)) * rect.width)

        def x_to_time(x: int) -> float:
            return t_start + ((x - rect.left) / float(rect.width)) * (t_end - t_start)

        # 1. BeatNet Downbeats Overlay (Measure boundary lines)
        if len(self.downbeats) > 0:
            db_visible = self.downbeats[(self.downbeats >= t_start - 0.5) & (self.downbeats <= t_end + 0.5)]
            for db in db_visible:
                dx = time_to_x(db)
                if rect.left <= dx <= rect.right:
                    # Subtle vertical measure line
                    pygame.draw.line(self.screen, COLOR_DOWNBEAT_LINE, (dx, rect.top + 24), (dx, rect.bottom - 20), 1)
                    # Downbeat tick at bottom ruler
                    pygame.draw.line(self.screen, COLOR_DOWNBEAT, (dx, rect.bottom - 16), (dx, rect.bottom - 2), 2)

        # 2. Time ruler ticks
        ruler_step = 1.0 if self.timeline_zoom_sec <= 20 else (2.0 if self.timeline_zoom_sec <= 40 else 5.0)
        first_tick = math.floor(t_start / ruler_step) * ruler_step
        curr_tick = first_tick
        while curr_tick <= t_end + 0.1:
            tx = time_to_x(curr_tick)
            if rect.left <= tx <= rect.right and curr_tick >= 0:
                pygame.draw.line(self.screen, COLOR_BORDER_LIGHT, (tx, rect.top), (tx, rect.top + 8), 1)
                pygame.draw.line(self.screen, COLOR_BORDER_LIGHT, (tx, rect.bottom - 8), (tx, rect.bottom), 1)
                # Timestamp label
                m = int(curr_tick // 60)
                s = curr_tick % 60
                lbl = self.get_text(self.font_mono_small, f"{m}:{s:04.1f}", COLOR_TEXT_DIM)
                self.screen.blit(lbl, (tx - lbl.get_width() // 2, rect.top + 9))
            curr_tick += ruler_step

        # 3. Waveform Envelope
        if self.envelope:
            mid_y = rect.centery + 4
            amp_scale = (rect.height / 2.0 - 32) * 0.95
            n_px = rect.width
            sub_min, sub_max = self.envelope.get_timeline_slice(t_start, t_end, n_px)

            pts_top = []
            pts_bot = []
            for i in range(len(sub_min)):
                x = rect.left + i
                y_top = mid_y - int(sub_max[i] * amp_scale)
                y_bot = mid_y - int(sub_min[i] * amp_scale)
                pts_top.append((x, y_top))
                pts_bot.append((x, y_bot))

            if len(pts_top) > 1:
                poly = pts_top + pts_bot[::-1]
                pygame.draw.polygon(self.screen, COLOR_WAVE_FILL, poly)
                pygame.draw.lines(self.screen, COLOR_WAVE_PEAK, False, pts_top, 1)

            pygame.draw.line(self.screen, COLOR_WAVE_CENTER, (rect.left, mid_y), (rect.right, mid_y), 1)

        # 4. Event Markers
        events = self.current_track_data()["events"]
        # Render Buildup-to-Drop pair connector arcs
        pair_map: Dict[str, List[Dict[str, Any]]] = {}
        for e in events:
            pid = e.get("pair_id")
            if pid:
                pair_map.setdefault(pid, []).append(e)

        for pid, p_events in pair_map.items():
            if len(p_events) == 2:
                x1 = time_to_x(p_events[0]["time_sec"])
                x2 = time_to_x(p_events[1]["time_sec"])
                if not (x2 < rect.left or x1 > rect.right):
                    # Draw connector bracket above markers
                    arc_y = rect.top + 28
                    p_min_x = max(rect.left + 5, min(x1, x2))
                    p_max_x = min(rect.right - 5, max(x1, x2))
                    pygame.draw.line(self.screen, COLOR_ACCENT_AMBER, (p_min_x, arc_y), (p_max_x, arc_y), 2)
                    lbl_pair = self.get_text(self.font_mono_small, f"PAIR: {pid}", COLOR_ACCENT_AMBER)
                    self.screen.blit(lbl_pair, ((p_min_x + p_max_x) // 2 - lbl_pair.get_width() // 2, arc_y - 12))

        # Render marker flags
        for e in events:
            t = e["time_sec"]
            mx = time_to_x(t)
            if rect.left - 40 <= mx <= rect.right + 40:
                is_selected = (e["id"] == self.selected_event_id)
                col = EVENT_COLORS.get(e["type"], COLOR_TEXT_MAIN)
                line_w = 3 if is_selected else 2

                # Vertical marker line
                pygame.draw.line(self.screen, col, (mx, rect.top + 32), (mx, rect.bottom - 18), line_w)

                # Flag banner at top
                tag_name = EVENT_ICONS.get(e["type"], e["type"])
                snap_badge = " [G]" if e.get("snapped_to_downbeat") else ""
                flag_text = f"{tag_name}{snap_badge}"
                flag_surf = self.get_text(self.font_tag, flag_text, COLOR_BG)
                fw = flag_surf.get_width() + 10
                fh = 20
                flag_rect = pygame.Rect(mx - fw // 2, rect.top + 34, fw, fh)

                pygame.draw.rect(self.screen, col, flag_rect, border_radius=4)
                if is_selected:
                    pygame.draw.rect(self.screen, COLOR_PLAYHEAD, flag_rect, width=2, border_radius=4)
                    # Glow dot at bottom
                    pygame.draw.circle(self.screen, COLOR_SELECTION, (mx, rect.bottom - 18), 5)
                self.screen.blit(flag_surf, (flag_rect.left + 5, flag_rect.top + 3))

                # Millisecond time badge under flag
                time_lbl = self.get_text(self.font_mono_small, f"{t:.3f}s", col)
                self.screen.blit(time_lbl, (mx - time_lbl.get_width() // 2, flag_rect.bottom + 2))

        # 5. Playhead Line & Cursor
        px = time_to_x(cur_time)
        if rect.left <= px <= rect.right:
            pygame.draw.line(self.screen, COLOR_PLAYHEAD, (px, rect.top), (px, rect.bottom), 2)
            # Needle triangle indicator
            pts = [(px - 6, rect.top), (px + 6, rect.top), (px, rect.top + 10)]
            pygame.draw.polygon(self.screen, COLOR_PLAYHEAD, pts)

        # Active reflex offset badge on timeline
        reflex_str = "Reflex: -100ms (Active)" if (self.streamer and self.streamer.is_playing) else "Reflex: 0ms (Paused)"
        reflex_col = COLOR_ACCENT_GREEN if (self.streamer and self.streamer.is_playing) else COLOR_TEXT_MUTED
        r_surf = self.get_text(self.font_small, reflex_str, reflex_col)
        self.screen.blit(r_surf, (rect.right - r_surf.get_width() - 12, rect.top + 8))

    def _render_event_table(self, rect: pygame.Rect) -> None:
        """Renders the scrollable event table."""
        pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, width=1, border_radius=6)

        # Header bar
        th_h = 32
        th_rect = pygame.Rect(rect.left, rect.top, rect.width, th_h)
        pygame.draw.rect(self.screen, COLOR_PANEL_HEADER, th_rect, border_top_left_radius=6, border_top_right_radius=6)
        pygame.draw.line(self.screen, COLOR_BORDER, (rect.left, rect.top + th_h), (rect.right, rect.top + th_h))

        headers = [
            ("ID", 70),
            ("Time (s)", 90),
            ("Type", 140),
            ("Snap", 80),
            ("Pair ID", 90),
            ("Note", rect.width - 470),
        ]
        hx = rect.left + 12
        for title, width in headers:
            h_surf = self.get_text(self.font_small, title, COLOR_TEXT_MUTED)
            self.screen.blit(h_surf, (hx, rect.top + 8))
            hx += width

        # Row entries
        events = self.current_track_data()["events"]
        row_h = 28
        vis_rows = (rect.height - th_h - 10) // row_h
        start_idx = max(0, min(self.event_table_scroll, max(0, len(events) - vis_rows)))

        for i in range(vis_rows):
            evt_idx = start_idx + i
            if evt_idx >= len(events):
                break
            e = events[evt_idx]
            ry = rect.top + th_h + 5 + i * row_h
            r_rect = pygame.Rect(rect.left + 4, ry, rect.width - 8, row_h - 2)

            is_selected = (e["id"] == self.selected_event_id)
            if is_selected:
                pygame.draw.rect(self.screen, (40, 50, 70), r_rect, border_radius=4)
                pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN, r_rect, width=1, border_radius=4)

            rx = rect.left + 12
            # ID
            self.screen.blit(self.get_text(self.font_mono, e["id"], COLOR_TEXT_MUTED), (rx, ry + 5))
            rx += 70

            # Time
            t_col = COLOR_PLAYHEAD if is_selected else COLOR_TEXT_MAIN
            self.screen.blit(self.get_text(self.font_mono, f"{e['time_sec']:06.3f}", t_col), (rx, ry + 5))
            rx += 90

            # Type badge
            etype = e["type"]
            badge_col = EVENT_COLORS.get(etype, COLOR_TEXT_MAIN)
            badge_surf = self.get_text(self.font_tag, EVENT_ICONS.get(etype, etype), COLOR_BG)
            bw = badge_surf.get_width() + 10
            pygame.draw.rect(self.screen, badge_col, (rx, ry + 4, bw, 18), border_radius=3)
            self.screen.blit(badge_surf, (rx + 5, ry + 6))
            rx += 140

            # Snap status
            if e.get("snapped_to_downbeat"):
                d_ms = e.get("snap_delta_ms", 0.0)
                snap_str = f"YES ({d_ms:+.0f}ms)"
                snap_col = COLOR_ACCENT_CYAN
            else:
                snap_str = "—"
                snap_col = COLOR_TEXT_DIM
            self.screen.blit(self.get_text(self.font_mono_small, snap_str, snap_col), (rx, ry + 6))
            rx += 80

            # Pair ID
            pid = e.get("pair_id")
            pid_str = pid if pid else "—"
            pid_col = COLOR_ACCENT_AMBER if pid else COLOR_TEXT_DIM
            self.screen.blit(self.get_text(self.font_mono_small, pid_str, pid_col), (rx, ry + 6))
            rx += 90

            # Note
            note_str = e.get("note", "")
            if not note_str:
                note_str = "(click or press [E] to add note)"
                note_col = COLOR_TEXT_DIM
            else:
                note_col = COLOR_TEXT_MUTED
            self.screen.blit(self.get_text(self.font_small, note_str, note_col), (rx, ry + 5))

    def _render_guide_panel(self, rect: pygame.Rect) -> None:
        """Renders the hotkey guide and active marker inspection card."""
        pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, width=1, border_radius=6)

        # Header
        gh_h = 32
        gh_rect = pygame.Rect(rect.left, rect.top, rect.width, gh_h)
        pygame.draw.rect(self.screen, COLOR_PANEL_HEADER, gh_rect, border_top_left_radius=6, border_top_right_radius=6)
        pygame.draw.line(self.screen, COLOR_BORDER, (rect.left, rect.top + gh_h), (rect.right, rect.top + gh_h))

        h_surf = self.get_text(self.font_main, "HOTKEY GUIDE & CONTROLS", COLOR_TEXT_MAIN)
        self.screen.blit(h_surf, (rect.left + 14, rect.top + 7))

        # Hotkey sections
        sections = [
            ("Tagging Keys (1-Tap)", [
                ("[D]", "CLIMAX_OR_DROP (Red)"),
                ("[B]", "BUILDUP_OR_RISER (Yellow)"),
                ("[X]", "BREAKDOWN_OR_SOLO (Blue)"),
                ("[S]", "SECTION_CHANGE (Green)"),
            ]),
            ("Marker Editing & Nudging", [
                ("[,] / [.]", "Nudge marker +/-10ms (Shift: +/-50ms)"),
                ("[G]", "Snap to nearest BeatNet downbeat"),
                ("[Del/Back]", "Delete selected marker"),
                ("[L] / [U]", "Link buildup-drop pair / Unlink"),
                ("[E]", "Edit note / description for marker"),
            ]),
            ("Transport & Workflow", [
                ("[Space]", "Play / Pause (-100ms reflex while playing)"),
                ("[<-] / [->]", "Seek +/-2.0s (Home: 0.0s)"),
                ("[Ctrl+Z / Y]", "Undo / Redo event changes"),
                ("[Ctrl+S]", "Atomic save to structural_annotations.json"),
                ("[N] / [P]", "Next / Previous track in suite"),
                ("[R] / [C]", "Toggle Reviewed / Toggle Has-Climaxes"),
            ]),
        ]

        sy = rect.top + gh_h + 10
        col_w = (rect.width - 24)
        for sec_title, items in sections:
            s_title_surf = self.get_text(self.font_small, sec_title.upper(), COLOR_ACCENT_CYAN)
            self.screen.blit(s_title_surf, (rect.left + 14, sy))
            sy += 18
            for k, desc in items:
                k_surf = self.get_text(self.font_mono, k, COLOR_SELECTION)
                d_surf = self.get_text(self.font_small, f": {desc}", COLOR_TEXT_MUTED)
                self.screen.blit(k_surf, (rect.left + 20, sy))
                self.screen.blit(d_surf, (rect.left + 20 + k_surf.get_width(), sy))
                sy += 18
            sy += 6

    def _render_footer(self, rect: pygame.Rect) -> None:
        """Renders status bar at bottom of window."""
        pygame.draw.rect(self.screen, COLOR_PANEL_HEADER, rect)
        pygame.draw.line(self.screen, COLOR_BORDER, (rect.left, rect.top), (rect.right, rect.top))

        # Status text
        st_surf = self.get_text(self.font_small, self.status_text, self.status_color)
        self.screen.blit(st_surf, (rect.left + 16, rect.top + 6))

        # Audio stream telemetry
        if self.streamer:
            dac_ms = self.streamer.dac_latency * 1000.0
            sr = self.streamer.sample_rate
            mode_str = "DAC Hardware Sync" if not self.streamer._fallback_mode else "Software Clock Fallback"
            info_str = f"Audio: {sr} Hz | Latency: {dac_ms:.1f}ms | Mode: {mode_str}"
            info_surf = self.get_text(self.font_mono_small, info_str, COLOR_TEXT_MUTED)
            self.screen.blit(info_surf, (rect.right - info_surf.get_width() - 16, rect.top + 7))

    def _render_note_modal(self) -> None:
        """Renders modal dialog for editing marker note."""
        w, h = self.screen.get_size()
        dw, dh = 480, 140
        modal_rect = pygame.Rect((w - dw) // 2, (h - dh) // 2, dw, dh)

        # Dim overlay
        dim_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 160))
        self.screen.blit(dim_surf, (0, 0))

        # Modal box
        pygame.draw.rect(self.screen, COLOR_PANEL, modal_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN, modal_rect, width=2, border_radius=8)

        # Title
        t_surf = self.get_text(self.font_main, f"Edit Note for {self.selected_event_id}:", COLOR_TEXT_MAIN)
        self.screen.blit(t_surf, (modal_rect.left + 16, modal_rect.top + 14))

        # Text input box
        box_rect = pygame.Rect(modal_rect.left + 16, modal_rect.top + 46, dw - 32, 36)
        pygame.draw.rect(self.screen, COLOR_TIMELINE_BG, box_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_BORDER_LIGHT, box_rect, width=1, border_radius=4)

        buf_surf = self.get_text(self.font_main, self.note_edit_buffer + "|", COLOR_PLAYHEAD)
        self.screen.blit(buf_surf, (box_rect.left + 8, box_rect.top + 8))

        # Help hint
        hint_surf = self.get_text(self.font_small, "Press [Enter] to Save, [Esc] to Cancel", COLOR_TEXT_MUTED)
        self.screen.blit(hint_surf, (modal_rect.left + 16, modal_rect.top + 98))

    # =================================================================
    # EVENT HANDLING & MAIN LOOP
    # =================================================================

    def handle_keydown(self, event: pygame.event.Event) -> bool:
        """Processes keyboard input events. Returns True if application should keep running."""
        # Note editing mode intercepts all keys
        if self.is_editing_note:
            if event.key == pygame.K_RETURN:
                evt = self.get_selected_event()
                if evt:
                    self.manager.push_state(self.current_track_name())
                    evt["note"] = self.note_edit_buffer.strip()
                    self.set_status(f"Updated note for {evt['id']}", COLOR_ACCENT_GREEN)
                self.is_editing_note = False
            elif event.key == pygame.K_ESCAPE:
                self.is_editing_note = False
            elif event.key == pygame.K_BACKSPACE:
                self.note_edit_buffer = self.note_edit_buffer[:-1]
            else:
                if event.unicode and event.unicode.isprintable():
                    self.note_edit_buffer += event.unicode
            return True

        mods = pygame.key.get_mods()
        ctrl_held = bool(mods & pygame.KMOD_CTRL)
        shift_held = bool(mods & pygame.KMOD_SHIFT)

        # Global Hotkeys
        if event.key == pygame.K_ESCAPE:
            return False

        # Undo / Redo
        elif ctrl_held and event.key == pygame.K_z:
            if shift_held:
                if self.manager.redo(self.current_track_name()):
                    self.set_status("Redo action", COLOR_ACCENT_CYAN)
            else:
                if self.manager.undo(self.current_track_name()):
                    self.set_status("Undo action", COLOR_ACCENT_CYAN)
        elif ctrl_held and event.key == pygame.K_y:
            if self.manager.redo(self.current_track_name()):
                self.set_status("Redo action", COLOR_ACCENT_CYAN)

        # Save JSON
        elif ctrl_held and event.key == pygame.K_s:
            if self.manager.save():
                self.set_status(f"Saved annotations to {os.path.basename(self.manager.json_path)}", COLOR_ACCENT_GREEN)

        # Transport: Play / Pause
        elif event.key == pygame.K_SPACE:
            if self.streamer:
                self.streamer.toggle_play()
                status_str = "PLAYING" if self.streamer.is_playing else "PAUSED"
                self.set_status(status_str, COLOR_TEXT_MAIN)

        # Transport: Seek
        elif event.key == pygame.K_RIGHT:
            delta = 5.0 if shift_held else 2.0
            if self.streamer:
                self.streamer.seek(self.streamer.get_current_time() + delta)
        elif event.key == pygame.K_LEFT:
            delta = 5.0 if shift_held else 2.0
            if self.streamer:
                self.streamer.seek(self.streamer.get_current_time() - delta)
        elif event.key == pygame.K_HOME:
            if self.streamer:
                self.streamer.seek(0.0)
        elif event.key == pygame.K_END:
            if self.streamer:
                self.streamer.seek(self.streamer.total_duration - 1.0)

        # Structural Tagging Hotkeys
        elif not ctrl_held and event.key == pygame.K_d:
            self.add_event(EVENT_CLIMAX)
        elif not ctrl_held and event.key == pygame.K_b:
            self.add_event(EVENT_BUILDUP)
        elif not ctrl_held and event.key == pygame.K_x:
            self.add_event(EVENT_BREAKDOWN)
        elif not ctrl_held and event.key == pygame.K_s:
            self.add_event(EVENT_SECTION)

        # Marker Editing
        elif event.key in (pygame.K_COMMA, pygame.K_LESS):
            step = -0.050 if shift_held else -0.010
            self.nudge_selected(step)
        elif event.key in (pygame.K_PERIOD, pygame.K_GREATER):
            step = 0.050 if shift_held else 0.010
            self.nudge_selected(step)
        elif event.key == pygame.K_g:
            self.snap_selected_to_downbeat()
        elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
            self.delete_selected()
        elif event.key == pygame.K_l:
            self.link_selected_pair()
        elif event.key == pygame.K_u:
            self.unlink_selected()
        elif event.key == pygame.K_e:
            evt = self.get_selected_event()
            if evt:
                self.is_editing_note = True
                self.note_edit_buffer = evt.get("note", "")

        # Track Navigation
        elif event.key == pygame.K_n:
            self.change_track(1)
        elif event.key == pygame.K_p:
            self.change_track(-1)
        elif event.key == pygame.K_r:
            self.toggle_status()
        elif event.key == pygame.K_c:
            self.toggle_has_climaxes()

        # Zoom Controls
        elif event.key == pygame.K_UP:
            self.timeline_zoom_sec = max(2.0, self.timeline_zoom_sec * 0.8)
        elif event.key == pygame.K_DOWN:
            self.timeline_zoom_sec = min(60.0, self.timeline_zoom_sec * 1.25)

        return True

    def handle_mouse_click(self, pos: Tuple[int, int], button: int) -> None:
        """Handles mouse clicks on overview, timeline, and event table."""
        mx, my = pos
        w, h = self.width, self.height
        cur_time = self.streamer.get_current_time() if self.streamer else 0.0
        total_dur = self.streamer.total_duration if self.streamer else 1.0

        overview_rect = pygame.Rect(20, 74, w - 40, 56)
        timeline_rect = pygame.Rect(20, 138, w - 40, 260)
        table_rect = pygame.Rect(20, 408, int(w * 0.52) - 30, h - 408 - 36)

        # Overview click -> seek directly
        if overview_rect.collidepoint(mx, my):
            frac = (mx - overview_rect.left) / float(overview_rect.width)
            target_t = frac * total_dur
            if self.streamer:
                self.streamer.seek(target_t)
            return

        # Timeline click -> select marker or seek
        if timeline_rect.collidepoint(mx, my):
            t_center = self.timeline_scroll_center if self.timeline_scroll_center is not None else cur_time
            half_win = self.timeline_zoom_sec / 2.0
            t_start = t_center - half_win
            t_end = t_center + half_win

            def time_to_x(t: float) -> int:
                return timeline_rect.left + int(((t - t_start) / (t_end - t_start)) * timeline_rect.width)

            # Check if clicked near an existing event marker (pick closest)
            events = self.current_track_data()["events"]
            clicked_event = None
            min_dist = 13
            for e in events:
                ex = time_to_x(e["time_sec"])
                dist = abs(mx - ex)
                if dist <= 12 and (timeline_rect.top + 28 <= my <= timeline_rect.bottom - 15):
                    if dist < min_dist:
                        min_dist = dist
                        clicked_event = e

            if clicked_event:
                self.selected_event_id = clicked_event["id"]
                self.set_status(f"Selected {clicked_event['id']} ({clicked_event['type']}) at {clicked_event['time_sec']:.3f}s", COLOR_ACCENT_CYAN)
            else:
                # Seek to clicked position
                clicked_t = t_start + ((mx - timeline_rect.left) / float(timeline_rect.width)) * (t_end - t_start)
                if self.streamer:
                    self.streamer.seek(clicked_t)
            return

        # Event Table click -> select row and seek (or edit note if clicked on note column)
        if table_rect.collidepoint(mx, my):
            th_h = 32
            row_h = 28
            if my >= table_rect.top + th_h + 5:
                row_idx = (my - (table_rect.top + th_h + 5)) // row_h
                events = self.current_track_data()["events"]
                target_idx = self.event_table_scroll + row_idx
                if 0 <= target_idx < len(events):
                    sel_evt = events[target_idx]
                    self.selected_event_id = sel_evt["id"]
                    if mx >= table_rect.left + 460:
                        self.is_editing_note = True
                        self.note_edit_buffer = sel_evt.get("note", "")
                        self.set_status(f"Editing note for {sel_evt['id']}", COLOR_ACCENT_CYAN)
                    else:
                        if self.streamer:
                            self.streamer.seek(sel_evt["time_sec"])
                        self.set_status(f"Jumped to {sel_evt['id']} ({sel_evt['type']}) at {sel_evt['time_sec']:.3f}s", COLOR_ACCENT_CYAN)

    def handle_scroll(self, dy: int) -> None:
        """Handles mouse wheel scrolling (zoom on timeline, scroll on table)."""
        mx, my = pygame.mouse.get_pos()
        timeline_rect = pygame.Rect(20, 138, self.width - 40, 260)
        table_rect = pygame.Rect(20, 408, int(self.width * 0.52) - 30, self.height - 408 - 36)

        if timeline_rect.collidepoint(mx, my):
            factor = 0.85 if dy > 0 else 1.18
            self.timeline_zoom_sec = max(2.0, min(60.0, self.timeline_zoom_sec * factor))
        elif table_rect.collidepoint(mx, my):
            self.event_table_scroll = max(0, self.event_table_scroll - dy)

    def run(self) -> None:
        """Main application interactive event and render loop."""
        if self.headless:
            print("[Headless Mode] Application initialized successfully without UI.")
            return

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if not self.handle_keydown(event):
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_mouse_click(event.pos, event.button)
                    elif event.button in (4, 5):
                        # Scroll up/down in older pygame or Linux
                        dy = 1 if event.button == 4 else -1
                        self.handle_scroll(dy)
                elif event.type == pygame.MOUSEWHEEL:
                    self.handle_scroll(event.y)
                elif event.type == pygame.VIDEORESIZE:
                    self.width = max(1000, event.w)
                    self.height = max(700, event.h)
                    self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE | pygame.DOUBLEBUF)

            self.render()
            self.clock.tick(60)

        # Cleanup on exit
        if self.manager.is_dirty:
            self.manager.save()
        if self.streamer:
            self.streamer.stop()
        pygame.quit()


# =====================================================================
# CLI ENTRY POINT
# =====================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Dedicated Structural Music Annotator")
    parser.add_argument("--track", type=str, default=None, help="Initial track to load from neural-core suite")
    parser.add_argument("--headless", action="store_true", help="Run without opening Pygame display (for test verification)")
    args = parser.parse_args()

    app = StructuralAnnotatorApp(
        repo_root=_REPO_ROOT,
        initial_track=args.track,
        headless=args.headless
    )
    app.run()


if __name__ == "__main__":
    main()
