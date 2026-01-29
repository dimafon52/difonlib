#!/usr/bin/env python

import os
import re
import pexpect
import sys
import time
from typing import Optional
from ctypes import LittleEndianStructure, c_uint32
from difonlib.utils import logdbg
from difonlib.input_devs import get_connected_input_devices


dbg = logdbg

MAJOR_CLASSES = {
    0x00: "Miscellaneous",
    0x01: "Computer",
    0x02: "Phone",
    0x03: "LAN/Network Access Point",
    0x04: "Audio/Video",
    0x05: "HID Device",
    0x06: "Imaging",
    0x07: "Wearable",
    0x08: "Toy",
    0x09: "Health",
    0x1F: "Uncategorized",
}


# === Class of Device (CoD)===
class CoD(LittleEndianStructure):
    _fields_ = [
        ("FormatType", c_uint32, 2),  # 2 бита
        ("MinorDevClass", c_uint32, 6),  # 6 бит
        ("MajorDevClass", c_uint32, 5),  # 5 бит
        ("ServiceClass", c_uint32, 11),  # 11 бит
        ("Reserved", c_uint32, 8),  # оставшиеся до 32
    ]


def bt_parse_cod(cod_val: str) -> str:
    """Разобрать Class of Device (CoD) в словарь с описанием"""
    cod32 = c_uint32(int(cod_val, 0))
    fields = CoD.from_buffer_copy(cod32)
    major = fields.MajorDevClass
    return MAJOR_CLASSES.get(major, f"0x{major:02X}")


def bt_scan() -> list:
    # px = pexpect.spawn("hcitool scan", encoding="utf-8")
    devs = []
    # inquery remote devices
    scan_devs = os.popen("hcitool inq").readlines()
    if len(scan_devs) > 1:
        for _dev in scan_devs:
            if "Inquiring" in _dev:
                continue
            # devs.append(re.sub("\t", " ", dev).strip())
            # print(f" -- dev: '{dev.strip()}'")
            m, _, c = _dev.strip().split("\t")
            dev = dict()
            dev["mac"] = m
            dev["name"] = os.popen(f"hcitool name {m}").read().strip()
            dev_class = c.split(":")[1].strip()
            dev["class"] = bt_parse_cod(dev_class)
            devs.append(dev)
    return devs


def bt_scan_hid_devs() -> list:
    devs = bt_scan()
    hid_devs = []
    for dev in devs:
        if dev["class"] == "HID Device":
            hid_devs.append(dev)
    return hid_devs


def bt_scan2() -> list:
    # px = pexpect.spawn("hcitool scan", encoding="utf-8")
    devs = []
    _devs = os.popen("hcitool scan").readlines()
    if len(_devs) > 1:
        for _dev in _devs:
            if "Scanning" in _dev:
                continue
            # devs.append(re.sub("\t", " ", dev).strip())
            # print(f" -- dev: '{dev.strip()}'")
            mac, name = re.sub("\t", " ", _dev).strip().split(" ", 1)
            dev = {}
            dev["mac"] = mac
            dev["name"] = name
            devs.append(dev)
    return devs


def btctl_add(mac_address: str, timeout: int = 10) -> Optional[dict]:
    """
    Подключает HID или любое Bluetooth устройство по MAC через bluetoothctl.
    Возвращает dev_info, если подключение успешно, {} иначе.
    """
    # prompt = r"\[bluetoothctl\]>"
    prompt = r"\[.*\][#>]"
    dev_info = {}
    response = ""
    btctl = None
    try:
        btctl = pexpect.spawn("bluetoothctl", encoding="utf-8")
        # btctl.logfile_read = sys.stdout
        # btctl.logfile = open("bt_debug.log", "w")   # весь вывод в файл
        btctl.expect(prompt)  # ждём приглашения

        ### RESTART BT ADAPTER
        btctl.sendline("power off")
        btctl.expect("PowerState: off", timeout=3)
        btctl.expect(prompt)
        time.sleep(1)

        btctl.sendline("power on")
        # btctl.expect("PowerState: on", timeout=3)
        btctl.expect("Powered: yes", timeout=3)
        btctl.expect(prompt)
        time.sleep(1)
        dbg("Adapter restarted")

        ### REMOVE DEVICE (RECONNECT)
        btctl.sendline(f"remove {mac_address}")
        btctl.expect(prompt, timeout=3)

        btctl.sendline("scan on")
        btctl.expect("Discovery started", timeout=3)
        btctl.expect(prompt)
        time.sleep(1)

        dbg("Scan On")

        responses = [
            "Pairing successful",
            "Connection successful",
            # "Discovery started",
            "Failed to start discovery",
            f"Device {mac_address} not available",
            "Failed to connect",
            f"Attempting to pair with {mac_address}",
            f"Changing {mac_address} trust succeeded",
        ]

        ### PAIRING
        dbg(" === PAIRING ===")
        while response != "Pairing successful":
            btctl.sendline(f"pair {mac_address}")
            btctl.expect(list(responses))
            response = btctl.after
            dbg(f"{response}")
            time.sleep(1)
            if response == f"Device {mac_address} not available":
                timeout -= 1
            if timeout == 0:
                return {"Connected": response}

        ### TRUST
        dbg(" === TRUSTING ===")
        while response != f"Changing {mac_address} trust succeeded":
            btctl.sendline(f"trust {mac_address}")
            btctl.expect(list(responses))
            response = btctl.after
            dbg(f" {response}")
            time.sleep(1)

        ### CONNECTION
        dbg(" === CONNECTION ===")
        while response != "Connection successful":
            btctl.sendline(f"connect {mac_address}")
            btctl.expect(list(responses))
            response = btctl.after
            dbg(f" {response}")
            time.sleep(1)

        ### SCAN OFF
        btctl.sendline("scan off")
        # btctl.expect("Discovery stopped", timeout=5)
        btctl.expect(prompt, timeout=5)
        dbg(" === Scan OFF ===")  # //Dima
        # time.sleep(0.1)
        _info = ""
        while "Connected" not in _info:
            btctl.sendline(f"info {mac_address}")
            btctl.expect(f"Device {mac_address}", timeout=5)
            btctl.expect(prompt, timeout=5)
            if btctl.before is None:
                dbg("info........")  # //Dima
                time.sleep(1)
                continue
            _info = btctl.before.strip()

        btctl.sendline("quit")
        btctl.close()
        # print("=== INFO OUTPUT ===")
        # print(info)
        # print("===================")
        if not _info:
            return None
        info = _info.splitlines()
        info[0] = "Device: " + mac_address
        i = 0
        for line in info:
            if ":" in line:
                k, v = line.split(":", 1)
                field_name = k.strip()
                if field_name in dev_info:
                    i += 1
                    field_name += f"-{i}"
                dev_info[field_name] = v.strip()

    except Exception as e:
        print(f" =!= Error: {e}")
        return None

    return dev_info


def btctl_get_dev_info(mac_address: str, timeout: int = 5) -> Optional[dict]:
    prompt = r"\[.*\][#>]"
    dev_info = {}
    try:
        btctl = pexpect.spawn("bluetoothctl", encoding="utf-8")
        # btctl.logfile_read = sys.stdout
        # btctl.logfile = open("bt_debug.log", "w")   # весь вывод в файл
        btctl.expect(prompt)  # ждём приглашения

        dbg("------------")  # //Dima

        _info = ""
        while "Connected" not in _info:
            btctl.sendline(f"info {mac_address}")
            btctl.expect(f"Device {mac_address}", timeout=5)
            btctl.expect(prompt, timeout=5)
            if btctl.before is None:
                dbg("before")  # //Dima
                continue
            timeout -= 1
            if timeout == 0:
                break
            _info = btctl.before.strip()
            dbg("info....")  # //Dima
            time.sleep(1)

        btctl.sendline("quit")
        btctl.close()
        if timeout == 0:
            return None

        # print("=== INFO OUTPUT ===")
        # print(info)
        # print("===================")
        if not _info:
            return None
        info = _info.splitlines()
        info[0] = "Device: " + mac_address
        i = 0
        for line in info:
            if ":" in line:
                k, v = line.split(":", 1)
                field_name = k.strip()
                if field_name in dev_info:
                    i += 1
                    field_name += f"-{i}"
                dev_info[field_name] = v.strip()

    except Exception as e:
        print(f" =!= Error: {e}")
        return None
    return dev_info


def btctl_dev_remove(mac_address: str) -> bool:
    """Return True if no errors, False in other case"""
    # prompt = r"\[bluetoothctl\]>"
    prompt = r"\[.*\][#>]"
    # dev_info = {}
    # response = ""
    try:
        btctl = pexpect.spawn("bluetoothctl", encoding="utf-8")
        # btctl.logfile_read = sys.stdout
        # btctl.logfile = open("bt_debug.log", "w")   # весь вывод в файл
        btctl.expect(prompt)  # ждём приглашения

        ### REMOVE DEVICE (RECONNECT)
        btctl.sendline(f"remove {mac_address}")
        btctl.expect(prompt, timeout=3)
        return True
    except Exception as e:
        print(f" =!= Error: {e}")
        return False


def bt_hid_conn_devs() -> list:
    """Return list of connected bluetooth HID devices"""
    all_devs = get_connected_input_devices()
    bt_hid_devs = []
    for dev in all_devs:
        if "/uhid/" not in dev["Sysfs"]:
            continue
        bt_dev = {}
        bt_dev["name"] = dev["Name"]
        bt_dev["mac"] = dev["Uniq"]
        bt_dev["event"] = re.findall(r"event\d+", dev["Handlers"])[0]
        # bt_dev["btns"] = dev["B"]["KEY"]
        bt_hid_devs.append(bt_dev)
    return bt_hid_devs


# # Пример использования:
# if __name__ == "__main__":
#     mac = "XX:XX:XX:XX:XX:XX"  # замени на MAC твоего устройства
#     btctl_add(mac)


if __name__ == "__main__":

    dev_mac = "41:42:68:D8:DA:39"

    from difonlib.utils import print_dicts_list

    print(" ======== ALL connected devices ==========")
    all_connected_devs = get_connected_input_devices()
    print_dicts_list(all_connected_devs)

    print(" ======== HID connected devices ==========")
    conn_devs = bt_hid_conn_devs()
    print_dicts_list(conn_devs)

    # available_bt_devs = bt_scan()
    # print_lists(available_bt_devs)  # //Dima

    sys.exit(0)

    # btctl_dev_remove(dev_mac)
    # input(f" ====== After Remove {dev_mac}")
    # devs = bt_scan()
    # for dev in devs:
    #     print(f"dev: {dev}")
    # input("+++++++++++++++++++++++++++++++++")
    # sys.exit(1)

    # dev = btctl_add(dev_mac, dbg=verbose)
    # if not dev:
    #     sys.exit(1)
    # dbg(f"--------------------------")  # //Dima
    # pprint(dev)
    # dbg(f"--------------------------")  # //Dima
    # dev_status = dev.get("Connected")
    # if dev_status == "yes":
    #     print(f"Device {dev['Device']} - connected!")
    # else:
    #     print(f" =!= {dev_status}")

    # dev_info = btctl_get_dev_info(dev_mac)
    # if dev_info:
    #     pprint(dev_info)

# [dima@archryzen bluetooth_lib]$ ./bt_utils.py
# dev: 08:E9:F6:4E:99:9B n/a
# dev: D0:49:7C:DF:47:0E OnePlus Nord2 5G
# dev: 20:50:E7:58:02:6D n/a
# dev: 41:42:68:D8:DA:39 BT006
# dev: 64:57:25:7B:50:70 Smart TV Pro
# dev: 08:EB:ED:1F:AC:70 Mi Portable BT Speaker 16W


#############################################################################

#########################################################
### Как определить, что HID device является клавиатурой??
#########################################################
# I: Bus=0003 Vendor=1e4e Product=0110 Version=0201
# N: Name="USB2.0 Camera: USB2.0 Camera"
# P: Phys=usb-0000:04:00.3-2/button
# S: Sysfs=/devices/pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-2/1-2:1.0/input/input20
# U: Uniq=
# H: Handlers=kbd event17
# B: PROP=0
# B: EV=3
# B: KEY=100000 0 0 0

#############################################################################
# dima@dima-mpd ~]$ cat /proc/bus/input/devices
# I: Bus=0019 Vendor=0000 Product=0001 Version=0000
# N: Name="Power Button"
# P: Phys=PNP0C0C/button/input0
# S: Sysfs=/devices/LNXSYSTM:00/LNXSYBUS:00/PNP0C0C:00/input/input0
# U: Uniq=
# H: Handlers=kbd event0
# B: PROP=0
# B: EV=3
# B: KEY=8000 10000000000000 0

# I: Bus=0019 Vendor=0000 Product=0001 Version=0000
# N: Name="Power Button"
# P: Phys=LNXPWRBN/button/input0
# S: Sysfs=/devices/LNXSYSTM:00/LNXPWRBN:00/input/input1
# U: Uniq=
# H: Handlers=kbd event1
# B: PROP=0
# B: EV=3
# B: KEY=8000 10000000000000 0

# I: Bus=0003 Vendor=8089 Product=0003 Version=0111
# N: Name="SayoDevice SayoDevice M3K RGB"
# P: Phys=usb-0000:00:15.0-4/input0
# S: Sysfs=/devices/pci0000:00/0000:00:15.0/usb1/1-4/1-4:1.0/0003:8089:0003.0002/input/input2
# U: Uniq=0061BC18586F
# H: Handlers=sysrq kbd leds event2
# B: PROP=0
# B: EV=120013
# B: KEY=1000000000007 ff9f207ac14057ff febeffdfffefffff fffffffffffffffe
# B: MSC=10
# B: LED=1f

# I: Bus=0019 Vendor=0000 Product=0006 Version=0000
# N: Name="Video Bus"
# P: Phys=LNXVIDEO/video/input0
# S: Sysfs=/devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A08:00/LNXVIDEO:00/input/input3
# U: Uniq=
# H: Handlers=kbd event3
# B: PROP=0
# B: EV=3
# B: KEY=3e000b00000000 0 0 0

# I: Bus=0003 Vendor=8089 Product=0003 Version=0111
# N: Name="SayoDevice SayoDevice M3K RGB Mouse"
# P: Phys=usb-0000:00:15.0-4/input1
# S: Sysfs=/devices/pci0000:00/0000:00:15.0/usb1/1-4/1-4:1.1/0003:8089:0003.0003/input/input5
# U: Uniq=0061BC18586F
# H: Handlers=event4 mouse0
# B: PROP=0
# B: EV=17
# B: KEY=ff0000 0 0 0 0
# B: REL=903
# B: MSC=10

# I: Bus=0003 Vendor=8089 Product=0003 Version=0111
# N: Name="SayoDevice SayoDevice M3K RGB Consumer Control"
# P: Phys=usb-0000:00:15.0-4/input1
# S: Sysfs=/devices/pci0000:00/0000:00:15.0/usb1/1-4/1-4:1.1/0003:8089:0003.0003/input/input6
# U: Uniq=0061BC18586F
# H: Handlers=kbd event5
# B: PROP=0
# B: EV=1f
# B: KEY=3f00033fff 0 0 483ffff17aff32d bfd4444600000000 1 130ff38b17d000 677bfad9415fed 19ed68000004400 10000002
# B: REL=1040
# B: ABS=100000000
# B: MSC=10

# I: Bus=0000 Vendor=0000 Product=0000 Version=0000
# N: Name="sof-essx8336 Headset"
# P: Phys=ALSA
# S: Sysfs=/devices/pci0000:00/0000:00:0e.0/sof-essx8336/sound/card1/input7
# U: Uniq=
# H: Handlers=kbd event6
# B: PROP=0
# B: EV=23
# B: KEY=1000000000 0 0
# B: SW=14

# I: Bus=0000 Vendor=0000 Product=0000 Version=0000
# N: Name="sof-essx8336 HDMI/DP,pcm=5"
# P: Phys=ALSA
# S: Sysfs=/devices/pci0000:00/0000:00:0e.0/sof-essx8336/sound/card1/input8
# U: Uniq=
# H: Handlers=event7
# B: PROP=0
# B: EV=21
# B: SW=140

# I: Bus=0000 Vendor=0000 Product=0000 Version=0000
# N: Name="sof-essx8336 HDMI/DP,pcm=6"
# P: Phys=ALSA
# S: Sysfs=/devices/pci0000:00/0000:00:0e.0/sof-essx8336/sound/card1/input9
# U: Uniq=
# H: Handlers=event8
# B: PROP=0
# B: EV=21
# B: SW=140

# I: Bus=0000 Vendor=0000 Product=0000 Version=0000
# N: Name="sof-essx8336 HDMI/DP,pcm=7"
# P: Phys=ALSA
# S: Sysfs=/devices/pci0000:00/0000:00:0e.0/sof-essx8336/sound/card1/input10
# U: Uniq=
# H: Handlers=event9
# B: PROP=0
# B: EV=21
# B: SW=140

# I: Bus=0005 Vendor=05ac Product=022c Version=011b
# N: Name="MINI_KEYBOARD"
# P: Phys=34:6f:24:62:0b:0e
# S: Sysfs=/devices/virtual/misc/uhid/0005:05AC:022C.0004/input/input11
# U: Uniq=97:ec:92:2e:2c:e0
# H: Handlers=sysrq kbd leds event10 mouse1
# B: PROP=0
# B: EV=12001f
# B: KEY=3f00033fff 0 0 483ffff17aff32d bfd4444600000000 70001 130ff38b17d000 677bfad9415fed e19effdf01cfffff fffffffffffffffe
# B: REL=1943
# B: ABS=100000000
# B: MSC=10
# B: LED=1f

# I: Bus=0005 Vendor=05ac Product=022c Version=011b
# N: Name="MINI_KEYBOARD"
# P: Phys=34:6f:24:62:0b:0e
# S: Sysfs=/devices/virtual/misc/uhid/0005:05AC:022C.0005/input/input12
# U: Uniq=2d:bb:bc:fa:10:f5
# H: Handlers=sysrq kbd leds event11 mouse2
# B: PROP=0
# B: EV=12001f
# B: KEY=3f00033fff 0 0 483ffff17aff32d bfd4444600000000 70001 130ff38b17d000 677bfad9415fed e19effdf01cfffff fffffffffffffffe
# B: REL=1943
# B: ABS=100000000
# B: MSC=10
# B: LED=1f

# I: Bus=0005 Vendor=05ac Product=022c Version=011b
# N: Name="MINI_KEYBOARD"
# P: Phys=34:6f:24:62:0b:0e
# S: Sysfs=/devices/virtual/misc/uhid/0005:05AC:022C.0006/input/input13
# U: Uniq=8a:bd:f7:49:11:6f
# H: Handlers=sysrq kbd leds event12 mouse3
# B: PROP=0
# B: EV=12001f
# B: KEY=3f00033fff 0 0 483ffff17aff32d bfd4444600000000 70001 130ff38b17d000 677bfad9415fed e19effdf01cfffff fffffffffffffffe
# B: REL=1943
# B: ABS=100000000
# B: MSC=10
# B: LED=1f

# I: Bus=0005 Vendor=05ac Product=022c Version=011b
# N: Name="MINI_KEYBOARD"
# P: Phys=34:6f:24:62:0b:0e
# S: Sysfs=/devices/virtual/misc/uhid/0005:05AC:022C.0007/input/input14
# U: Uniq=b9:4b:6d:31:bb:97
# H: Handlers=sysrq kbd leds event13 mouse4
# B: PROP=0
# B: EV=12001f
# B: KEY=3f00033fff 0 0 483ffff17aff32d bfd4444600000000 70001 130ff38b17d000 677bfad9415fed e19effdf01cfffff fffffffffffffffe
# B: REL=1943
# B: ABS=100000000
# B: MSC=10
# B: LED=1f

# [dima@dima-mpd ~]$
