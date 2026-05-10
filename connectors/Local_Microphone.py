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
            
        self.listener.process_raw_audio(self.audio_data)
                
        if self.showMicrophoneDetails:
            logger.debug(f"(Local_mic) Bands: {list(self.listener.fft_band_values)}")
            
        if self.printTimeOfCalculation:
            duration = time.time() - time_mem
            logger.debug(f"(Local_mic) temps de calcul = {duration}")
