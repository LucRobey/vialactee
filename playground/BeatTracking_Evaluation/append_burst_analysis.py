import os

with open('run_eval_headless.py', 'r', encoding='utf-8') as f:
    source = f.read()

burst_analysis_code = """
print("\\n=== TEMPORAL BURST ANALYSIS OF BEAT TRACKING ERRORS ===\\n")

for song, res in results.items():
    our_beats = np.array(res['our_beats'])
    librosa_beats = np.array(res['librosa_beats'])
    if 'librosa_sub_beats' in res:
        valid_grid = np.unique(np.concatenate((librosa_beats, res['librosa_sub_beats'])))
    else:
        valid_grid = librosa_beats
        
    if len(our_beats) == 0:
        print(f"{song}: 0 beats emitted.")
        continue
        
    # Analyze Off-Rhythm Bursts (False Positives)
    is_off_rhythm = []
    for b in our_beats:
        dist = np.min(np.abs(valid_grid - b))
        is_off_rhythm.append(dist > 0.070)
        
    off_rhythm_bursts = []
    current_burst = 0
    for flag in is_off_rhythm:
        if flag:
            current_burst += 1
        else:
            if current_burst > 0:
                off_rhythm_bursts.append(current_burst)
            current_burst = 0
    if current_burst > 0:
        off_rhythm_bursts.append(current_burst)
        
    # Analyze Missed Beat Bursts (False Negatives)
    is_missed = []
    for b in librosa_beats:
        if len(our_beats) > 0:
            dist = np.min(np.abs(our_beats - b))
            is_missed.append(dist > 0.070)
        else:
            is_missed.append(True)
            
    missed_bursts = []
    current_burst = 0
    for flag in is_missed:
        if flag:
            current_burst += 1
        else:
            if current_burst > 0:
                missed_bursts.append(current_burst)
            current_burst = 0
    if current_burst > 0:
        missed_bursts.append(current_burst)
        
    print(f"--- {song} ---")
    if off_rhythm_bursts:
        print(f"  Off-Rhythm Bursts:")
        print(f"    - Max consecutive off-rhythm beats: {max(off_rhythm_bursts)}")
        print(f"    - Median consecutive off-rhythm beats: {np.median(off_rhythm_bursts)}")
        print(f"    - Total off-rhythm bursts: {len(off_rhythm_bursts)}")
    else:
        print("  No Off-Rhythm beats.")
        
    if missed_bursts:
        print(f"  Missed Beat Bursts:")
        print(f"    - Max consecutive missed beats: {max(missed_bursts)}")
        print(f"    - Median consecutive missed beats: {np.median(missed_bursts)}")
        print(f"    - Total missed bursts: {len(missed_bursts)}")
    else:
        print("  No Missed beats.")
    print()
"""

with open('run_eval_headless_bursts.py', 'w', encoding='utf-8') as f:
    f.write(source + "\n" + burst_analysis_code)
