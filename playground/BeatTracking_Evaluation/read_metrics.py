import pickle

try:
    with open('full_benchmark_results.pkl', 'rb') as f:
        data = pickle.load(f)
        
    for song, results in data.items():
        metrics = results.get('metrics', {})
        print(f"--- {song} ---")
        for k, v in metrics.items():
            print(f"  {k}: {v}")
except Exception as e:
    print(f"Error: {e}")
