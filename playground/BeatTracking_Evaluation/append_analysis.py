import os

with open('run_eval_headless.py', 'r', encoding='utf-8') as f:
    source = f.read()

# remove the pickle dump and replace it
source = source.replace("with open(os.path.join('librosa results', 'full_benchmark_results.pkl'), 'wb') as f:\n    pickle.dump(results, f)\nprint(\"Finished Headless Evaluation!\")", "")

analysis_code = """
print("\\n--- BEAT SYNCHRONIZATION ANALYSIS ---")
print("Tolerance: 70ms (standard mir_eval window)\\n")

total_out_of_sync = 0
total_missed = 0
total_our_beats = 0

for song, res in results.items():
    our_beats = np.array(res['our_beats'])
    librosa_beats = np.array(res['librosa_beats'])
    if 'librosa_sub_beats' in res:
        valid_grid = np.unique(np.concatenate((librosa_beats, res['librosa_sub_beats'])))
    else:
        valid_grid = librosa_beats
        
    if len(our_beats) == 0:
        print(f"{song}: Tracker produced 0 beats. Missed all {len(librosa_beats)} beats.")
        total_missed += len(librosa_beats)
        continue

    out_of_sync = 0
    for b in our_beats:
        dist = np.min(np.abs(valid_grid - b))
        if dist > 0.070:
            out_of_sync += 1

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

print(f"\\nOVERALL DATASET:")
print(f"Total Beats Emitted: {total_our_beats}")
print(f"Total Out of Sync: {total_out_of_sync}")
print(f"Total Missed: {total_missed}")
"""

with open('run_eval_headless.py', 'w', encoding='utf-8') as f:
    f.write(source + "\n" + analysis_code)
