import json
import os

with open('MusicAnalyzer.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Change title
nb['cells'][0]['source'] = ['# 🕒 Delayed Lookahead Analyzer (5s Buffer)\n', '\n', 'This notebook simulates the 5-second `Delayed Buffer` approach, allowing **Non-Causal Peak Snapping** and perfect synchronization without causal PLL guessing lag.']

loop_code = """
infos = {"printAsservmentDetails": False, "useMicrophone": True ,
        "momentum_mult": 3,
        "base_pull":0.005}

SIMULATED_FPS = 60.0
TIME_PER_FRAME = 1.0 / SIMULATED_FPS

class MockTime:
    def __init__(self):
        self.current_time = 0.0
    def time(self):
        return self.current_time

mock_timer = MockTime()
import core.Listener as ListenerModule
ListenerModule.time.time = mock_timer.time

listener = ListenerModule.Listener(infos)

mic = Simulated_Microphone(AUDIO_FILE, listener.fft_band_values, infos)
listener.hasBeenSilenceCalibrated = True
listener.hasBeenBBCalibrated = True
listener.calibrate_silence = lambda: None
listener.calibrate_bb = lambda: None

from collections import deque

lookahead_frames = int(5.0 * SIMULATED_FPS)
future_queue = deque()

algorithmic_beats = []
algorithmic_sub_beats = []

history_time = []
history_bpm = []
history_binary_trust = []
history_bpm_trust = []
history_bass_flux = []

print("🚀 Starting Lookahead Analysis (5s Buffer)...")
start_real_world_time = time.time()
CHUNK_SIZE_FOR_60FPS = int(44100 / 60.0)

last_logged_beat_count = getattr(listener, 'beat_count', 0)
last_logged_beat_phase = getattr(listener, 'beat_phase', 0.0)
frame = 0

audio_time = 0.0
playhead_time = 0.0

cooldown = 0
cooldown_sub = 0

while mic.pop_chunk(CHUNK_SIZE_FOR_60FPS):
    mic.calculate_fft()
    listener.update()
    
    is_beat = False
    is_sub_beat = False
    
    current_beat_count = getattr(listener, 'beat_count', 0)
    if current_beat_count > last_logged_beat_count:
        is_beat = True
        last_logged_beat_count = current_beat_count
        
    current_phase = getattr(listener, 'beat_phase', 0.0)
    if last_logged_beat_phase < 0.5 and current_phase >= 0.5:
        is_sub_beat = True
    last_logged_beat_phase = current_phase
    
    # Store the causal output into the future_queue (we are 5 seconds ahead of output)
    future_queue.append({
        'time': audio_time,
        'bpm': listener.bpm,
        'binary_trust': getattr(listener, 'binary_trust', 0.0),
        'bpm_trust': getattr(listener, 'bpm_trust', 0.0),
        'bass_flux': listener.band_flux[0] + listener.band_flux[1],
        'is_beat': is_beat,
        'is_sub_beat': is_sub_beat,
        'band_peak': listener.band_peak.copy()
    })
    
    # The output playhead pops the oldest frame when the buffer has 5 seconds of footage
    if len(future_queue) >= lookahead_frames:
        present = future_queue.popleft()
        
        trigger_main = present['is_beat']
        trigger_sub = present['is_sub_beat']
        
        if cooldown > 0: cooldown -= 1
        if cooldown_sub > 0: cooldown_sub -= 1
        
        # --- LOOKAHEAD PEAK SNAPPING ---
        correction_window = 9
        
        has_bass_peak = present['band_peak'][0] > 0 or present['band_peak'][1] > 0
        
        if has_bass_peak and cooldown == 0:
            beat_upcoming = any(f['is_beat'] for f in list(future_queue)[:correction_window])
            
            if beat_upcoming:
                trigger_main = True
                cooldown = correction_window * 2
                
                for f in list(future_queue)[:correction_window]:
                    if f['is_beat']:
                        f['is_beat'] = False
                        break
        
        if trigger_main and cooldown == 0:
            algorithmic_beats.append(playhead_time)
            
        if trigger_sub and cooldown_sub == 0:
            algorithmic_sub_beats.append(playhead_time)
            
        history_time.append(playhead_time)
        history_bpm.append(present['bpm'])
        history_binary_trust.append(present['binary_trust'])
        history_bpm_trust.append(present['bpm_trust'])
        history_bass_flux.append(present['bass_flux'])
        
        playhead_time += TIME_PER_FRAME
        
    audio_time += TIME_PER_FRAME
    mock_timer.current_time += TIME_PER_FRAME
    frame += 1
    
    if frame % 1800 == 0:
        print(f"Processed audio time {audio_time:.1f}s...")

ListenerModule.time.time = time.time # Restore time

# Empty the remaining queue to finish the song
while future_queue:
    present = future_queue.popleft()
    if present['is_beat']:
        algorithmic_beats.append(playhead_time)
    if present['is_sub_beat']:
        algorithmic_sub_beats.append(playhead_time)
        
    history_time.append(playhead_time)
    history_bpm.append(present['bpm'])
    history_binary_trust.append(present['binary_trust'])
    history_bpm_trust.append(present['bpm_trust'])
    history_bass_flux.append(present['bass_flux'])
    playhead_time += TIME_PER_FRAME

alg_beats_array = np.array(algorithmic_beats)
alg_sub_beats_array = np.array(algorithmic_sub_beats)
print(f"✅ Finished! Extracted {len(alg_beats_array)} Lookahead algorithmic beats and {len(alg_sub_beats_array)} sub-beats.")
"""

for i, cell in enumerate(nb['cells']):
    if cell['cell_type']== 'code' and 'mic.pop_chunk' in ''.join(cell['source']):
        nb['cells'][i]['source'] = loop_code

with open('DelayedMusicAnalyzer.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Fixed DelayedMusicAnalyzer.ipynb successfully!")
