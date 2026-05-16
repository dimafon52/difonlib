import evdev
from evdev import ecodes, InputDevice
from difonlib.input_devs import get_connected_input_devices
import re

NOT_KBD_KEYWORDS = [
    "mouse",
    "hd-audio",
    "headset",
    # "headphone",
    "system control",
    "video bus",
    "power button",
    "avrcp",
]


def maybe_keyboard(dev: dict) -> bool:
    # /proc/bus/input/devices
    name = dev["Name"].lower()
    handlers = dev["Handlers"].lower()
    kw_in_name = any(kw in name for kw in NOT_KBD_KEYWORDS)
    kw_handlers = any(kw in handlers for kw in NOT_KBD_KEYWORDS)
    return not kw_in_name and not kw_handlers


def get_keyboard_like_devices() -> list[InputDevice]:
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    keyboard_likes = []
    for device in devices:
        caps = device.capabilities()
        if evdev.ecodes.EV_KEY not in caps:
            continue
        name_lower = device.name.lower()
        if any(kw in name_lower for kw in NOT_KBD_KEYWORDS):
            continue
        keyboard_likes.append(device)
    return keyboard_likes


def has_keys(dev: InputDevice) -> bool:
    caps = dev.capabilities()
    if ecodes.EV_KEY not in caps:
        return False
    keys = set(caps[ecodes.EV_KEY])
    remote_keys = {
        ecodes.KEY_UP,
        ecodes.KEY_DOWN,
        ecodes.KEY_LEFT,
        ecodes.KEY_RIGHT,
        ecodes.KEY_OK,
        # ecodes.KEY_SELECT,
        # ecodes.KEY_BACK,
        # ecodes.KEY_PLAYPAUSE,
        # ecodes.KEY_VOLUMEUP,
        # ecodes.KEY_VOLUMEDOWN,
        # ecodes.KEY_HOME,
        # ecodes.KEY_MENU,
        # ecodes.KEY_NEXT,
        # ecodes.KEY_PREVIOUS,
    }
    return bool(remote_keys & keys)


if __name__ == "__main__":

    cdevs = get_connected_input_devices()
    for cdev in cdevs:
        print(f"{cdev['Name']:<42} | maybe keyboard: {maybe_keyboard(cdev)}")
        event = f"/dev/input/{re.findall(r"event\d+", cdev["Handlers"])[0]}"
        dev = InputDevice(event)
        hk = has_keys(dev)
        abs = ecodes.EV_ABS in dev.capabilities()
        print(f" {event} has_keys: {hk} ecodes.EV_ABS in dev.capabilities(): {abs}\n")

    for cdev in cdevs:
        if maybe_keyboard(cdev):
            event = f"/dev/input/{re.findall(r"event\d+", cdev["Handlers"])[0]}"
            dev = InputDevice(event)
            if has_keys(dev):
                print(f"{dev.name} {dev.path} {ecodes.EV_ABS in dev.capabilities()}")

    #######################################################
    #######################################################
    #######################################################
    # print(f"{'Path':<18} | {'Name'}")
    # print("-" * 60)

    # idevs = [evdev.InputDevice(path) for path in evdev.list_devices()]
    # for dev in idevs:
    #     if has_keys(dev):
    #         print(f"{dev.path:<18} | {dev.name}")
    # print("-" * 60)
    # print("-" * 60)
    # for dev in get_keyboard_like_devices():
    #     print(f"{dev.path:<18} | {dev.name}")
