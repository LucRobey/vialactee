import json

def patch_inertia():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    for cell in nb.get('cells', []):
        if cell.get('cell_type') != 'code':
            continue
            
        source = "".join(cell['source'])
        
        changed = False
        
        # We look for the phase_inertia assignment
        old_inertia = "phase_inertia = np.exp(-0.5 * (norm_dist / 0.35)**2)"
        new_inertia = "phase_inertia = np.exp(-0.5 * (norm_dist / 0.20)**2)"
        
        old_blend = "p_scores = p_scores * (0.5 + 0.5 * phase_inertia)"
        new_blend = "p_scores = p_scores * (0.1 + 0.9 * phase_inertia)"
        
        if old_inertia in source:
            source = source.replace(old_inertia, new_inertia)
            changed = True
            
        if old_blend in source:
            source = source.replace(old_blend, new_blend)
            changed = True
            
        if changed:
            lines = []
            parts = source.split('\n')
            for i, part in enumerate(parts):
                if i < len(parts) - 1:
                    lines.append(part + '\n')
                else:
                    if part:
                        lines.append(part)
            cell['source'] = lines

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    patch_inertia()
    print("Inertia logic patched.")
