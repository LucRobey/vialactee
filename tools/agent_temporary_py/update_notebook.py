import json

with open('MusicAnalyzer.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Change title
nb['cells'][0]['source'] = ['# 🕒 Delayed Lookahead Analyzer (5s Buffer)\n', '\n', 'This notebook simulates the 5-second `Delayed Buffer` approach, allowing **Non-Causal Magnetic Peak Snapping** and perfect synchronization without causal PLL guessing lag.']

loop_code = """from collections import deque

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

eval_code = """# EVALUATING ALGORITHMIC PERFORMANCE VS GROUND TRUTH
def evaluate_single_stream(alg_stream, true_stream, tolerance=0.150):
    matched_true = set()
    matched_alg = set()
    
    for i, a_beat in enumerate(alg_stream):
        closest_dist = float('inf')
        closest_j = -1
        for j, t_beat in enumerate(true_stream):
            if j in matched_true: continue
            dist = abs(a_beat - t_beat)
            if dist < closest_dist and dist <= tolerance:
                closest_dist = dist
                closest_j = j
                
        if closest_j != -1:
            matched_true.add(closest_j)
            matched_alg.add(i)
            
    hits = len(matched_alg)
    false_positives = len(alg_stream) - hits
    false_negatives = len(true_stream) - hits
    
    precision = hits / len(alg_stream) if len(alg_stream) > 0 else 0
    recall = hits / len(true_stream) if len(true_stream) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return hits, false_positives, false_negatives, precision, recall, f1_score, matched_alg, matched_true

m_hits, m_wrongs, m_misses, m_precision, m_recall, m_f1, m_alg_main, m_true = evaluate_single_stream(alg_beats_array, true_beat_times, TOLERANCE_WINDOW)
s_hits, s_wrongs, s_misses, s_precision, s_recall, s_f1, m_alg_sub, m_true_sub = evaluate_single_stream(alg_sub_beats_array, true_subbeat_times, TOLERANCE_WINDOW)

total_hits = m_hits + s_hits
total_wrongs = m_wrongs + s_wrongs
total_misses = m_misses + s_misses
total_alg = len(alg_beats_array) + len(alg_sub_beats_array)
total_true = len(true_beat_times) + len(true_subbeat_times)

tot_precision = total_hits / total_alg if total_alg > 0 else 0
tot_recall = total_hits / total_true if total_true > 0 else 0
tot_f1 = 2 * (tot_precision * tot_recall) / (tot_precision + tot_recall) if (tot_precision + tot_recall) > 0 else 0

print("============ 📈 EVALUATION REPORT ============")
print(f"Tolerance Window: +/- {int(TOLERANCE_WINDOW*1000)}ms")
print(f"Total True Beats: {len(true_beat_times)} | Total Sub-beats: {len(true_subbeat_times)}")
print(f"Total Algorithmic Beats: {len(alg_beats_array)} | Total Algorithmic Sub-beats: {len(alg_sub_beats_array)}")
print("----------------------------------------------")
print(f"✅ RIGHT (Main Beats): {m_hits} perfectly synced.")
print(f"☑️ RIGHT (Sub-Beats): {s_hits} perfectly synced.")
print(f"❌ WRONG (False Positives): {total_wrongs} extra/ghost commands.")
print(f"👻 MISSED (True commands): {total_misses} true beats slipped through.")
print("----------------------------------------------")
print(f"🎯 Precision: {tot_precision*100:.1f}%")
print(f"🏅 Recall: {tot_recall*100:.1f}%")
print(f"🏆 F1-SCORE (Overall Sync Quality): {tot_f1*100:.1f}%")
print("==============================================")
"""

for i, cell in enumerate(nb['cells']):
    if cell['cell_type']== 'code' and 'mic.pop_chunk' in ''.join(cell['source']):
        nb['cells'][i]['source'] = loop_code.splitlines(True)
    elif cell['cell_type']== 'code' and 'EVALUATION REPORT' in ''.join(cell['source']):
        nb['cells'][i]['source'] = eval_code.splitlines(True)

with open('DelayedMusicAnalyzer.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Created DelayedMusicAnalyzer.ipynb successfully with emojis!")
