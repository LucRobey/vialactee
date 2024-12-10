import modes.Mode as Mode
import modes.christmas_modes.christmas_colors as chtm_colors
import time

class Christmas_mode_1(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)
        
        self.invasion_time = 5
        self.size_of_conquest = 9       #impair
        self.invader = chtm_colors.red
        self.victim = chtm_colors.green
        self.new_invasion = True
        self.start_invasion_time = time.time()


    def update(self): 
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time()  
        #====================================================================================

        if(self.new_invasion):
            self.fill(self.victim)
            self.new_invasion = False

        time_coef = float(time.time() - self.start_invasion_time)/self.invasion_time
        if(self.printThisModeDetail):
            print("(CM_1)       time_coef = ",time_coef)

        if( time_coef>=1 ):
            self.new_invasion = True
            self.start_invasion_time = time.time()
            if(self.invader == chtm_colors.red):
                self.invader = chtm_colors.green
                self.victim = chtm_colors.red
            else:
                self.invader = chtm_colors.red
                self.victim = chtm_colors.green
            if(self.printThisModeDetail):
                print("(CM_1)       Nouvelle invasion!")
                
        else:
            nb_of_invader = int(self.size_of_conquest*time_coef)
            if(self.printThisModeDetail):
                print("(CM_1)       nb_of_invader = ",nb_of_invader)

            country_index = 0
            while self.size_of_conquest * country_index < self.nb_of_leds:
                for invader_index in range(0 , nb_of_invader):
                    self.rgb_list[country_index*self.size_of_conquest-invader_index] = self.invader
                    if (country_index*self.size_of_conquest+invader_index<self.nb_of_leds):
                        self.rgb_list[country_index*self.size_of_conquest+invader_index] = self.invader
                country_index += 1

        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM_1) temps pour ",self.name," : ",duration)