"""
connectors/Local_AudioFile.py - Sample-accurate MP3/WAV Audio File Streamer

Provides hardware-parity audio streaming and predictive ingestion for Main.py.
Plays local audio files through physical speakers via sounddevice while feeding
Listener with 5.0-second lookahead pre-roll, sample-accurate 60 FPS ingestion,
and zero artificial ADC latency (matching tools/mode_studio.py and tools/music_studio.py).
"""

from __future__ import annotations
import os
import sys
import time
import math
import glob
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import soundfile as sf

try:
    import sounddevice as sd
except ImportError:
    sd = None

logger = logging.getLogger(__name__)


class Local_AudioFile:
    """
    Sample-accurate audio streamer using sounddevice with 5.0s predictive lookahead.
    Feeds future audio chunks to Listener.process_raw_audio() while streaming
    speaker-time audio to physical speakers in perfect synchronization.
    """

    def __init__(self, listener: Any, infos: Dict[str, Any], song_path: Optional[str] = None):
        self.listener = listener
        self.infos = infos
        self.sample_rate = int(infos.get("sample_rate", 44100))
        self.buffer_size = int(infos.get("buffer_size", 4096))
        self.hop_samples = int(round(self.sample_rate / 60.0))  # Exactly 735 samples at 44100 Hz
        self.output_device_id = infos.get("output_device_id", None)
        self.loop_mode = bool(infos.get("loop", False))

        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.assets_music_dir = os.path.join(self.repo_root, "assets", "musics", "mp3_files")

        # Discover all available songs in assets/musics/mp3_files
        self.song_list: List[str] = []
        if os.path.isdir(self.assets_music_dir):
            self.song_list = sorted(glob.glob(os.path.join(self.assets_music_dir, "*.mp3")))

        # Resolve requested song path
        target_song = song_path or infos.get("song") or infos.get("audio_file")
        resolved_path = self.resolve_song_path(target_song)

        # Include song directory if external
        song_dir = os.path.dirname(resolved_path) if resolved_path else None
        if song_dir and os.path.isdir(song_dir) and song_dir != self.assets_music_dir:
            external_songs = sorted(glob.glob(os.path.join(song_dir, "*.mp3")) + glob.glob(os.path.join(song_dir, "*.wav")))
            if external_songs and resolved_path in external_songs:
                self.song_list = external_songs

        self.song_index = 0
        if resolved_path and self.song_list:
            norm_target = os.path.normpath(os.path.abspath(resolved_path))
            for i, s in enumerate(self.song_list):
                if os.path.normpath(os.path.abspath(s)) == norm_target:
                    self.song_index = i
                    break

        self.file_path = resolved_path or (self.song_list[0] if self.song_list else "")
        if not self.file_path or not os.path.exists(self.file_path):
            raise FileNotFoundError(f"No audio file found for '{target_song}'. Ensure valid MP3 file or path.")

        # Load persisted A/V sync calibration offset if present
        self.sync_offset_ms = float(infos.get("sync_offset_ms", 0.0))
        studio_sync_file = os.path.join(self.repo_root, "tools", "studio_sync.json")
        if self.sync_offset_ms == 0.0 and os.path.exists(studio_sync_file):
            try:
                import json
                with open(studio_sync_file, "r") as f:
                    cfg = json.load(f)
                    self.sync_offset_ms = float(cfg.get("sync_offset_ms", 0.0))
            except Exception:
                pass

        # Lookahead setup
        self.lookahead_seconds = getattr(self.listener.analyzer, 'lookahead_seconds', 5.0)
        self.lookahead_samples = int(self.lookahead_seconds * self.sample_rate)

        # In direct audio file mode, zero out microphone ADC buffer delay
        self.listener.dynamic_audio_latency = 0.0
        # Flag Mode_master to avoid double-stepping the ring buffer
        self.listener.is_externally_clocked = True

        # Playback cursor state
        self.speaker_sample_pos = 0
        self.ingest_sample_pos = 0
        self.dac_latency = 0.0
        self.is_playing = False
        self.is_finished = False
        self._stop_requested = False

        self.stream: Optional[Any] = None

        # Load audio buffer
        self._load_audio(self.file_path)

    def resolve_song_path(self, raw_path: Optional[str]) -> str:
        """Resolves raw song path, filename, or fuzzy name into an absolute path."""
        if not raw_path:
            # Fallback default: Palladium.mp3 or first file in assets
            palladium = os.path.join(self.assets_music_dir, "Palladium.mp3")
            if os.path.exists(palladium):
                return palladium
            return self.song_list[0] if self.song_list else ""

        # 1. Direct path check (absolute or cwd-relative)
        if os.path.exists(raw_path):
            return os.path.abspath(raw_path)

        # 2. Repo-relative check
        repo_rel = os.path.join(self.repo_root, raw_path)
        if os.path.exists(repo_rel):
            return os.path.abspath(repo_rel)

        # 3. Assets directory check
        assets_rel = os.path.join(self.assets_music_dir, raw_path)
        if os.path.exists(assets_rel):
            return os.path.abspath(assets_rel)

        # 4. Check with .mp3 extension appended
        if not raw_path.lower().endswith(".mp3"):
            cand = raw_path + ".mp3"
            if os.path.exists(cand):
                return os.path.abspath(cand)
            cand_repo = os.path.join(self.repo_root, cand)
            if os.path.exists(cand_repo):
                return os.path.abspath(cand_repo)
            cand_assets = os.path.join(self.assets_music_dir, cand)
            if os.path.exists(cand_assets):
                return os.path.abspath(cand_assets)

        # 5. Fuzzy match in song_list by basename substring
        clean_target = os.path.splitext(os.path.basename(raw_path))[0].lower()
        for s in self.song_list:
            base = os.path.splitext(os.path.basename(s))[0].lower()
            if clean_target in base:
                return os.path.abspath(s)

        return raw_path

    def _load_audio(self, audio_file_path: str) -> None:
        """Loads and resamples audio data into memory."""
        logger.info(f"(Local_AudioFile) Loading track: {os.path.basename(audio_file_path)}...")
        raw_data, sr = sf.read(audio_file_path, dtype='float32')
        if sr != self.sample_rate:
            logger.info(f"(Local_AudioFile) Resampling from {sr} Hz to {self.sample_rate} Hz...")
            try:
                import scipy.signal as signal
                gcd = math.gcd(int(sr), int(self.sample_rate))
                up = self.sample_rate // gcd
                down = sr // gcd
                raw_data = signal.resample_poly(raw_data, up, down, axis=0).astype(np.float32)
            except Exception as e:
                logger.warning(f"(Local_AudioFile) scipy resample failed ({e}), using linear interpolation fallback.")
                old_len = len(raw_data)
                new_len = int(old_len * float(self.sample_rate) / float(sr))
                x_old = np.linspace(0, 1, old_len)
                x_new = np.linspace(0, 1, new_len)
                if raw_data.ndim == 1:
                    raw_data = np.interp(x_new, x_old, raw_data).astype(np.float32)
                else:
                    chans = [np.interp(x_new, x_old, raw_data[:, c]) for c in range(raw_data.shape[1])]
                    raw_data = np.column_stack(chans).astype(np.float32)

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
        self.is_finished = False

    def start_stream(self) -> None:
        """Starts PortAudio output stream."""
        if sd is None:
            logger.warning("(Local_AudioFile) sounddevice not installed; audio playback disabled.")
            return

        if self.stream is None:
            try:
                self.stream = sd.OutputStream(
                    device=self.output_device_id,
                    samplerate=self.sample_rate,
                    channels=2,
                    blocksize=1024,
                    callback=self._audio_callback
                )
                self.stream.start()
                logger.info(f"(Local_AudioFile) Output stream started on device {self.output_device_id or 'default'}.")
            except Exception as e:
                logger.error(f"(Local_AudioFile) Failed to start audio output stream: {e}")
                self.stream = None

    def stop_stream(self) -> None:
        """Stops and closes PortAudio output stream."""
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        """PortAudio C-thread callback streaming audio to physical speakers."""
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
        """Returns the sample currently playing at speaker cone, subtracting DAC latency."""
        dac_frames = int(self.dac_latency * self.sample_rate)
        return max(0, self.speaker_sample_pos - dac_frames)

    def get_current_time(self) -> float:
        """Current speaker playback timestamp in seconds."""
        return float(self.get_actual_speaker_sample()) / float(self.sample_rate)

    def seek(self, target_seconds: float, sync_offset_seconds: float = 0.0) -> None:
        """Seek to a specific song timestamp and re-prime the 5s lookahead buffer."""
        target_sample = int(np.clip(target_seconds * self.sample_rate, 0, max(0, self.total_samples - 1024)))
        self.speaker_sample_pos = target_sample
        self.is_finished = False
        if hasattr(self.listener, 'reset'):
            self.listener.reset()
        elif hasattr(self.listener.analyzer, 'reset'):
            self.listener.analyzer.reset()
        self.prime_analyzer(sync_offset_seconds)

    def seek_relative(self, delta_seconds: float) -> None:
        """Seek relative to current playback position."""
        target = self.get_current_time() + delta_seconds
        self.seek(target, self.sync_offset_ms / 1000.0)

    def toggle_pause(self) -> bool:
        """Toggles playback pause state. Returns new is_playing state."""
        self.is_playing = not self.is_playing
        logger.info(f"(Local_AudioFile) {'RESUMED' if self.is_playing else 'PAUSED'} playback.")
        return self.is_playing

    def change_song(self, index_or_path: Any) -> None:
        """Switches to another song in playlist or explicit path."""
        if isinstance(index_or_path, int):
            if not self.song_list:
                return
            self.song_index = index_or_path % len(self.song_list)
            new_path = self.song_list[self.song_index]
        else:
            new_path = self.resolve_song_path(str(index_or_path))
            if self.song_list and new_path in self.song_list:
                self.song_index = self.song_list.index(new_path)

        was_playing = self.is_playing
        self.is_playing = False
        if hasattr(self.listener, 'reset'):
            self.listener.reset()
        elif hasattr(self.listener.analyzer, 'reset'):
            self.listener.analyzer.reset()

        self.file_path = new_path
        self._load_audio(new_path)
        self.prime_analyzer(self.sync_offset_ms / 1000.0)
        self.is_playing = was_playing
        logger.info(f"(Local_AudioFile) Switched track to: {os.path.basename(new_path)}")

    def next_song(self) -> None:
        """Advances to next song in playlist."""
        if self.song_list:
            self.change_song(self.song_index + 1)

    def prev_song(self) -> None:
        """Returns to previous song in playlist."""
        if self.song_list:
            self.change_song(self.song_index - 1)

    def change_song_number(self, num: int) -> None:
        """Jump directly to 1-based song number in playlist (1-9)."""
        if self.song_list and 0 <= num < len(self.song_list):
            self.change_song(num)

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

    def advance_ingest_frame(self, sync_offset_seconds: float = 0.0) -> int:
        """
        Advances ingestion in exact 735-sample increments to match actual speaker playback.
        Calls listener.process_raw_audio() and listener.update(fixed_dt=1/60.0) for hardware parity.
        """
        actual_speaker = self.get_actual_speaker_sample()
        target_ingest = (
            actual_speaker
            + self.lookahead_samples
            + int(sync_offset_seconds * self.sample_rate)
        )

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

        return frames_stepped

    async def play_forever(self) -> None:
        """Main asynchronous streaming task."""
        self.start_stream()
        self.prime_analyzer(self.sync_offset_ms / 1000.0)
        self.is_playing = True
        self.listener.audio_stream_state = "running"
        self.listener.audio_stream_error = None
        logger.info(f"(Local_AudioFile) Playing '{os.path.basename(self.file_path)}' with 5.0s predictive lookahead...")

        try:
            while not self._stop_requested:
                self.listener.last_audio_callback_time = time.time()
                if self.is_playing:
                    self.advance_ingest_frame(self.sync_offset_ms / 1000.0)
                    if self.is_finished:
                        if self.loop_mode:
                            logger.info("(Local_AudioFile) Track finished. Looping...")
                            self.seek(0.0)
                            self.is_playing = True
                        elif len(self.song_list) > 1:
                            logger.info("(Local_AudioFile) Track finished. Advancing to next track...")
                            self.next_song()
                            self.is_playing = True
                        else:
                            logger.info("(Local_AudioFile) Track finished. Repeating...")
                            self.seek(0.0)
                            self.is_playing = True

                await asyncio.sleep(0.005)
        except asyncio.CancelledError:
            self.listener.audio_stream_state = "stopped"
            logger.info("(Local_AudioFile) Audio streaming task cancelled.")
            raise
        finally:
            self.stop_stream()

    async def listen_forever(self) -> None:
        """Duck-typing alias for Local_Microphone.listen_forever()."""
        await self.play_forever()


AudioFile_Player = Local_AudioFile
