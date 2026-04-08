from Mode_Globaux  import Matrix_data as Matrix_data
class Matrix:

    def __init__(self):        
        self.matrix       = Matrix_data.Matrix_data().matrix
        self.matrix_light = [[[0, 0, 0] for _ in range(len(row))] for row in self.matrix]
        # print(len(self.matrix),len(self.matrix[0]))
        # print(len(self.matrix_light),len(self.matrix_light[0]))
    def reset_matrix(self):
        self.matrix = Matrix_data().matrix
        self.matrix_light = [[[0, 0, 0] for _ in range(len(row))] for row in self.matrix]

    