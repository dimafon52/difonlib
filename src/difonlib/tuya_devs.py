#!/usr/bin/env python

# 24.07.25

from typing import Any, Optional, Dict, cast, List
import xmltodict  # pip install xmltodict
import json
import os
from pathlib import Path
import tinytuya
from tinytuya import Contrib

# from typing import Dict, Optional, cast, Any, Callable, Type, LiteralString
# import ctypes

### export PYTHONPATH=$HOME/tips/devel/python/pymylib
from difonlib.utils import print_dicts

cur_dir = os.path.dirname(os.path.realpath(__file__))

# {'@name': 's_home_data23007434', '#text': '{"deviceRespBeen":[{"activeTime":1752406424,"devId":"bf36796bdace7a62fav1ys","displayOrder":0,"dpMaxTime":1752406939811,"dpName":{},"dps":{"1":true,"17":0,"18":0,"19":0,"20":2328,"21":1,"22":578,"23":29500,"24":15873,"25":2620,"26":0,"38":"memory","39":false,"40":"relay","41":false,"42":"","43":"","44":"","9":0},"errorCode":0,"iconUrl":"https://images.tuyaeu.com/smart/program_category_icon/cz.png","isShare":false,"key":"bf36796bdace7a62fav1ys","lat":"32.094","localKey":"lXeI5[a5-~F}MQAi","lon":"34.8863","moduleMap":{"mcu":{"cadv":"","isOnline":true,"verSw":"1.1.8"},"wifi":{"bv":"40.00","cadv":"1.0.3","isOnline":true,"pv":"2.2","verSw":"1.1.8"}},"name":"Outlet-20A-2","productId":"qm0iq4nqnrlzh4qc","resptime":0,"runtimeEnv":"prod","timezoneId":"Asia/Jerusalem","uuid":"6b789696c51d698a","virtual":false},

tuya_xml_data_file = Path(
    os.path.join(
        cur_dir,
        "./docker-android/shared_prefs/preferences_global_keyeu1609443890901OWMrJ.xml",
    )
)


class TuyaDevs:
    def __init__(
        self,
        xml_file: Path = tuya_xml_data_file,
        file_scan_result: str = "snapshot.json",
    ):
        self.fscan_result = file_scan_result
        self.xml_file = xml_file
        self.devs_cfg = self.load_cfg()

    def load_cfg(self) -> List[Dict[str, Any]]:
        """Return list of tuya devices as list of dictionaries"""
        with open(self.xml_file) as fxml:
            data_dict = xmltodict.parse(fxml.read())
            txt = data_dict["map"]["string"][3]["#text"]
            devices = json.loads(txt)["deviceRespBeen"]
        return cast(List[Dict[str, Any]], devices)

    def get_localkey(self, id: str) -> Optional[str]:
        """Get localKey by device ID (key)"""
        for dev in self.devs_cfg:
            # print_dicts(dev)
            if not dev["localKey"]:
                continue
            if dev["key"] == id:
                return cast(str, dev["localKey"])
        return None

    def get_dev(self, id: str) -> Optional[Dict[str, Any]]:
        """Return device config by ID, or None if not found."""
        for dev in self.devs_cfg:
            if dev["key"] == id:
                return dev
        return None

    # def _scan(self, force_update=False) -> Optional[Dict[str, str]]:
    def _scan(self, force_update: bool = False) -> dict:
        """Get last list of connected devices
        If force_update=True - Get connected devives for now
        """
        if not os.path.isfile(self.fscan_result) or force_update:
            tinytuya.scan()
        with open(self.fscan_result) as f:
            scan_data: dict = json.load(f)
        return cast(dict, scan_data["devices"])

    def connected_devs(self, force_update: bool = False) -> list:
        """
        If force_update=True - get connected devives for now
        if not then last scan of connected devices from self.fscan_result
        """
        con_devs = []
        connected_devices = self._scan(force_update)
        for con_dev in connected_devices:
            dev_id = con_dev["id"]
            dev_ip = con_dev["ip"]
            dev_descript = self.get_dev(dev_id)
            dev_name = None
            dev_lk = None
            if dev_descript:
                dev_name = dev_descript["name"]
                dev_lk = dev_descript["localKey"]
            con_devs += [{"id": dev_id, "ip": dev_ip, "name": dev_name, "localkey": dev_lk}]
        return con_devs

    def all_devs(self) -> list:
        """
        If force_update=True - get connected devives for now
        if not then last scan of connected devices from self.fscan_result
        """
        all_devs = []
        for con_dev in self.devs_cfg:
            dev_id = con_dev["devId"]
            dev_descript = self.get_dev(dev_id)
            dev_name = None
            dev_lk = None
            if dev_descript:
                dev_name = dev_descript["name"]
                dev_lk = dev_descript["localKey"]
            all_devs += [{"id": dev_id, "name": dev_name, "localkey": dev_lk}]
        return all_devs

    def ir_connect_to_dev(
        self, dev_id: str, local_key: str
    ) -> Optional[Contrib.IRRemoteControlDevice]:
        try:
            ir_dev = Contrib.IRRemoteControlDevice(
                dev_id=dev_id,
                # address            = '192.168.0.89', #- no must
                local_key=local_key,
                persist=True,
                connection_timeout=5,
            )
        except Exception as e:
            print(f" =!= ir_connect_to_dev(): {e}")
            return None
        return ir_dev

    # learn a new IR button key
    def ir_receive_button(
        self, ir_dev: Optional[Contrib.IRRemoteControlDevice], timeout: int = 20
    ) -> Optional[str]:
        if not ir_dev:
            print(f" =!= IR device is not connected! ir_dev:{ir_dev}")
            return None
        print("Press button on your remote control")
        button = ir_dev.receive_button(timeout=timeout)
        if isinstance(button, str):
            return button
        return None


dbg = print
if __name__ == "__main__":

    # devs_list = tuya_xml_cfg_get_data(tuya_xml_data_file)

    # from pymylib import print_dicts

    # for i, dev in enumerate(devs_list, start=1):
    #     # print(f" {i}) {dev}")
    #     print(f"----------------------- {i} --------------------------")
    #     print_dicts(dev)
    #     print(f"-----------------------------------------------------")

    # to = TuyaDevsData(xml_file=tuya_xml_data_file)
    td = TuyaDevs(xml_file=tuya_xml_data_file)

    for i, _dev in enumerate(td.devs_cfg, start=1):
        # print(f" {i}) {dev}")
        print(f"----------------------- {i} --------------------------")
        print_dicts(_dev)
        print("-----------------------------------------------------")

    dev_id = "bf04409288bdad3dd5dx35"

    dev = td.get_dev(dev_id)
    dbg(f"dev: {dev}")  # //Dima

    localkey = td.get_localkey(dev_id)
    dbg(f"dev_id: {dev_id}; localkey: {localkey}")  # //Dima

    dev_id = "bf54140ad95255549f5d2h"
    localkey = td.get_localkey(dev_id)
    dbg(f"dev_id: {dev_id}; localkey: {localkey}")  # //Dima

    all_devs = td.all_devs()
    for i, dev in enumerate(all_devs, start=1):
        # print(f" {i}) {dev}")
        print(f"----------------------- {i} --------------------------")
        print_dicts(dev)
        print("-----------------------------------------------------")

    con_devs = td.connected_devs()
    for i, dev in enumerate(con_devs, start=1):
        # print(f" {i}) {dev}")
        print(f"----------------------- {i} --------------------------")
        print_dicts(dev)
        print("-----------------------------------------------------")

    # con_devs = td.tuya_devs(force_update=True)
    # for i, dev in enumerate(con_devs, start=1):
    #     # print(f" {i}) {dev}")
    #     print(f"----------------------- {i} --------------------------")
    #     print_dicts(dev)
    #     print(f"-----------------------------------------------------")
