import socket

class Connector:
    HOST = ''  # Listen on all available network interfaces
    PORT = 12345

    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.HOST, self.PORT))
        self.server_socket.listen(1)
        self.server_socket.settimeout(0.0001)  # Set timeout to 5 seconds for waiting on connections

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