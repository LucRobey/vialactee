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
            await asyncio.sleep(0.0001)

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
        for band_index in range(self.nb_of_fft_band):          
            min_bar = np.max([self.band_means[band_index] - 2*self.band_mean_distances[band_index] , 0])
            #sensi : remplacer le 2 par (3 - sensi)?
            max_bar = self.band_means[band_index] + 2*self.band_mean_distances[band_index]
    
            if(max_bar == min_bar):
                self.asserved_fft_band[band_index] = 0.5
            else:
                self.asserved_fft_band[band_index] = float(self.smoothed_fft_band_values[band_index] - min_bar)/(max_bar - min_bar)

            if(self.asserved_fft_band[band_index] > 1):
                self.asserved_fft_band[band_index] = 1
            elif (self.asserved_fft_band[band_index] < 0):
                self.asserved_fft_band[band_index] = 0

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
            if(self.smoothed_fft_band_values[band_index]<1):
                self.smoothed_fft_band_values[band_index] = self.fft_band_values[band_index]
            else:
                self.smoothed_fft_band_values[band_index] = self.smooth_sensi[band_index] * self.smoothed_fft_band_values[band_index] + (1-self.smooth_sensi[band_index])*self.fft_band_values[band_index]
            
            if(self.band_means[band_index]<1):
                self.band_means[band_index] = self.smoothed_fft_band_values[band_index]
            else:
                self.band_means[band_index] = 0.999 * self.band_means[band_index] + 0.001 * self.smoothed_fft_band_values[band_index]
            
            if(self.band_mean_distances[band_index]<1):
                self.band_mean_distances[band_index] = self.smoothed_fft_band_values[band_index]/2
            else:
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
