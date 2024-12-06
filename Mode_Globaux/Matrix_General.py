from Mode_Globaux import Segments_Locations as Segments_Locations
class Matrix_General : 
    def __init__(self, mode_Global):
        self.mode = mode_Global
        self.matrix_class = mode_Global.matrix_class
        self.fusion_type = mode_Global.fusion_type
        self.matrix = self.matrix_class.matrix
        self.matrix_light = self.matrix_class.matrix_light
        self.segments_location = Segments_Locations.Segments_Locations()
        self.segment_values = []
        self.init_segments()
        self.set_segments()

    def change_mode(self, new_mode):
        self.matrix_class.reset_matrix()
        self.mode = new_mode
        self.fusion_type = new_mode.fusion_type

    def update(self):
        self.mode.update()
        self.matrix = self.mode.matrix
        self.matrix_light = self.mode.matrix_light
        self.fusion_type = self.mode.fusion_type
        self.set_segments()
        

    
    def set_segments(self):
        #return the coordinates and the values of the segments
        

        for index_segment in range(len(self.segments_location.segment_coords)):
            new_segment = []
            for index in range(len(self.segments_location.segment_coords[index_segment])):
                segment = self.segments_location.segment_coords[index_segment]
                new_segment.append(self.matrix_light[segment[index][1]][segment[index][0]])
            self.segment_values[index_segment] = new_segment
            
    def init_segments(self):
    

        for index_segment in range(len(self.segments_location.segment_coords)):
            new_segment = []
            for index in range(len(self.segments_location.segment_coords[index_segment])):
                segment = self.segments_location.segment_coords[index_segment]
                new_segment.append(self.matrix_light[segment[index][1]][segment[index][0]])
            self.segment_values.append(new_segment)
            
        

    def get_segments(self):
        dictionary = {} 
        for i in range(len(self.segments_location.segment_names)):
            dictionary[self.segments_location.segment_names[i]] = self.segment_values[i]
        return dict(dictionary)