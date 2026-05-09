import time
import numpy as np
import random
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class AudioIngestion:
    def __init__(self, infos: Dict[str, Any]) -> None:
        self.printAsservmentDetails = infos.get("printAsservmentDetails", False)
        self.useMicrophone          = infos.get("useMicrophone", True)
        self.momentum_multiplier = infos.get("momentum_mult", 0.05)
        self.base_pull = infos.get("base_pull", 0.01)
        self.dynamic_audio_latency = 0.069
        self.decay_base = infos.get("decay_base", 0.98)
        self.luminosite = 1.0
        self.sensi = 1.0
        self.nb_of_fft_band = 8

        self.build_asserved_fft_lists()
        self.build_asserved_total_power()
        self.prepare_for_calibration()


    def build_asserved_fft_lists(self) -> None:
        """
        This function prepares the asservissement of the fft

        The human ear hears the frequencies in a x^n way, meaning we notice the difference between 2 frequencies as a ratio, not a difference

        Therefore, in order to represent that effect, we have to regroup the fft results in bands wich sizes change according to the frequency
        the first band will be only 1 value wide, when the last one is actually more than a 1000 wide!

        this is what this function trys to represent

        Nf(k) represents the index of the k'th note 

        There is an A such that Nf(k+1)=A*Nf(k), therefore Nf(k)=A^(k-1)*Nf(1)
        we choose Nf(1)=1
        we need to hafe Nf(nb_of_bands) = lenFFT, therefore A^(nb_of_bands-1) = lenFFT
        therefore, A = (lenFFT)^(1/(nb_of_bands-1))
        """

        self.fft_bary = 0             #by_center of the frequencies
        
        
        self.fft_band_values = []   
        self.smoothed_fft_band_values = []
        self.band_means = [] 
        self.band_mean_distances = []   
        self.asserved_fft_band_2 = []     
        self.band_lm = []                  #asserved_fft_band_local_max   used for the asservissement of the band values
        self.band_gm = []                  #asserved_fft_band_global_max   used for the asservissement of the band values
        self.asserved_fft_band = []     #result of the asservissement (numbers between 0 and 1)
        self.band_proportion = []
        self.segm_fft_indexs = [1]    #index that separate each band
        
        self.nb_of_chroma = 12
        self.chroma_values = []
        self.smoothed_chroma_values = []

        """self.lenFFT = int(512/2)
        
        A=np.power(self.lenFFT,1/(self.nb_of_fft_band-1))
        for _ in range(1,self.nb_of_fft_band):
            self.segm_fft_indexs.append(self.segm_fft_indexs[-1]*A)
        for band_index in range(1,self.nb_of_fft_band):
            self.segm_fft_indexs[band_index]=int(self.segm_fft_indexs[band_index])
            print(self.segm_fft_indexs)"""
        
        
        for _ in range(self.nb_of_fft_band):
            self.fft_band_values.append(0.0)
            self.band_lm.append(100.0)
            self.band_gm.append(100.0)
            self.asserved_fft_band.append(0.0)
            self.smoothed_fft_band_values.append(0.0)
            self.band_means.append(0.0)
            self.band_mean_distances.append(0.0)
            self.asserved_fft_band_2.append(0.0)
            self.band_proportion.append(0.0)
            
        for _ in range(self.nb_of_chroma):
            self.chroma_values.append(0.0)
            self.smoothed_chroma_values.append(0.0)
     
        self.fft_band_values = np.array(self.fft_band_values)
        self.chroma_values = np.array(self.chroma_values)
        self.smoothed_chroma_values = np.array(self.smoothed_chroma_values)
        self.band_lm = np.array(self.band_lm)
        self.band_gm = np.array(self.band_gm)
        self.asserved_fft_band = np.array(self.asserved_fft_band)
        self.smoothed_fft_band_values=np.array(self.smoothed_fft_band_values)
        self.band_means=np.array(self.band_means)
        self.band_mean_distances=np.array(self.band_mean_distances)
        
        self.smooth_sensi = [0.9,0.6,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5]
        self.rearrange_list=[]
        for band_index in range(self.nb_of_fft_band):
            self.rearrange_list.append(np.power((band_index+1),1.8))

        self.manual_calibration = [1500,300,120,140,220,350,300,270,250,310,318,380,467,630,850,1266]
        
        
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
        if hasattr(self, 'chroma_values'):
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
        
        if not isinstance(self.band_proportion, np.ndarray):
            self.band_proportion = np.array(self.band_proportion)
            
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

    def asserv_fft_bands(self, fps_ratio: float) -> None:
        """
        we use a glomal_max and local_max to asser each band's value

        each time the smoothed_value is not higher than the local_mac, we lower local_max a little

        global max triez to stabilize at 1.2 times the local max but smoothly
        """
        for band_index in range(self.nb_of_fft_band):
            if( self.smoothed_fft_band_values[band_index]>=self.band_lm[band_index] ):
                self.band_lm[band_index]=self.smoothed_fft_band_values[band_index]
            else :
                self.band_lm[band_index] *= (0.9995 ** fps_ratio)

            if( self.smoothed_fft_band_values[band_index]>=self.band_gm[band_index] ):
                self.band_gm[band_index]=1.01*self.smoothed_fft_band_values[band_index]
            else:
                self.band_gm[band_index] *= 1 + (0.005 * fps_ratio) * (self.band_lm[band_index]/max(0.001, self.band_gm[band_index]) - 0.9)

            self.asserved_fft_band[band_index] += min(1.0, 0.4 * fps_ratio) * (self.smoothed_fft_band_values[band_index]/self.band_gm[band_index] - self.asserved_fft_band[band_index])

    def apply_fake_fft(self, fps_ratio: float) -> None:
        for band_index in range(self.nb_of_fft_band):
            self.fft_band_values[band_index] += random.randint(-10,10)
            if ( self.fft_band_values[band_index] <= 0):
                self.fft_band_values[band_index] = 20
                
        num=0
        denom=0
        for i in range(self.nb_of_fft_band):
            num+=i*self.fft_band_values[i]
            denom+=self.fft_band_values[i]
        self.fft_bary =  (num/denom) /(self.nb_of_fft_band-1)
        

    def asserv_total_power(self, fps_ratio: float) -> None:
        instantPower = 0
        for band_index in range(self.nb_of_fft_band):
            instantPower+= self.fft_band_values[band_index]

        retention_power = 0.5 ** fps_ratio
        self.smoothed_total_power = retention_power * self.smoothed_total_power + (1 - retention_power) * instantPower

        if (self.smoothed_total_power > self.total_power_lm):
            self.total_power_lm = self.smoothed_total_power
        else:
            self.total_power_lm *= (0.9998 ** fps_ratio)  

        if (self.smoothed_total_power > self.total_power_gm):
            self.total_power_gm = 1.01 * self.smoothed_total_power
        else:
            self.total_power_gm *= 1 + (0.005 * fps_ratio) * ( (self.total_power_lm/self.total_power_gm) - 0.9)

        self.asserved_total_power += min(1.0, 0.4 * fps_ratio) * ( self.smoothed_total_power/self.total_power_gm - self.asserved_total_power)
