import modes.Mode as Mode
import time
import random

class Alcool_randomer(Mode.Mode):

    def __init__(self , name ,segment_name , listener , leds , indexes , rgb_list , infos):
        super().__init__(name ,segment_name , listener , leds , indexes , rgb_list , infos)

        self.begining_speed = self.nb_of_leds/40
        self.end_of_phase_one_speed = 4 * self.begining_speed

        self.activated = False
        self.hasEnded = False
        self.pos_int = int(self.nb_of_leds/2)
        self.pos_float = float(int(self.nb_of_leds/2))
        self.last_pos_int = self.pos_int
        self.speed = 0
        self.direction = 1
        


    def update(self):
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            time_me = time.time()  
        #====================================================================================
         
        self.fade_to_black(0.4)
        if(self.activated):
            self.check_phase()
            if(self.phase==1):
                self.speed = self.begining_speed + (float(self.new_time)/self.first_phase_end_time) * (self.end_of_phase_one_speed - self.begining_speed)
            elif(self.phase==2):
                pass
            elif(self.phase==3):
                self.speed = self.end_of_phase_one_speed * (1 - (float(self.new_time-self.second_phase_end_time)/(self.third_phase_end_time-self.second_phase_end_time)))
            elif(self.phase==4):
                self.speed=0
            elif(self.phase==5):
                self.speed=0
            elif(self.phase==6):
                self.speed=0
                self.activated = False
                self.hasEnded = True
            self.moove_ball()
            
        self.color_head()
        #====================================================================================
        if(self.printTimeOfCalculation and self.printThisModeDetail):
            duration = time.time() - time_me
            print("      (CM) temps pour ",self.name," : ",duration)
        
        
    def activate(self):
        self.activated = True
        self.hasEnded = False
        self.time_to_spin = random.randint(15,20)
        self.direction =  -1 if random.randint(0,1)==0 else 1
        self.speed = self.begining_speed
        self.last_moove = 0
        
        self.pos_int = int(self.nb_of_leds/2)
        self.pos_float = float(int(self.nb_of_leds/2))
        self.last_pos_int = self.pos_int
        
        self.first_phase_duration = random.randint(2,int(0.33*self.time_to_spin))
        self.second_phase_duration = random.randint(2,int(0.33*self.time_to_spin))
        self.third_phase_duration = self.time_to_spin - self.first_phase_duration - self.second_phase_duration
        self.fourth_phase_duration = 1

        self.phase = 1
        self.starting_time = time.time()
        self.new_time = 0

        self.first_phase_end_time  =  self.starting_time         + self.first_phase_duration
        self.second_phase_end_time =  self.first_phase_end_time  + self.second_phase_duration
        self.third_phase_end_time  =  self.second_phase_end_time + self.third_phase_duration
        self.fourth_phase_end_time = self.third_phase_end_time   + self.fourth_phase_duration
        
        """
        print("On a activé le mode shot:")
        print("first_duration = ", self.first_phase_duration)
        print("second_phase_duration = ", self.second_phase_duration)
        print("third_phase_duration = ", self.third_phase_duration)
        print("fourth_phase_duration = ", self.fourth_phase_duration)
        print("==")
        print("time_ends :")
        print("starting_time = ", self.starting_time)
        print("first_phase_end_time = ",self.first_phase_end_time)
        print("second_phase_end_time = ",self.second_phase_end_time)
        print("third_phase_end_time = ",self.third_phase_end_time)
        print("fourth_phase_end_time = ",self.fourth_phase_end_time)
        """



    def check_phase(self):
        self.new_time = time.time()
        if( self.new_time > self.first_phase_end_time ):
            if (self.new_time > self.second_phase_end_time ):
                if (self.new_time > self.third_phase_end_time ): 
                    if(self.new_time > self.fourth_phase_end_time):
                        self.phase = 5
                    else:
                        self.phase = 4
                        if(self.last_moove==0):
                            self.last_moove = random.uniform(-5,5)
                else:
                    self.phase = 3
            else:
                self.phase = 2

    def moove_ball(self):
        self.last_pos_int = self.pos_int
        self.pos_float += self.speed * self.direction
        if( self.pos_float >= self.nb_of_leds):
            self.pos_float = self.nb_of_leds-1
            self.direction *= (-1)
        if( self.pos_float < 0):
            self.pos_float = 0
            self.direction *= (-1)
        self.pos_int = int(self.pos_float)

        if(self.phase==5):
            self.pos_float += self.last_moove
            self.pos_int = int(self.pos_float)
            self.last_moove = 0
            
            if( self.pos_int > self.nb_of_leds-1):
                self.pos_int = self.nb_of_leds-1
            if( self.pos_int < 0):
                self.pos_int = 0
            self.phase=6
 
            
    def color_head(self):
        #On colorie tout entre last_pos et new_pos
        if(self.pos_int > self.last_pos_int):
            for led_index in range(self.last_pos_int , self.pos_int+1):
                self.rgb_list[led_index]=self.white
        else:
            for led_index in range(self.pos_int , self.last_pos_int+1):
                self.rgb_list[led_index]=self.white
