import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV

class Rainbow_mode(Mode.Mode):
    
    def __init__(self , listener , leds , rgb_list):
        super().__init__(listener , leds , rgb_list)
        
        #Used to calculate the hue and the intensity of each pixel
        self.delta_margin=float(self.nb_of_leds)/(self.listener.nb_of_segm_fft-1)
        self.nb_of_fft_segment = len(self.listener.asserv_segm_fft)

    


    def smooth(self, led_index,new_color):
        old_col=self.leds[led_index]
        mixed_color=((old_col[0]+new_color[0])/2,(old_col[1]+new_color[1])/2,(old_col[2]+new_color[2])/2)
        self.rgb_list[led_index]=mixed_color
        
    def update(self):
        for led_index in range(self.nb_of_leds):
            hue = led_index/self.nb_of_leds
            
            low_margin = int(led_index / self.delta_margin)
            high_margin= low_margin+1
            #print(led_index / self.delta_margin)
            position_coef = 1 -(led_index / self.delta_margin - low_margin)
            intensity = position_coef * self.listener.asserv_segm_fft[low_margin] + (1-position_coef) * self.listener.asserv_segm_fft[high_margin]
        
            #print("low_margin = " , low_margin)
            #print("coef = ", position_coef)
            #print("intensity = " , intensity)
            color = RGB_HSV.fromHSV_toRGB(hue,1.0,intensity)
            #print(color)
            self.smooth(led_index,color)
            
        #for index in range(self.listener.nb_of_segm_fft):
        #    color=self.fromHSV_toRGB(float(index)/self.nb_of_fft_segment,1.0,self.listener.asserv_segm_fft[index] * self.listener.power)
        #    for k in range(4):
        #        self.smooth(4*index+k,color)
                #self.leds[4*index+k]=(2*self.leds[4*index+k]+color)/3
                    