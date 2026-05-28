import json

def dump_updated_code():
    with open('BeatTracking_Evaluation_Test.ipynb', encoding='utf-8') as f:
        nb = json.load(f)
    
    with open('run_updated_algorithm.py', 'w', encoding='utf-8') as out:
        for c in nb.get('cells', []):
            if c.get('cell_type') == 'code':
                source = ''.join(c.get('source', []))
                # Only dump functions and classes, skip plotting to avoid GUI hangs
                if 'class ' in source or 'def ' in source or 'import ' in source or 'FakeListener defined' in source:
                    if 'def plot' not in source and 'import matplotlib' not in source:
                        out.write(source)
                        out.write("\n\n")

if __name__ == "__main__":
    dump_updated_code()
