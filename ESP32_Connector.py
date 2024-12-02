import socket

class ESP32_Connector:

    def _init_(self , leds1 , leds2 ):
        self.UDP_IP ="192.168.1.10"  # ESP32 IP address
        self.PORT = 5050 # Port to send data to
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.leds1 = leds1  # LED data for the first batch
        self.leds2 = leds2  # LED data for the second batch

    def send_to_ESP1(self):
        led_data = bytearray(self.leds1)  # Convert LED data to a byte array
        self.sock.sendto(led_data, (self.UDP_IP, self.PORT))  # Send data to ESP32