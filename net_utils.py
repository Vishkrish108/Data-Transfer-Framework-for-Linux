import select
import socket
import threading
import os
import time
from concurrent.futures import ThreadPoolExecutor
from handshake_utils import perform_handshake, receive_handshake, create_socket, verify_user
from fs_utils import FS
from ssl_utils import wrap_client_ssl, wrap_server_ssl
from ip_utils import DATA_PORT, GREET_PORT, CHUNK_SIZE
from colors import FG_BLUE, FG_YELLOW, FG_BG_CLEAR
import signal

class Client:

    def __init__(self):
        self.devices = []
        self.client_socket = None


    def start_connection(self, dest_ip):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket = wrap_client_ssl(self.client_socket)
        self.client_socket.connect((dest_ip, DATA_PORT))
        print("Connected to server")
        perform_handshake(self.client_socket, "fs")
        username = input("Enter username: ")
        password = input("Enter password: ")
        perform_handshake(self.client_socket, f"{username}:{password}")
        response = receive_handshake(self.client_socket)
        if response == "invalid credentials":
            print("Invalid credentials")
            self.client_socket.close()

    def ping_server(self, dest_ip):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock = wrap_client_ssl(sock)
                sock.settimeout(1)
                sock.connect((dest_ip, GREET_PORT))
                perform_handshake(sock, "ping")
                mode = receive_handshake(sock)
                if not mode.startswith("reject"):
                    self.devices.append((dest_ip, mode))
        except Exception as e:
            pass

    def send_fs_command(self, command):
        try:
            command, *args = command.split()
            if command == "get":
                perform_handshake(self.client_socket, f"{command} {' '.join(args)}")
                port_no = receive_handshake(self.client_socket)
                time.sleep(1)
                fs_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                fs_sock = wrap_client_ssl(fs_sock)
                fs_sock.connect((self.client_socket.getpeername()[0], int(port_no)))
                with open(args[0], 'wb') as file:
                    while True:
                        data = fs_sock.recv(CHUNK_SIZE)
                        if not data:
                            break
                        file.write(data)
                print("hi!")
                response = receive_handshake(self.client_socket)
                return response
            elif command == "put":
                perform_handshake(self.client_socket, f"{command} {args[0]}")
                port_no = receive_handshake(self.client_socket)
                time.sleep(1)
                fs_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                fs_sock = wrap_client_ssl(fs_sock)
                print(port_no)
                fs_sock.connect((self.client_socket.getpeername()[0], int(port_no)))
                with open(args[0], 'rb') as file:
                    while (data := file.read(CHUNK_SIZE)):
                        fs_sock.send(data)
                fs_sock.shutdown(socket.SHUT_WR)
                response = receive_handshake(self.client_socket)
                return response
            else:
                perform_handshake(self.client_socket, f"{command} {' '.join(args)}")
                response = b""
                try:
                    data = self.client_socket.recv(CHUNK_SIZE)
                    response += data
                except socket.error:
                    pass
                return response.decode(errors='ignore')
        except Exception as e:
            return f"Error sending command: {e}"

    def run_scan(self, iprange):
        self.devices = []
        threads = [threading.Thread(target=self.ping_server, args=(i,)) for i in iprange]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.devices = list(set(self.devices))


class Server:
    def __init__(self):
        self.data_socket = None
        self.greet_socket = None
        self.socks = None
        self.running = True
        self.executor = ThreadPoolExecutor(5)
        self.active_connections = 0
        self.lock = threading.Lock()

    def get_fs_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(True)
        sock.settimeout(5)
        sock.bind((self.ip, 0))
        sock = wrap_server_ssl(sock)
        sock.listen()
        return sock, sock.getsockname()[1]

    def start_server(self, ip, hostname):
        self.data_socket = create_socket(ip, DATA_PORT)
        self.data_socket = wrap_server_ssl(self.data_socket)
        self.data_socket.listen()
        self.ip=ip

        self.greet_socket = create_socket(ip, GREET_PORT)
        self.greet_socket = wrap_server_ssl(self.greet_socket)
        self.greet_socket.listen()

        self.socks = [self.greet_socket, self.data_socket]

        print(
            f"[ALERT] You are discoverable as {FG_BLUE}{hostname}{FG_BG_CLEAR} @ "
            f"{FG_BLUE}{ip}{FG_BG_CLEAR}",
            end="\n\n",
        )

        while self.running:
            try:
                readable, _, _ = select.select(self.socks, [], [])
                for sock in readable:
                    conn, addr = sock.accept()
                    with self.lock:
                        self.active_connections += 1
                    threading.Thread(
                        target=self.handle_client, args=(conn, addr, sock, hostname)
                    ).start()

                    # self.executor.submit(self.handle_client, conn, addr, sock, hostname)
                    # for thread pooling. incorporate once get, put etc are working

            except Exception as e:
                print(f"Error occurred: {e}")
                break

    def handle_ping(self, conn, addr, hostname):
        print(
            f"[ALERT] {FG_YELLOW}Ping{FG_BG_CLEAR} from {FG_BLUE}{hostname}{FG_BG_CLEAR} @ "
            f"{FG_BLUE}{addr[0]}{FG_BG_CLEAR}",
            end="\n\n",
        )
        perform_handshake(conn, hostname)

    def handle_fs(self, conn, addr, mode, sock, hostname):
        print(
            f"[ALERT] {FG_YELLOW}Connection from{FG_BG_CLEAR} from {FG_BLUE}{hostname}{FG_BG_CLEAR} @ "
            f"{FG_BLUE}{addr[0]}{FG_BG_CLEAR}",
            end="\n\n",
        )
        perform_handshake(conn, "accept")
        fs = FS(addr[0])  # Assuming username is the IP address for simplicity

        while True:
            try:
                data = receive_handshake(conn)
                if not data:
                    break
                command, *args = data.split()
                if command == "cat":
                    response = fs.cat(*args)
                    perform_handshake(conn, response)
                elif command == "ls":
                    response = fs.ls(*args)
                    print("response:", response)
                    perform_handshake(conn, response)
                elif command == "get":
                    fs_sock, fs_port = self.get_fs_socket()
                    perform_handshake(conn, f"{fs_port}")
                    while True:
                        fs_conn, fs_addr = fs_sock.accept()
                        if fs_addr[0] == addr[0]:
                            break
                    file_data = fs.get(*args)
                    fs_conn.sendall(file_data)
                    fs_conn.shutdown(socket.SHUT_WR)
                    fs_sock.close()
                    perform_handshake(conn, "File received successfully")
                elif command == "put":
                    fs_sock, fs_port = self.get_fs_socket()
                    perform_handshake(conn, f"{fs_port}")
                    print(fs_port)
                    while True:
                        fs_conn, fs_addr = fs_sock.accept()
                        if fs_addr[0] == addr[0]:
                            break
                    with open(os.path.join(fs.current_path, args[0]), 'wb') as file:
                        while True:
                            file_data = fs_conn.recv(CHUNK_SIZE)
                            if not file_data:
                                break
                            file.write(file_data)
                    perform_handshake(conn, "File sent successfully")
                    fs_conn.close()
                elif command == "cd":
                    response = fs.cd(*args)
                    perform_handshake(conn, response)
                else:
                    response = "Unknown command"
                    perform_handshake(conn, response)
            except Exception as e:
                perform_handshake(conn, f"Error handling command: {e}")
                break
        conn.close()
        with self.lock:
            self.active_connections -= 1
            if not self.running and self.active_connections == 0:
                self.shutdown_complete.set()

    def handle_client(self, conn, addr, sock, hostname):
        handshake_mode = receive_handshake(conn)
        if handshake_mode.startswith("fs"):
            username, password = receive_handshake(conn).split(":")
            if verify_user(username, password):
                print(f"User {username} authenticated from {addr[0]}")
                self.handle_fs(conn, addr, handshake_mode, sock, hostname)
            else:
                print(f"Invalid credentials from {addr[0]}")
                perform_handshake(conn, "invalid credentials")
                conn.close()
        elif handshake_mode.startswith("ping"):
            self.handle_ping(conn, addr, hostname)

    def shutdown_server(self):
        print("[ALERT] Shutting down server...")
        self.running = False
        self.shutdown_complete = threading.Event()
        for sock in self.socks:
            sock.close()
        if self.active_connections == 0:
            self.shutdown_complete.set()
        self.shutdown_complete.wait()
        self.executor.shutdown(wait=True)
        print("[ALERT] Server shutdown complete.")