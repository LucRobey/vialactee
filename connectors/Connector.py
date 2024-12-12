import socket
import asyncio
import Mode_master

class Connector:
    HOST = '0.0.0.0'  # Listen on all available network interfaces
    PORT = 12345

    def __init__(self , mode_master , infos):

        self.printAppDetails = infos["printAppDetails"]
        self.current_page = "Main"
        self.list_of_pages = ["Main","Playlists","Configuration","Shot","Parametres","Calibration"]

        self.list_of_segments = ["Segment h00","Segment v1","Segment h10","Segment h11","Segment v2",
                                 "Segment h20","Segment v3","Segment h30","Segment h31","Segment h32",
                                 "Segment v4"]
        
        self.mode_master = mode_master
        
    async def start_server(self):
        """Start the asynchronous TCP server."""
        server = await asyncio.start_server(self.handle_client, self.HOST, self.PORT)
        print(f"Server started on {self.HOST}:{self.PORT}")
        
        async with server:
            await server.serve_forever()
            
    async def handle_client(self, reader, writer):
        """Handle incoming client connections."""
        client_address = writer.get_extra_info('peername')
        print(f"Connection from {client_address}")
        
        try:
            # Read the message sent by the client
            data = await reader.read(1024)
            message = data.decode().strip()
            if not message:
                if (self.printAppDetails):
                    print(f"(C) No data received from {client_address}")
                return
            if (self.printAppDetails):
                print(f"(C) Message received: {message}")
            response = self.process_message(message)

            writer.write(b"ack\n")  # Acknowledge receipt
            await writer.drain()

        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            # Close the connection
            writer.close()
            await writer.wait_closed()
            print(f"(C) Connection with {client_address} closed.")

    def process_message(self, message):
        """Process the incoming message and execute the appropriate command."""
        if(self.printAppDetails):
            print("(C) message reçu : ",message)
        splited_message = message.split(":")
        category = splited_message[0]
        rest_of_the_message = message[len(splited_message[0])+1:]

        if (category == "chgpage"):
            category = splited_message[1]
            page = splited_message[2]
            order = self.change_page(category,page)

        elif (category == "chgmode"):
            segment = splited_message[1]
            new_mode = splited_message[2]
            order = self.change_mode(segment , new_mode)
        
        elif (category == "chgway"):
            segment = splited_message[1]
            new_way = splited_message[2]
            order = self.change_way(segment , new_way)

        elif (category == "switchway"):
            segment = splited_message[1]
            order = self.switch_way(segment)

        elif (category == "chgconf"):
            mode_orders = splited_message[1]
            ways_orders = splited_message[2]
            order = self.change_conf(mode_orders,ways_orders)

        elif (category == "lockseg"):
            segment = splited_message[1]
            lock_unlock = splited_message[2]
            order = self.block_seg(segment,lock_unlock)

        elif (category == "chgparam"):
            parametre = splited_message[1]
            nouvelle_valeur = splited_message[2]
            order = self.change_param(parametre,nouvelle_valeur)

        elif (category == "calibration"):
            calibration_type = splited_message[1]
            phase = splited_message[2]
            order = self.calibrate_fft(calibration_type , phase)
            
        elif (category == "special"):
            order = self.handle_special(rest_of_the_message)
            
        else:
            print("(C) invalid category")
            return []

        if(self.printAppDetails):
            print("(C)          state : " , self.current_page)
            print("(C)          order : " , order)
        self.mode_master.obey_orders(order)
        
        
    def change_page(self , category , page):
        order = []
        if (category == "enter"):
            self.current_page = page
            self.check_current_page
            if (self.current_page == "Shot"):
                order.append("force:Segment h00:Shot")
                order.append("block:Segment h00")
                order.append("force:Segment h20:Shot")
                order.append("block:Segment h20")
        elif (category == "leave"):
            self.current_page = "Main"
            if(page == "Shot"):
                order.append("unblock:Segment h00")
                order.append("force:Segment h00:Rainbow")
                order.append("unblock:Segment h20")
                order.append("force:Segment h20:Rainbow")
        else :
            print("(C) ON ENTRE DANS AUCUNE CATEGORIE!")

        return order


    def check_current_page(self):
        if (not self.current_page in self.list_of_pages):
            print("(C) CURRENT PAGE PAS DANS LA LISTE")

    def change_mode(self , segment , new_mode):
        order = []
        order.append("change_mode:"+segment+":"+new_mode)
        return order
    
    def change_way(self , segment , new_way):
        order = []
        order.append("change_way:"+segment+":"+new_way)
        return order
    
    def switch_way(self , segment):
        order = []
        order.append("switch_way:"+segment)
        return order
    
    def change_conf(self , mode_orders , ways_orders):
        order = []
        modes = mode_orders[1:-2].split(',')  #on enleve les "{" et  "}" au debut et a la fin
        ways = ways_orders[1:-2].split(',')
        for segment_index in range(len(self.list_of_segments)):
            order.append("change_mode:"+self.list_of_segments[segment_index]+":"+modes[segment_index])
            order.append("change_way:"+self.list_of_segments[segment_index]+":"+ways[segment_index])
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
    
    def change_param(self , parametre , nouvelle_valeur):
        order = ["update:"+parametre+":"+str(nouvelle_valeur)]
        return order
    
    def calibrate_fft(self , calibration_type , phase):
        order = []
        if (phase == "start"):
            for segment_name in self.list_of_segments:              # On bloque les segments pdt la calibration
                order.append("block:"+segment_name)
            order.append("calibration:"+calibration_type+":"+phase)
        
        elif (phase == "end"):
            for segment_name in self.list_of_segments:
                order.append("unblock:"+segment_name)               # On les debloque à la fin
            order.append("calibration:"+calibration_type+":"+phase)

        else:
            print("(C) ON NE START NI END LA CALIBRATION!")
        return order

    
    def handle_special(self , message):
        return ["special:Shot"]
