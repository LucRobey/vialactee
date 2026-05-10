from typing import Dict, Any, Optional
import time
import asyncio
import logging
import numpy as np
from collections import deque

from core.AudioIngestion import AudioIngestion
from core.AudioAnalyzer import AudioAnalyzer

logger = logging.getLogger(__name__)

class Listener:
    def __init__(self, infos: Dict[str, Any]) -> None:
        self.ingestion = AudioIngestion(infos)
        self.analyzer = AudioAnalyzer(self.ingestion, infos)
        
        # Delayed state queues for perfect sync with beat predictions
        self.spectral_delay_queue = deque()
        self._delayed_fft_band_values = np.zeros(self.ingestion.nb_of_fft_band)
        self._delayed_chroma_values = np.zeros(self.ingestion.nb_of_chroma)
        self._delayed_smoothed_fft_band_values = np.zeros(self.ingestion.nb_of_fft_band)
        self._delayed_smoothed_chroma_values = np.zeros(self.ingestion.nb_of_chroma)
        self._delayed_asserved_fft_band = np.zeros(self.ingestion.nb_of_fft_band)
        self._delayed_band_proportion = np.zeros(self.ingestion.nb_of_fft_band)
        self._delayed_band_means = np.zeros(self.ingestion.nb_of_fft_band)
        self._delayed_smoothed_total_power = 0.0
        self._delayed_asserved_total_power = 0.0

    async def update_forever(self) -> None:
        while True:
            self.update()
            await asyncio.sleep(1/60)

    def update(self) -> None:
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
                self.ingestion.asserv_fft_bands(self.fps_ratio)
                self.ingestion.asserv_total_power(self.fps_ratio)
                self.analyzer.update_structural_novelty(current_time, self.fps_ratio)
                self.analyzer.detect_band_peaks(current_time, self.dt, self.fps_ratio)
        else:
            self.ingestion.apply_fake_fft(self.fps_ratio)
            self.ingestion.asserv_fft_bands(self.fps_ratio)
            self.ingestion.update_band_means_and_smoothed_values(self.fps_ratio)
            self.ingestion.asserv_total_power(self.fps_ratio)
            self.analyzer.update_structural_novelty(current_time, self.fps_ratio)
            self.analyzer.detect_band_peaks(current_time, self.dt, self.fps_ratio)

        # -------------------------------------------------------------
        # SPECTRAL DELAY BUFFER
        # We capture the instantaneous audio state and delay it by exactly
        # lookahead_seconds so it aligns perfectly with the delayed beat triggers.
        # -------------------------------------------------------------
        self.spectral_delay_queue.append({
            'time': current_time,
            'fft_band_values': np.copy(self.ingestion.fft_band_values),
            'chroma_values': np.copy(self.ingestion.chroma_values) if hasattr(self.ingestion, 'chroma_values') else None,
            'smoothed_fft_band_values': np.copy(self.ingestion.smoothed_fft_band_values),
            'smoothed_chroma_values': np.copy(self.ingestion.smoothed_chroma_values) if hasattr(self.ingestion, 'smoothed_chroma_values') else None,
            'asserved_fft_band': np.copy(self.ingestion.asserved_fft_band),
            'band_proportion': np.copy(self.ingestion.band_proportion),
            'band_means': np.copy(self.ingestion.band_means),
            'smoothed_total_power': self.ingestion.smoothed_total_power,
            'asserved_total_power': self.ingestion.asserved_total_power
        })

        while len(self.spectral_delay_queue) > 0:
            if current_time - self.spectral_delay_queue[0]['time'] >= self.analyzer.lookahead_seconds:
                popped = self.spectral_delay_queue.popleft()
                self._delayed_fft_band_values = popped['fft_band_values']
                if popped['chroma_values'] is not None:
                    self._delayed_chroma_values = popped['chroma_values']
                self._delayed_smoothed_fft_band_values = popped['smoothed_fft_band_values']
                if popped['smoothed_chroma_values'] is not None:
                    self._delayed_smoothed_chroma_values = popped['smoothed_chroma_values']
                self._delayed_asserved_fft_band = popped['asserved_fft_band']
                self._delayed_band_proportion = popped['band_proportion']
                self._delayed_band_means = popped['band_means']
                self._delayed_smoothed_total_power = popped['smoothed_total_power']
                self._delayed_asserved_total_power = popped['asserved_total_power']
            else:
                break

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
    def band_peak(self): return self.analyzer.band_peak

    @property
    def band_flux(self): return self.analyzer.band_flux

    @property
    def beat_count(self): return self.analyzer.beat_count

    @property
    def beat_phase(self): return self.analyzer.beat_phase

    @property
    def is_song_change(self): return self.analyzer.is_song_change

    @property
    def is_verse_chorus_change(self): return self.analyzer.is_verse_chorus_change

    @property
    def bpm(self): return self.analyzer.bpm

    @property
    def standalone_bpm(self): return self.analyzer.standalone_bpm

    def process_raw_audio(self, audio_data: np.ndarray) -> None:
        self.ingestion.process_raw_audio(audio_data)

