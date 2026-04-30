import sounddevice as sd
import numpy as np
import time

def callback(indata, outdata, frames, time, status):
    if status:
        print(status)
    outdata[:] = indata

try:
    print("Testing loopback for 5 seconds...")
    with sd.Stream(channels=2, callback=callback):
        time.sleep(5)
    print("Test finished.")
except Exception as e:
    print("Exception:", e)
