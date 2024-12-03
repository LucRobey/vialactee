import socket
import time

class ESP32_Connector:

    def __init__(self , leds1 , leds2 ):
        self.UDP_IP ="192.168.1.75"  # ESP32 IP address
        self.PORT = 5050 # Port to send data to
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.leds1 = leds1  # LED data for the first batch
        self.leds2 = leds2  # LED data for the second batch
        
        self.init_time = time.time()
        self.counter = 0
        
        #self.sock.sendto(bytearray([0,1,2]),(self.UDP_IP, self.PORT))

    def send_to_ESP1(self):
        
        flat_led_data = [int(byte) for led in self.leds2[:100] for byte in led]
        
        led_data = bytearray(flat_led_data)  # Convert LED data to a byte array
        self.sock.sendto(led_data, (self.UDP_IP, self.PORT))  # Send data to ESP32
        
        self.counter+=1
        if(self.counter == 1000):
            print("itérations/secondes = " ,1000.0/(time.time()-self.init_time))