from pathlib import Path
from evdev import InputDevice, categorize, ecodes, list_devices
from evdev.events import KeyEvent
from typing import Dict, Any, List, Optional

from difonlib.utils import logdbg
from dataclasses import dataclass
import re
import asyncio

dbg = logdbg

# import asyncio


@dataclass
class IDevKbd:
    """event: /dev/input/eventX"""

    name: str = ""
    uniq: str = ""
    event = ""


@dataclass
class IDevKbdKey:
    scancode: int = 0
    hold_time: float = 0
    keycode: str | tuple = ""


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


NOT_KBD_KEYWORDS = [
    "mouse",
    "hd-audio",
    "headset",
    "headphone",
    "system control",
    "video bus",
    "power button",
    "avrcp",
]


def keyboard_like(dev: Dict[str, Any]) -> bool:
    # /proc/bus/input/devices
    name = dev["Name"].lower()
    handlers = dev["Handlers"].lower()
    kw_in_name = any(kw in name for kw in NOT_KBD_KEYWORDS)
    kw_handlers = any(kw in handlers for kw in NOT_KBD_KEYWORDS)
    return not kw_in_name and not kw_handlers


def get_kbd_like_devs() -> list[str]:
    return [
        f"/dev/input/{re.findall(r"event\d+", dev['Handlers'])[0]}"
        for dev in get_connected_input_devices()
        if keyboard_like(dev)
    ]


def idev_get_dev(dev_name: str, dev_uniq: str) -> InputDevice | None:
    dev_path = [
        f"/dev/input/{re.findall(r"event\d+", dev['Handlers'])[0]}"
        for dev in get_connected_input_devices()
        if dev["Name"] == dev_name and dev["Uniq"].lower() == dev_uniq.lower()
    ]
    if dev_path:
        return InputDevice(dev_path[0])
    return None


def idev_get_connected_kbds(
    uniqs: list[str] | None = None, carefully: bool = False
) -> list[InputDevice]:
    """Use in asyc:
    1. connected_hid_devs = await asyncio.to_thread(idev_get_connected_kbds)
    2. connected_hid_devs = await asyncio.to_thread(lambda: idev_get_connected_kbds(['11:2a:3b:44:55:6c', 'F1:ba:3B:41:52:6e']))
    """
    connected_kbds = []
    _uniqs = [u.lower() for u in uniqs] if uniqs else []
    devs_list = get_kbd_like_devs() if carefully else list_devices()

    for path in devs_list:
        try:
            dev = InputDevice(path)
            if has_keys(dev):
                if uniqs:
                    if dev.uniq.lower() in _uniqs:
                        connected_kbds.append(dev)
                    else:
                        dev.close()
                else:
                    connected_kbds.append(dev)
            else:
                dev.close()
        except (OSError, PermissionError):
            continue
    return connected_kbds


def get_connected_input_devices() -> List[Dict[str, Any]]:
    path = Path("/proc/bus/input/devices")
    devices: List[Dict[str, Any]] = []
    dev: Dict[str, Any] = {}

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:  # пустая строка -> новый девайс
                if dev:
                    devices.append(dev)
                    dev = {}
                continue

            key = line[0]
            value = line[3:]  # пропускаем "X: "

            if key == "I":
                # I: Bus=0003 Vendor=05ac Product=024f Version=0111
                dev["I"] = dict(item.split("=") for item in value.split())
            elif key in ("N", "P", "S", "U", "H"):
                # Строковые поля
                k, v = value.strip().split("=", 1)
                dev[k] = v.strip('"')
            elif key == "B":
                # B: PROP=0 или B: KEY=... B: EV=...
                bkey, bval = value.split("=", 1)
                if "B" not in dev:
                    dev["B"] = {}
                dev["B"][bkey] = bval
            else:
                dev[key] = value

        # не забыть последний блок, так, на всякий случай. Обычно его там нет.
        if dev:
            devices.append(dev)

    return devices


def idev_get_by_field(field: str, field_value: str) -> Optional[List[IDevKbd]]:
    """If device connected by bluetooth - field 'Uniq' is mac address"""
    conn_devs = get_connected_input_devices()
    # dbg(f" = conn_devs: {conn_devs}")  # //Dima
    try:
        devs = [dev for dev in conn_devs if dev[field] == field_value]
    except Exception:
        return None
    kdevs = None
    if devs:
        kdevs = []
        for dev in devs:
            kdev = IDevKbd()
            kdev.name = dev["Name"]
            kdev.uniq = dev["Uniq"]
            kdev.event = re.findall(r"event\d+", dev["Handlers"])[0]
            kdevs.append(kdev)
    return kdevs


def idev_key_monitor(dev_path: str) -> Optional[IDevKbdKey]:
    """
    Wait for any pressed key on dev_event
    Return: ( key_event.scancode, hold_time, key_event.keycode )"""

    press_time: float | None = None  # timer key down timestamp
    key: IDevKbdKey | None = None

    dev = InputDevice(dev_path)
    dbg(f"Listening on: {dev.name}")
    dev.grab()  # capture input device
    for event in dev.read_loop():
        # if event.type == ecodes.EV_KEY:
        key_event = categorize(event)

        if not isinstance(key_event, KeyEvent):
            continue

        if key_event.keystate == KeyEvent.key_down:
            press_time = key_event.event.timestamp()

        elif key_event.keystate == KeyEvent.key_up and press_time is not None:
            key = IDevKbdKey()
            key.hold_time = round(key_event.event.timestamp() - press_time, 2)
            key.scancode = key_event.scancode
            key.keycode = (
                key_event.keycode
                if not isinstance(key_event.keycode, list)
                else key_event.keycode[0]
            )
            break
    dev.ungrab()
    dev.close()
    return key


async def idev_get_pressed_key(dev_path: str, timeout: int = 5) -> Optional[IDevKbdKey | OSError]:
    """
    Wait timeout seconds for pressed key on dev_event
    """
    dev = InputDevice(dev_path)
    dbg(f" - Listening on: {dev.name}")
    dev.grab()
    try:
        key = await asyncio.wait_for(
            _get_first_key_event(dev),
            timeout=timeout,
        )
        return key
    except OSError as e:
        print(f"❌ {e}")
        return e
    except asyncio.CancelledError:
        print(" =!= idev_get_pressed_key cancelled")
        raise
    except Exception as e:
        print(f" =!= Error: {e}")
    finally:
        dev.ungrab()
        dev.close()
    return None


async def _get_first_key_event(dev: InputDevice) -> Optional[IDevKbdKey]:
    press_time: float | None = None

    async for event in dev.async_read_loop():
        key_event = categorize(event)

        if not isinstance(key_event, KeyEvent):
            continue

        if key_event.keystate == KeyEvent.key_down:
            press_time = key_event.event.timestamp()

        elif key_event.keystate == KeyEvent.key_up and press_time is not None:
            key = IDevKbdKey()
            key.hold_time = round(key_event.event.timestamp() - press_time, 2)
            key.scancode = key_event.scancode
            key.keycode = (
                key_event.keycode
                if not isinstance(key_event.keycode, list)
                else key_event.keycode[0]
            )
            return key

    return None


# U: Uniq=40:b4:cd:ce:31:d6
if __name__ == "__main__":
    dbg(" == START ==")  # //Dima
    # devs = get_connected_input_devices()
    # print_dicts_list(devs)
    # dbg(f"---------------------------------------------")  # //Dima
    # exit()
    # devs = idev_kbd_get_by_uniq("40:B4:cd:CE:31:d6")
    # print(f"devs: {devs}")
    # exit()
    # monitored_devs = [
    #     "40:b4:cd:ce:31:d6",  # Amazon Fire TV Remote
    #     "ff:23:05:30:30:8c",  # HID Remote01
    #     "c1:03:01:5a:02:95",  # BOXPUT BPR1 c1:03:01:5c:02:95
    # ]

    for dev in idev_get_connected_kbds():
        print(f"{dev.path:<18} | {dev.name}")

    import asyncio
    import functools

    async def test_idev_get_connected_kbds(
        uniqs: list[str] | None = None,
    ) -> list[InputDevice]:
        return await asyncio.to_thread(lambda: idev_get_connected_kbds(uniqs))

    async def testA_idev_get_connected_kbds(
        uniqs: list[str] | None = None,
    ) -> list[InputDevice]:
        return await asyncio.to_thread(functools.partial(idev_get_connected_kbds, uniqs))

    async def test2_idev_get_connected_kbds() -> list[InputDevice]:
        return await asyncio.get_running_loop().run_in_executor(None, idev_get_connected_kbds)

    print("-" * 65)
    con_devs = asyncio.run(test_idev_get_connected_kbds())
    print(f"con_devs: {[dev.name for dev in con_devs]}")
    print("-" * 55)
    con_devs = asyncio.run(test2_idev_get_connected_kbds())
    print(f"con_devs: {[dev.name for dev in con_devs]}")
    print("-" * 55)
    con_devs = asyncio.run(
        testA_idev_get_connected_kbds(uniqs=["40:b4:cd:ce:31:d6", "c1:03:01:5c:02:95"])
    )
    print(f"con_devs: {[(dev.name, dev.uniq) for dev in con_devs]}")
    """
    https://claude.ai/share/342dbe4e-3eff-4732-8249-bd68837c6fba
       Oба варианта корректны и делают одно и то же. Разница чисто косметическая:
    asyncio.to_thread — это обёртка над run_in_executor(None, ...),
    добавленная в Python 3.9 именно чтобы не писать get_running_loop() вручную.
    Используй to_thread — он чище и современнее.
    run_in_executor оставь для случаев когда нужен кастомный executor (например ThreadPoolExecutor с лимитом потоков).
    
       Передача параметров:
    await asyncio.to_thread(
        lambda: idev_get_connected_kbds(uniqs=["aa:bb:cc:dd:ee:ff"])
    )
    import functools
    await asyncio.to_thread(functools.partial(idev_get_connected_kbds, uniqs=["aa:bb:cc:dd:ee:ff"]))
    """
    # devs = idev_get_by_field("Name", "Keychron Keychron K5")
    # if devs:
    #     for dev in devs:
    #         dbg(f"dev: {dev.__dict__}")  # //Dima

    # devs = idev_get_by_field(field="Uniq", field_value="40:b4:cd:ce:31:d6")
    # # print(repr(f"dev: {dev.__dict__}"))
    # if devs:
    #     dev = devs[0]
    #     dbg(f"Input dev: {dev.__dict__}")

    #     key = idev_key_monitor(dev.event)
    #     dbg(f"Pressed key: {key.__dict__}")

    #     key = asyncio.run(idev_get_pressed_key(dev.event))
    #     if key:
    #         dbg(f"Pressed key: {key}")
    #         dbg(f"Pressed key: {key.__dict__}")

    dbg(" == FINISH ==")  # //Dima
