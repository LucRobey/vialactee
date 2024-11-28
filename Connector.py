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

        self.list_of_segments = ["segment h00"]

    def update(self):
        message = self.listen()

        if(message):
            print("(C) message reçu : ",message)
            splited_message = message.split(":")
            category = splited_message[0]
            res_of_the_message = message[len(splited_message[0])+1:]

            if (category == "chgpage"):
                order = self.change_page(res_of_the_message)

            elif (category == "chgmode"):
                order = self.change_mode(res_of_the_message)

            elif (category == "chgconf"):
                order = self.change_conf(res_of_the_message)

            elif (category == "lockseg"):
                segment = splited_message[1]
                lock_unlock = splited_message[2]
                order = self.block_seg(segment,lock_unlock)
                
            elif (category == "special"):
                order self.handle_special()
                
            else:
                print("(C) mauvaise premiere catégorie")

            print("(C)          state : " , self.current_page)
            print("(C)          order : " , order)
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
        splited_message = message.split(":")
        category = splited_message[0]
        page = splited_message[1]
        if (category == "enter"):
            self.current_page = page
            self.check_current_page
            if (self.current_page == "Shot"):
                order.append("force:Segment h00:Shot")
                order.append("block:Segment h00")
        elif (category == "leave"):
            self.current_page = "Main"
            if(page == "Shot"):
                order.append("unblock:Segment h00")
                order.append("force:Segment h00:Rainbow")
        else :
            print("(C) ON ENTRE DANS AUCUNE CATEGORIE!")

        return order


    def check_current_page(self):
        if (not self.current_page in self.list_of_pages):
            print("(C) CURRENT PAGE PAS DANS LA LISTE")

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
    
    def block_seg(self , segment , lock_unlock):
        order = []
        if(lock_unlock == "true"):
            order.append("block:"+segment)
        elif(lock_unlock == "false"):
            order.append("unblock:"+segment)
        else:
            print("(C) ON N EST NI LOCK NI UNLOCK")
        return order
    
    def handle_special(self , message):
        return []
