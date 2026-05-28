import json
import re

def update_notebook():
    with open('BeatTracking_Evaluation_Test.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for c in nb.get('cells', []):
        if c.get('cell_type') != 'code':
            continue
            
        source = "".join(c['source'])
        
        # 1. evaluate_specific_bpms
        if 'def evaluate_specific_bpms' in source:
            source = source.replace("best_bpm_pearson = candidate_bpms[0]", 
                                  "best_bpm_pearson = candidate_bpms[0]\n    best_phase_idx_pearson = 0")
                                  
            source = source.replace("weighted_score = np.max(p_scores_pearson) * human_prior",
                                    "max_idx = np.argmax(p_scores_pearson)\n        weighted_score = p_scores_pearson[max_idx] * human_prior")
            
            source = source.replace("best_bpm_pearson = bpm_val",
                                    "best_bpm_pearson = bpm_val\n            best_phase_idx_pearson = max_idx")
                                    
            source = source.replace("return best_bpm_pearson, best_score_pearson",
                                    "return best_bpm_pearson, best_score_pearson, best_phase_idx_pearson")
                                    
            c['source'] = [line + '\n' for line in source.split('\n')]
            # Remove trailing newline from last element if needed, but jupyter handles it.
            c['source'][-1] = c['source'][-1].rstrip('\n')
            
        # 2. class_based_phase_sweep
        if 'def class_based_phase_sweep' in source:
            source = source.replace("best_overall_class = class_evals[0] % 1.0",
                                    "best_overall_class = class_evals[0] % 1.0\n    best_phase_idx = 0")
                                    
            source = source.replace("tau_max_score = np.max(p_scores) * human_prior",
                                    "max_idx = np.argmax(p_scores)\n        tau_max_score = p_scores[max_idx] * human_prior")
                                    
            source = source.replace("best_overall_class = c",
                                    "best_overall_class = c\n            best_phase_idx = max_idx")
                                    
            source = source.replace("return best_overall_class, best_overall_score",
                                    "return best_overall_class, best_overall_score, best_phase_idx")
                                    
            c['source'] = [line + '\n' for line in source.split('\n')]
            c['source'][-1] = c['source'][-1].rstrip('\n')
            
        # 3. run_simulation_with_beats
        if 'def run_simulation_with_beats' in source:
            source = source.replace("best_class, _ = class_based_phase_sweep",
                                    "best_class, _, scout_phase_idx = class_based_phase_sweep")
                                    
            source = source.replace("bpm_pearson_raw, score_pearson = evaluate_specific_bpms",
                                    "bpm_pearson_raw, score_pearson, judge_phase_idx = evaluate_specific_bpms")
                                    
            # Insert the phase snapping logic when locked
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
            source = source.replace("listener.bpm = bpm_pearson_raw\n                time_since_good_confidence = 0.0", 
                                    snapping_code.strip('\n'))
                                    
            c['source'] = [line + '\n' for line in source.split('\n')]
            c['source'][-1] = c['source'][-1].rstrip('\n')

    with open('BeatTracking_Evaluation_Test.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == "__main__":
    update_notebook()
    print("Notebook updated.")
