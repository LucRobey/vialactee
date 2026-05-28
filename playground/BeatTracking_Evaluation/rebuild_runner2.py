import re

def fix_indentation():
    with open('run_eval_headless.py', 'r', encoding='utf-8') as f:
        source = f.read()

    # Find the problematic block and replace it correctly
    # The error says "line 498: unexpected indent"
    # We can just run a python script to fix the indentation by dedenting the snapping code back 16 spaces where it was added.
    
    # Let's just rebuild from clean again, but fix the replace string!
    with open('algorithm_code.py', 'r', encoding='utf-8') as f:
        source_clean = f.read()

    source_clean = re.sub(r'={80}', '', source_clean)
    
    source_clean = source_clean.replace("best_bpm_pearson = candidate_bpms[0]\n", 
                          "best_bpm_pearson = candidate_bpms[0]\n    best_phase_idx_pearson = 0\n")
                          
    source_clean = source_clean.replace("weighted_score = np.max(p_scores_pearson) * human_prior",
                            "max_idx = np.argmax(p_scores_pearson)\n        weighted_score = p_scores_pearson[max_idx] * human_prior")
    
    source_clean = source_clean.replace("best_bpm_pearson = bpm_val\n",
                            "best_bpm_pearson = bpm_val\n            best_phase_idx_pearson = max_idx\n")
                            
    source_clean = source_clean.replace("return best_bpm_pearson, best_score_pearson\n",
                            "return best_bpm_pearson, best_score_pearson, best_phase_idx_pearson\n")

    source_clean = source_clean.replace("best_overall_class = class_evals[0] % 1.0\n",
                            "best_overall_class = class_evals[0] % 1.0\n    best_phase_idx = 0\n")
                            
    source_clean = source_clean.replace("tau_max_score = np.max(p_scores) * human_prior",
                            "max_idx = np.argmax(p_scores)\n        tau_max_score = p_scores[max_idx] * human_prior")
                            
    source_clean = source_clean.replace("best_overall_class = c\n",
                            "best_overall_class = c\n            best_phase_idx = max_idx\n")
                            
    source_clean = source_clean.replace("return best_overall_class, best_overall_score\n",
                            "return best_overall_class, best_overall_score, best_phase_idx\n")

    source_clean = source_clean.replace("best_class, _ = class_based_phase_sweep",
                            "best_class, _, scout_phase_idx = class_based_phase_sweep")
                            
    source_clean = source_clean.replace("bpm_pearson_raw, score_pearson = evaluate_specific_bpms",
                            "bpm_pearson_raw, score_pearson, judge_phase_idx = evaluate_specific_bpms")
                            
    snapping_code = """
                listener.bpm = bpm_pearson_raw
                time_since_good_confidence = 0.0
                
                # Phase Snapping Bug Fix
                tau_val = 60.0 * 60.0 / listener.bpm
                target_phase = (judge_phase_idx % tau_val) / tau_val
                phase_err = (target_phase - phase + 0.5) % 1.0 - 0.5
                phase += 0.20 * phase_err  # Proportional snap
                phase = phase % 1.0
"""
    search_str = "                listener.bpm = bpm_pearson_raw\n                time_since_good_confidence = 0.0"
    source_clean = source_clean.replace(search_str, snapping_code.strip('\n'))
                            
    source_clean = source_clean.replace("plot_failures(results)", "# plot_failures(results)")
    source_clean = source_clean.replace("plot_beats_comparison", "# plot_beats_comparison")
    
    eval_call = """
import os
import json
import librosa
import pickle
root        = '../../assets/musics/mp3_files/'
DB_PATH     = os.path.join(root, 'bpm_database.json')
with open(DB_PATH, 'r', encoding='utf-8') as _f:
    _bpm_db = json.load(_f)

TEST_SONGS = [
    'Palladium', 'Pumped Up Kicks', 'Nobody Rules the Streets',
    'Another One Bites The Dust - Remastered 2011', "Stayin' Alive - From _Saturday Night Fever_ Soundtrack",
    'Boogie Wonderland', 'Roxanne - Remastered 2003', 'September', '01-Plastic-People',
    "Djon maya maï (feat. Victor Démé)", "Feeling Good", "Money For Nothing_1"
]

SONGS      = [(name, _bpm_db[name]['bpm']) for name in TEST_SONGS if name in _bpm_db]
song_files = [root + name + '.mp3' for name, _ in SONGS]
librosa_dir = os.path.join(root, 'librosa')
os.makedirs(librosa_dir, exist_ok=True)

y_list = []
for f in song_files:
    basename  = os.path.basename(f)
    save_path = os.path.join(librosa_dir, f'{basename}.npz')
    data = np.load(save_path, allow_pickle=True)
    y_list.append(data['y'])

results = evaluate_all_songs(song_files, y_list)
with open(os.path.join('librosa results', 'full_benchmark_results.pkl'), 'wb') as f:
    pickle.dump(results, f)
print("Finished Headless Evaluation!")
"""
    source_clean += eval_call
    
    with open('run_eval_headless.py', 'w', encoding='utf-8') as f:
        f.write(source_clean)

if __name__ == "__main__":
    fix_indentation()
