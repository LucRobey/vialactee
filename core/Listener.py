import time
import asyncio
import logging
import numpy as np

from core.AudioIngestion import AudioIngestion
from core.AudioAnalyzer import AudioAnalyzer

logger = logging.getLogger(__name__)

class Listener:
    def __init__(self, infos):
        self.ingestion = AudioIngestion(infos)
        self.analyzer = AudioAnalyzer(self.ingestion, infos)
        
    async def update_forever(self):
        while True:
            self.update()
            await asyncio.sleep(1/60)

    def update(self):
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
                self.analyzer.update_structural_novelty(current_time, self.fps_ratio)
                self.analyzer.detect_band_peaks(current_time, self.dt, self.fps_ratio)
        else:
            self.ingestion.apply_fake_fft(self.fps_ratio)
            self.ingestion.asserv_fft_bands(self.fps_ratio)
            self.ingestion.update_band_means_and_smoothed_values(self.fps_ratio)
            self.ingestion.asserv_total_power(self.fps_ratio)
            self.analyzer.update_structural_novelty(current_time, self.fps_ratio)
            self.analyzer.detect_band_peaks(current_time, self.dt, self.fps_ratio)

    # ==========================================
    # FACADE PROPERTIES FOR MODES AND CONNECTORS
    # ==========================================

    # 1. Ingestion properties
    @property
    def fft_band_values(self): return self.ingestion.fft_band_values
    @fft_band_values.setter
    def fft_band_values(self, val): self.ingestion.fft_band_values = val

    @property
    def chroma_values(self): return self.ingestion.chroma_values
    @chroma_values.setter
    def chroma_values(self, val): self.ingestion.chroma_values = val

    @property
    def nb_of_fft_band(self): return self.ingestion.nb_of_fft_band

    @property
    def smoothed_fft_band_values(self): return self.ingestion.smoothed_fft_band_values

    @property
    def smoothed_chroma_values(self): return self.ingestion.smoothed_chroma_values

    @property
    def asserved_fft_band(self): return self.ingestion.asserved_fft_band

    @property
    def band_proportion(self): return self.ingestion.band_proportion

    @property
    def smoothed_total_power(self): return self.ingestion.smoothed_total_power

    @property
    def asserved_total_power(self): return self.ingestion.asserved_total_power

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
    def band_means(self): return self.ingestion.band_means

    # Calibrations
    def start_silence_calibration(self): self.ingestion.start_silence_calibration(self.fps_ratio)
    def stop_silence_calibration(self): self.ingestion.stop_silence_calibration(self.fps_ratio)
    def start_bb_calibration(self): self.ingestion.start_bb_calibration(self.fps_ratio)
    def stop_bb_calibration(self): self.ingestion.stop_bb_calibration(self.fps_ratio)

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
