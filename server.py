import ip_utils
from net_utils import Server
import signal
import threading


def main():
    ip_list, hostname = ip_utils.get_ip()
    chosen_ip = ip_utils.choose_ip(ip_list)

    server = Server()

    def shutdown_handler(signum, frame):
        server.shutdown_server()
        exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)

    try:
        server.start_server(chosen_ip, hostname)
    except KeyboardInterrupt:
        server.shutdown_server()
    except Exception as e:
        print(f"Server error: {e}")
        server.shutdown_server()


if __name__ == "__main__":
    main()
