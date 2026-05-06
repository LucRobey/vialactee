import sounddevice as sd
import numpy as np

valid_devs = []
for i, d in enumerate(sd.query_devices()):
    if d['max_input_channels'] > 0:
        try:
            # Quick block rec for 0.5 sec
            rec = sd.rec(int(0.5 * 44100), device=i, samplerate=44100, channels=1, blocking=True)
            max_vol = np.max(np.abs(rec))
            valid_devs.append((i, d['name'], max_vol))
        except Exception as e:
            try:
                rec = sd.rec(int(0.5 * 48000), device=i, samplerate=48000, channels=1, blocking=True)
                max_vol = np.max(np.abs(rec))
                valid_devs.append((i, d['name'] + " (48kHz)", max_vol))
            except Exception as e2:
                valid_devs.append((i, d['name'], "Error"))

for v in valid_devs:
    print(v)
