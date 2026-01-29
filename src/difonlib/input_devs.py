from pathlib import Path
from evdev import InputDevice, categorize
from evdev.events import KeyEvent
from typing import Dict, Any, List, Optional
from difonlib.utils import logdbg
from dataclasses import dataclass
import re
import asyncio

dbg = logdbg

# import asyncio

KEY_LONG_PRESSED = 1000
KEY_LONG_TIME_HOLD = 0.7


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


def idev_key_monitor(dev_event: str) -> Optional[IDevKbdKey]:
    """
    Wait for any pressed key on dev_event
    Return: ( key_event.scancode, hold_time, key_event.keycode )"""

    press_time: float | None = None  # timer key down timestamp
    key: IDevKbdKey | None = None

    dev = InputDevice(f"/dev/input/{dev_event}")
    dbg(f"Listening on: {dev.name}")

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
    dev.close()
    return key


async def idev_get_pressed_key(dev_event: str, timeout: int = 5) -> Optional[IDevKbdKey]:
    """
    Wait timeout seconds for pressed key on dev_event
    """
    dev = InputDevice(f"/dev/input/{dev_event}")
    dbg(f" - Listening on: {dev.name}")
    # key = await _get_first_key_event(dev)
    try:
        # asyncio.wait_for ограничивает выполнение асинхронной задачи по времени
        key = await asyncio.wait_for(
            # Вложенная функция, которая читает loop и возвращает первое событие
            _get_first_key_event(dev),
            timeout=timeout,
        )
        return key
    except asyncio.CancelledError:
        print(" =!= idev_get_pressed_key cancelled")
        raise
    except asyncio.TimeoutError:
        print(f" =!= Timeout ({timeout} sec)")
    except Exception as e:
        print(f" =!= Error: {e}")

    finally:
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
    devs = idev_get_by_field("Name", "Keychron Keychron K5")
    if devs:
        for dev in devs:
            dbg(f"dev: {dev.__dict__}")  # //Dima

    devs = idev_get_by_field(field="Uniq", field_value="40:b4:cd:ce:31:d6")
    # print(repr(f"dev: {dev.__dict__}"))
    if devs:
        dev = devs[0]
        dbg(f"Input dev: {dev.__dict__}")

        key = idev_key_monitor(dev.event)
        dbg(f"Pressed key: {key.__dict__}")

        key = asyncio.run(idev_get_pressed_key(dev.event))
        if key:
            dbg(f"Pressed key: {key}")
            dbg(f"Pressed key: {key.__dict__}")

    dbg(" == FINISH ==")  # //Dima
