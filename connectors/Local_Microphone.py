import numpy as np
import asyncio
import time

try:
    import sounddevice as sd
except ImportError:
    sd = None

class Local_Microphone:
    def __init__(self, bandValues, infos, chromaValues=None):
        self.showMicrophoneDetails  = infos.get("printMicrophoneDetails", False)
        self.printTimeOfCalculation = infos.get("printTimeOfCalculation", False)
        self.useMicrophone          = infos.get("useMicrophone", True)
        
        self.bandValues = bandValues
        self.chromaValues = chromaValues
        self.nb_of_fft_band = len(self.bandValues)
        
        # Audio capture settings
        self.sample_rate = 44100
        self.chunk_size = 1024  # Size of the microphone chunk callbacks
        self.buffer_size = 4096 # Size of the sliding FFT window
        self.audio_data = np.zeros(self.buffer_size)
        self.stream = None
        
        # We map linear FFT bins into 8 Mel-scale overlapping triangular filterbanks.
        # rfft of 4096 points = 2049 bins. Frequency range: 0 -> 22050 Hz
        fft_size = self.buffer_size // 2 + 1
        self.weight_matrix = np.zeros((self.nb_of_fft_band, fft_size))
        
        def hz_to_mel(f): return 2595 * np.log10(1 + f / 700.0)
        def mel_to_hz(m): return 700 * (10**(m / 2595.0) - 1)
        
        # We start at 20Hz (ignoring super low sub-rumble) up to 20000Hz
        lower_mel = hz_to_mel(20)
        upper_mel = hz_to_mel(20000)
        mel_points = np.linspace(lower_mel, upper_mel, self.nb_of_fft_band + 2)
        hz_points = mel_to_hz(mel_points)
        bin_points = np.floor((self.buffer_size + 1) * hz_points / self.sample_rate).astype(int)
        
        for i in range(self.nb_of_fft_band):
            start = min(bin_points[i], fft_size - 1)
            mid = min(bin_points[i + 1], fft_size - 1)
            end = min(bin_points[i + 2], fft_size - 1)
            
            # Create overlapping triangular filters
            if mid > start:
                self.weight_matrix[i, start:mid] = np.linspace(0, 1, mid - start, endpoint=False)
            if end > mid:
                self.weight_matrix[i, mid:end] = np.linspace(1, 0, end - mid, endpoint=False)
            
            # Normalize so each band operates effectively as a 'mean'
            band_sum = np.sum(self.weight_matrix[i, :])
            if band_sum > 0:
                self.weight_matrix[i, :] /= band_sum

        # Harmonic Synesthesia (Chromagram) Transformation Matrix
        self.chroma_matrix = np.zeros((12, fft_size))
        bin_freqs = np.fft.rfftfreq(self.buffer_size, 1 / self.sample_rate)
        
        for k in range(fft_size):
            f = bin_freqs[k]
            if f > 30: # 30 Hz roughly avoids subsonic DC noise
                pitch_midi = 69 + 12 * np.log2(f / 440.0)
                pitch_class = int(np.round(pitch_midi)) % 12
                self.chroma_matrix[pitch_class, k] = 1.0
                
        # Normalize each pitch class to avoid bias (some classes cover more bins at high frequencies)
        for i in range(12):
            s = np.sum(self.chroma_matrix[i, :])
            if s > 0:
                self.chroma_matrix[i, :] /= s

    def audio_callback(self, indata, frames, time_info, status):
        """ This callback is called by sounddevice in a separate C-thread """
        if status and self.showMicrophoneDetails:
            print("(Local_mic) status:", status)
        
        # If stereo, average out the two channels into mono
        if indata.shape[1] > 1:
            incoming = np.mean(indata, axis=1)
        else:
            incoming = indata[:, 0]
            
        # Roll the continuous buffer backwards and append new data to the front
        m = len(incoming)
        self.audio_data = np.roll(self.audio_data, -m)
        self.audio_data[-m:] = incoming

    async def listen_forever(self):
        if not self.useMicrophone or sd is None:
            print("(Local_mic) Microphone disabled or sounddevice not installed.")
            while True:
                await asyncio.sleep(1)
                
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=self.audio_callback,
                blocksize=self.chunk_size
            )
            print("(Local_mic) Microphone started correctly.")
            with self.stream:
                while True:
                    await self.listen()
                    # Limit the update loop slightly to match a smooth 60fps
                    await asyncio.sleep(1/60)
        except Exception as e:
            print(f"(Local_mic) Stream Error: {e}")
            while True:
                await asyncio.sleep(1)

    async def listen(self):
        if self.printTimeOfCalculation:
            time_mem = time.time()
            
        # 1. Apply a Hanning window to the raw audio to prevent edge clipping artifacts
        windowed_data = self.audio_data * np.hanning(self.buffer_size)
        
        # 2. Compute the FFT (magnitude)
        fft_result = np.abs(np.fft.rfft(windowed_data))
        
        # 3. Apply Mel Scale weight matrix (Vectorized C-backend math)
        scale = 150.0 / (self.buffer_size / 1024.0)
        mel_bands = np.dot(self.weight_matrix, fft_result) * scale
        
        # 4. Apply Chroma transformation matrix (12 pitch classes)
        if self.chromaValues is not None:
            chroma_bands = np.dot(self.chroma_matrix, fft_result) * scale
            for i in range(12):
                self.chromaValues[i] = chroma_bands[i]
        
        # Map values back directly to shared bandValues array
        for i in range(self.nb_of_fft_band):
            self.bandValues[i] = int(mel_bands[i])
                
        if self.showMicrophoneDetails:
            print(f"(Local_mic) Bands: {list(self.bandValues)}")
            
        if self.printTimeOfCalculation:
            duration = time.time() - time_mem
            print("(Local_mic) temps de calcul = ", duration)
