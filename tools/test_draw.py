import matplotlib.pyplot as plt

segments_def = [
    # Strip 0 (segs_1)
    [
        (173, "vertical", 962, 164, "segment_v4", "b"),
        (48, "horizontal", 866, 270, "segment_h32", "r"),
        (48, "horizontal", 866, 442, "segment_h31", "m"),
        (47, "horizontal", 866, 102, "segment_h30", "gray"),
        (173, "vertical", 684, 246, "segment_v3", "c"),
        (91, "horizontal", 684, 132, "segment_h20", "g"),
        (205, "horizontal", 100, 132, "segment_h00", "b")
    ],
    # Strip 1 (segs_2)
    [
        (173, "vertical", 510, 132, "segment_v2", "g"),
        (87, "horizontal", 510, 246, "segment_h11", "orange"),
        (86, "horizontal", 510, 478, "segment_h10", "purple"),
        (173, "vertical", 866, 132, "segment_v1", "y")
    ]
]

fig, ax = plt.subplots()

for strip in segments_def:
    for (size, orientation, start_x, start_y, name, color) in strip:
        x, y = start_x, start_y
        xs, ys = [], []
        for _ in range(size):
            xs.append(x)
            ys.append(y)
            if orientation == "horizontal":
                x += 2
            elif orientation == "vertical":
                y += 2
        ax.plot(xs, ys, color=color, label=name)

plt.gca().invert_yaxis()
plt.savefig('test_layout.png')
