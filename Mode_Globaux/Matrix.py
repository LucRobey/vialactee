from Mode_Globaux  import Matrix_data as Matrix_data
class Matrix:

    def __init__(self):
        
        self.matrix = Matrix_data.Matrix_data().matrix

    def reset_matrix(self):
        self.matrix = Matrix_data().matrix

    