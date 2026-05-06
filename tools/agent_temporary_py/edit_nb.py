import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        
        target = '''        # --- SYMMETRIC LOOKAHEAD PEAK SNAPPING (MAIN BEATS) ---
        if future_queue[target].get('is_beat', False) and not future_queue[target].get('main_snapped', False):
            start_index = 0
            end_index = 2 * window + 1
            
            best_idx = start_index + np.argmax(flux_array[start_index:end_index])
            peak_power = flux_array[best_idx]
            
            # Snap safely onto the exact acoustic peak! (Lowered threshold avoids misses)
            local_mean = np.mean(flux_array[start_index:end_index])
            if peak_power > max(2.0, (local_mean * 1.5)*np.abs(best_idx-window)/window):
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
            
            local_mean = np.mean(flux_array[start_index:end_index])
            if peak_power > max(2.0, local_mean * 1.5):
                future_queue[target]['is_sub_beat'] = False
                future_queue[best_idx]['is_sub_beat'] = True
                future_queue[best_idx]['sub_snapped'] = True
            else:
                future_queue[target]['sub_snapped'] = True'''
                
        replacement = '''        # --- SYMMETRIC LOOKAHEAD PEAK SNAPPING (MAIN BEATS) ---
        if future_queue[target].get('is_beat', False) and not future_queue[target].get('main_snapped', False):
            start_index = 0
            end_index = 2 * window + 1
            
            best_idx = start_index + np.argmax(flux_array[start_index:end_index])
            peak_power = flux_array[best_idx]
            target_power = flux_array[window]
            
            # We want to encourage staying on the predicted beat (window).
            # So a new peak must be noticeably larger than the predicted beat's flux to warrant shifting the beat.
            if best_idx != window and peak_power > max(2.0, target_power * 1.2):
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
            
            if best_idx != window and peak_power > max(2.0, target_power * 1.2):
                future_queue[target]['is_sub_beat'] = False
                future_queue[best_idx]['is_sub_beat'] = True
                future_queue[best_idx]['sub_snapped'] = True
            else:
                future_queue[target]['sub_snapped'] = True'''
        
        if target in source:
            source = source.replace(target, replacement)
            # Reconstruct cell source lines
            lines = [line + '\n' for line in source.split('\n')]
            # Remove trailing newline from last line to match standard notebook format
            if len(lines) > 0:
                lines[-1] = lines[-1][:-1]
            cell['source'] = lines

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
