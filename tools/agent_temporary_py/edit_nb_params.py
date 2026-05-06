import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        
        # Change 1: Remove 16th notes from localized_continuous_phase_sweep
        target_16th = '''template_vals[((abs_phi >= 0.22) & (abs_phi <= 0.28))] = 0.3'''
        if target_16th in source:
            source = source.replace(target_16th, '''# template_vals[((abs_phi >= 0.22) & (abs_phi <= 0.28))] = 0.3 # Sub-sub-beats ignored!''')
            
        # Change 2: Divide search_radius by 2 (3.0 -> 1.5)
        target_radius = '''search_radius=3.0,'''
        if target_radius in source:
            source = source.replace(target_radius, '''search_radius=1.5,''')
            
        # Change 3: Protect standalone_phase from impossible jumps, but force realignment
        target_phase_jump = '''standalone_phase += phase_diff * 1.0  # HARD RESET onto the precise sweep'''
        replacement_phase_jump = '''# HARD RESET onto the precise sweep, but ONLY if we maintain temporal sanity
        if abs(phase_diff) < 0.15:
            standalone_phase += phase_diff * 1.0  
        else:
            # We reject the sweep as it likely aligned onto an off-beat / subdivision
            pass'''
        if target_phase_jump in source:
            source = source.replace(target_phase_jump, replacement_phase_jump)

        # Change 4: Increase snapping window and use user's 1.1x multiplier
        # Also clean up the main beat snapping
        target_snap_window = '''window = 3 # +/- 66ms'''
        if target_snap_window in source:
            source = source.replace(target_snap_window, '''window = 5 # +/- 83ms''')

        target_snap_logic = '''if best_idx != window and peak_power > max(2.0, target_power * 1.2):'''
        if target_snap_logic in source:
            source = source.replace(target_snap_logic, '''if best_idx != window and peak_power > max(2.0, target_power * 1.1):''')
            
        # Reconstruct cell source lines
        lines = [line + '\n' for line in source.split('\n')]
        if len(lines) > 0:
            lines[-1] = lines[-1][:-1]
        cell['source'] = lines

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
