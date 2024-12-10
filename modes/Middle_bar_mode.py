import modes.Mode as Mode
import random
import calculations.rgb_hsv as RGB_HSV
import time

class Middle_bar_mode(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)

        #we need to know if we have a middle or two
        if (self.nb_of_leds%2 == 0):
            self.middle_index = [int(self.nb_of_leds/2) , int(self.nb_of_leds/2) +1]
        else:
             self.middle_index = [int((self.nb_of_leds+1)/2),int((self.nb_of_leds+1)/2)]
        
        #the maximum size of a side bar
        self.max_size = int((self.nb_of_leds+1)/2)

        #the actual size of a size bar (middle included)
        self.size = 0

        #we randomly choose a asserved_band to listen to and we choose the color accordingly
        self.band_to_listen = random.randint(0,self.listener.nb_of_fft_band-1)
        hue = float(self.band_to_listen) / (self.listener.nb_of_fft_band - 1)
        self.color = RGB_HSV.fromHSV_toRGB(hue,1.0,1.0)



    def update(self):
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time() 
        #==================================================================================== 
        """
        calculate
        """
        #We listen to the chosen band
        new_size = self.listener.asserved_fft_band[self.band_to_listen] * self.max_size

        #could put some sensi here
        self.size = int((self.size + new_size)/2)

        #if the new value is superior to the max_size (wich should be impossible) we bring it back to a max_size
        if (self.size > self.max_size):
            self.size = self.max_size

        """
        show
        """
        #we color/decolor the leds starting from the middle(s)
        self.smooth_segment(0.5 , int(self.middle_index[0]-(self.size-1)) , int(self.middle_index[1]+(self.size-1)) , self.color)
        self.fade_to_black_segment(0.5 ,                      0             , int(self.middle_index[0]-(self.size-1)))
        self.fade_to_black_segment(0.5 , int(self.middle_index[1]+(self.size-1)) ,        self.nb_of_leds-1          )
            
        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM) temps pour ",self.name," : ",duration)
