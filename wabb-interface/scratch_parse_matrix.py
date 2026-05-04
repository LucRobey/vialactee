import sys
sys.path.append('c:/Users/Users/Desktop/vialactée/vialactee')
from Mode_Globaux.Matrix_data import Matrix_data

m = Matrix_data().matrix
height = len(m)
width = len(m[0])
visited = set()
components = []

for y in range(height):
    for x in range(width):
        if m[y][x] == 1 and (x, y) not in visited:
            q = [(x, y)]
            visited.add((x, y))
            min_x, max_x, min_y, max_y = x, x, y, y
            while q:
                cx, cy = q.pop(0)
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < width and 0 <= ny < height and m[ny][nx] == 1 and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        q.append((nx, ny))
            components.append({'x': min_x, 'y': min_y, 'w': max_x - min_x + 1, 'h': max_y - min_y + 1})

for i, c in enumerate(components):
    print(f"Component {i+1}: {c}")

if len(components) == 1:
    print('Only 1 component found (overlapping)')
