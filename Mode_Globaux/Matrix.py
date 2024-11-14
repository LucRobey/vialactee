import Matrix_data
class Matrix:

    def __init__(self):
        
        self.matrix = Matrix_data().matrix

    def update(self, new_matrix):
        self.matrix = new_matrix

    