import sounddevice as sd
import numpy as np
import time

sample_rate = 44100
delay_seconds = 5.0
delay_frames = int(sample_rate * delay_seconds)
delay_buffer = np.zeros((delay_frames, 2), dtype=np.float32)
delay_index = 0

def callback(indata, outdata, frames, time_info, status):
    global delay_index, delay_buffer
    if status:
        print(status)
    m = len(indata)
    end_idx = delay_index + m
    
    if indata.shape[1] == 1:
        write_data = np.tile(indata, (1, 2))
    elif indata.shape[1] >= 2:
        write_data = indata[:, :2]
    else:
        write_data = indata

    if end_idx <= delay_frames:
        outdata[:] = delay_buffer[delay_index:end_idx]
        delay_buffer[delay_index:end_idx] = write_data
    else:
        chunk1 = delay_frames - delay_index
        chunk2 = m - chunk1
        outdata[:chunk1] = delay_buffer[delay_index:]
        outdata[chunk1:] = delay_buffer[:chunk2]
        
        delay_buffer[delay_index:] = write_data[:chunk1]
        delay_buffer[:chunk2] = write_data[chunk1:]
        
    delay_index = (delay_index + m) % delay_frames

print("Running 7s test (5s silence, then loopback)")
try:
    with sd.Stream(channels=2, callback=callback, samplerate=sample_rate):
        time.sleep(7)
    print("Done")
except Exception as e:
    print(e)
