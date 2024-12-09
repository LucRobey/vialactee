import serial
import time
import asyncio

class ESP32_Microphone:

    def __init__(self, bandValues, showMicrophoneDetails):
        self.ser = serial.Serial('/dev/ttyUSB0', 1000000, timeout=0.1)
        self.showMicrophoneDetails = showMicrophoneDetails
        self.bandValues = bandValues
        self.nb_of_fft_band = len(self.bandValues)
                
    async def listen_forever(self):
        while True:
            await self.listen()
            await asyncio.sleep(0.0001)
            
    async def listen(self):
        if self.ser.in_waiting > 0:
            # Read the response in a separate thread to avoid blocking the event loop
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


class Listener:

    def __init__(self, bandValues):
        self.bandValues = bandValues
        self.microphone = ESP32_Microphone(bandValues, showMicrophoneDetails=True)

    async def update_forever(self):
        while True:
            success = await self.microphone.listen()  # await the listen method
            if success:
                print("Data received and processed")
            else:
                print("No data received")
            await asyncio.sleep(0.001)  # To avoid blocking, ensure the event loop continues

# Start the asyncio event loop
async def main():
    bandValues = [0] * 8  # Initialize with the number of bands you're using
    listener = Listener(bandValues)
    await listener.update_forever()

if __name__ == '__main__':
    asyncio.run(main())
