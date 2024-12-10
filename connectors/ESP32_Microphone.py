#import serial
import asyncio
import time

class ESP32_Microphone:

    def __init__(self, bandValues, infos):
        self.showMicrophoneDetails  = infos["printMicrophoneDetails"]
        self.onRaspberry            = infos["onRaspberry"]
        self.printTimeOfCalculation = infos["printTimeOfCalculation"]
        self.useMicrophone          = infos["useMicrophone"]

        self.bandValues = bandValues
        self.nb_of_fft_band = len(self.bandValues)

        self.ser = None
        if(self.onRaspberry and self.useMicrophone):
            self.ser = serial.Serial('/dev/ttyUSB0', 1000000, timeout=0.1)
        
                
    async def listen_forever(self):
        while True:
            if(self.printTimeOfCalculation):
                time_mem = time.time()
            await self.listen()
            if(self.printTimeOfCalculation):
                duration = time.time() - time_mem
                print("(ESPmicro) temps de calcul = ",duration)
            await asyncio.sleep(0.0001)
            
    async def listen(self):
        if(self.onRaspberry and self.useMicrophone):
            #s'il y a au moins un message en attente
            if self.ser.in_waiting > 0:
                # Read the response in a separate thread to avoid blocking the event loop
                # on lit tous les messages et on garde le dernier
                while self.ser.in_waiting > 0:
                    response = await asyncio.to_thread(self.ser.readline)
                
                if self.showMicrophoneDetails:
                    print("(ESP_mic)   message reçu ", response)
                
                cleaned_data = response.decode().strip()
                split_data = cleaned_data.split(',')
                
                # Update the band values
                for band_index in range(self.nb_of_fft_band):
                    self.bandValues[band_index] = int(split_data[band_index])
                
                return True
            else:
                if self.showMicrophoneDetails:
                    print("(ESP_mic)   pas de message reçu ")
                return False
        else:
            pass

