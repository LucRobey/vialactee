import json
import re

def build_headless():
    with open('BeatTracking_Evaluation_Test.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    code_lines = []
    for c in nb.get('cells', []):
        if c.get('cell_type') == 'code':
            source = "".join(c.get('source', []))
            
            # Avoid matplotlib blocking
            source = source.replace('plt.show()', '# plt.show()')
            source = source.replace('plot_failures(results)', '# plot_failures(results)')
            
            code_lines.append(source)
            code_lines.append('\n\n')
            
    with open('run_eval_headless.py', 'w', encoding='utf-8') as f:
        f.writelines(code_lines)

if __name__ == "__main__":
    build_headless()
