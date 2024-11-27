from Mode_Globaux import Mode_Global as Mode_Global
import random

class Mode_Tchou_Tchou(Mode_Global.Mode_Global):
    def __init__(self, matrix_class):
        """
        Initializes the Mode_Tchou_Tchou instance with the given matrix_class.
        Sets up the train's attributes and initializes the train on the matrix.
        """
        super().__init__(matrix_class, fusion_type="Priority")
        self.train_head_coordinate = None
        self.train_coordinates = []
        self.train_color = (255, 255, 255)
        self.train_length = 7
        self.matrix = matrix_class.matrix
        self.matrix_light = matrix_class.matrix_light
        self.init_train()

    def init_train(self):
        """
        Initializes the train by selecting a random starting position
        along the border and setting its initial coordinates.
        """
        self.train_head_coordinate = self.get_random_coordinate_touching_border()
        self.train_coordinates.append(self.train_head_coordinate)

        # Build the train's initial coordinates
        for _ in range(self.train_length - 1):
            possible_directions = self.get_list_possible_direction(
                self.train_coordinates[-1], self.matrix
            )
            if possible_directions:
                next_coord = random.choice(possible_directions)
                self.train_coordinates.append(next_coord)
            else:
                raise ValueError("Not enough space to initialize the train!")

    def get_list_possible_direction(self, coord, matrix):
        directions = [
            (coord[0] - 1, coord[1]),  # Up
            (coord[0] + 1, coord[1]),  # Down
            (coord[0], coord[1] - 1),  # Left
            (coord[0], coord[1] + 1)   # Right
        ]
        return [
            (x, y) for x, y in directions
            if 0 <= x < len(matrix) and 0 <= y < len(matrix[0])
            and matrix[x][y] == 1 and (x, y) not in self.train_coordinates
        ]


    def update_train(self):
        """
        Updates the train's position by moving the head to a new valid coordinate
        or resetting to a new border position if no valid moves are available.
        """
        possible_directions = self.get_list_possible_direction(
            self.train_head_coordinate, self.matrix
        )
        print(possible_directions)
  
        if possible_directions:
            next_head = random.choice(possible_directions)
            self.train_coordinates.insert(0, next_head)
            self.train_head_coordinate = next_head
            self.train_coordinates.pop()
        else:
            # Reset train head if stuck
            self.train_head_coordinate = self.get_random_coordinate_touching_border()
            self.train_coordinates.insert(0, self.train_head_coordinate)
            self.train_coordinates.pop()

    def get_random_coordinate_touching_border(self):
        """
        Returns a random valid coordinate touching the border of the matrix
        that has only one possible direction (a dead end).
        """
        valid_borders = [
            (0, y) for y in range(len(self.matrix[0])) if self.matrix[0][y] == 1
        ] + [
            (len(self.matrix) - 1, y) for y in range(len(self.matrix[0])) if self.matrix[-1][y] == 1
        ] + [
            (x, 0) for x in range(len(self.matrix)) if self.matrix[x][0] == 1
        ] + [
            (x, len(self.matrix[0]) - 1) for x in range(len(self.matrix)) if self.matrix[x][-1] == 1
        ]
       
        if not valid_borders:
            raise ValueError("Matrix contains no valid border coordinates.")
        
        dead_end_borders = [
            coord for coord in valid_borders
            if len(self.get_list_possible_direction(coord, self.matrix, )) == 1
        ]
        
        if not dead_end_borders:
            print("No dead-end border found, defaulting to a random border.")
            return random.choice(valid_borders)

        # Avoid choosing a coordinate already in the train
        visited = set(self.train_coordinates)
        for _ in range(100):  # Retry limit to prevent infinite loops
            coordinate = random.choice(dead_end_borders)
            if coordinate not in visited:
                return coordinate
        
        raise ValueError("Failed to find a unique dead-end border coordinate.")

    def update_matrix(self):
        """
        Updates the matrix to reflect the train's current position.
        """
        for coord in self.train_coordinates:
            self.matrix_light[coord[0]][coord[1]] = self.train_color

    def update(self):
        """
        Updates the train's state and matrix, then calls the parent class update.
        """
        self.update_train()
        self.update_matrix()
        super().update()
        return self.matrix
