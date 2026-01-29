from difonlib.utils import logdbg
from difonlib.bt_utils import bt_hid_conn_devs, get_connected_input_devices

# import pytest

dbg = logdbg


def test_bt_utils():
    assert type(bt_hid_conn_devs()) is list, "Return value type is not list"
    assert type(get_connected_input_devices()) is list, "Return value type is not list"
    # answer = input("Please connect any HID device to your PC, Y/n ?")
    # if answer.upper() == "Y":
    #     hid_devs = bt_hid_conn_devs()
    #     dbg(f"hid_devs: {hid_devs}")  # //Dima
    #     assert hid_devs != [], "List of connected HID devs is empty"
