import numpy as np
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
except ImportError:
    sd = None

class Local_Microphone:
    def __init__(self, listener, infos):
        self.listener = listener
        self.showMicrophoneDetails  = infos.get("printMicrophoneDetails", False)
        self.printTimeOfCalculation = infos.get("printTimeOfCalculation", False)
        self.useMicrophone          = infos.get("useMicrophone", True)
        self.simulate_delay         = infos.get("fakeDelay", 5.0)
        self.input_device_id        = infos.get("input_device_id", None)
        
        self.bandValues = listener.fft_band_values
        self.chromaValues = getattr(listener, 'chroma_values', None)
        self.nb_of_fft_band = len(self.bandValues)
        
        # Audio capture settings
        self.sample_rate = 44100
        self.chunk_size = 1024  # Size of the microphone chunk callbacks
        self.buffer_size = 4096 # Size of the sliding FFT window
        self.audio_data = np.zeros(self.buffer_size)
        self.stream = None
        
        # Audio delay buffer for fake X seconds delay
        if self.simulate_delay > 0:
            self.delay_frames = int(self.sample_rate * self.simulate_delay)
            self.delay_buffer = np.zeros((self.delay_frames, 2), dtype=np.float32)
            self.delay_index = 0
        
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

    def audio_callback(self, *args):
        """ This callback is called by sounddevice in a separate C-thread """
        if len(args) == 4:
            indata, frames, time_info, status = args
            outdata = None
        else:
            indata, outdata, frames, time_info, status = args

        if status and self.showMicrophoneDetails:
            logger.debug(f"(Local_mic) status: {status}")
            
        # 0. Simulate Delay Playback
        if outdata is not None and hasattr(self, 'delay_buffer'):
            m = len(indata)
            end_idx = self.delay_index + m
            
            # Map indata to buffer shape safely
            if indata.shape[1] == 1 and self.delay_buffer.shape[1] == 2:
                write_data = np.tile(indata, (1, 2))
            elif indata.shape[1] >= 2 and self.delay_buffer.shape[1] == 2:
                write_data = indata[:, :2]
            else:
                write_data = indata

            if end_idx <= self.delay_frames:
                outdata[:] = self.delay_buffer[self.delay_index:end_idx]
                self.delay_buffer[self.delay_index:end_idx] = write_data
            else:
                chunk1 = self.delay_frames - self.delay_index
                chunk2 = m - chunk1
                outdata[:chunk1] = self.delay_buffer[self.delay_index:]
                outdata[chunk1:] = self.delay_buffer[:chunk2]
                
                self.delay_buffer[self.delay_index:] = write_data[:chunk1]
                self.delay_buffer[:chunk2] = write_data[chunk1:]
                
            self.delay_index = self.delay_index + m
            if self.delay_index >= self.delay_frames:
                if not getattr(self, '_delay_played_trigger', False):
                    logger.info("(Local_mic) 🔊🔥 5-SECOND DELAY REACHED! DELAYED AUDIO NOW PLAYING OUT OF SPEAKERS! 🔥🔊")
                    self._delay_played_trigger = True
                self.delay_index %= self.delay_frames
        elif outdata is not None:
             outdata.fill(0)

        # Dynamic latency tracking
        # time_info contains the PortAudio timestamp when the first sample hit the ADC
        os_latency = max(0.0, time_info.currentTime - time_info.inputBufferAdcTime)
        
        # We lock the time.time() of when the newest sample in this frame was acoustically captured
        self._newest_sample_time = time.time() - os_latency
        
        # If stereo, average out the two channels into mono for FFT pipeline
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
            logger.warning("(Local_mic) Microphone disabled or sounddevice not installed.")
            while True:
                await asyncio.sleep(1)
                
        try:
            if self.simulate_delay > 0:
                self.stream = sd.Stream(
                    device=(self.input_device_id, None),
                    samplerate=self.sample_rate,
                    channels=(1, 2), # Explicitly handle 1 mono mic to 2 output speakers
                    callback=self.audio_callback,
                    blocksize=self.chunk_size
                )
            else:
                self.stream = sd.InputStream(
                    device=self.input_device_id,
                    samplerate=self.sample_rate,
                    channels=1,
                    callback=self.audio_callback,
                    blocksize=self.chunk_size
                )
            logger.info("(Local_mic) Microphone started correctly.")
            with self.stream:
                while True:
                    await self.listen()
                    # Limit the update loop slightly to match a smooth 60fps
                    await asyncio.sleep(1/60)
        except Exception as e:
            logger.error(f"(Local_mic) Stream Error: {e}")
            while True:
                await asyncio.sleep(1)

    async def listen(self):
        if self.printTimeOfCalculation:
            time_mem = time.time()
            
        if hasattr(self, '_newest_sample_time'):
            # The center of the Hanning window is delayed by exactly half the buffer size
            algorithmic_delay = (self.buffer_size / 2.0) / self.sample_rate
            # The async polling drift + OS audio latency
            time_since_newest = time.time() - self._newest_sample_time
            self.listener.dynamic_audio_latency = time_since_newest + algorithmic_delay
            
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
            logger.debug(f"(Local_mic) Bands: {list(self.bandValues)}")
            
        if self.printTimeOfCalculation:
            duration = time.time() - time_mem
            logger.debug(f"(Local_mic) temps de calcul = {duration}")
