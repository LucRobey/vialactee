import socket

class Connector:
    HOST = ''  # Listen on all available network interfaces
    PORT = 12345

    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.HOST, self.PORT))
        self.server_socket.listen(1)
        self.server_socket.settimeout(0.0001)  # Set timeout to 0.0001 seconds for waiting on connections

        self.current_page = "Main"
        self.list_of_pages = ["Main","Playlists","Configuration","Shot"]

        self.list_of_segments = ["segment_h00"]

    def update(self):
        message = self.listen()

        if(message):
            print("message reçu : ",message)
            category = message[0:7]

            if (category == "chgpage"):
                order = self.change_page(message[8:])

            elif (category == "chgmode"):
                order = self.change_mode(message[8:])

            elif (category == "chgconf"):
                order = self.change_conf(message[8:])

            print("         state : " , self.current_page)
            print("         order : " , order)
            return order
        return []

    def listen(self):
        try:
            conn, addr = self.server_socket.accept()
            #print(f"Connected by {addr}")
            data = conn.recv(1024).decode()
            if data:
                print(f"Received: {data}")
                conn.close()
                return data
            else:
                #print("No data received from the client.")
                conn.close()
                return None
        except socket.timeout:
            # Handle the case where no connection was received within the timeout
            #print("No connection received. Doing something else...")
            return None
        
    def change_page(self , message):
        order = []
        if (message[0:5] == "enter"):
            self.current_page = message[6:]
            self.check_current_page
            if (self.current_page == "Shot"):
                order.append("change:segment_h00:Shot")
                order.append("block:segment_h00")
        elif (message[0:5] == "leave"):
            self.current_page = "Main"
            if(message[6:] == "Shot"):
                order.append("unblock:segment_h00")
                order.append("change:segment_h00:Rainbow")

        return order


    def check_current_page(self):
        if (not self.current_page in self.list_of_pages):
            print("Current page pas dans la liste")

    def change_mode(self , message):
        order = []
        order.append("change:"+message[:11]+":"+message[12:])
        return order
    
    def change_conf(self , message):
        order = []

        modes = message[1:-2].split(',')
        for segment_index in range(len(self.list_of_segments)):
            order.append("change:"+self.list_of_segments[segment_index]+":"+modes[segment_index])

        return order
