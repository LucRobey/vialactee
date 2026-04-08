from Mode_Globaux import Mode_Global as Mode_Global
import random

class Mode_Snow(Mode_Global.Mode_Global):
    def __init__(self, matrix_class):
        super().__init__(matrix_class, fusion_type="Priority")
        self.flakes_density = 0.1
        self.flakes = set()
        self.matrix = matrix_class.matrix
        self.matrix_light = matrix_class.matrix_light
        self.flake_color = (255, 255, 255)

    def update(self):
        if random.random() < self.flakes_density:
            self.init_flake()
        for flake in list(self.flakes):
            self.update_flake(flake)

        self.update_matrix_light()

    def init_flake(self):
        """
        Initializes the snowflake by randomly selecting coordinates
        at the top and setting their initial color to white.
        """
        top_row = 0
        for j in range(len(self.matrix[0])):
            if random.random() < self.flakes_density:
                self.flakes.add((j, top_row))

    def destroy_flake(self, flake):
        """
        when the flake reaches the bottom of the matrix, it is destroyed.
        """
        self.flakes.discard(flake)

    def update_flake(self, flake):
        """
        make the flake fall down by one unit.
        """
        x, y = flake
        y += 1
        if y >= len(self.matrix):
            self.destroy_flake(flake)
        else:
            self.flakes.discard(flake)
            self.flakes.add((x, y))

    def update_matrix_light(self):
        """
        Updates the matrix_light with the current flake positions.
        """
        self.matrix_light = [[[0, 0, 0] for _ in range(len(self.matrix[0]))] for _ in range(len(self.matrix))]
        for x, y in self.flakes:
            self.matrix_light[y][x] = self.flake_color
        super().update()