import numpy as np

class Fake_leds:

    def __init__(self , nb_of_leds):
        self.data = []
        for _ in range(nb_of_leds):
            self.data.append([0,0,0])
        self.data = np.array(self.data)

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, value):
        self.data[index] = value

    def __len__(self):
        return len(self.data)

    def append(self, value):
        self.data.append(value)

    def show(self):
        pass
