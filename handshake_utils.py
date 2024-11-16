import socket
from ip_utils import CHUNK_SIZE

def perform_handshake(sock, data):
    sock.send(data.encode())

def receive_handshake(sock):
    data = sock.recv(CHUNK_SIZE)
    return data.decode()

def create_socket(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.settimeout(5)
    sock.bind((ip, port))
    return sock

def verify_user(username, password, filename="user_credentials.txt"):
    """Verifies the username and password from a file."""
    hashed_password = password
    try:
        with open(filename, "r") as f:
            for line in f:
                stored_username, stored_hashed_password = line.strip().split(":")
                if stored_username == username and stored_hashed_password == hashed_password:
                    return True
    except FileNotFoundError:
        print("User credentials file not found.")
    return False