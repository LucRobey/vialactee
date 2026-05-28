import json
import sys

def dump_code():
    with open('BeatTracking_Evaluation_Test.ipynb', encoding='utf-8') as f:
        nb = json.load(f)
    
    with open('algorithm_code.py', 'w', encoding='utf-8') as out:
        for c in nb.get('cells', []):
            if c.get('cell_type') == 'code':
                source = ''.join(c.get('source', []))
                # Only dump if it looks like the tracker class or simulation function
                if 'class ' in source or 'def ' in source or 'ContinuousHybridTracker' in source:
                    out.write(source)
                    out.write("\n\n" + "="*80 + "\n\n")

if __name__ == "__main__":
    dump_code()
