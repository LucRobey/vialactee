import numpy as np
import asyncio
import time
import logging
import threading

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
except ImportError:
    sd = None

class Local_Microphone:
    MAX_TICKS_PER_CALL = 6    # analyzer ticks made in one go when the task comes late (0.1 s of audio)
    MAX_BACKLOG_TICKS = 12    # further behind than this, the missed audio is skipped instead of replayed

    def __init__(self, listener, infos):
        self.listener = listener
        self.useMicrophone          = infos.get("useMicrophone", True)
        self.simulate_delay         = infos.get("fakeDelay", 5.0)
        self.input_device_id        = infos.get("input_device_id", None)
        self.output_device_id       = infos.get("output_device_id", None)
        
        # Audio capture settings
        self.sample_rate = 44100
        self.chunk_size = 1024  # Size of the microphone chunk callbacks
        self.buffer_size = 4096 # Size of the sliding FFT window
        # The analyzer counts time in ticks of 1/60 s. It is advanced here, one tick per 735 samples of audio
        # received (as connectors/Local_AudioFile.py does), not by the display loop, which runs at another rate.
        self.hop_samples = int(round(self.sample_rate / 60.0))
        self.ring_size = 4 * self.buffer_size  # audio kept, so a task that comes late can still cut the windows it missed
        self.audio_data = np.zeros(self.ring_size)
        self.audio_lock = threading.Lock()
        self._audio_write_pos = 0
        self._total_written = 0      # samples received since the stream started
        self._processed = 0          # sample position of the last analyzer tick
        self._windows = np.zeros((self.MAX_TICKS_PER_CALL, self.buffer_size))
        self._window_ends = [0] * self.MAX_TICKS_PER_CALL
        self._newest_sample_time = None
        self.stream = None

        self.listener.audio_stream_state = "disabled" if (not self.useMicrophone or sd is None) else "starting"
        self.listener.audio_stream_error = None
        self.listener.last_audio_callback_time = None
        
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

        if status:
            logger.debug(f"(Local_mic) status: {status}")

        self.listener.last_audio_callback_time = time.time()
            
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
                    logger.info("(Local_mic) 5-SECOND DELAY REACHED! DELAYED AUDIO NOW PLAYING OUT OF SPEAKERS!")
                    self._delay_played_trigger = True
                self.delay_index %= self.delay_frames
        elif outdata is not None:
             outdata.fill(0)

        # Dynamic latency tracking
        # time_info contains the PortAudio timestamp when the first sample hit the ADC
        os_latency = max(0.0, time_info.currentTime - time_info.inputBufferAdcTime)
        
        # If stereo, average out the two channels into mono for FFT pipeline
        if indata.shape[1] > 1:
            incoming = np.mean(indata, axis=1)
        else:
            incoming = indata[:, 0]
            
        # Write incoming data into circular buffer (zero allocation)
        m = len(incoming)
        with self.audio_lock:
            pos = self._audio_write_pos
            end = pos + m
            if end <= self.ring_size:
                self.audio_data[pos:end] = incoming
            else:
                chunk1 = self.ring_size - pos
                self.audio_data[pos:] = incoming[:chunk1]
                self.audio_data[:m - chunk1] = incoming[chunk1:]
            self._audio_write_pos = end % self.ring_size
            self._total_written += m
            self._newest_sample_time = time.time() - os_latency

    async def listen_forever(self):
        if not self.useMicrophone or sd is None:
            self.listener.audio_stream_state = "disabled"
            logger.warning("(Local_mic) Microphone disabled or sounddevice not installed.")
            while True:
                await asyncio.sleep(1)
                
        retry_delay = 1
        while True:
            try:
                self.listener.audio_stream_state = "starting"
                # Dynamically determine input channels (1 or 2) based on device capabilities
                in_channels = 1
                if self.input_device_id is not None and sd is not None:
                    try:
                        dev_info = sd.query_devices(self.input_device_id)
                        in_channels = min(2, max(1, int(dev_info.get("max_input_channels", 1))))
                    except Exception:
                        in_channels = 1
                elif sd is not None:
                    try:
                        default_in = sd.default.device[0]
                        if default_in is not None and default_in >= 0:
                            dev_info = sd.query_devices(default_in)
                            in_channels = min(2, max(1, int(dev_info.get("max_input_channels", 1))))
                    except Exception:
                        in_channels = 1

                if self.simulate_delay > 0:
                    self.stream = sd.Stream(
                        device=(self.input_device_id, self.output_device_id),
                        samplerate=self.sample_rate,
                        channels=(in_channels, 2), # Explicitly handle 1 mono / 2 stereo in to 2 output speakers
                        callback=self.audio_callback,
                        blocksize=self.chunk_size
                    )
                else:
                    self.stream = sd.InputStream(
                        device=self.input_device_id,
                        samplerate=self.sample_rate,
                        channels=in_channels,
                        callback=self.audio_callback,
                        blocksize=self.chunk_size
                    )
                self.listener.audio_stream_state = "running"
                self.listener.audio_stream_error = None
                # From here the analyzer is ticked by the audio (step_analyzer); Mode_master must not tick it too.
                self.listener.is_externally_clocked = True
                logger.info("(Local_mic) Microphone started correctly.")
                with self.stream:
                    retry_delay = 1
                    while True:
                        if not self.stream.active:
                            self.listener.audio_stream_state = "disconnected"
                            self.listener.is_externally_clocked = False
                            logger.warning("(Local_mic) Audio stream became inactive (device disconnected?)")
                            break
                        await self.listen()
                        # Come back often enough to never be more than a tick or two behind the audio
                        await asyncio.sleep(1/60)
            except asyncio.CancelledError:
                self.listener.audio_stream_state = "stopped"
                self.listener.is_externally_clocked = False
                logger.info("(Local_mic) Audio stream task cancelled.")
                raise
            except Exception as e:
                self.listener.is_externally_clocked = False
                self.listener.audio_stream_state = "error"
                self.listener.audio_stream_error = str(e)
                logger.error(f"(Local_mic) Stream Error: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(60, retry_delay * 2)

    def _copy_window(self, end: int, out: np.ndarray) -> None:
        """Copy the buffer_size samples ending at sample position `end` into `out` (zeros before the stream started)."""
        start = end - self.buffer_size
        if start < 0:
            out[:-end if end > 0 else None].fill(0.0)
            if end > 0:
                out[-end:] = self.audio_data[:end]
            return
        a = start % self.ring_size
        if a + self.buffer_size <= self.ring_size:
            out[:] = self.audio_data[a:a + self.buffer_size]
        else:
            first = self.ring_size - a
            out[:first] = self.audio_data[a:]
            out[first:] = self.audio_data[:self.buffer_size - first]

    def step_analyzer(self) -> int:
        """
        Advance the analyzer by the audio received: one tick (spectrum + listener.update at 1/60 s) per
        hop_samples of new audio. Returns the number of ticks made.

        The analyzer counts time in ticks of 1/60 s, so it must get exactly 60 per second of music whatever the
        pace of this task or of the display loop. A task that comes late makes several ticks at once; one that
        comes very late skips the audio it missed.
        """
        hop = self.hop_samples
        with self.audio_lock:
            total = self._total_written
            newest_sample_time = self._newest_sample_time
            if newest_sample_time is None:
                return 0
            if (total - self._processed) // hop > self.MAX_BACKLOG_TICKS:
                self._processed = total - 2 * hop
            ticks = min(self.MAX_TICKS_PER_CALL, (total - self._processed) // hop)
            for k in range(ticks):
                self._processed += hop
                self._window_ends[k] = self._processed
                self._copy_window(self._processed, self._windows[k])

        if ticks == 0:
            return 0
        # Age of the centre of each window: time since the newest sample was captured, plus the samples
        # received after the window's end, plus half the Hanning window.
        age_of_newest = time.time() - newest_sample_time
        half_window = (self.buffer_size / 2.0) / self.sample_rate
        for k in range(ticks):
            behind = (total - self._window_ends[k]) / self.sample_rate
            self.listener.dynamic_audio_latency = age_of_newest + behind + half_window
            self.listener.process_raw_audio(self._windows[k])
            self.listener.update(fixed_dt=1.0 / 60.0)
        return ticks

    async def listen(self):
        self.step_analyzer()
        logger.debug(f"(Local_mic) Bands: {list(self.listener.fft_band_values)}")
