from typing import Dict, Any, Optional
import time
import asyncio
import logging
import numpy as np

from core.AudioIngestion import AudioIngestion
from core.AudioAnalyzer import AudioAnalyzer

logger = logging.getLogger(__name__)

class Listener:
    def __init__(self, infos: Dict[str, Any]) -> None:
        self.ingestion = AudioIngestion(infos)
        self.analyzer = AudioAnalyzer(self.ingestion, infos)

        # Ring buffer dimensions
        lookahead = getattr(self.analyzer, 'lookahead_seconds', 5.0)
        self._ring_capacity = int(lookahead * 60 * 1.5) + 2  # ~450 slots for 5s at 60fps
        nb_fft = self.ingestion.nb_of_fft_band
        nb_chroma = self.ingestion.nb_of_chroma

        # Pre-allocated ring arrays (ZERO per-frame allocation)
        self._ring_timestamps = np.zeros(self._ring_capacity, dtype=np.float64)
        self._ring_fft_band = np.zeros((self._ring_capacity, nb_fft), dtype=np.float64)
        self._ring_chroma = np.zeros((self._ring_capacity, nb_chroma), dtype=np.float64)
        self._ring_smoothed_fft = np.zeros((self._ring_capacity, nb_fft), dtype=np.float64)
        self._ring_smoothed_chroma = np.zeros((self._ring_capacity, nb_chroma), dtype=np.float64)
        self._ring_asserved_fft = np.zeros((self._ring_capacity, nb_fft), dtype=np.float64)
        self._ring_band_proportion = np.zeros((self._ring_capacity, nb_fft), dtype=np.float64)
        self._ring_band_means = np.zeros((self._ring_capacity, nb_fft), dtype=np.float64)
        self._ring_smoothed_total_power = np.zeros(self._ring_capacity, dtype=np.float64)
        self._ring_asserved_total_power = np.zeros(self._ring_capacity, dtype=np.float64)
        self._ring_band_peak = np.zeros((self._ring_capacity, nb_fft), dtype=np.float64)
        self._ring_band_flux = np.zeros((self._ring_capacity, nb_fft), dtype=np.float64)
        self._ring_is_song_change = np.zeros(self._ring_capacity, dtype=bool)
        self._ring_is_verse_chorus_change = np.zeros(self._ring_capacity, dtype=bool)
        self._ring_asserved_novelty = np.zeros(self._ring_capacity, dtype=np.float64)
        self._ring_combined_novelty = np.zeros(self._ring_capacity, dtype=np.float64)

        self._ring_write = 0  # Next write position
        self._ring_read = 0   # Next read position
        self._ring_count = 0  # Number of valid entries

        # Delayed output state (what modes see)
        self._delayed_fft_band_values = np.zeros(nb_fft)
        self._delayed_chroma_values = np.zeros(nb_chroma)
        self._delayed_smoothed_fft_band_values = np.zeros(nb_fft)
        self._delayed_smoothed_chroma_values = np.zeros(nb_chroma)
        self._delayed_asserved_fft_band = np.zeros(nb_fft)
        self._delayed_band_proportion = np.zeros(nb_fft)
        self._delayed_band_means = np.zeros(nb_fft)
        self._delayed_smoothed_total_power = 0.0
        self._delayed_asserved_total_power = 0.0
        self._delayed_band_peak = np.zeros(nb_fft)
        self._delayed_band_flux = np.zeros(nb_fft)
        self._delayed_is_song_change = False
        self._delayed_is_verse_chorus_change = False
        self._delayed_asserved_novelty = 0.0
        self._delayed_combined_novelty = 0.0

    async def update_forever(self) -> None:
        while True:
            self.update()
            await asyncio.sleep(1/60)

    def update(self) -> None:
        self._delayed_is_song_change = False
        self._delayed_is_verse_chorus_change = False

        if not hasattr(self, 'last_env_time'):
            self.last_env_time = time.time()
        
        current_time = time.time()
        self.dt = current_time - self.last_env_time
        self.last_env_time = current_time
        self.fps_ratio = max(0.001, self.dt * 60.0)

        if self.ingestion.useMicrophone:
            if self.ingestion.isSilenceCalibrating:
                self.ingestion.calibrate_silence(self.fps_ratio)
            elif self.ingestion.isBBCalibrating:
                self.ingestion.calibrate_bb(self.fps_ratio)
            else:
                self.ingestion.update_band_means_and_smoothed_values(self.fps_ratio)
                self.ingestion.asserv_fft_bands_2(self.fps_ratio)
                self.ingestion.asserv_total_power(self.fps_ratio)
                self.analyzer.update_structural_novelty(current_time, self.dt, self.fps_ratio)
                self.analyzer.detect_band_peaks(current_time, self.dt, self.fps_ratio)
        else:
            self.ingestion.apply_fake_fft(self.fps_ratio)
            self.ingestion.asserv_fft_bands_2(self.fps_ratio)
            self.ingestion.update_band_means_and_smoothed_values(self.fps_ratio)
            self.ingestion.asserv_total_power(self.fps_ratio)
            self.analyzer.update_structural_novelty(current_time, self.dt, self.fps_ratio)
            self.analyzer.detect_band_peaks(current_time, self.dt, self.fps_ratio)

        # ---- WRITE into ring buffer (zero allocation) ----
        w = self._ring_write
        self._ring_timestamps[w] = current_time
        self._ring_fft_band[w, :] = self.ingestion.fft_band_values
        self._ring_chroma[w, :] = self.ingestion.chroma_values
        self._ring_smoothed_fft[w, :] = self.ingestion.smoothed_fft_band_values
        self._ring_smoothed_chroma[w, :] = self.ingestion.smoothed_chroma_values
        self._ring_asserved_fft[w, :] = self.ingestion.asserved_fft_band
        self._ring_band_proportion[w, :] = self.ingestion.band_proportion
        self._ring_band_means[w, :] = self.ingestion.band_means
        self._ring_smoothed_total_power[w] = self.ingestion.smoothed_total_power
        self._ring_asserved_total_power[w] = self.ingestion.asserved_total_power
        self._ring_band_peak[w, :] = self.analyzer.band_peak if hasattr(self.analyzer, 'band_peak') else 0.0
        self._ring_band_flux[w, :] = self.analyzer.band_flux if hasattr(self.analyzer, 'band_flux') else 0.0
        self._ring_is_song_change[w] = getattr(self.analyzer, 'is_song_change', False)
        self._ring_is_verse_chorus_change[w] = getattr(self.analyzer, 'is_verse_chorus_change', False)
        self._ring_asserved_novelty[w] = getattr(self.analyzer, 'asserved_novelty', 0.0)
        self._ring_combined_novelty[w] = getattr(self.analyzer, 'combined_novelty', 0.0)

        self._ring_write = (w + 1) % self._ring_capacity
        if self._ring_count < self._ring_capacity:
            self._ring_count += 1
        else:
            # Buffer full — advance read pointer (oldest entry overwritten)
            self._ring_read = (self._ring_read + 1) % self._ring_capacity

        # ---- READ expired entries from ring buffer ----
        lookahead = self.analyzer.lookahead_seconds
        best_idx = -1
        best_power = -1.0
        any_song_change = False
        any_verse_chorus_change = False
        expired_count = 0

        while self._ring_count > 0:
            r = self._ring_read
            if current_time - self._ring_timestamps[r] >= lookahead:
                # This entry has expired
                expired_count += 1
                power = self._ring_smoothed_total_power[r]
                if power > best_power:
                    best_power = power
                    best_idx = r
                if self._ring_is_song_change[r]:
                    any_song_change = True
                if self._ring_is_verse_chorus_change[r]:
                    any_verse_chorus_change = True
                self._ring_read = (r + 1) % self._ring_capacity
                self._ring_count -= 1
            else:
                break

        if expired_count > 0:
            self._delayed_fft_band_values = self._ring_fft_band[best_idx].copy()
            self._delayed_chroma_values = self._ring_chroma[best_idx].copy()
            self._delayed_smoothed_fft_band_values = self._ring_smoothed_fft[best_idx].copy()
            self._delayed_smoothed_chroma_values = self._ring_smoothed_chroma[best_idx].copy()
            self._delayed_asserved_fft_band = self._ring_asserved_fft[best_idx].copy()
            self._delayed_band_proportion = self._ring_band_proportion[best_idx].copy()
            self._delayed_band_means = self._ring_band_means[best_idx].copy()
            self._delayed_smoothed_total_power = float(self._ring_smoothed_total_power[best_idx])
            self._delayed_asserved_total_power = float(self._ring_asserved_total_power[best_idx])
            self._delayed_band_peak = self._ring_band_peak[best_idx].copy()
            self._delayed_band_flux = self._ring_band_flux[best_idx].copy()
            self._delayed_is_song_change = any_song_change
            self._delayed_is_verse_chorus_change = any_verse_chorus_change
            self._delayed_asserved_novelty = float(self._ring_asserved_novelty[best_idx])
            self._delayed_combined_novelty = float(self._ring_combined_novelty[best_idx])

    # ==========================================
    # FACADE PROPERTIES FOR MODES AND CONNECTORS
    # ==========================================

    # 1. Ingestion properties
    @property
    def fft_band_values(self): return self._delayed_fft_band_values
    @fft_band_values.setter
    def fft_band_values(self, val): self.ingestion.fft_band_values = val

    @property
    def chroma_values(self): return self._delayed_chroma_values
    @chroma_values.setter
    def chroma_values(self, val): self.ingestion.chroma_values = val

    @property
    def nb_of_fft_band(self): return self.ingestion.nb_of_fft_band

    @property
    def smoothed_fft_band_values(self): return self._delayed_smoothed_fft_band_values

    @property
    def smoothed_chroma_values(self): return self._delayed_smoothed_chroma_values

    @property
    def asserved_fft_band(self): return self._delayed_asserved_fft_band

    @property
    def band_proportion(self): return self._delayed_band_proportion

    @property
    def smoothed_total_power(self): return self._delayed_smoothed_total_power

    @property
    def asserved_total_power(self): return self._delayed_asserved_total_power

    @property
    def dynamic_audio_latency(self): return self.ingestion.dynamic_audio_latency
    @dynamic_audio_latency.setter
    def dynamic_audio_latency(self, val): self.ingestion.dynamic_audio_latency = val

    @property
    def sensi(self): return self.ingestion.sensi
    @sensi.setter
    def sensi(self, val): self.ingestion.sensi = val

    @property
    def luminosite(self): return self.ingestion.luminosite
    @luminosite.setter
    def luminosite(self, val): self.ingestion.luminosite = val

    @property
    def band_means(self): return self._delayed_band_means

    # Calibrations
    def start_silence_calibration(self) -> None: self.ingestion.start_silence_calibration(self.fps_ratio)
    def stop_silence_calibration(self) -> None: self.ingestion.stop_silence_calibration(self.fps_ratio)
    def start_bb_calibration(self) -> None: self.ingestion.start_bb_calibration(self.fps_ratio)
    def stop_bb_calibration(self) -> None: self.ingestion.stop_bb_calibration(self.fps_ratio)

    @property
    def hasBeenSilenceCalibrated(self): return self.ingestion.hasBeenSilenceCalibrated
    @hasBeenSilenceCalibrated.setter
    def hasBeenSilenceCalibrated(self, val): self.ingestion.hasBeenSilenceCalibrated = val

    @property
    def hasBeenBBCalibrated(self): return self.ingestion.hasBeenBBCalibrated
    @hasBeenBBCalibrated.setter
    def hasBeenBBCalibrated(self, val): self.ingestion.hasBeenBBCalibrated = val

    # 2. Analyzer properties
    @property
    def band_peak(self): return self._delayed_band_peak

    @property
    def band_flux(self): return self._delayed_band_flux

    @property
    def beat_count(self): return self.analyzer.beat_count

    @property
    def beat_phase(self): return self.analyzer.beat_phase

    @property
    def is_beat(self): return getattr(self.analyzer, 'is_beat', False)

    @property
    def is_real_beat(self): return getattr(self.analyzer, 'is_real_beat', False)

    @property
    def is_dropped_beat(self): return getattr(self.analyzer, 'is_dropped_beat', False)

    @property
    def beat_tag(self): return getattr(self.analyzer, 'current_beat_tag', 'Bass/Kick')

    @property
    def beat_confidence(self): return getattr(self.analyzer, 'confidence_score', 0.0)

    @property
    def flywheel_status(self): return getattr(self.analyzer, 'flywheel_status', 'coasting')

    @property
    def is_song_change(self): return self._delayed_is_song_change

    @property
    def is_verse_chorus_change(self): return self._delayed_is_verse_chorus_change
    
    @property
    def live_is_song_change(self): return getattr(self.analyzer, 'is_song_change', False)
    
    @property
    def live_is_verse_chorus_change(self): return getattr(self.analyzer, 'is_verse_chorus_change', False)

    @property
    def asserved_novelty(self): return self._delayed_asserved_novelty

    @property
    def combined_novelty(self): return self._delayed_combined_novelty

    @property
    def live_asserved_novelty(self): return getattr(self.analyzer, 'asserved_novelty', 0.0)

    @property
    def live_combined_novelty(self): return getattr(self.analyzer, 'combined_novelty', 0.0)

    @property
    def bpm(self): return self.analyzer.bpm

    @property
    def standalone_bpm(self): return self.analyzer.standalone_bpm

    @property
    def standalone_phase(self): return self.analyzer.standalone_phase

    def process_raw_audio(self, audio_data: np.ndarray) -> None:
        self.ingestion.process_raw_audio(audio_data)



