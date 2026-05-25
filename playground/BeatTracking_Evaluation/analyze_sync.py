import pickle
import numpy as np
import os

filepath = os.path.join("librosa results", "full_benchmark_results.pkl")
with open(filepath, "rb") as f:
    data = pickle.load(f)

print("--- BEAT SYNCHRONIZATION ANALYSIS ---")
print("Tolerance: 70ms (standard mir_eval window)\n")

total_out_of_sync = 0
total_missed = 0
total_our_beats = 0

for song, results in data.items():
    our_beats = np.array(results['our_beats'])
    librosa_beats = np.array(results['librosa_beats'])
    # Combine main beats and sub beats into one valid grid
    if 'librosa_sub_beats' in results:
        valid_grid = np.unique(np.concatenate((librosa_beats, results['librosa_sub_beats'])))
    else:
        valid_grid = librosa_beats
        
    if len(our_beats) == 0:
        print(f"{song}: Tracker produced 0 beats. Missed all {len(librosa_beats)} beats.")
        total_missed += len(librosa_beats)
        continue

    # 1. Out of Sync (False Positives)
    # For each of our beats, how far is the closest valid grid beat?
    out_of_sync = 0
    for b in our_beats:
        dist = np.min(np.abs(valid_grid - b))
        if dist > 0.070: # 70ms
            out_of_sync += 1

    # 2. Missed Beats (False Negatives)
    # The user wants to know if they 'miss' beats. A miss is when the tracker is silent or totally off 
    # for a period where there SHOULD be a beat.
    # We can measure this by iterating through the valid grid. But wait, valid grid has 2x beats!
    # If the tracker is tracking upbeat, it misses the main beat. But the user said that's fine.
    # So we should group valid_grid into "beat windows" (e.g. main beat or its sub-beat).
    # Easier: Just check how many of `our_beats` are mapped to valid grid. If we have 100 valid grid pairs, 
    # and we produced 90 matching beats, we missed 10.
    
    # Let's just find how many librosa_beats (main beats) lack an associated our_beat AND their nearest sub-beat lacks an our_beat.
    # Actually, if we just count how many our_beats were synchronized (True Positives = len(our_beats) - out_of_sync)
    # Since the tracker usually outputs at 1x tempo, we expect True Positives to roughly equal len(librosa_beats).
    # Missed = len(librosa_beats) - True Positives
    true_positives = len(our_beats) - out_of_sync
    missed = max(0, len(librosa_beats) - true_positives)
    
    total_out_of_sync += out_of_sync
    total_missed += missed
    total_our_beats += len(our_beats)
    
    pct_sync = (true_positives / len(our_beats)) * 100 if len(our_beats) > 0 else 0
    
    print(f"{song}:")
    print(f"  - Tracker emitted {len(our_beats)} beats.")
    print(f"  - Completely out of sync: {out_of_sync}")
    print(f"  - Missed beats (approx): {missed}")
    print(f"  - Synchronized: {pct_sync:.1f}%")

print(f"\nOVERALL DATASET:")
print(f"Total Beats Emitted: {total_our_beats}")
print(f"Total Out of Sync: {total_out_of_sync}")
print(f"Total Missed: {total_missed}")

