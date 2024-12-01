import modes.Mode as Mode
import calculations.rgb_hsv as RGB_HSV
import time
import random

class Alcool_randomer(Mode.Mode):

    def __init__(self , listener , leds , indexes , rgb_list):
        super().__init__(listener , leds , indexes , rgb_list)

        self.begining_speed = self.nb_of_leds/40
        self.end_of_phase_one_speed = 4 * self.begining_speed

        self.activated = False
        self.hasEnded = False
        self.pos_int = int(self.nb_of_leds/2)
        self.pos_float = float(int(self.nb_of_leds/2))
        self.speed = 0
        self.direction = 1
        


    def update(self):
        if(self.activated):
            self.check_phase()
            if(self.phase==1):
                self.speed = self.begining_speed + (float(self.current_time)/self.first_phase_end_time) * (self.end_of_phase_one_speed - self.begining_speed)
            elif(self.phase==2):
                pass
            elif(self.phase==3):
                self.speed = self.end_of_phase_one_speed * (1 - (float(self.current_time-self.second_phase_end_time)/(self.third_phase_end_time-self.second_phase_end_time)))
            elif(self.phase==4):
                self.speed=0
            elif(self.phase==5):
                self.speed=0
            elif(self.phase==6):
                self.speed=0
                self.activated = False
                self.hasEnded = True
            self.moove_ball()
        self.fade_to_black(0.4)
        self.color_head()
        
        
    def activate(self):
        print("On est activé")

        self.activated = True
        self.hasEnded = False
        self.time_to_spin = random.randint(15,20)
        self.direction =  -1 if random.randint(0,1)==0 else 1
        self.speed = self.begining_speed
        self.last_moove = 0
        
        self.pos_int = int(self.nb_of_leds/2)
        self.pos_float = float(int(self.nb_of_leds/2))
        
        self.first_phase_duration = random.randint(2,int(0.4*self.time_to_spin))
        self.second_phase_duration = random.randint(2,int(0.33*self.time_to_spin))
        self.third_phase_duration = self.time_to_spin - self.first_phase_duration - self.second_phase_duration
        self.fourth_phase_duration = 1
        self.fifth_phase_duration = 5

        self.phase = 1
        self.starting_time = time.time()
        self.current_time = 0

        self.first_phase_end_time  =  self.first_phase_duration
        self.second_phase_end_time =  self.first_phase_duration + self.second_phase_duration
        self.third_phase_end_time  =  self.first_phase_duration + self.second_phase_duration + self.third_phase_duration
        self.fourth_phase_end_time = self.third_phase_end_time + self.fourth_phase_duration
        self.fifth_phase_end_time = self.fourth_phase_end_time + self.fifth_phase_duration

    def check_phase(self):
        new_time = time.time()
        self.current_time = new_time - self.starting_time
        if( self.current_time > self.first_phase_end_time ):
            if (self.current_time > self.second_phase_end_time ):
                if (self.current_time > self.third_phase_end_time ): 
                    if(self.current_time > self.fourth_phase_end_time):
                        if(self.current_time > self.fifth_phase_end_time):
                            self.phase = 6
                        else:
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
            
            if( self.pos_int > self.nb_of_leds-1):
                self.pos_int = self.nb_of_leds-1
            if( self.pos_int < 0):
                self.pos_int = 0
 
            
    def color_head(self):
        self.rgb_list[self.pos_int]=self.white
        if(self.pos_int+1 < self.nb_of_leds):
            self.rgb_list[self.pos_int+1]=self.white
        if(self.pos_int-1 >= 0):
            self.rgb_list[self.pos_int-1]=self.white
    
        
