from Mode_Globaux import Mode_Global as Mode_Global
import random

class Mode_France(Mode_Global.Mode_Global):
    def __init__(self, matrix_class):
        super().__init__(matrix_class, fusion_type="Priority")
        self.matrix = matrix_class.matrix
        self.matrix_light = matrix_class.matrix_light
        self.blue = (0, 0, 255)
        self.white = (255, 255, 255)
        self.red = (255, 0, 0)
        self.updated = False
    def update(self):
        if(not self.updated):
            self.update_matrix_light()
            self.updated = True
        
        super().update()
        

    def update_matrix_light(self):
        for i in range(len(self.matrix)):
            for j in range(len(self.matrix[i])):
                if i < len(self.matrix) // 3:
                    self.matrix_light[i][j] = self.blue
                elif i < 2 * len(self.matrix) // 3:
                    self.matrix_light[i][j] = self.white
                else:
                    self.matrix_light[i][j] = self.red