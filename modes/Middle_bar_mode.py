import modes.Mode as Mode
import random
import calculations.rgb_hsv as RGB_HSV

class Middle_bar_mode(Mode.Mode):

    def __init__(self , listener , leds , rgb_list):
        super().__init__(listener , leds , rgb_list)

        #we need to know if we have a middle or two
        if (self.nb_of_leds%2 == 0):
            self.hasAMiddle = False
            self.middle_index = [int(self.nb_of_leds/2) , int(self.nb_of_leds/2 +1)]
        else:
             self.hasAMiddle = True
             self.middle_index = [int((self.nb_of_leds+1)/2)]
        
        #the maximum size of a side bar
        self.max_size = int((self.nb_of_leds+1)/2)

        #the actual size of a size bar (middle included)
        self.size = 0

        #we randomly choose a asserved_band to listen to and we choose the color accordingly
        self.band_to_listen = random.randint(0,len(self.listener.asserv_segm_fft))
        hue = float(self.band_to_listen) / (len(self.listener.asserv_segm_fft) - 1)
        self.color = RGB_HSV.fromHSV_toRGB(hue,1.0,1.0)



    def update(self):
        """
        calculate
        """
        #We listen to the chosen band
        new_size = self.listener.asserv_segm_fft[self.band_to_listen] * self.max_size

        #could put some sensi here
        self.size = int((self.size + new_size)/2)

        #if the new value is superior to the max_size (wich should be impossible) we bring it back to a max_size
        if (self.size > self.max_size):
            self.size = self.max_size

        """
        show
        """
        print(self.middle_index)
        #we color/decolor the leds starting from the middle(s)
        if(self.hasAMiddle):
            self.smooth_segment(0.5 , self.middle_index[0]-(self.size-1) , self.middle_index[0]+(self.size-1) , self.color)
            self.fade_to_black_segment(0.5 , self.middle_index[0]+self.size , self.nb_of_leds-1              )
            self.fade_to_black_segment(0.5 ,             0                  , self.middle_index[0]-self.size )
        else:
            self.smooth_segment(0.5 , self.middle_index[0]-(self.size-1) , self.middle_index[1]+(self.size-1) , self.color)
            self.fade_to_black_segment(0.5 , self.middle_index[1]+self.size , self.nb_of_leds-1              )
            self.fade_to_black_segment(0.5 ,             0                  , self.middle_index[0]-self.size )
            