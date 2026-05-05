import sys
sys.path.append('.')
from geometry.Matrix_data import Matrix_data
import numpy as np

m = np.array(Matrix_data().matrix)

rows, cols = m.shape
print(f"Matrix shape: {rows}x{cols}")

for name, row, col_start, col_end in [
    ("H00", 16, 0, 204),
    ("H20", 16, 292, 382),
    ("H11", 73, 205, 291),
    ("H10", 189, 205, 290),
    ("H30", 1, 383, 429),
    ("H32", 85, 383, 430),
    ("H31", 171, 383, 430)
]:
    c_s = col_start
    c_e = col_end
    print(f"{name}: row {row}, col {c_s} to {c_e}, len {c_e-c_s+1}. Matrix has 1s: {np.all(m[row, c_s:c_e+1] == 1)}")

for name, col, row_start, row_end in [
    ("V2", 205, 16, 188),
    ("V3", 292, 73, 245),
    ("V1", 383, 1, 188),
    ("V4", 431, 32, 204)
]:
    r_s = row_start
    r_e = row_end
    print(f"{name}: col {col}, row {r_s} to {r_e}, len {r_e-r_s+1}. Matrix has 1s: {np.all(m[r_s:r_e+1, col] == 1)}")
