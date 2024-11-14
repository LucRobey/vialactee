class Mode:

    listener = None
    def __init__(self , listener , leds , rgb_list):
        if(self.listener==None):
            self.listener = listener
            
        self.rgb_list = rgb_list
        self.leds     = leds
        
        self.nb_of_leds = len(rgb_list)

    def update(self):
        pass