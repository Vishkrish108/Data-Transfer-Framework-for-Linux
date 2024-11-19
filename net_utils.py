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
from colors import FG_BLUE, FG_YELLOW, FG_BG_CLEAR, FG_GREEN, FG_RED


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
            print(f"\n{FG_GREEN}Connected to server{FG_BG_CLEAR}\n")

            perform_handshake(self.client_socket, "fs")

            username = input("Enter username: ")
            password = input("Enter password: ")
            perform_handshake(self.client_socket, f"{username}:{password}")

            response = receive_handshake(self.client_socket)
            if response == "invalid credentials":
                print(f"\n{FG_RED}Invalid credentials{FG_BG_CLEAR}\n")
                self.client_socket.close()
                self.client_socket = None
                exit(0)
        except Exception as e:
            print(f"\n{FG_RED}Error connecting to server: {e}{FG_BG_CLEAR}\n")
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
                print(f"\n{FG_RED}Error closing connection: {e}{FG_BG_CLEAR}\n")
            finally:
                self.client_socket = None
            print(f"\n{FG_GREEN}Connection closed.{FG_BG_CLEAR}\n")

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
                return f"\n{FG_RED}No command provided.{FG_BG_CLEAR}\n"

            cmd, *args = cmd_parts

            if cmd == "get":
                return self.handle_get(args)
            elif cmd == "put":
                return self.handle_put(args)
            elif cmd == "rm":
                return self.handle_rm(args)
            elif cmd == "mkdir":
                return self.handle_mkdir(args)
            elif cmd == "rmdir":
                return self.handle_rmdir(args)
            elif cmd == "exit":
                return self.handle_exit()
            else:
                return self.handle_other_commands(cmd, args)
        except Exception as e:
            return f"\n{FG_RED}Error sending command: {e}{FG_BG_CLEAR}\n"

    def handle_get(self, args):
        """
        Handles the 'get' command to receive a file from the server.
        """
        if not args:
            return f"\n{FG_RED}No filename provided for get command.{FG_BG_CLEAR}\n"

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
            return f"\n{FG_GREEN}{response}{FG_BG_CLEAR}\n"
        except Exception as e:
            return f"\n{FG_RED}Error receiving file '{filename}': {e}{FG_BG_CLEAR}\n"

    def handle_put(self, args):
        """
        Handles the 'put' command to send a file to the server.
        """
        if not args:
            return f"\n{FG_RED}No filename provided for put command.{FG_BG_CLEAR}\n"

        filename = args[0]
        if not os.path.isfile(filename):
            return f"\n{FG_RED}File '{filename}' does not exist.{FG_BG_CLEAR}\n"

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
            return f"\n{FG_GREEN}{response}{FG_BG_CLEAR}\n"
        except Exception as e:
            return f"\n{FG_RED}Error sending file '{filename}': {e}{FG_BG_CLEAR}\n"

    def handle_other_commands(self, cmd, args):
        """
        Handles other file system commands like 'ls', 'cd', etc.
        """
        perform_handshake(self.client_socket, f"{cmd} {' '.join(args)}")
        response = receive_handshake(self.client_socket)
        return f"\n{FG_GREEN}{response}{FG_BG_CLEAR}\n"

    def handle_rm(self, args):
        """
        Handles the 'rm' command to remove a file on the server.
        """
        if not args:
            return f"\n{FG_RED}No filename provided for rm command.{FG_BG_CLEAR}\n"
        perform_handshake(self.client_socket, f"rm {args[0]}")
        response = receive_handshake(self.client_socket)
        return f"\n{FG_GREEN}{response}{FG_BG_CLEAR}\n"

    def handle_mkdir(self, args):
        """
        Handles the 'mkdir' command to create a directory on the server.
        """
        if not args:
            return f"\n{FG_RED}No directory name provided for mkdir command.{FG_BG_CLEAR}\n"
        perform_handshake(self.client_socket, f"mkdir {args[0]}")
        response = receive_handshake(self.client_socket)
        return f"\n{FG_GREEN}{response}{FG_BG_CLEAR}\n"

    def handle_rmdir(self, args):
        """
        Handles the 'rmdir' command to remove a directory on the server.
        """
        if not args:
            return f"\n{FG_RED}No directory name provided for rmdir command.{FG_BG_CLEAR}\n"
        perform_handshake(self.client_socket, f"rmdir {args[0]}")
        response = receive_handshake(self.client_socket)
        return f"\n{FG_GREEN}{response}{FG_BG_CLEAR}\n"

    def handle_exit(self):
        """
        Handles the 'exit' command to gracefully terminate the client connection.
        """
        self.close_connection()
        exit(0)

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
            f"\n[{FG_GREEN}ALERT{FG_BG_CLEAR}] You are discoverable as {FG_BLUE}{hostname}{FG_BG_CLEAR} @ "
            f"{FG_BLUE}{ip}{FG_BG_CLEAR}\n"
        )

        while self.running:
            try:
                readable, _, _ = select.select(self.socks, [], [])
                for sock in readable:
                    conn, addr = sock.accept()
                    self.executor.submit(self.handle_client, conn, addr, hostname)
            except Exception as e:
                print(f"Error occurred: {e}")
                break

    def handle_ping(self, conn, addr, hostname):
        """
        Handles ping requests from clients.
        """
        print(
            f"\n[{FG_YELLOW}ALERT{FG_BG_CLEAR}] {FG_YELLOW}Ping{FG_BG_CLEAR} from {FG_BLUE}{addr[0]}{FG_BG_CLEAR}\n"
        )
        perform_handshake(conn, hostname)
        conn.close()

    def handle_fs(self, conn, addr, username):
        """
        Handles file system commands from authenticated clients.
        """
        print(
            f"\n[{FG_YELLOW}ALERT{FG_BG_CLEAR}] Connection from {FG_BLUE}{username}{FG_BG_CLEAR} @ "
            f"{FG_BLUE}{addr[0]}{FG_BG_CLEAR}\n"
        )
        perform_handshake(conn, "accept")
        fs = FS(username)  # Use the authenticated username

        with self.lock:
            self.active_connections += 1

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
                elif cmd == "rm":
                    response = fs.rm(*args)
                    perform_handshake(conn, response)
                elif cmd == "mkdir":
                    response = fs.mkdir(*args)
                    perform_handshake(conn, response)
                elif cmd == "rmdir":
                    response = fs.rmdir(*args)
                    perform_handshake(conn, response)
                elif cmd == "cd":
                    response = fs.cd(*args)
                    perform_handshake(conn, response)
                else:
                    perform_handshake(conn, f"{FG_RED}Unknown command{FG_BG_CLEAR}\n")
        except Exception as e:
            perform_handshake(conn, f"{FG_RED}Error handling command: {e}{FG_BG_CLEAR}\n")
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
            perform_handshake(conn, f"{FG_RED}No filename provided for get command.{FG_BG_CLEAR}\n")
            return

        filename = args[0]
        fs_sock, fs_port = self.get_fs_socket()
        perform_handshake(conn, f"{fs_port}\n")

        try:
            fs_conn, fs_addr = fs_sock.accept()
            with fs_conn:
                file_data = fs.get(filename)
                fs_conn.sendall(file_data)
                fs_conn.shutdown(socket.SHUT_WR)
            perform_handshake(conn, f"{FG_GREEN}File sent successfully{FG_BG_CLEAR}\n")
        except Exception as e:
            perform_handshake(conn, f"{FG_RED}Error sending file '{filename}': {e}{FG_BG_CLEAR}\n")
        finally:
            fs_sock.close()

    def handle_put(self, conn, fs, args):
        """
        Handles the 'put' command to receive a file from the client.
        """
        if not args:
            perform_handshake(conn, f"{FG_RED}No filename provided for put command.{FG_BG_CLEAR}\n")
            return

        filename = args[0]
        fs_sock, fs_port = self.get_fs_socket()
        perform_handshake(conn, f"{fs_port}\n")

        try:
            fs_conn, fs_addr = fs_sock.accept()
            with fs_conn, open(os.path.join(fs.current_path, filename), 'wb') as file:
                while True:
                    data = fs_conn.recv(CHUNK_SIZE)
                    if not data:
                        break
                    file.write(data)
            perform_handshake(conn, f"{FG_GREEN}File received successfully{FG_BG_CLEAR}\n")
        except Exception as e:
            perform_handshake(conn, f"{FG_RED}Error receiving file '{filename}': {e}{FG_BG_CLEAR}\n")
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
                    perform_handshake(conn, f"{FG_RED}invalid credentials{FG_BG_CLEAR}\n")
                    conn.close()
                    return
                username, password = username_password
                if verify_user(username, password):
                    print(f"\n{FG_GREEN}User {username} authenticated from {addr[0]}{FG_BG_CLEAR}\n")
                    self.handle_fs(conn, addr, username)
                else:
                    print(f"\n{FG_RED}Invalid credentials from {addr[0]}{FG_BG_CLEAR}\n")
                    perform_handshake(conn, f"{FG_RED}invalid credentials{FG_BG_CLEAR}\n")
                    conn.close()
            elif handshake_mode.startswith("ping"):
                self.handle_ping(conn, addr, hostname)
            else:
                print(f"\n{FG_RED}Unknown handshake mode from {addr[0]}{FG_BG_CLEAR}\n")
                conn.close()
        except Exception as e:
            perform_handshake(conn, f"{FG_RED}Error during handshake: {e}{FG_BG_CLEAR}\n")
            conn.close()

    def shutdown_server(self):
        """
        Shuts down the server gracefully.
        """
        print("[ALERT] Shutting down server...")
        self.running = False
        initial_connections=self.active_connections
        self.active_connections=self.active_connections//2

        with self.lock:
            if self.active_connections == 0:
                self.shutdown_complete.set()

        # Periodically display what the server is waiting for
        while not self.shutdown_complete.is_set():
            with self.lock:
                if self.active_connections == 0:
                    self.shutdown_complete.set()
                    break
            time.sleep(1)

        self.shutdown_complete.wait()
        self.executor.shutdown(wait=True)
        print("[ALERT] Server shutdown complete.")