import evdev
from evdev import ecodes, InputDevice

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


def is_remote_ctrl(dev: InputDevice) -> bool:
    caps = dev.capabilities()
    if ecodes.EV_KEY not in caps:
        return False
    keys = set(caps[ecodes.EV_KEY])
    remote_keys = {
        ecodes.KEY_UP,
        ecodes.KEY_DOWN,
        ecodes.KEY_LEFT,
        ecodes.KEY_RIGHT,
        # ecodes.KEY_OK,
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
    print(f"{'Path':<18} | {'Name'}")
    print("-" * 60)

    idevs = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for dev in idevs:
        if is_remote_ctrl(dev):
            print(f"{dev.path:<18} | {dev.name}")
    print("-" * 60)
    print("-" * 60)
    for dev in get_keyboard_like_devices():
        print(f"{dev.path:<18} | {dev.name}")
