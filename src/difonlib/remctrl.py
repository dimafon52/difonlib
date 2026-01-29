import asyncio
from difonlib.input_devs import idev_get_pressed_key, IDevKbdKey
from difonlib.utils import logdbg, YamlConfig
from typing import List, Optional  # Dict, Any, List

dbg = logdbg

KEY_LONG_PRESSED_TIME = 0.7
KEY_LONG_PRESSED_CONST = 1000


class RemoteControls:
    """
    Remote Control.
    1. Learn buttons
       Bind func_keys with remote control buttons
    2. Run monitor service of remote control pressed button (async mode)
    """

    def __init__(self, config_file_name: str) -> None:
        # Load(create) config file
        self.config = YamlConfig(config_file_name)
        if self.config.config == {}:
            self.config.config["infrared_devs"] = {}  # {dev_id:xxx, dev_local_key:xxx}
            self.config.config["remctrl_devs"] = {}
            self.config.config["func_keys"] = []
            self.config.save()

        self.cfg_ir_devs = self.config.config["infrared_devs"]
        self.cfg_rc_devs = self.config.config["remctrl_devs"]
        self.cfg_func_keys = self.config.config["func_keys"]

        # if self.func_keys != self.cfg_func_keys:
        #     self.cfg_func_keys = self.func_keys
        #     self.config.save()

    def set_func_keys(self, func_keys: List[str]) -> None:
        if func_keys != self.cfg_func_keys:
            self.config.config.update({"func_keys": func_keys})
            self.cfg_func_keys = self.config.config["func_keys"]
            self.config.save()

    def remove_func_btn(self, remctrl_name: str, func_key: Optional[str] = None) -> None:
        if not func_key:
            # remove remctrl_name from config
            try:
                self.config.config.pop(remctrl_name)
            except Exception:
                pass
        else:
            self.config.config[remctrl_name][func_key] = None
        self.config.save()

    def get_func_btn(self, rem_ctrl_name: Optional[str] = None) -> list:
        rem_ctrl = self.cfg_rc_devs.get(rem_ctrl_name)
        if rem_ctrl:
            dbg(f" * rem_ctrl: {rem_ctrl}")  # //Dima
            fs = [{f: rem_ctrl.get(f)} for f in self.cfg_func_keys]
            return fs
        fs = [{f: None} for f in self.cfg_func_keys]
        return fs

    def get_func_btn_format(
        self,
        func_field_name: str,
        btn_field_name: str,
        rem_ctrl_name: Optional[str] = None,
    ) -> list:
        _rows = self.get_func_btn(rem_ctrl_name)
        rows = [
            {
                func_field_name: list(row.keys())[0],
                btn_field_name: list(row.values())[0],
            }
            for row in _rows
        ]
        return rows

    async def devs_monitor(self) -> None:
        """
        Monitor input event devices for pressed key
        Detect pressed key and call handler('KEY_XXXXXX')
        """
        pass

    async def get_pressed_button(self, dev_event: str, timeout: int = 7) -> Optional[IDevKbdKey]:
        key = await idev_get_pressed_key(dev_event, timeout=timeout)
        dbg(f" * Pressed KEY: {key}")  # //Dima
        return key

    async def learn_button(
        self, idev_name: str, idev_event: str, func_key: str, timeout: int = 10
    ) -> Optional[IDevKbdKey]:
        # dbg(f"self.cfg_func_keys: {self.cfg_func_keys}")  # //Dima
        if func_key not in self.cfg_func_keys:
            print(f" =!= func_key: '{func_key}' is not exist")
            return None

        # dbg(f"*** CONFIG: {self.config.config}")  # //Dima
        # idev_name = idev["name"]
        # # dev_uniq = idev["mac"]
        # idev_event = idev["event"]
        key = await idev_get_pressed_key(idev_event, timeout=timeout)
        dbg(f" * Pressed KEY: {key}")  # //Dima
        if key:
            key_scan_code = key.scancode
            if key.hold_time > KEY_LONG_PRESSED_TIME:
                key_scan_code += KEY_LONG_PRESSED_CONST
            if not self.cfg_rc_devs.get(idev_name):
                self.cfg_rc_devs[idev_name] = {}
            # self.config.config["remctrl_devs"].add(dev_uniq)
            self.cfg_rc_devs[idev_name].update({func_key: key_scan_code})
            self.config.save()

        return key


if __name__ == "__main__":

    REMOTE_CTRL_CONFIG = "./___remctrl_devs_config.yaml"
    func_keys = [
        "KEY_PREV",
        "KEY_PLAY_ALBUM",
        "KEY_PAUSE_PLAY",
        "KEY_NEXT",
        "KEY_SEEKCUR",
        "KEY_RADIO",
        "KEY_JUKEBOX_ON",
        "KEY_PLAY_LIKE",
        "KEY_SET_LIKE",
        "KEY_VOL+",
        "KEY_VOL-",
        "KEY_OnOff",
        "KEY_EXT_DISP",
    ]

    rc = RemoteControls(REMOTE_CTRL_CONFIG)
    rc.set_func_keys(func_keys)

    from difonlib.input_devs import idev_get_by_field

    remctrl_name = "Amazon Fire TV Remote Keyboard"
    idev_kbd = idev_get_by_field(field="Name", field_value=remctrl_name)

    if idev_kbd:
        key = asyncio.run(
            rc.learn_button(
                idev_name=remctrl_name,
                idev_event=idev_kbd[0].event,
                func_key="KEY_PAUSE_PLAY",
            )
        )
        dbg(f"key: {key}")  # //Dima
    else:
        dbg(f"The Input Device '{remctrl_name}' is not connected.")  # //Dima
    fb = rc.get_func_btn(remctrl_name)
    dbg(f"Function-Button: {fb}")  # //Dima
