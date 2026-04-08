import time
import numpy as np
import random
import asyncio


class Listener:
    def __init__(self , infos):
        self.printAsservmentDetails = infos["printAsservmentDetails"]
        self.useMicrophone          = infos["useMicrophone"]
        
        self.sensi = 0.5            # global sensi (not used yet)
        self.luminosite = 1.0

        self.nb_of_fft_band = 8     # number of bands we divide the frequencies

        self.build_asserved_fft_lists()
        self.build_asserved_total_power()
        self.build_band_peaks()

        self.prepare_for_calibration()
        
    async def update_forever(self):
        while True:
            await self.update()
            await asyncio.sleep(1/60)

    def update(self):
        if self.useMicrophone:
            if self.isSilenceCalibrating:
                self.calibrate_silence()
            elif self.isBBCalibrating:
                self.calibrate_bb()
            else:
                self.update_band_means_and_smoothed_values()
                self.asserv_fft_bands_2()
                self.asserv_total_power()
                self.detect_band_peaks()
        else:
            self.apply_fake_fft()
            self.asserv_fft_bands()
            self.update_band_means_and_smoothed_values()
            self.asserv_total_power()
            self.detect_band_peaks()

        
    def asserv_fft_bands_2(self):
        min_bar = np.maximum(self.band_means - 2*self.band_mean_distances, 0)
        max_bar = self.band_means + 2*self.band_mean_distances
        
        diff = max_bar - min_bar
        # Avoid divide by zero safely
        safe_diff = np.where(diff == 0, 1.0, diff)
        
        self.asserved_fft_band = np.where(diff == 0, 
                                          0.5, 
                                          (self.smoothed_fft_band_values - min_bar) / safe_diff)
        
        self.asserved_fft_band = np.clip(self.asserved_fft_band, 0.0, 1.0)

    def asserv_fft_bands(self):
        """
        we use a glomal_max and local_max to asser each band's value

        each time the smoothed_value is not higher than the local_mac, we lower local_max a little

        global max triez to stabilize at 1.2 times the local max but smoothly
        """
        for band_index in range(self.nb_of_fft_band):
            if( self.smoothed_fft_band_values[band_index]>=self.band_lm[band_index] ):
                self.band_lm[band_index]=self.smoothed_fft_band_values[band_index]
            else :
                self.band_lm[band_index]*=0.9995

            if( self.smoothed_fft_band_values[band_index]>=self.band_gm[band_index] ):
                self.band_gm[band_index]=1.01*self.smoothed_fft_band_values[band_index]
            else:
                self.band_gm[band_index] *= 1 + 0.005 * (self.band_lm[band_index]/self.band_lm[band_index] - 0.9)

            self.asserved_fft_band[band_index] += 0.4 *  (self.smoothed_fft_band_values[band_index]/self.band_gm[band_index] - self.asserved_fft_band[band_index])

    def update_band_means_and_smoothed_values(self):
        # ADSR Vectorization: Fast attack, slow release instead of static smooth_sensi
        attack = 0.2
        release = 0.85
        
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
        
        self.band_means = np.where(self.band_means < 1,
                                   self.smoothed_fft_band_values,
                                   0.999 * self.band_means + 0.001 * self.smoothed_fft_band_values)
        self.band_means = np.maximum(self.band_means, 0)
        
        distances_target = np.abs(self.smoothed_fft_band_values - self.band_means)
        self.band_mean_distances = np.where(self.band_mean_distances < 1,
                                            self.smoothed_fft_band_values / 2.0,
                                            0.999 * self.band_mean_distances + 0.001 * distances_target)
        
        total = np.sum(self.smoothed_fft_band_values)
        
        if not isinstance(self.band_proportion, np.ndarray):
            self.band_proportion = np.array(self.band_proportion)
            
        if total > 0:
            self.band_proportion = self.smoothed_fft_band_values / total
        else:
            self.band_proportion.fill(0.0)
                
                    
        
    def apply_fake_fft(self):
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
        

    def asserv_total_power(self):
        instantPower = 0
        for band_index in range(self.nb_of_fft_band):
            instantPower+= self.fft_band_values[band_index]

        self.smoothed_total_power = 0.5 * (self.smoothed_total_power + instantPower)

        if (self.smoothed_total_power > self.total_power_lm):
            self.total_power_lm = self.smoothed_total_power
        else:
            self.total_power_lm*=0.9998  

        if (self.smoothed_total_power > self.total_power_gm):
            self.total_power_gm = 1.01 * self.smoothed_total_power
        else:
            self.total_power_gm *= 1 + 0.005 * ( (self.total_power_lm/self.total_power_gm) - 0.9)

        self.asserved_total_power += 0.4 *  ( self.smoothed_total_power/self.total_power_gm - self.asserved_total_power)

    def detect_band_peaks(self):
        """
        Spectral Flux onset detection combined with dynamic variance trackers.
        Calculates positive energy influx to find sharp transients quickly.
        """
        if not hasattr(self, 'prev_fft_band_values'):
            self.prev_fft_band_values = np.zeros(self.nb_of_fft_band)
            
        # Spectral Flux: Positive difference between current frame and previous frame
        flux = np.maximum(0, self.fft_band_values - self.prev_fft_band_values)
        self.band_flux = flux
        self.prev_fft_band_values = np.copy(self.fft_band_values)
        
        current_time = time.time()
        # Instead of absolute energy, threshold against Flux
        variance_threshold = (self.band_means * 0.2) + (self.peak_sensitivity * self.band_mean_distances)
        
        # Vectorized peak detection
        is_peak = (flux > variance_threshold) & (current_time > self.peak_times + self.delta_time_peak)
        
        self.band_peak = is_peak.astype(int)
        
        # Update peak times where peak detected
        self.peak_times = np.where(is_peak, current_time, self.peak_times)
        
        # Adjust sensitivity: up heavily on beat, down slowly otherwise
        self.peak_sensitivity = np.where(is_peak, 
                                         np.minimum(self.peak_sensitivity + 0.5, 5.0),
                                         np.maximum(self.peak_sensitivity - 0.005, 1.5))
                                         
        # --- BPM Phase-Locked Loop (PLL) ---
        # Trigger global beat on bass/sub-bass onsets
        bass_peak = is_peak[0] or is_peak[1]
        
        if bass_peak:
            delta = current_time - self.last_beat_time
            
            energy = np.sum(self.band_flux[0:2])
            
            # --- IOI Histogram Logic (The 16th-Note Mathematical Octave Folder) ---
            # 1. Forget peaks older than 4 seconds
            # Use tuples to store both Time and Energy
            self.recent_peaks = [(t, e) for (t, e) in self.recent_peaks if current_time - t < 4.0]
            
            # 2. Decay previous histogram probability to favor new beats
            # 0.98 gives strong historical memory: 145 and 146 will physically stack into a massive mountain of trust!
            self.bpm_histogram *= 0.98 
            
            # 3. Calculate interval between current hit and ALL historical hits
            for old_t, old_e in self.recent_peaks:
                dt = current_time - old_t
                if dt < 0.05: continue
                
                # 4. Ponderate: exponential decay based on how far back the old beat was + power of BOTH beats
                # Using sqrt so a massive bass drop doesn't cause floating point explosions
                weight = np.sqrt(energy * old_e) * np.exp(-dt / 1.5)
                
                implied_bpm = 60.0 / dt
                
                # 5. Octave Folder: Force 32nd, 16th, and 8th notes natively down into 60-180 range
                b = implied_bpm
                while b > 180.0:
                    b /= 2.0
                while b < 60.0:
                    b *= 2.0
                    
                # 6. Apply Gaussian bell-curve probability vote into the histogram
                if 60.0 <= b < 180.0:
                    # Only calculate Gaussian spread for nearby bins to save CPU
                    center_idx = int(round(b)) - 60
                    min_idx = max(0, center_idx - 4)
                    max_idx = min(120, center_idx + 5)
                    for i in range(min_idx, max_idx):
                        bin_bpm = 60 + i
                        dist = abs(b - bin_bpm)
                        self.bpm_histogram[i] += weight * np.exp(-(dist**2) / 2.0)
            
            # Store current beat and its energy for future hits to measure against
            self.recent_peaks.append((current_time, energy))
            
            # --- CONTINUOUS MULTI-PEAK EXTRACTION ---
            self.continuous_candidates = []
            if np.max(self.bpm_histogram) > 0.05:
                local_maxima = []
                for i in range(1, 119):
                    if self.bpm_histogram[i] > self.bpm_histogram[i-1] and self.bpm_histogram[i] > self.bpm_histogram[i+1]:
                        if self.bpm_histogram[i] > 0.02:
                            # Center of Mass (Barycenter) around the local peak
                            w_min = max(0, i - 2)
                            w_max = min(120, i + 3)
                            weights = self.bpm_histogram[w_min:w_max]
                            if np.sum(weights) > 0:
                                p_bpm = 60.0 + np.average(np.arange(w_min, w_max), weights=weights)
                                local_maxima.append((self.bpm_histogram[i], p_bpm))
                
                # Sort by highest trust probability
                local_maxima.sort(reverse=True, key=lambda x: x[0])
                self.continuous_candidates = [b for w, b in local_maxima[:3]]
                
                if self.continuous_candidates:
                    self.ioi_bpm = self.continuous_candidates[0]
                
            print(f"🥁 [Hit!] | 🎯 IOI BPM: {self.ioi_bpm:.2f} | ", end="")
            
            # Accept tempo bounds between ~60 BPM (1.0s) and ~180 BPM (0.33s)
            if 0.33 < delta < 1.0:
                self.beat_intervals.append(delta)
                if len(self.beat_intervals) > 8:
                    self.beat_intervals.pop(0)
                if len(self.beat_intervals) >= 3:
                    binary_candidate = 60.0 / np.median(self.beat_intervals)
                    
                    agreed_continuous = None
                    # Binary checks if its real-world candidate matches ANY of the top Continuous peaks
                    if len(self.continuous_candidates) > 0:
                        for cbpm in self.continuous_candidates:
                            if abs(binary_candidate - cbpm) / cbpm < 0.05: # Overlap found!
                                agreed_continuous = cbpm
                                break
                    
                    if agreed_continuous is not None:
                        # 🤝 Consensus reached! Continuous Method leads the way.
                        self.binary_trust = min(1.0, self.binary_trust + 0.3)
                        self.bpm = 0.5 * self.bpm + 0.5 * agreed_continuous
                        print(f"🤝 Consensus! Binary locking to IOI: {self.bpm:.1f} (Trust: {self.binary_trust:.2f})")
                    else:
                        # No consensus. Binary relies on its own historic trust.
                        if self.binary_trust > 0:
                            if abs(binary_candidate - self.bpm) / self.bpm < 0.05: # 5% tolerance
                                self.binary_trust = min(1.0, self.binary_trust + 0.20)
                                self.bpm = 0.8 * self.bpm + 0.2 * binary_candidate
                            else:
                                self.binary_trust -= 0.15
                                if self.binary_trust <= 0:
                                    self.bpm = binary_candidate
                                    self.binary_trust = 0.5
                        else:
                            self.bpm = binary_candidate
                            self.binary_trust = 0.5
                            
                        print(f"🎵 Binary tracking solo: {self.bpm:.1f} (Trust: {self.binary_trust:.2f})")
                else:
                    print(f"⏳ Wait... ({len(self.beat_intervals)}/3)")
            else:
                print(f"🚫 Ignored")
            
            # Snap to grid / Hard sync if valid rhythmic distance
            if delta > 0.33:
                self.last_beat_time = current_time
                self.beat_count += 1
                self.beat_phase = 0.0

        # Predict current phase
        expected_interval = 60.0 / self.bpm if self.bpm > 0 else 0.5
        time_since = current_time - self.last_beat_time
        
        # Freewheel mathematically through missing beats (silent breakdowns)
        if time_since >= expected_interval:
            beats_passed = int(time_since / expected_interval)
            self.last_beat_time += beats_passed * expected_interval
            self.beat_count += beats_passed
            time_since = current_time - self.last_beat_time
            
        self.beat_phase = time_since / expected_interval
            
        # --- Continuous Autocorrelation BPM Tracking ---
        self.flux_history = np.roll(self.flux_history, -1)
        self.time_history = np.roll(self.time_history, -1)
        self.flux_history[-1] = np.sum(self.band_flux[0:2]) # Log exact bass energy
        self.time_history[-1] = current_time
        
        self.frame_counter += 1
        # Re-evaluate tempo mathematically every ~2 seconds (120 frames)
        if self.frame_counter % 120 == 0 and self.time_history[0] > 0:
            elapsed_time = self.time_history[-1] - self.time_history[0]
            avg_fps = self.history_size / elapsed_time if elapsed_time > 0 else 60.0
            
            # Centralize data to remove DC offset and magnify periodicity
            centered_flux = self.flux_history - np.mean(self.flux_history)
            autocorr = np.correlate(centered_flux, centered_flux, mode='full')
            half_corr = autocorr[self.history_size - 1:]
            
            # Target human dance tempos between 75 and 180 BPM
            min_lag = max(1, int(avg_fps * 60.0 / 180.0))
            max_lag = min(self.history_size - 1, int(avg_fps * 60.0 / 75.0))
            
            if max_lag > min_lag:
                valid_corr = half_corr[min_lag:max_lag]
                
                # Find top 3 distinct peaks (separated by at least 3 frames so we don't pick adjacent points of the same peak)
                sorted_indices = np.argsort(valid_corr)[::-1]
                top_lags = []
                for idx in sorted_indices:
                    lag = min_lag + idx
                    if all(abs(lag - l) > 3 for l in top_lags):
                        top_lags.append(lag)
                        if len(top_lags) == 3:
                            break
                            
                if len(top_lags) > 0:
                    top_bpms = [60.0 * avg_fps / l for l in top_lags]
                    
                    agreed_bpm = None
                    # If we already have trust, see if any of the top 3 peaks agree with our current BPM
                    if self.autocorr_trust > 0:
                        for b in top_bpms:
                            # 3% tolerance for agreement
                            if abs(b - self.autocorr_bpm) / self.autocorr_bpm < 0.03:
                                agreed_bpm = b
                                break
                    
                    if agreed_bpm is not None:
                        # It agreed! Keep the current bpm (or gently blend it) and build trust
                        self.autocorr_bpm = 0.8 * self.autocorr_bpm + 0.2 * agreed_bpm
                        self.autocorr_trust = min(1.0, self.autocorr_trust + 0.15)
                    else:
                        # It disagreed. Lose trust.
                        self.autocorr_trust -= 0.20
                        
                        # If trust falls entirely, snap to the absolute best peak
                        if self.autocorr_trust <= 0:
                            best_lag = top_lags[0]
                            # Let's derive a continuous floating point lag using center-of-mass on the peak
                            idx = best_lag - min_lag
                            w_min = max(0, idx - 2)
                            w_max = min(len(valid_corr), idx + 3)
                            weights = np.maximum(0, valid_corr[w_min:w_max])
                            if np.sum(weights) > 0:
                                continuous_idx = np.average(np.arange(w_min, w_max), weights=weights)
                                best_lag = min_lag + continuous_idx
                                
                            self.autocorr_bpm = 60.0 * avg_fps / best_lag
                            self.autocorr_trust = 0.5
                
                print(f"🔄 [Autocorr] BPM: {self.autocorr_bpm:.1f} (Trust: {self.autocorr_trust:.2f}) | [Binary] BPM: {self.bpm:.1f}")
            

    def build_asserved_total_power(self):
        self.smoothed_total_power = 0
        self.asserved_total_power = 0
        self.total_power_gm = 100
        self.total_power_lm = 100

    def build_asserved_fft_lists(self):
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
        
        
    def build_band_peaks(self):
        # We start looking for peaks roughly 2.0 "standard deviations" above the exponential mean
        self.peak_sensitivity = np.ones(self.nb_of_fft_band) * 2.0
        self.delta_time_peak = 0.15 #seconde
        self.peak_times = []
        self.band_peak = []
        self.band_flux = []
        for band_index in range(self.nb_of_fft_band):
            self.peak_times.append(0.0)
            self.band_peak.append(0)
            self.band_flux.append(0.0)

        self.peak_times = np.array(self.peak_times)
        self.band_peak = np.array(self.band_peak)
        self.band_flux = np.array(self.band_flux)
        
        # BPM Anticipation Grid Variables
        self.bpm = 120.0
        self.autocorr_bpm = 120.0
        self.autocorr_trust = 0.0
        self.ioi_bpm = 120.0
        self.binary_trust = 0.0
        self.recent_peaks = []
        self.bpm_histogram = np.zeros(120)
        
        self.beat_intervals = []
        self.last_beat_time = time.time()
        self.beat_count = 0
        self.beat_phase = 0.0
        
        # Continuous Autocorrelation Buffers
        self.history_size = 256
        self.flux_history = np.zeros(self.history_size)
        self.time_history = np.zeros(self.history_size)
        self.frame_counter = 0
        
        
    def prepare_for_calibration(self):
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
        
    def start_silence_calibration(self):
        self.isSilenceCalibrating = True
        
    def start_bb_calibration(self):
        self.isBBCalibrating = True
        
    def stop_silence_calibration(self):
        self.isSilenceCalibrating = False
        self.hasBeenSilenceCalibrated = True
        print("mean_silence = ",self.mean_silence)
    
    def stop_bb_calibration(self):
        self.isBBCalibrating = False
        self.hasBeenBBCalibrated = True
        print(self.mean_bb)
            
    def calibrate_silence(self):
        #on calcule la moyenne sur la durée de calibration
        self.nb_of_listen_silence += 1
        self.mean_silence = (1/(self.nb_of_listen_silence+1)) * (self.nb_of_listen_silence* self.mean_silence + self.fft_band_values)
        print(self.fft_band_values,self.mean_silence)
                    
        
    def calibrate_bb(self):
        #on calcule la moyenne sur la durée de calibration
        self.nb_of_listen_bb += 1
        self.mean_bb = (1/(self.nb_of_listen_bb+1)) * (self.nb_of_listen_bb* self.mean_bb + self.fft_band_values)
        

# Assuming the Listener class is defined properly and contains the update_forever method

"""
async def main():
    listener = Listener()  # or Mode_master(), depending on where you want to start
    # Start the async update_forever method
    await listener.update_forever()

if __name__ == '__main__':
    # Start the asyncio event loop
    asyncio.run(main())

"""
