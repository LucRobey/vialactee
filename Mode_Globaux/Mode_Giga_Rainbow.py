from Mode_Globaux import Mode_Global as Mode_Global
import random

class Mode_Giga_Rainbow(Mode_Global.Mode_Global):
    def __init__(self, matrix_class):
        super().__init__(matrix_class, fusion_type="Priority")
        self.matrix = matrix_class.matrix
        self.matrix_light = matrix_class.matrix_light

    def update(self):   
        self.update_matrix_light()
        super().update()

    def update_matrix_light(self):
        """
        Make the matrix light a rainbow.
        """
        height = len(self.matrix)
        width = len(self.matrix[0]) if height > 0 else 0
        self.matrix_light = [
            [
                self.hue_to_rgb((i + j * width) % 256) for i in range(width)
            ] for j in range(height)
        ]

    def hue_to_rgb(self, hue):
        """
        Convert a hue (0-255) to an RGB triplet.
        """
        hue = float(hue) / 256.0
        r = int(255 * (1 - abs((hue * 6) % 2 - 1)))
        g = int(255 * (1 - abs((hue * 6 - 2) % 2 - 1)))
        b = int(255 * (1 - abs((hue * 6 - 4) % 2 - 1)))
        return (r, g, b)