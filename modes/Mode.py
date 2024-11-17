import calculations.rgb_hsv as RGB_HSV

class Mode:

    listener = None
    def __init__(self , listener , leds , rgb_list):
        if(self.listener==None):
            self.listener = listener
            
        #rgb_list est la liste donnée au mode
        self.rgb_list = rgb_list
        self.leds     = leds
        
        
        #utils
        self.nb_of_leds = len(rgb_list)
        self.full_white = RGB_HSV.fromHSV_toRGB(0,0,1)
        
    def smooth(self , ratio_new , led_index , new_color):
        old_col=self.leds[led_index]
        mixed_color=((1-ratio_new)*old_col[0]+ratio_new*new_color[0] , (1-ratio_new)*old_col[1]+ratio_new*new_color[1] , (1-ratio_new)*old_col[2]+ratio_new*new_color[2])
        self.rgb_list[led_index]=mixed_color
        
    def smooth_segment(self,ratio_new , start_index , stop_index , new_color):
        for led_index in range(start_index , stop_index+1):
            self.smooth(ratio_new , led_index , new_color)

    def fade_to_black(self , ratio_black):
        for led_index in range(self.nb_of_leds):
            self.smooth( ratio_black , led_index , (0,0,0))
            
    def fade_to_black_led(self , ratio_black , led_index):
        self.smooth( ratio_black , led_index , (0,0,0))
        
    def fade_to_black_segment(self , ratio_black , start_index , stop_index):
        for led_index in range(start_index,stop_index+1):
            self.smooth( ratio_black , led_index , (0,0,0))

    def update(self):
        pass