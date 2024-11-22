from Mode_Globaux import Segments_Locations as Segments_Locations
class Matrix_General : 
    def __init__(self, mode_Global):
        self.mode = mode_Global
        self.matrix_class = mode_Global.matrix_class
        self.fusion_type = mode_Global.fusion_type
        self.matrix = self.matrix_class.matrix
        self.segments_location = Segments_Locations.Segments_Locations()
        self.segment_values = None
        self.set_segments()

    def change_mode(self, new_mode):
        self.matrix_class.reset_matrix()
        self.mode = new_mode
        self.fusion_type = new_mode.fusion_type

    def update(self):
        self.mode.update()
        self.matrix = self.mode.matrix
        self.fusion_type = self.mode.fusion_type
        self.set_segments()

    
    def set_segments(self):
        #return the coordinates and the values of the segments
        self.segment_values = [
            [self.matrix[x][y] for x, y in segment]
            for segment in self.segments_location.segment_coords
        ]

    def get_segments(self):
        return self.segments_location.segment_coords  , self.segment_values