import sys
sys.path.append('.')
from Mode_Globaux.Matrix_data import Matrix_data
import numpy as np

m = np.array(Matrix_data().matrix)

h_segments = []
v_segments = []

rows, cols = m.shape
for r in range(rows):
    c = 0
    while c < cols:
        if m[r, c] == 1:
            start_c = c
            while c < cols and m[r, c] == 1:
                c += 1
            length = c - start_c
            if length > 1:
                h_segments.append((length, r, start_c))
        else:
            c += 1

for c in range(cols):
    r = 0
    while r < rows:
        if m[r, c] == 1:
            start_r = r
            while r < rows and m[r, c] == 1:
                r += 1
            length = r - start_r
            if length > 1:
                v_segments.append((length, start_r, c))
        else:
            r += 1

print("Horizontal segments (length, row, start_col):")
for s in h_segments:
    print(s)

print("\nVertical segments (length, start_row, col):")
for s in v_segments:
    print(s)
