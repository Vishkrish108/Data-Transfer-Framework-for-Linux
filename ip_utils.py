import socket
import netifaces
import ipaddress
import curses
from colors import *

DATA_PORT = 5001
CONTROL_PORT = 5002
GREET_PORT = 5003
CHUNK_SIZE = 4096


def get_ip():
    hostname = socket.gethostname()
    ip_list = []

    for interface in netifaces.interfaces():
        try:
            for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                ip_list.append(link["addr"]) if not link["addr"].startswith(
                    "127.0"
                ) else None
        except KeyError:
            pass

    return ip_list, hostname


# Function to return all the IP addresses in the same network as the given IP address
def get_ip_range(ip):
    ip_range = ""
    network = netifaces.interfaces()

    for i in network:
        addr = netifaces.ifaddresses(i)
        if netifaces.AF_INET in addr:
            addr = addr[netifaces.AF_INET]
        else:
            continue
        for j in addr:
            if j["addr"] == ip:
                ip_range = j["addr"] + "/" + j["netmask"]
                break

    ips = [str(ip) for ip in ipaddress.IPv4Network(ip_range, strict=False)]
    return ips

ips = []
ip = None

def character(stdscr):
    attributes = {}
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    attributes['normal'] = curses.color_pair(1)

    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    attributes['highlighted'] = curses.color_pair(2)

    c = 0
    option = 0
    while c not in (10, 32):  # 10 is ENTER, 32 is SPACE
        stdscr.erase()
        stdscr.addstr("Select the IP you want to use\n", curses.A_UNDERLINE)
        for i in range(len(ips)):
            if i == option:
                attr = attributes['highlighted']
            else:
                attr = attributes['normal']
            stdscr.addstr(ips[i] + '\n', attr)
        c = stdscr.getch()
        if c == curses.KEY_UP and option > 0:
            option -= 1
        elif c == curses.KEY_DOWN and option < len(ips) - 1:
            option += 1

    stdscr.getch()

    global ip
    ip = ips[option]


def choose_ip(ip_addr):
    global ips, ip
    if len(ip_addr) == 1:
        ip = ip_addr[0]
    elif len(ip_addr) > 1:
        ips = ip_addr
        print(ips)
        id=int(input())
        ip = ip_addr[id]
    return ip