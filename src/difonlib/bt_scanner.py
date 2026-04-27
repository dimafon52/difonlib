"""
Bluetooth HID Device Scanner
Requires: pip install bleak hid
On Linux may also need: sudo apt install libhidapi-hidraw0 libhidapi-libusb0
Run with: python bt_hid_scanner.py
https://claude.ai/share/54cf3394-15f2-4ca9-8730-b70bf2973646
"""

import asyncio
import hid
import pydbus
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from ctypes import LittleEndianStructure, c_uint32

# HID Usage Page 0x01 = Generic Desktop
# HID Usages: 0x02=Mouse, 0x04=Joystick, 0x05=Gamepad, 0x06=Keyboard, 0x08=Multi-axis
HID_USAGE_NAMES = {
    0x01: "Pointer",
    0x02: "Mouse",
    0x04: "Joystick",
    0x05: "Gamepad",
    0x06: "Keyboard",
    0x07: "Keypad",
    0x08: "Multi-axis Controller",
    0x09: "Tablet PC Controls",
}


# Bluetooth HID Service UUID
HID_SERVICE_UUID = "00001812-0000-1000-8000-00805f9b34fb"

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


def bt_parse_cod(cod_val: int) -> str:
    """Разобрать Class of Device (CoD) в словарь с описанием"""
    # cod32 = c_uint32(int(cod_val, 0))
    cod32 = c_uint32(cod_val)
    fields = CoD.from_buffer_copy(cod32)
    major = fields.MajorDevClass
    return MAJOR_CLASSES.get(major, f"0x{major:02X}")


async def adapter_restart(adapter_path: str = "/org/bluez/hci0", duration: float = 0.5) -> None:
    bus = pydbus.SystemBus()
    adapter = bus.get("org.bluez", adapter_path)
    adapter.StartDiscovery()
    await asyncio.sleep(duration)
    try:
        adapter.StopDiscovery()
    except Exception:
        pass
    await asyncio.sleep(0.5)


# ─── USB HID Devices (connected right now) ────────────────────────────────────


def scan_usb_hid_devices() -> list[dict]:
    """Return a list of currently connected USB HID devices."""
    devices = []
    seen = set()

    for info in hid.enumerate():
        key = (info["vendor_id"], info["product_id"], info["usage_page"], info["usage"])
        if key in seen:
            continue
        seen.add(key)

        devices.append(
            {
                "name": info.get("product_string") or "Unknown",
                "manufacturer": info.get("manufacturer_string") or "Unknown",
                "vid": f"0x{info['vendor_id']:04X}",
                "pid": f"0x{info['product_id']:04X}",
                "usage_page": f"0x{info['usage_page']:04X}",
                "usage": HID_USAGE_NAMES.get(info["usage"], f"0x{info['usage']:04X}"),
                "serial": info.get("serial_number") or "—",
                "path": info.get("path", b"").decode(errors="replace"),
                "interface": info.get("interface_number", -1),
                "transport": "USB / HID",
            }
        )

    return devices


# ─── Bluetooth LE HID Devices (nearby) ────────────────────────────────────────


class BluetoothScanner:
    def __init__(self, duration: float = 5.0, dev_type: str = ""):
        self.duration = duration
        self.found: dict[str, dict] = {}  # addr -> device info
        self.dev_type = dev_type
        self.available_types = [v for v in MAJOR_CLASSES.values()]

    def _on_device(self, device: BLEDevice, adv: AdvertisementData) -> None:
        # print(f"device: {device}")
        # print(f"Class: {device.details['Class']}")
        # print(f"adv: {adv}")
        service_uuids = [u.lower() for u in (adv.service_uuids or [])]
        ble_hid_dev = HID_SERVICE_UUID in service_uuids
        dclass = device.details.get("props", {}).get("Class")
        # print(f" = DETAILS: {device.details}")
        dev_class = None
        if ble_hid_dev:
            dev_class = "HID Device"
        elif dclass:
            dev_class = bt_parse_cod(dclass)

        addr = device.address
        if addr in self.found:
            # update RSSI
            self.found[addr]["rssi"] = adv.rssi
            return

        self.found[addr] = {
            "name": device.name or "Unknown",
            "address": addr,
            "dev_class": dev_class,
            "rssi": adv.rssi,
            "services": service_uuids,
            "tx_power": adv.tx_power,
        }
        # print(
        #     f"  [+] Found: {device.name or 'Unknown':30s}  {addr}  RSSI {adv.rssi} dBm"
        # )
        # print(f"      service_uuids: {service_uuids}")

    def _filter(self, devs: list[dict], dev_type: str) -> list[dict]:
        _devs = []
        for dev in devs:
            if dev["dev_class"] == dev_type:
                _devs.append(dev)
        return _devs

    async def run(self) -> list[dict]:
        print(f"   Scanning BLE for {self.duration}s ...")
        async with BleakScanner(detection_callback=self._on_device):
            await asyncio.sleep(self.duration)
        if self.dev_type in self.available_types:
            return self._filter(list(self.found.values()), self.dev_type)
        elif self.dev_type != "":
            print(" =!= Device Type ERROR")
            print(f"   Type '{self.dev_type}' is not available.")
            print(f"   Available types: {self.available_types}")
        return list(self.found.values())


# def get_bt_hid_devs(devs:list[dict]) -> list[dict]:
#     hid_devs = []
#     for dev in devs:
#         if HID_SERVICE_UUID in dev["services"] or dev['dev_class'] == "HID Device":
#             hid_devs.append(dev)
#     return hid_devs


# ─── Pretty printing ───────────────────────────────────────────────────────────


def print_separator(char: str = "─", width: int = 60) -> None:
    print(char * width)


def print_usb_devices(devices: list[dict]) -> None:
    print_separator("═")
    print(f"  USB HID DEVICES  ({len(devices)} found)")
    print_separator("═")

    if not devices:
        print("  No USB HID devices found.\n")
        return

    for i, d in enumerate(devices, 1):
        print(f"\n  [{i}] {d['name']}")
        print(f"       Manufacturer : {d['manufacturer']}")
        print(f"       VID / PID    : {d['vid']} / {d['pid']}")
        print(f"       Usage        : {d['usage']}  (page {d['usage_page']})")
        print(f"       Serial       : {d['serial']}")
        print(f"       Interface    : {d['interface']}")
        print(f"       Path         : {d['path']}")

    print()


def print_bt_devices(devices: list[dict], type: str = "DEVICES") -> None:
    print_separator("═")
    print(f"  BLUETOOTH AVAILABLE {type}  ({len(devices)} found)")
    print_separator("═")

    if not devices:
        print("  No devices found.\n")
        return

    for i, d in enumerate(devices, 1):
        tx = f"{d['tx_power']} dBm" if d["tx_power"] is not None else "—"
        print(f"\n  [{i}] {d['name']}")
        print(f"       Address      : {d['address']}")
        print(f"       Services     : {d['services']}")
        print(f"       Device Class : {d['dev_class']}")
        print(f"       RSSI         : {d['rssi']} dBm")
        print(f"       TX Power     : {tx}")
        # print(f"       Transport    : {d['transport']}")

    print()


# ─── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║          Bluetooth Device Scanner                        ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # # 1. USB HID
    # print("Scanning USB HID devices ...")
    # usb_devices = scan_usb_hid_devices()
    # print_usb_devices(usb_devices)

    # # Сначала — inquiry, чтобы BlueZ узнал о Classic устройствах
    # print("Triggering Classic BT inquiry via bluetoothctl...")
    # await trigger_classic_inquiry(duration=2)

    await adapter_restart()

    # 2. BLE HID
    try:
        # bt_scanner = BluetoothScanner(duration=6.0, dev_type="Audio/Video")
        dev_type = "HID Device"
        # dev_type = ""
        bt_scanner = BluetoothScanner(duration=6.0, dev_type=dev_type)
        bt_devices = await bt_scanner.run()
        print_bt_devices(bt_devices, type=dev_type)
    except Exception as e:
        print(f"  Bluetooth device scan failed: {e}")
        print("  Make sure Bluetooth is enabled and bleak is installed.\n")
        bt_devices = []

    # # 3. Summary
    # print_separator("═")
    # total = len(usb_devices) + len(ble_devices)
    # print(
    #     f"  SUMMARY: {len(usb_devices)} USB HID + {len(ble_devices)} BLE HID = {total} total devices"
    # )
    # print_separator("═")
    # print(f"bt_devices: {bt_devices}")


if __name__ == "__main__":
    asyncio.run(main())
