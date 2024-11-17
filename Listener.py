import pyaudio
import time
import numpy as np

class Listener:
    
    SAMPLES = 4048#4*44100 #
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    SAMPLING_FREQUENCY = 44100
    sampling_period_us = 1000000 / SAMPLING_FREQUENCY
    
    p = pyaudio.PyAudio()
    input_device_index = 2  # Update this to the correct device index
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=SAMPLING_FREQUENCY, input=True, input_device_index=input_device_index, frames_per_buffer=SAMPLES)

    
    
    
    def __init__(self):
        self.samples = []
        self.power = 1
        self.sensi = 0.5
    
        self.fft_bary=0
        self.nb_of_segm_fft=10
        self.segm_fft=[]
        self.lm=[]
        self.gm=[]
        self.asserv_segm_fft=[]
        self.segm_fft_indexs=[]
        self.lenFFT = int((self.SAMPLES+1)/2-1)
        f_0 = 1.0
        A=self.lenFFT*(1-1/np.power(2,f_0))/(np.power(2,self.nb_of_segm_fft*f_0)-1)
        print("f_0 = ", f_0)
        print("A = ", A)
        H=[]
        for k in range(self.nb_of_segm_fft):
            H.append(A*np.power(2,(k+1)*f_0))
        for k in range(self.nb_of_segm_fft):
            self.segm_fft_indexs.append(np.max([1,int(H[k])]))
        self.segm_fft_indexs=np.array(self.segm_fft_indexs)
        self.segm_fft_indexs[-1]+=self.lenFFT-np.sum(self.segm_fft_indexs)
        print("indexes = ", self.segm_fft_indexs)
        print(np.sum(self.segm_fft_indexs))
        for k in range(self.nb_of_segm_fft):
            self.segm_fft.append(0.0)
            self.lm.append(0.0)
            self.gm.append(0.0)
            self.asserv_segm_fft.append(0.0)
     
        self.segm_fft = np.array(self.segm_fft)
        self.lm = np.array(self.lm)
        self.gm = np.array(self.gm)
        self.asserv_segm_fft = np.array(self.asserv_segm_fft)
        self.total_power = 0
        self.total_power_lm = 0
        self.total_power_gm = 0
        
    def listen(self):
        try:
            data = self.stream.read(self.SAMPLES, exception_on_overflow=False)
            self.samples = np.frombuffer(data, dtype=np.int16)
            return True
        except:
            print("On arrive pas à écouter")
            return False

    def calculate_asserv_segm_fft(self):
        for index in range(self.nb_of_segm_fft):
            if( self.segm_fft[index]>=self.lm[index] ):
                self.lm[index]=1.1*self.segm_fft[index]
                if( self.lm[index]>=self.gm[index] ):
                    self.gm[index]=1.2*self.lm[index]
            else:
                self.lm[index]*=(1-0.001*self.sensi)
            self.gm[index]+=0.01*((1.3-0.2*self.sensi)*self.lm[index]-self.gm[index])
        
        sensi=1-self.sensi/1.7
        for index in range(self.nb_of_segm_fft):
            self.asserv_segm_fft[index]=(sensi*self.asserv_segm_fft[index]+(self.segm_fft[index]/self.gm[index]))/(sensi+1)

            
    def apply_fft(self):
        fft_sample = np.abs(np.fft.fft(self.samples))[1:self.lenFFT+1]
        a=0
        b=0
        index=0
        self.segm_fft[index]=0
        for i in range(self.lenFFT):
            if(index<self.nb_of_segm_fft-1):
                if(i>=self.segm_fft_indexs[index]):
                    index+=1
                    self.segm_fft[index]=0
            self.segm_fft[index]+=fft_sample[i]

        for i in range(self.nb_of_segm_fft):
            a+=i*self.segm_fft[i]
            b+=self.segm_fft[i]
        self.fft_bary =  (a/b) /(self.nb_of_segm_fft-1)
        
        self.calculate_asserv_segm_fft()
        
    def update(self):
        success = self.listen()
        if (success):
            self.apply_fft()
            self.calculate_asserv_segm_fft()
            self.asserv_total_power()
    
    def asserv_total_power(self):
        new_total_power = np.sum(self.lm)
        if( new_total_power >= self.total_power_lm ):
            self.total_power_lm = 1.1*new_total_power
            if( self.total_power_lm >= self.total_power_gm ):
                self.total_power_gm *= 1.2#1.2*self.total_power_lm
        else:
            self.total_power_lm *= 0.995 #(1-0.001*self.sensi)
        self.total_power_gm += 0.01*(1.2*self.total_power_lm-self.total_power_gm)
        
        sensi=1-self.sensi/1.7
        self.total_power=sensi*self.total_power+(1-sensi)*(new_total_power/self.total_power_gm)
        if(self.total_power > 1):
            self.total_power =1