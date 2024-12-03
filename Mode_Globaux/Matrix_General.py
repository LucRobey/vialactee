from Mode_Globaux import Segments_Locations as Segments_Locations

class Matrix_General:
    def __init__(self, mode_Global):
        self.mode = mode_Global
        self.matrix_class = mode_Global.matrix_class
        self.fusion_type = mode_Global.fusion_type
        self.matrix = self.matrix_class.matrix
        self.matrix_light = self.matrix_class.matrix_light
        self.segments_location = Segments_Locations.Segments_Locations()
        self.segment_values = [None] * len(self.segments_location.segment_coords)  # Preallocate
        self.init_segments()

    def change_mode(self, new_mode):
        """
        Changes the mode and resets the matrix for the new mode.
        """
        self.matrix_class.reset_matrix()
        self.mode = new_mode
        self.fusion_type = new_mode.fusion_type

    def update(self):
        """
        Updates the current mode and all associated data structures.
        """
        self.mode.update()
        self.matrix = self.mode.matrix
        self.matrix_light = self.mode.matrix_light
        self.fusion_type = self.mode.fusion_type
        self.set_segments()

    def set_segments(self):
        """
        Updates segment values based on current `matrix_light`.
        """
        for i, segment in enumerate(self.segments_location.segment_coords):
            # Use a single list comprehension to efficiently extract values
            self.segment_values[i] = [
                self.matrix_light[coord[1]][coord[0]] for coord in segment
            ]

    def init_segments(self):
        """
        Initializes segment values with their current states in `matrix_light`.
        """
        self.set_segments()  # Direct reuse of set_segments for initialization

    def get_segments(self):
        """
        Returns a dictionary mapping segment names to their corresponding values.
        """
        return dict(zip(self.segments_location.segment_names, self.segment_values))
