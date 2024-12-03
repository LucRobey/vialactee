class Segments_Locations:
    def __init__(self):
        self.len_h00 = 205
        self.len_h10 = 87
        self.len_h11 = 86
        self.len_h20 = 91
        self.len_h30 = 47
        self.len_h31 = 48
        self.len_h32 = 48

        self.len_v1 = 173
        self.len_v2 = 173
        self.len_v3 = 173
        self.len_v4 = 173

        self.coord_y_h31 = self.len_v1*2//5 + 16
        self.coord_y_h32 = self.len_v1*9//10 + 16

        self.offset_h30_v4 = 16

        self.segment_h00 = [[coord_x, self.offset_h30_v4] for coord_x in range(self.len_h00)]
        self.segment_h10 = [[coord_x + self.len_h00, self.len_v1//3 + self.offset_h30_v4] for coord_x in range(self.len_h10)]
        self.segment_h11 = [[coord_x + self.len_h00, self.len_v1 + self.offset_h30_v4] for coord_x in range(self.len_h11)]
        self.segment_h20 = [[coord_x + self.len_h10 + self.len_h00, self.offset_h30_v4] for coord_x in range(self.len_h20)]
        self.segment_h30 = [[coord_x + self.len_h00 + self.len_h10 + self.len_h20, 1] for coord_x in range(self.len_h30)]
        self.segment_h31 = [[coord_x + self.len_h00 + self.len_h10 + self.len_h20, self.coord_y_h31] for coord_x in range(self.len_h31)]
        self.segment_h32 = [[coord_x + self.len_h00 + self.len_h10 + self.len_h20, self.coord_y_h32] for coord_x in range(self.len_h32)]

        self.segment_v1 = [[self.len_h00, coord_y + self.offset_h30_v4] for coord_y in range(self.len_v1)]
        self.segment_v2 = [[self.len_h00 + self.len_h10, coord_y + self.offset_h30_v4 + self.len_v1//3] for coord_y in range(self.len_v2)]
        self.segment_v3 = [[self.len_h00 + self.len_h10 + self.len_h20, coord_y + self.offset_h30_v4] for coord_y in range(self.len_v3)]
        self.segment_v4 = [[self.len_h00 + self.len_h10 + self.len_h20 + self.len_h31, coord_y + self.offset_h30_v4*2] for coord_y in range(self.len_v4)]

        self.segment_coords = [self.segment_h00, self.segment_h10, self.segment_h11, self.segment_h20, self.segment_h30, self.segment_h31, self.segment_h32, self.segment_v1, self.segment_v2, self.segment_v3, self.segment_v4]
        self.segment_names = ["h00", "h10", "h11", "h20", "h30", "h31", "h32", "v1", "v2", "v3", "v4"]
    