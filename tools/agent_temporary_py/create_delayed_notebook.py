import json
import os

with open('MusicAnalyzer.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Change title
nb['cells'][0]['source'] = ['# 🕒 Delayed Lookahead Analyzer (5s Buffer)\n', '\n', 'This notebook simulates the 5-second `Delayed Buffer` approach, allowing **Non-Causal Magnetic Peak Snapping** and perfect synchronization without causal PLL guessing lag.']

loop_code = """
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
        window = 9 # +/- 150ms 
        target = window
        
        # --- SYMMETRIC LOOKAHEAD PEAK SNAPPING (MAIN BEATS) ---
        if future_queue[target].get('is_beat', False) and not future_queue[target].get('main_snapped', False):
            best_dist = 999
            best_idx = -1
            
            # Scan +/- window around the target
            for i in range(0, 2 * window + 1):
                f = future_queue[i]
                has_bass_peak = f['band_peak'][0] > 0 or f['band_peak'][1] > 0
                if has_bass_peak:
                    dist = abs(i - target)
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = i
                        
            if best_idx != -1:
                future_queue[target]['is_beat'] = False
                future_queue[best_idx]['is_beat'] = True
                future_queue[best_idx]['main_snapped'] = True
            else:
                future_queue[target]['main_snapped'] = True

        # --- SYMMETRIC LOOKAHEAD PEAK SNAPPING (SUB-BEATS) ---
        if future_queue[target].get('is_sub_beat', False) and not future_queue[target].get('sub_snapped', False):
            best_dist = 999
            best_idx = -1
            
            # Scan +/- window around the target
            for i in range(0, 2 * window + 1):
                f = future_queue[i]
                # Subbeats can snap to mid/high transients too
                has_peak = any(val > 0 for val in f['band_peak'])
                if has_peak:
                    dist = abs(i - target)
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = i
                        
            if best_idx != -1:
                future_queue[target]['is_sub_beat'] = False
                future_queue[best_idx]['is_sub_beat'] = True
                future_queue[best_idx]['sub_snapped'] = True
            else:
                future_queue[target]['sub_snapped'] = True

        # Safe to pop now, as the frame at index 0 was evaluated 9 frames ago!
        present = future_queue.popleft()
        
        if present.get('is_beat', False):
            algorithmic_beats.append(playhead_time)
            
        if present.get('is_sub_beat', False):
            algorithmic_sub_beats.append(playhead_time)
            
        history_time.append(playhead_time)
        history_bpm.append(present['bpm'])
        history_binary_trust.append(present['binary_trust'])
        history_bpm_trust.append(present['bpm_trust'])
        history_bass_flux.append(present['bass_flux'])
        
        playhead_time += TIME_PER_FRAME
        
    audio_time += TIME_PER_FRAME
    frame += 1
    
    if frame % 1800 == 0:
        print(f"Processed audio time {audio_time:.1f}s...")

ListenerModule.time.time = time.time # Restore time

# Empty the remaining queue to finish the song
while future_queue:
    present = future_queue.popleft()
    if present.get('is_beat', False):
        algorithmic_beats.append(playhead_time)
    if present.get('is_sub_beat', False):
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

print("Created DelayedMusicAnalyzer.ipynb successfully!")
