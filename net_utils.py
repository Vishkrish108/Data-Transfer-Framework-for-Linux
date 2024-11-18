# TODO: investigate server shutdown logic (assigned mainly to vishnu)
# TODO: add the remove file thing (assigned mainly to varun)
# TODO: prettify the client and make the prompts look good (assigned to vishal/manas)


import select
import socket
import threading
import os
import time
from concurrent.futures import ThreadPoolExecutor
from handshake_utils import (
    perform_handshake,
    receive_handshake,
    create_socket,
    verify_user,
)
from fs_utils import FS
from ssl_utils import wrap_client_ssl, wrap_server_ssl
from ip_utils import DATA_PORT, GREET_PORT, CHUNK_SIZE
from colors import FG_BLUE, FG_YELLOW, FG_BG_CLEAR


class Client:
    def __init__(self):
        self.devices = []
        self.client_socket = None

    def start_connection(self, dest_ip):
        """
        Starts a connection to the server and performs authentication.
        """
        try:
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
                self.client_socket = None
        except Exception as e:
            print(f"Error connecting to server: {e}")
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None

    def close_connection(self):
        """
        Closes the connection to the server gracefully.
        """
        if self.client_socket:
            try:
                perform_handshake(self.client_socket, "exit")
                self.client_socket.close()
            except Exception as e:
                print(f"Error closing connection: {e}")
            finally:
                self.client_socket = None
            print("Connection closed.")


    def ping_server(self, dest_ip):
        """
        Pings the server to check if it's available.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock = wrap_client_ssl(sock)
                sock.settimeout(1)
                sock.connect((dest_ip, GREET_PORT))
                perform_handshake(sock, "ping")
                mode = receive_handshake(sock)
                if not mode.startswith("reject"):
                    self.devices.append((dest_ip, mode))
        except Exception:
            pass  # Suppress exceptions during scanning

    def send_fs_command(self, command):
        """
        Sends file system commands to the server.
        """
        try:
            cmd_parts = command.strip().split()
            if not cmd_parts:
                return "No command provided."

            cmd, *args = cmd_parts

            if cmd == "get":
                return self.handle_get(args)
            elif cmd == "put":
                return self.handle_put(args)
            else:
                return self.handle_other_commands(cmd, args)
        except Exception as e:
            return f"Error sending command: {e}"

    def handle_get(self, args):
        """
        Handles the 'get' command to receive a file from the server.
        """
        if not args:
            return "No filename provided for get command."

        filename = args[0]
        perform_handshake(self.client_socket, f"get {filename}")
        port_no = receive_handshake(self.client_socket)

        time.sleep(1)  # Brief pause before connecting to the file socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as fs_sock:
                fs_sock = wrap_client_ssl(fs_sock)
                fs_sock.connect(
                    (self.client_socket.getpeername()[0], int(port_no))
                )
                with open(filename, 'wb') as file:
                    while True:
                        data = fs_sock.recv(CHUNK_SIZE)
                        if not data:
                            break
                        file.write(data)
            response = receive_handshake(self.client_socket)
            return response
        except Exception as e:
            return f"Error receiving file '{filename}': {e}"

    def handle_put(self, args):
        """
        Handles the 'put' command to send a file to the server.
        """
        if not args:
            return "No filename provided for put command."

        filename = args[0]
        if not os.path.isfile(filename):
            return f"File '{filename}' does not exist."

        perform_handshake(self.client_socket, f"put {filename}")
        port_no = receive_handshake(self.client_socket)

        time.sleep(1)  # Brief pause before connecting to the file socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as fs_sock:
                fs_sock = wrap_client_ssl(fs_sock)
                fs_sock.connect((self.client_socket.getpeername()[0], int(port_no)))
                with open(filename, 'rb') as file:
                    while True:
                        data = file.read(CHUNK_SIZE)
                        if not data:
                            break
                        fs_sock.sendall(data)
                fs_sock.shutdown(socket.SHUT_WR)
            response = receive_handshake(self.client_socket)
            return response
        except Exception as e:
            return f"Error sending file '{filename}': {e}"

    def handle_other_commands(self, cmd, args):
        """
        Handles other file system commands like 'ls', 'cd', etc.
        """
        perform_handshake(self.client_socket, f"{cmd} {' '.join(args)}")
        response = receive_handshake(self.client_socket)
        return response

    def run_scan(self, iprange):
        """
        Scans a range of IP addresses to find available devices.
        """
        self.devices = []
        threads = [
            threading.Thread(target=self.ping_server, args=(ip,))
            for ip in iprange
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.devices = list(set(self.devices))


class Server:
    def __init__(self):
        self.data_socket = None
        self.greet_socket = None
        self.socks = []
        self.running = True
        self.executor = ThreadPoolExecutor(5)
        self.active_connections = 0
        self.lock = threading.Lock()
        self.shutdown_complete = threading.Event()
        self.ip = None

    def get_fs_socket(self):
        """
        Creates a new socket for file transfer operations.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(True)
        sock.settimeout(5)
        sock.bind((self.ip, 0))
        sock = wrap_server_ssl(sock)
        sock.listen()
        return sock, sock.getsockname()[1]

    def start_server(self, ip, hostname):
        """
        Starts the server and listens for incoming connections.
        """
        self.ip = ip

        self.data_socket = create_socket(ip, DATA_PORT)
        self.data_socket = wrap_server_ssl(self.data_socket)
        self.data_socket.listen()

        self.greet_socket = create_socket(ip, GREET_PORT)
        self.greet_socket = wrap_server_ssl(self.greet_socket)
        self.greet_socket.listen()

        self.socks = [self.greet_socket, self.data_socket]

        print(
            f"[ALERT] You are discoverable as {FG_BLUE}{hostname}{FG_BG_CLEAR} @ "
            f"{FG_BLUE}{ip}{FG_BG_CLEAR}\n"
        )

        while self.running:
            try:
                readable, _, _ = select.select(self.socks, [], [])
                for sock in readable:
                    conn, addr = sock.accept()
                    # with self.lock:
                    #     self.active_connections += 1
                    # threading.Thread(
                    #     target=self.handle_client, args=(conn, addr, hostname)
                    # ).start()
                    self.executor.submit(self.handle_client, conn, addr, hostname)
            except Exception as e:
                print(f"Error occurred: {e}")
                break

    def handle_ping(self, conn, addr, hostname):
        """
        Handles ping requests from clients.
        """
        print(
            f"[ALERT] {FG_YELLOW}Ping{FG_BG_CLEAR} from {FG_BLUE}{addr[0]}{FG_BG_CLEAR}"
        )
        perform_handshake(conn, hostname)
        conn.close()

    def handle_fs(self, conn, addr, username):
        """
        Handles file system commands from authenticated clients.
        """
        print(
            f"[ALERT] {FG_YELLOW}Connection from{FG_BG_CLEAR} {FG_BLUE}{username}{FG_BG_CLEAR} @ "
            f"{FG_BLUE}{addr[0]}{FG_BG_CLEAR}\n"
        )
        perform_handshake(conn, "accept")
        fs = FS(username)  # Use the authenticated username

        try:
            while True:
                data = receive_handshake(conn)
                if not data or data.strip() == "exit":
                    break
                cmd, *args = data.strip().split()
                if cmd == "cat":
                    response = fs.cat(*args)
                    perform_handshake(conn, response)
                elif cmd == "ls":
                    response = fs.ls(*args)
                    perform_handshake(conn, response)
                elif cmd == "get":
                    self.handle_get(conn, fs, args)
                elif cmd == "put":
                    self.handle_put(conn, fs, args)
                elif cmd == "cd":
                    response = fs.cd(*args)
                    perform_handshake(conn, response)
                else:
                    perform_handshake(conn, "Unknown command")
        except Exception as e:
            perform_handshake(conn, f"Error handling command: {e}")
        finally:
            conn.close()
            with self.lock:
                self.active_connections -= 1
                if not self.running and self.active_connections == 0:
                    self.shutdown_complete.set()

    def handle_get(self, conn, fs, args):
        """
        Handles the 'get' command to send a file to the client.
        """
        if not args:
            perform_handshake(conn, "No filename provided for get command.")
            return

        filename = args[0]
        fs_sock, fs_port = self.get_fs_socket()
        perform_handshake(conn, f"{fs_port}")

        try:
            fs_conn, fs_addr = fs_sock.accept()
            with fs_conn:
                file_data = fs.get(filename)
                fs_conn.sendall(file_data)
                fs_conn.shutdown(socket.SHUT_WR)
            perform_handshake(conn, "File sent successfully")
        except Exception as e:
            perform_handshake(conn, f"Error sending file '{filename}': {e}")
        finally:
            fs_sock.close()

    def handle_put(self, conn, fs, args):
        """
        Handles the 'put' command to receive a file from the client.
        """
        if not args:
            perform_handshake(conn, "No filename provided for put command.")
            return

        filename = args[0]
        fs_sock, fs_port = self.get_fs_socket()
        perform_handshake(conn, f"{fs_port}")

        try:
            fs_conn, fs_addr = fs_sock.accept()
            with fs_conn, open(os.path.join(fs.current_path, filename), 'wb') as file:
                while True:
                    data = fs_conn.recv(CHUNK_SIZE)
                    if not data:
                        break
                    file.write(data)
            perform_handshake(conn, "File received successfully")
        except Exception as e:
            perform_handshake(conn, f"Error receiving file '{filename}': {e}")
        finally:
            fs_sock.close()

    def handle_client(self, conn, addr, hostname):
        """
        Handles incoming client connections and authentication.
        """
        try:
            handshake_mode = receive_handshake(conn)
            if handshake_mode.startswith("fs"):
                credentials = receive_handshake(conn)
                username_password = credentials.split(":")
                if len(username_password) != 2:
                    perform_handshake(conn, "invalid credentials")
                    conn.close()
                    return
                username, password = username_password
                if verify_user(username, password):
                    print(f"User {username} authenticated from {addr[0]}")
                    self.handle_fs(conn, addr, username)
                else:
                    print(f"Invalid credentials from {addr[0]}")
                    perform_handshake(conn, "invalid credentials")
                    conn.close()
            elif handshake_mode.startswith("ping"):
                self.handle_ping(conn, addr, hostname)
            else:
                print(f"Unknown handshake mode from {addr[0]}")
                conn.close()
        except Exception as e:
            perform_handshake(conn, f"Error during handshake: {e}")
            conn.close()

    def shutdown_server(self):
        """
        Shuts down the server gracefully.
        """
        print("[ALERT] Shutting down server...")
        self.running = False
        initial_connections=self.active_connections

        with self.lock:
            if self.active_connections == 0:
                print("[ALERT] No active connections. Shutting down server immediately...")
                self.shutdown_complete.set()
            else:
                print(f"[ALERT] Waiting for {self.active_connections} active connection(s) to close...")
                if hasattr(self, 'client_addresses'):
                    for addr in self.client_addresses:
                        print(f" - Connection with {addr}")

        # Periodically display what the server is waiting for
        while not self.shutdown_complete.is_set():
            with self.lock:
                if self.active_connections == 0:
                    self.shutdown_complete.set()
                    break
                else:
                    progress_percentage=100-(self.active_connections/initial_connections)*100
                    print(f"[ALERT] Progress: {progress_percentage}% closed. Still waiting for {self.active_connections} active connection(s)...")
                    if hasattr(self, 'client_addresses'):
                        for addr in self.client_addresses:
                            with self.lock:         # basically for a visual gimmick if wanted
                                self.progress_states(f'Closing connection {addr}', 4)
                                print(f" - Connection with {addr}")
            time.sleep(1)

        self.shutdown_complete.wait()
        self.executor.shutdown(wait=True)
        print("[ALERT] Server shutdown complete.")


    # faking it basically
    def progress_states(self, task_name, duration):
        progress=[25,50,75,100]
        stage_duration= duration/4  #length of progress

        for i in progress:
            print(f"[ALERT] {task_name}: {i}% completed")
            time.sleep(stage_duration)
