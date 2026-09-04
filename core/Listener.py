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
        self._delayed_band_peak = np.zeros(self.ingestion.nb_of_fft_band)
        self._delayed_band_flux = np.zeros(self.ingestion.nb_of_fft_band)
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

        # -------------------------------------------------------------
        # SPECTRAL DELAY BUFFER
        # We capture the instantaneous audio state and delay it by exactly
        # lookahead_seconds so it aligns perfectly with the delayed beat triggers.
        # -------------------------------------------------------------
        self.spectral_delay_queue.append({
            'time': current_time,
            'fft_band_values': np.copy(self.ingestion.fft_band_values),
            'chroma_values': np.copy(self.ingestion.chroma_values),
            'smoothed_fft_band_values': np.copy(self.ingestion.smoothed_fft_band_values),
            'smoothed_chroma_values': np.copy(self.ingestion.smoothed_chroma_values),
            'asserved_fft_band': np.copy(self.ingestion.asserved_fft_band),
            'band_proportion': np.copy(self.ingestion.band_proportion),
            'band_means': np.copy(self.ingestion.band_means),
            'smoothed_total_power': self.ingestion.smoothed_total_power,
            'asserved_total_power': self.ingestion.asserved_total_power,
            'band_peak': np.copy(self.analyzer.band_peak) if hasattr(self.analyzer, 'band_peak') else np.zeros(self.ingestion.nb_of_fft_band),
            'band_flux': np.copy(self.analyzer.band_flux) if hasattr(self.analyzer, 'band_flux') else np.zeros(self.ingestion.nb_of_fft_band),
            'is_song_change': getattr(self.analyzer, 'is_song_change', False),
            'is_verse_chorus_change': getattr(self.analyzer, 'is_verse_chorus_change', False),
            'asserved_novelty': getattr(self.analyzer, 'asserved_novelty', 0.0),
            'combined_novelty': getattr(self.analyzer, 'combined_novelty', 0.0)
        })

        popped_items = []
        while len(self.spectral_delay_queue) > 0:
            if current_time - self.spectral_delay_queue[0]['time'] >= self.analyzer.lookahead_seconds:
                popped_items.append(self.spectral_delay_queue.popleft())
            else:
                break
                
        if len(popped_items) > 0:
            best_popped = max(popped_items, key=lambda x: x['smoothed_total_power'])
            
            self._delayed_fft_band_values = best_popped['fft_band_values']
            self._delayed_chroma_values = best_popped['chroma_values']
            self._delayed_smoothed_fft_band_values = best_popped['smoothed_fft_band_values']
            self._delayed_smoothed_chroma_values = best_popped['smoothed_chroma_values']
            self._delayed_asserved_fft_band = best_popped['asserved_fft_band']
            self._delayed_band_proportion = best_popped['band_proportion']
            self._delayed_band_means = best_popped['band_means']
            self._delayed_smoothed_total_power = best_popped['smoothed_total_power']
            self._delayed_asserved_total_power = best_popped['asserved_total_power']
            self._delayed_band_peak = best_popped['band_peak']
            self._delayed_band_flux = best_popped['band_flux']
            
            self._delayed_is_song_change = any(x['is_song_change'] for x in popped_items)
            self._delayed_is_verse_chorus_change = any(x['is_verse_chorus_change'] for x in popped_items)
            self._delayed_asserved_novelty = best_popped.get('asserved_novelty', 0.0)
            self._delayed_combined_novelty = best_popped.get('combined_novelty', 0.0)

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


