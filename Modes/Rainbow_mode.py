import Modes.Mode as Mode

class Rainbow_mode(Mode.Mode):
    
    def __init__(self , listener , leds , rgb_list):
        super().__init__(listener , leds , rgb_list)
        pass

    def fromHSV_toRGB(self,h,s,v):
        if s:
            if h == 1.0: h = 0.0
            i = int(h*6.0); f = h*6.0 - i
            
            w = int(255*( v * (1.0 - s) ))
            q = int(255*( v * (1.0 - s * f) ))
            t = int(255*( v * (1.0 - s * (1.0 - f)) ))
            v = int(255*v)
            
            if i==0: return (v, t, w)
            if i==1: return (q, v, w)
            if i==2: return (w, v, t)
            if i==3: return (w, q, v)
            if i==4: return (t, w, v)
            if i==5: return (v, w, q)
        else: v = int(255*v); return (v, v, v)
        
    def rgb_to_hsv(self,r, g, b):
        r, g, b = r/255.0, g/255.0, b/255.0
        mx = max(r, g, b)
        mn = min(r, g, b)
        df = mx-mn
        if mx == mn:
            h = 0
        elif mx == r:
            h = (60 * ((g-b)/df) + 360) % 360
        elif mx == g:
            h = (60 * ((b-r)/df) + 120) % 360
        elif mx == b:
            h = (60 * ((r-g)/df) + 240) % 360
        if mx == 0:
            s = 0
        else:
            s = (df/mx)*100
        v = mx*100
        return h, s, v


    def smooth(self, led_index,new_color):
        old_col=self.leds[led_index]
        mixed_color=((old_col[0]+new_color[0])/2,(old_col[1]+new_color[1])/2,(old_col[2]+new_color[2])/2)
        self.rgb_list[led_index]=mixed_color
        
    def update(self):
        for index in range(self.listener.nb_of_segm_fft):
            color=self.fromHSV_toRGB(float(index)/self.listener.nb_of_segm_fft,1.0,self.listener.asserv_segm_fft[index] * self.listener.power)
            for k in range(4):
                self.smooth(4*index+k,color)
                #self.leds[4*index+k]=(2*self.leds[4*index+k]+color)/3
                    