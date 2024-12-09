import socket
import struct

class ESP32_Microphone:
    
    def __init__(self , nb_of_fft_band , showMicrophoneDetails):
        self.nb_of_fft_band = nb_of_fft_band
        self.UDP_IP = ""
        self.UDP_PORT = 4040
        
        self.showMicrophoneDetails = showMicrophoneDetails

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.UDP_IP,self.UDP_PORT))
        self.sock.settimeout(0.001)
        
        self.bandValues = []
        for k in range(self.nb_of_fft_band):
            self.bandValues.append(0)
                
    def listen(self):
        try:
            data, addr = self.sock.recvfrom(1024)  # Wait for incoming data
            self.bandValues = list(struct.unpack(f"{len(data)//4}i", data))
            return True , self.bandValues
        except socket.timeout:
            if (self.showMicrophoneDetails):
                print("(ESP_microphone) No data received within the timeout period.")
            return False , []
        except Exception as e:
            if ( self.showMicrophoneDetails):
                print(f"ESP_microphone) An error occurred: {e}")
            return False , []
