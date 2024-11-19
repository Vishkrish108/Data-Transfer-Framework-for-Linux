import ip_utils
from net_utils import Client
from colors import FG_GREEN, FG_RED, FG_CYAN, FG_YELLOW, FG_BG_CLEAR


def main():
    ip_list, hostname = ip_utils.get_ip()
    chosen_ip = ip_utils.choose_ip(ip_list)

    client = Client()
    ip_range = ip_utils.get_ip_range(chosen_ip)
    client.run_scan(ip_range)

    if client.devices:
        print(f"\n{FG_GREEN}Available devices:{FG_BG_CLEAR}\n")
        for i, device in enumerate(client.devices):
            print(f"{i}: {device[0]} ({device[1]})")

        choice = int(input(f"\n{FG_CYAN}Select a device to connect to: {FG_BG_CLEAR}"))
        dest_ip = client.devices[choice][0]
        client.start_connection(dest_ip)

        while True:
            command = input(f"\n{FG_YELLOW}Enter command (cat, ls, get, put, cd): {FG_BG_CLEAR}")
            response = client.send_fs_command(command)
            print(f"\n{response}\n")
    else:
        print(f"\n{FG_RED}No devices found.{FG_BG_CLEAR}\n")


if __name__ == "__main__":
    main()