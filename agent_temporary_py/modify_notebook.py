import json
import numpy as np

with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        if "SYMMETRIC LOOKAHEAD PEAK SNAPPING" in source:
            new_source = source.replace(
"""        if future_queue[target].get('is_beat', False) and not future_queue[target].get('main_snapped', False):
            start_index = 0
            end_index = 2 * window + 1
            
            best_idx = start_index + np.argmax(flux_array[start_index:end_index])
            peak_power = flux_array[best_idx]
            target_power = flux_array[window]
            
            # We want to encourage staying on the predicted beat (window).
            # So a new peak must be noticeably larger than the predicted beat's flux to warrant shifting the beat.
            if best_idx != window and peak_power > max(2.0, target_power * 1.1):
                future_queue[target]['is_beat'] = False
                future_queue[best_idx]['is_beat'] = True
                future_queue[best_idx]['main_snapped'] = True
            else:
                future_queue[target]['main_snapped'] = True

        # --- SYMMETRIC LOOKAHEAD PEAK SNAPPING (SUB-BEATS) ---
        if future_queue[target].get('is_sub_beat', False) and not future_queue[target].get('sub_snapped', False):
            start_index = 0
            end_index = 2 * window + 1
            best_idx = start_index + np.argmax(flux_array[start_index:end_index])
            peak_power = flux_array[best_idx]
            target_power = flux_array[window]
            
            if best_idx != window and peak_power > max(2.0, target_power * 1.1):
                future_queue[target]['is_sub_beat'] = False
                future_queue[best_idx]['is_sub_beat'] = True
                future_queue[best_idx]['sub_snapped'] = True
            else:
                future_queue[target]['sub_snapped'] = True""",
"""        if future_queue[target].get('is_beat', False) and not future_queue[target].get('main_snapped', False):
            start_index = 0
            end_index = 2 * window + 1
            
            best_idx = start_index + np.argmax(flux_array[start_index:end_index])
            peak_power = flux_array[best_idx]
            target_power = flux_array[window]
            local_mean = np.mean(flux_array[start_index:end_index])
            
            # Distance penalty: The further the peak is from the predicted beat (window), 
            # the higher the threshold multiplier to snap to it.
            dist_penalty = 1.0 + 0.5 * (np.abs(best_idx - window) / window)
            
            if best_idx != window and peak_power > max(2.0, (local_mean * 1.5) * dist_penalty):
                future_queue[target]['is_beat'] = False
                future_queue[best_idx]['is_beat'] = True
                future_queue[best_idx]['main_snapped'] = True
            else:
                future_queue[target]['main_snapped'] = True

        # --- SYMMETRIC LOOKAHEAD PEAK SNAPPING (SUB-BEATS) ---
        if future_queue[target].get('is_sub_beat', False) and not future_queue[target].get('sub_snapped', False):
            start_index = 0
            end_index = 2 * window + 1
            
            best_idx = start_index + np.argmax(flux_array[start_index:end_index])
            peak_power = flux_array[best_idx]
            target_power = flux_array[window]
            local_mean = np.mean(flux_array[start_index:end_index])
            
            dist_penalty = 1.0 + 0.5 * (np.abs(best_idx - window) / window)
            
            if best_idx != window and peak_power > max(2.0, (local_mean * 1.5) * dist_penalty):
                future_queue[target]['is_sub_beat'] = False
                future_queue[best_idx]['is_sub_beat'] = True
                future_queue[best_idx]['sub_snapped'] = True
            else:
                future_queue[target]['sub_snapped'] = True""")

            if new_source != source:
                # Add line endings back properly for nbformat
                lines = new_source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + [lines[-1]] if lines else []
                print("Replaced content successfully.")

with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
