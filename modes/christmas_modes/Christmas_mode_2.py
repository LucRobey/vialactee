import modes.Mode as Mode
import modes.christmas_modes.christmas_colors as chtm_colors
import random
import time

class Christmas_mode_2(Mode.Mode):

    sub_segment_size = 40

    delta_time = 1

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)
        
        self.colors = [chtm_colors.red , chtm_colors.blue , chtm_colors.green , chtm_colors.gold]

        self.next_apparition = time.time()


    def update(self): 
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time()  
        #====================================================================================
        # first we fade to black
        self.fade_to_black(0.01)

        if(time.time() > self.next_apparition):
            color = random.choice(self.colors)
            self.lightUp(color)
            self.next_apparition = time.time() + self.delta_time
            if(self.printThisModeDetail):
                print("(CM_2)       On fait apparaitre une couleur")
        
        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM_2) temps pour ",self.name," : ",duration)


    def lightUp(self , color):
        
        # we get a random pos under the size of the sub_segment than we show the led at this position modulo the sub_segment size
        random_pos = random.randint(0,self.sub_segment_size)

        segment_number = 0
        while ( segment_number * self.sub_segment_size + random_pos ) < self.nb_of_leds:
            self.rgb_list[segment_number * self.sub_segment_size + random_pos] = color
            segment_number+=1