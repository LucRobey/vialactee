import Mode_Global
import random
class Mode_Tchou_Tchou(Mode_Global.Mode_Global):

    def __init__(self,matrix_class):
        #here matrix modifies the matrix attribute of the parent class Mode_Global which modifies the matrix attribute in Matrix
        super().__init__(matrix_class,fusion_type = "Priority")
        self.train_head_coordinate = None
        self.train_coordinates= []
        self.train_color = (255,255,255)
        self.train_length = 7
        self.matrix = matrix_class.matrix

    def init_train(self):

        #get a random matrix coordinate equal to one
        self.train_head_coordinate = self.get_random_coordinate_touching_border()
        while self.matrix[self.train_head_coordinate[0]][self.train_head_coordinate[1]] != 1:
            self.train_head_coordinate = self.get_random_coordinate()
        
        #get the train coordinates from the head coordinate
        for i in range(self.train_length-1):
            possible_directions = self.get_list_possible_direction(self.train_coordinates[i],self.matrix, self.train_coordinates)
            self.train_coordinates[i+1]= possible_directions[random.randint(0,len(possible_directions)-1)]
            
    def get_list_possible_direction(coord, matrix,train_coordinates):
        #return a list of possible direction for the train
        possible_direction = []
        if coord[0] > 0 and matrix[coord[0]-1][coord[1]] == 1:
            possible_direction.append(coord[0]-1,coord[1])
        if coord[0] < len(matrix)-1 and matrix[coord[0]+1][coord[1]] == 1:
            possible_direction.append(coord[0]+1,coord[1])
        if coord[1] > 0 and matrix[coord[0]][coord[1]-1] == 1:
            possible_direction.append(coord[0],coord[1]-1)
        if coord[1] < len(matrix[0])-1 and matrix[coord[0]][coord[1]+1] == 1:
            possible_direction.append(coord[0],coord[1]+1)
        
        for directions in possible_direction:
            if directions in train_coordinates:
                possible_direction.remove(directions)

        return possible_direction



    def update_train(self):
        #update the head of the train
        possible_directions = self.get_list_possible_direction(self.train_head_coordinate,self.matrix,self.train_coordinates)
        if possible_directions != []:
            self.train_coordinates.insert(0,possible_directions[random.randint(0,len(possible_directions)-1)])
            self.train_head_coordinate = self.train_coordinates[0]
            self.train_coordinates.pop()
        else:
            self.train_coordinates.insert(0,self.get_random_coordinate_touching_border())
            self.train_head_coordinate = self.train_coordinates[0]
            self.train_coordinates.pop()

    def get_random_coordinate_touching_border(self):
        #return a random coordinate touching the border of the matrix
        coord = (0,0)
        while self.matrix[coord[0]][coord[1]] != 1:
            border = random.randint(0,3)
            if border == 0:
                coord = (0,random.randint(0,len(self.matrix[0])-1))
            elif border == 1:
                coord = (len(self.matrix)-1,random.randint(0,len(self.matrix[0])-1))
            elif border == 2:
                coord = (random.randint(0,len(self.matrix)-1),0)
            else:
                coord = (random.randint(0,len(self.matrix)-1),len(self.matrix[0])-1)

        return coord
        
    def update_matrix(self):
        #update the matrix with the train
        for i in self.train_length:
            for coord in self.train_coordinates[i]:
                self.matrix[coord[0]][coord[1]] = self.train_color

    def update(self):
        self.update_train()
        self.update_matrix()
        super().update()
        return self.matrix