from Mode_Globaux  import Matrix_data as Matrix_data
class Matrix:

    def __init__(self):        
        self.matrix       = Matrix_data.Matrix_data().matrix
        self.matrix_light = [[[0, 0, 0] for _ in range(len(row))] for row in self.matrix]
    def reset_matrix(self):
        self.matrix = Matrix_data().matrix
        self.matrix_light = [[[0, 0, 0] for _ in range(len(row))] for row in self.matrix]

    