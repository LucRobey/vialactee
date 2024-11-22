import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import random

class Selecteur_alcool(Mode.Mode):

    def __init__(self , listener , leds , rgb_list):
        super().__init__(listener , leds , rgb_list)

        self.speed = 1
        self.pos = int(self.nb_of_leds/2)
        self.activate = False
        self.nb_of_rebounds = 0
        
        self.hue = random.uniform(0,1)
        self.color = RGB_HSV.fromHSV_toRGB(self.hue,1.0,1.0)

        #speed at wich the white dot comes down
        self.white_speed = float((self.nb_of_leds)/20)

    
    def update(self):
        if
        
    def activate(self):
        self.speed = 1
        self.pos = int(self.nb_of_leds/2)
        self.activate = True
        self.total_time = random.randint(6,15)
        