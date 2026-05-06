import json

def modify():
    with open('ContinuousHybridTracker.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    for cell in nb.get('cells', []):
        if cell.get('cell_type') != 'code':
            continue
            
        source = "".join(cell['source'])
        
        # We need to initialize bass_flux and treble_flux where high_res_flux is initialized.
        if "self.high_res_flux = 0.0" in source and "self.raw_fft_history = None" in source:
            source = source.replace(
                "self.high_res_flux = 0.0",
                "self.bass_flux = 0.0\n        self.treble_flux = 0.0\n        self.high_res_flux = 0.0"
            )
            
            # Reconstruct cell source lines
            lines = []
            parts = source.split('\n')
            for i, part in enumerate(parts):
                if i < len(parts) - 1:
                    lines.append(part + '\n')
                else:
                    lines.append(part)
            cell['source'] = lines

    with open('ContinuousHybridTracker.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    modify()
    print("Notebook modified successfully.")
