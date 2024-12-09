import pyaudio
import time
import numpy as np
import random

import connectors.ESP32_Microphone as ESP32_Microphone

#yo les potos c poulette

class Listener:
    
    SAMPLES = 1024#4048#4*44100 #
    #FORMAT = pyaudio.paInt16
    #CHANNELS = 1
    SAMPLING_FREQUENCY = 44100
    sampling_period_us = 1000000 / SAMPLING_FREQUENCY
    
    #p = pyaudio.PyAudio()
    #input_device_index = 2  # Update this to the correct device index
    #stream = p.open(format=FORMAT, channels=CHANNELS, rate=SAMPLING_FREQUENCY, input=True, input_device_index=input_device_index, frames_per_buffer=SAMPLES)

    
    
    
    def __init__(self , microphone , showMicrophoneDetails):
        self.samples = []           #samples we listen os size SAMPLES
        self.power = 1              #global power  (not used yet)
        self.sensi = 0.5            #global sensi   (not used yet)
        self.luminosite = 1.0
        
        self.microphone = microphone
        self.showMicrophoneDetails = showMicrophoneDetails
        
        self.nb_of_fft_band = 8      #nb of bands we divide the frequencies
        self.connector = ESP32_Microphone.ESP32_Microphone(self.nb_of_fft_band , self.showMicrophoneDetails)

        self.build_asserved_fft_lists()
        self.build_asserved_total_power()
        self.build_band_peaks()
        
        

    def update(self):
        if (self.microphone):
            success = self.listen()
            if (success):
                #self.apply_fft()
                self.asserv_fft_bands()
                self.update_band_means_and_smoothed_values()
                self.asserv_total_power()
                self.detect_band_peaks()
                
            else:
                if (self.showMicrophoneDetails):
                    print("(L) on ecoute rien")
        else:
            self.apply_fake_fft()
            self.asserv_fft_bands()
            self.update_band_means_and_smoothed_values()
            self.asserv_total_power()
            self.detect_band_peaks()
        
    def listen(self):
        success , self.fft_band_values = self.connector.listen()
        return success
        
    def asserv_fft_bands_2(self):
        for band_index in range(self.nb_of_fft_band):
            min_bar = np.max([self.band_means[band_index] - 2*self.band_mean_distances[band_index] , 0])
            #sensi : remplacer le 2 par (3 - sensi)?
            max_bar = self.band_means[band_index] + 2*self.band_mean_distances[band_index]
            self.asserved_fft_band_2[band_index] = (self.smoothed_fft_band_values[band_index] - min_bar)/(max_bar - min_bar)

            if(self.asserved_fft_band_2[band_index] > 1):
                self.asserved_fft_band_2[band_index] = 1
            elif (self.asserved_fft_band_2[band_index] > 0):
                self.asserved_fft_band_2[band_index] = 0

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
        for band_index in range(self.nb_of_fft_band):
            self.smoothed_fft_band_values[band_index] = self.smooth_sensi[band_index] * self.smoothed_fft_band_values[band_index] + (1-self.smooth_sensi[band_index])*self.fft_band_values[band_index]
            self.band_means[band_index] = 0.999 * self.band_means[band_index] + 0.001 * self.smoothed_fft_band_values[band_index]
            self.band_mean_distances[band_index] = 0.999 * self.band_mean_distances[band_index] + 0.001 * np.abs(self.smoothed_fft_band_values[band_index] - self.band_means[band_index])
            if(self.smoothed_fft_band_values[band_index]<0):
                self.smoothed_fft_band_values[band_index]=0
            if(self.band_means[band_index]<0):
                self.band_means[band_index]=0
            
            total=0
            for band_index in range(self.nb_of_fft_band):
                total += self.smoothed_fft_band_values[band_index]
            for band_index in range(self.nb_of_fft_band):    
                self.band_proportion[band_index] = float(self.smoothed_fft_band_values[band_index])/total
                
                    
    def apply_fft(self):
        fft_sample = np.abs(np.fft.fft(self.samples))[1:self.lenFFT+1]
        
        band_index=0
        self.fft_band_values[band_index]=0
        for i in range(self.lenFFT):
            if(band_index<self.nb_of_fft_band-1):
                if(i>=self.segm_fft_indexs[band_index]):
                    band_index+=1
                    self.fft_band_values[band_index]=0
            self.fft_band_values[band_index]+=fft_sample[i]

        for band_index in range(self.nb_of_fft_band):
            self.fft_band_values[band_index] /= self.rearrange_list[band_index]
            self.fft_band_values[band_index] -=self.manual_calibration[band_index]
            
        #print(self.fft_band_values)
        num=0
        denom=0
        for i in range(self.nb_of_fft_band):
            num+=i*self.fft_band_values[i]
            denom+=self.fft_band_values[i]
        self.fft_bary =  (num/denom) /(self.nb_of_fft_band-1)
        
        
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
        if the band values is above the mean of it's band plus the sensitivity, it activates
        if it activates, it raises the sensibility, otherwise, the sensibility drops little by little
        """
        total=0
        for band_index in range(self.nb_of_fft_band):
            if (self.fft_band_values[band_index] > self.band_means[band_index] + self.peak_sensitivity  and 
                time.time() > self.peak_times[band_index] + self.delta_time_peak):
                self.band_peak[band_index] = 1
                total += 1
                self.peak_times[band_index] = time.time()
            else :
                self.band_peak[band_index] = 0
        self.peak_sensitivity *= 1+(total-1)*0.0001
            

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

        self.lenFFT = int((self.SAMPLES)/2-2) #Niquist-Shanon + the first value doesn't matter

        A=np.power(self.lenFFT,1/(self.nb_of_fft_band-1))
        for _ in range(1,self.nb_of_fft_band):
            self.segm_fft_indexs.append(self.segm_fft_indexs[-1]*A)
        for band_index in range(1,self.nb_of_fft_band):
            self.segm_fft_indexs[band_index]=int(self.segm_fft_indexs[band_index])
        print(self.segm_fft_indexs)
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
     
        self.fft_band_values = np.array(self.fft_band_values)
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
        self.peak_sensitivity = 500
        self.delta_time_peak = 0.15#seconde
        self.peak_times = []
        self.band_peak = []
        for band_index in range(self.nb_of_fft_band):
            self.peak_times.append(0.0)
            self.band_peak.append(0)

        self.peak_times = np.array(self.peak_times)
        self.band_peak = np.array(self.band_peak)
        
    
