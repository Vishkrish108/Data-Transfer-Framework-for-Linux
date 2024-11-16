import ip_utils
from net_utils import Client


def main():
    ip_list, hostname = ip_utils.get_ip()
    chosen_ip = ip_utils.choose_ip(ip_list)

    client = Client()
    ip_range = ip_utils.get_ip_range(chosen_ip)
    client.run_scan(ip_range)

    if client.devices:
        print("Available devices:")
        for i, device in enumerate(client.devices):
            print(f"{i}: {device[0]} ({device[1]})")

        choice = int(input("Select a device to connect to: "))
        dest_ip = client.devices[choice][0]
        client.start_connection(dest_ip)

        while True:
            command = input("Enter command (cat, ls, get, put, cd): ")
            response = client.send_fs_command(command)
            print(response)
    else:
        print("No devices found.")


if __name__ == "__main__":
    main()