import json

def fix_notebook_indent():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    for cell in nb.get('cells', []):
        if cell.get('cell_type') != 'code':
            continue
            
        source = "".join(cell['source'])
        
        # Exact string replacements to fix bad indents left by earlier script injections
        replacements = [
            ('    # Scale bass/treble to fit on the BPM axis for visualization\n', '# Scale bass/treble to fit on the BPM axis for visualization\n'),
            ('    plt.plot(time_arr, bass_arr * 10 + 60, color="blue", linewidth=1.0, alpha=0.6, label="Bass Flux (scaled)")\n', 'plt.plot(time_arr, bass_arr * 10 + 60, color="blue", linewidth=1.0, alpha=0.6, label="Bass Flux (scaled)")\n'),
            ('    plt.plot(time_arr, treble_arr * 10 + 60, color="orange", linewidth=1.0, alpha=0.6, label="Treble Flux (scaled)")\n', 'plt.plot(time_arr, treble_arr * 10 + 60, color="orange", linewidth=1.0, alpha=0.6, label="Treble Flux (scaled)")\n')
        ]
        
        for old, new in replacements:
            source = source.replace(old, new)
            
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
    fix_notebook_indent()
    print("Notebook indent logic fixed.")
