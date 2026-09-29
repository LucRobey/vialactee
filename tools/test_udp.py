import socket
import time

ip = "192.168.0.26"
port = 9001
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
small_packet = b"hello"

print(f"Sending small UDP packets to {ip}:{port}...")
for _ in range(5):
    sock.sendto(small_packet, (ip, port))
    print("Sent 5 bytes")
    time.sleep(1)
