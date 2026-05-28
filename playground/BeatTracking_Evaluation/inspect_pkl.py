import pickle
import os

filepath = os.path.join("librosa results", "full_benchmark_results.pkl")
with open(filepath, "rb") as f:
    data = pickle.load(f)

for song, results in list(data.items())[:1]:
    print(f"Keys for {song}: {list(results.keys())}")
