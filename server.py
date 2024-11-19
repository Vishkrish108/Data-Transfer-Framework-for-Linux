import ip_utils
from net_utils import Server
import signal
import threading
from colors import FG_RED, FG_BG_CLEAR


def main():
    ip_list, hostname = ip_utils.get_ip()
    chosen_ip = ip_utils.choose_ip(ip_list)

    server = Server()

    def shutdown_handler(signum, frame):
        print(f"\n{FG_RED}Shutdown signal received. Waiting for active connections to close...{FG_BG_CLEAR}")
        server.shutdown_server()
        exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)

    try:
        server.start_server(chosen_ip, hostname)
    except KeyboardInterrupt:
        shutdown_handler(None, None)
    except Exception as e:
        print(f"\n{FG_RED}Server error: {e}{FG_BG_CLEAR}")
        server.shutdown_server()


if __name__ == "__main__":
    main()