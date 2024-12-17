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

        # Predefined list of starting coordinates
        self.predefined_coordinates = [(16, 0), (245, 292), (1, 429), (32, 431)]  



        self.init_train()

      
    def init_train(self):
        """
        Initializes the train by selecting a random starting position
        from the predefined list and setting its initial coordinates.
        """
        self.train_head_coordinate = self.get_random_coordinate_touching_border()
        self.train_coordinates.append(self.train_head_coordinate)

        # Build the train's initial coordinates
        for _ in range(self.train_length - 1):
            possible_directions = self.get_list_possible_directions(self.train_coordinates[-1])
            # print(f"Current train coordinates: {self.train_coordinates}")
            # print(f"Possible directions from {self.train_coordinates[-1]}: {possible_directions}")
            
            if possible_directions:
                # print(f"Possible directions: {possible_directions}")
                next_coord = random.choice(possible_directions)
                self.train_coordinates.append(next_coord)
            else:
                raise ValueError("Not enough space to initialize the train!")
        print(f"Train head: {self.train_head_coordinate}, Train coordinates: {self.train_coordinates}")

    def get_random_coordinate_touching_border(self):
        """
        Returns a random coordinate from the predefined list.
        """
        if not self.predefined_coordinates:
            raise ValueError("No predefined starting coordinates available.")
        visited = set(self.train_coordinates)
        for _ in range(10):  # Retry limit
            coord = random.choice(self.predefined_coordinates)
            if coord not in visited:
                return coord
        raise ValueError("Failed to find a unique predefined coordinate.")

    def get_list_possible_directions(self, coord):
        """
        Returns a list of valid adjacent cells to the given coordinate.
        """
        x, y = coord
        directions = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
        return [
            (nx, ny)
            for nx, ny in directions
            if 0 <= nx < len(self.matrix) and 0 <= ny < len(self.matrix[0])
            and self.matrix[nx][ny] == 1
            and (nx, ny) not in self.train_coordinates
        ]

    def update_train(self):
        """
        Updates the train's position by moving the head to a new valid coordinate
        or resetting to a new predefined position if no valid moves are available.
        """
        possible_directions = self.get_list_possible_directions(self.train_head_coordinate)
        if possible_directions:
            next_head = random.choice(possible_directions)
            self.train_coordinates.insert(0, next_head)
            self.train_head_coordinate = next_head
            self.train_coordinates.pop()
        else:
            self.reset_train()
        
        # print(f"Train head: {self.train_head_coordinate}, Train coordinates: {self.train_coordinates}")

    def reset_train(self):
        """
        Resets the train to a new predefined position if no valid moves are available.
        """
        self.train_head_coordinate = self.get_random_coordinate_touching_border()
        self.train_coordinates[0] = self.train_head_coordinate

    def update_matrix(self):
        """
        Updates the matrix to reflect the train's current position.
        Only modifies affected cells instead of rebuilding the entire matrix.
        """
        for coord in self.train_coordinates:
            # print(f"Updating train color at {coord}")
            self.matrix_light[coord[0]][coord[1]] = self.train_color

    def update(self):
        """
        Updates the train's state and matrix, then calls the parent class update.
        """
        self.update_train()
        self.update_matrix()
        super().update()
        return self.matrix
