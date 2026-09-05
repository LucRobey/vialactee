import time
import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class AudioIngestion:
    def __init__(self, infos: Dict[str, Any]) -> None:
        self.useMicrophone          = infos.get("useMicrophone", True)
        self.dynamic_audio_latency = 0.069
        self.luminosite = max(0.0, min(1.0, float(infos.get("luminosity", 100)) / 100.0))
        self.sensi = max(0.0, float(infos.get("sensibility", 100)) / 100.0)
        self.nb_of_fft_band = 8

        self.build_asserved_fft_lists()
        self.build_asserved_total_power()
        self.prepare_for_calibration()

        # FFT Settings
        self.sample_rate = 44100
        self.buffer_size = 4096
        self.hanning_window = np.hanning(self.buffer_size)
        
        fft_size = self.buffer_size // 2 + 1
        self.weight_matrix = np.zeros((self.nb_of_fft_band, fft_size))
        
        def hz_to_mel(f): return 2595 * np.log10(1 + f / 700.0)
        def mel_to_hz(m): return 700 * (10**(m / 2595.0) - 1)
        
        lower_mel = hz_to_mel(20)
        upper_mel = hz_to_mel(20000)
        mel_points = np.linspace(lower_mel, upper_mel, self.nb_of_fft_band + 2)
        hz_points = mel_to_hz(mel_points)
        bin_points = np.floor((self.buffer_size + 1) * hz_points / self.sample_rate).astype(int)
        
        for i in range(self.nb_of_fft_band):
            start = min(bin_points[i], fft_size - 1)
            mid = min(bin_points[i + 1], fft_size - 1)
            end = min(bin_points[i + 2], fft_size - 1)
            
            if mid > start:
                self.weight_matrix[i, start:mid] = np.linspace(0, 1, mid - start, endpoint=False)
            if end > mid:
                self.weight_matrix[i, mid:end] = np.linspace(1, 0, end - mid, endpoint=False)
            
            band_sum = np.sum(self.weight_matrix[i, :])
            if band_sum > 0:
                self.weight_matrix[i, :] /= band_sum

        self.chroma_matrix = np.zeros((self.nb_of_chroma, fft_size))
        bin_freqs = np.fft.rfftfreq(self.buffer_size, 1 / self.sample_rate)
        
        for k in range(fft_size):
            f = bin_freqs[k]
            if f > 30:
                pitch_midi = 69 + 12 * np.log2(f / 440.0)
                pitch_class = int(np.round(pitch_midi)) % 12
                self.chroma_matrix[pitch_class, k] = 1.0
                
        for i in range(self.nb_of_chroma):
            s = np.sum(self.chroma_matrix[i, :])
            if s > 0:
                self.chroma_matrix[i, :] /= s



    def build_asserved_fft_lists(self) -> None:
        """Initialize the FFT band and chromagram analysis arrays."""
        self.nb_of_chroma = 12

        # FFT band arrays (nb_of_fft_band = 8)
        self.fft_band_values = np.zeros(self.nb_of_fft_band)
        self.smoothed_fft_band_values = np.zeros(self.nb_of_fft_band)
        self.band_means = np.zeros(self.nb_of_fft_band)
        self.band_mean_distances = np.zeros(self.nb_of_fft_band)
        self.asserved_fft_band = np.zeros(self.nb_of_fft_band)
        self.band_proportion = np.zeros(self.nb_of_fft_band)

        # Chromagram arrays (12 pitch classes)
        self.chroma_values = np.zeros(self.nb_of_chroma)
        self.smoothed_chroma_values = np.zeros(self.nb_of_chroma)
        
        
    def build_asserved_total_power(self) -> None:
        self.smoothed_total_power = 0
        self.asserved_total_power = 0
        self.total_power_gm = 100
        self.total_power_lm = 100

    def prepare_for_calibration(self) -> None:
        self.duration_of_calibration = 5
        
        self.isSilenceCalibrating = False
        self.hasBeenSilenceCalibrated = False
        self.time_of_start_silence_calibration = 0
        self.time_of_end_silence_calibration = 0
        self.nb_of_listen_silence = 0
        self.mean_silence = np.zeros(self.nb_of_fft_band)
        
        self.isBBCalibrating = False
        self.hasBeenBBCalibrated = False
        self.time_of_start_bb_calibration = 0
        self.time_of_end_bb_calibration = 0
        self.nb_of_listen_bb = 0
        self.mean_bb = np.zeros(self.nb_of_fft_band)
        
    def start_silence_calibration(self, fps_ratio: float) -> None:
        self.isSilenceCalibrating = True
        
    def start_bb_calibration(self, fps_ratio: float) -> None:
        self.isBBCalibrating = True
        
    def stop_silence_calibration(self, fps_ratio: float) -> None:
        self.isSilenceCalibrating = False
        self.hasBeenSilenceCalibrated = True
        logger.debug(f"mean_silence = {self.mean_silence}")
    
    def stop_bb_calibration(self, fps_ratio: float) -> None:
        self.isBBCalibrating = False
        self.hasBeenBBCalibrated = True
        logger.debug(f"mean_bb = {self.mean_bb}")
            
    def calibrate_silence(self, fps_ratio: float) -> None:
        #on calcule la moyenne sur la durée de calibration
        self.nb_of_listen_silence += 1
        self.mean_silence = (1/(self.nb_of_listen_silence+1)) * (self.nb_of_listen_silence* self.mean_silence + self.fft_band_values)
        logger.debug(f"{self.fft_band_values} {self.mean_silence}")
                    
        
    def calibrate_bb(self, fps_ratio: float) -> None:
        #on calcule la moyenne sur la durée de calibration
        self.nb_of_listen_bb += 1
        self.mean_bb = (1/(self.nb_of_listen_bb+1)) * (self.nb_of_listen_bb* self.mean_bb + self.fft_band_values)
        

    def update_band_means_and_smoothed_values(self, fps_ratio: float) -> None:
        # ADSR Vectorization: Fast attack, slow release instead of static smooth_sensi
        attack = 0.2 ** fps_ratio
        release = 0.85 ** fps_ratio
        
        # Where NEW is greater than OLD, we use Attack. If OLD is greater, we use Release.
        # This makes lights snap hard to beats, but fade smoothly.
        smoothing = np.where(self.fft_band_values > self.smoothed_fft_band_values, attack, release)
        
        self.smoothed_fft_band_values = np.where(self.smoothed_fft_band_values < 1, 
                                                 self.fft_band_values, 
                                                 smoothing * self.smoothed_fft_band_values + (1 - smoothing) * self.fft_band_values)
        self.smoothed_fft_band_values = np.maximum(self.smoothed_fft_band_values, 0)
        
        # --- Chromagram Smoothing ---
        chroma_smoothing = np.where(self.chroma_values > self.smoothed_chroma_values, attack, release)
        self.smoothed_chroma_values = np.where(self.smoothed_chroma_values < 1,
                                                self.chroma_values,
                                                chroma_smoothing * self.smoothed_chroma_values + (1 - chroma_smoothing) * self.chroma_values)
        self.smoothed_chroma_values = np.maximum(self.smoothed_chroma_values, 0)
        
        retention_mean = 0.999 ** fps_ratio
        self.band_means = np.where(self.band_means < 1,
                                   self.smoothed_fft_band_values,
                                   retention_mean * self.band_means + (1 - retention_mean) * self.smoothed_fft_band_values)
        self.band_means = np.maximum(self.band_means, 0)
        
        distances_target = np.abs(self.smoothed_fft_band_values - self.band_means)
        self.band_mean_distances = np.where(self.band_mean_distances < 1,
                                            self.smoothed_fft_band_values / 2.0,
                                            retention_mean * self.band_mean_distances + (1 - retention_mean) * distances_target)
        
        total = np.sum(self.smoothed_fft_band_values)
        
        if total > 0:
            self.band_proportion = self.smoothed_fft_band_values / total
        else:
            self.band_proportion.fill(0.0)
                
                    
        
    def asserv_fft_bands_2(self, fps_ratio: float) -> None:
        min_bar = np.maximum(self.band_means - 2*self.band_mean_distances, 0)
        max_bar = self.band_means + 2*self.band_mean_distances
        
        diff = max_bar - min_bar
        # Avoid divide by zero safely
        safe_diff = np.where(diff == 0, 1.0, diff)
        
        self.asserved_fft_band = np.where(diff == 0, 
                                          0.5, 
                                          (self.smoothed_fft_band_values - min_bar) / safe_diff)
        
        self.asserved_fft_band = np.clip(self.asserved_fft_band, 0.0, 1.0)

    def apply_fake_fft(self, fps_ratio: float) -> None:
        self.fft_band_values += np.random.randint(-10, 11, size=self.nb_of_fft_band)
        self.fft_band_values = np.where(self.fft_band_values <= 0, 20, self.fft_band_values)
        
    def process_raw_audio(self, audio_data: np.ndarray) -> None:
        windowed_data = audio_data * self.hanning_window
        fft_result = np.abs(np.fft.rfft(windowed_data))
        scale = 150.0 / (self.buffer_size / 1024.0)
        
        mel_bands = np.dot(self.weight_matrix, fft_result) * scale
        self.fft_band_values[:] = mel_bands.astype(int)

        chroma_bands = np.dot(self.chroma_matrix, fft_result) * scale
        self.chroma_values[:] = chroma_bands



    def asserv_total_power(self, fps_ratio: float) -> None:
        instantPower = np.sum(self.fft_band_values)

        retention_power = 0.5 ** fps_ratio
        self.smoothed_total_power = retention_power * self.smoothed_total_power + (1 - retention_power) * instantPower

        if (self.smoothed_total_power > self.total_power_lm):
            self.total_power_lm = self.smoothed_total_power
        else:
            self.total_power_lm *= (0.9998 ** fps_ratio)  

        if (self.smoothed_total_power > self.total_power_gm):
            self.total_power_gm = 1.01 * self.smoothed_total_power
        else:
            safe_gm = max(self.total_power_gm, 1e-9)
            self.total_power_gm *= 1 + (0.005 * fps_ratio) * ( (self.total_power_lm/safe_gm) - 0.9)

        safe_gm = max(self.total_power_gm, 1e-9)
        self.asserved_total_power += min(1.0, 0.4 * fps_ratio) * ( self.smoothed_total_power/safe_gm - self.asserved_total_power)
