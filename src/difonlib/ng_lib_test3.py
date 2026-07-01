import asyncio
from nicegui import ui
from ng_lib import CardTable, DialogBox
import functools
import threading
import time

from difonlib.bt_utils import logdbg

dbg = logdbg


def proc_dummy2(cancel_event: threading.Event) -> None:
    for i in range(10, 0, -1):
        if cancel_event.is_set():
            print("Exit")
            return
        print(f"Remaining: {i}")
        time.sleep(1)


def proc_dummy(cnt: int = 20) -> None:
    for i in range(cnt, 0, -1):
        print(f"Remaining: {i}")
        time.sleep(1)


async def aproc_dummy(cnt: int = 20) -> int:
    for i in range(cnt, 0, -1):
        print(f"aRemaining: {i}")
        await asyncio.sleep(2)
        raise RuntimeError("Runtime ERROR simulation")
    return 125


@ui.page("/", dark=True)
def main() -> None:

    card_table = CardTable(
        title="Connected Devices",
        columns=[
            {"name": "id", "label": "id", "field": "id"},
            {"name": "name", "label": "Name", "field": "name"},
            {"name": "ip", "label": "IP Address", "field": "ip"},
        ],
        selection="single",
        rows=[
            {"id": "123456", "name": "ANNNNN", "ip": "192.168.0.18"},
            {"id": "987654", "name": "VNNNNN", "ip": "192.168.0.118"},
            {"id": "123456", "name": "BNNNNN", "ip": "192.168.0.12"},
            {"id": "003456", "name": "SNNNNN", "ip": "192.168.0.144"},
            {"id": "129956", "name": "QNNNNN", "ip": "192.168.0.49"},
        ],
    )

    found = card_table.mark_row(id="123456", mark=True)
    print(f"card_table.table.rows:{card_table.table.rows}")  # //Dima
    found = card_table.mark_row(id="123456", name="ANNNNN", mark=False)
    found = card_table.mark_row(id="129956")
    print(f" ==> found: {found}")  # //Dima

    card_table.set_row_display_filter(_marked=True)
    # card_table.set_row_display_filter(id="123456")

    # self.table.props(':filter="\'online\'"')
    # self.table.update()

    # def only_marked(mark: bool = False, def_value="\\'\\'") -> None:
    #     print(f"table rows: {card_table.table.rows}")
    #     field_value = def_value
    #     vv = "123456"
    #     vv = mark
    #     # vv = "true"
    #     if mark:
    #         dbg(f" === MARK ===")  # //Dima
    #         if isinstance(vv, str):
    #             field_value = f"\\'{vv}\\'"
    #         else:
    #             field_value = mark
    #     else:
    #         dbg(f" === NOT MARK ===")  # //Dima
    #     dbg(f" * field_value: {field_value}")  # //Dima
    #     card_table.table.props(f':filter="{field_value}"')
    #     card_table.table.update()

    # card_table.add_checkbox(chbox_txt="Used Only", on_change=lambda v: ui.notify(v))
    # card_table.add_checkbox(chbox_txt="Used Only", on_change=lambda v: only_marked(v))
    card_table.add_checkbox(
        chbox_txt="Used Only",
        on_change=lambda v: card_table.row_display_filter(v),
    )

    dialog_box = DialogBox()

    def btnok() -> None:
        ui.notify("You press OK")

    def btncancel() -> None:
        ui.notify("You press Cancel")

    card_table.add_button(
        "test_ok_cancel",
        on_click=functools.partial(
            dialog_box.dialog_ok_cancel,
            text="OK or Cancel?",
            on_click_ok=btnok,
            on_click_cancel=btncancel,
        ),
    )

    async def confirm() -> None:
        result = await dialog_box.dialog_confirm()
        ui.notify(f"You chose {result}")

    card_table.add_button(
        "test_confirm",
        on_click=confirm,
    )

    async def dialog_input() -> None:
        inp = await dialog_box.dialog_input("Input IR_KEY_NAME", input_prefix="IR_KEY_")
        ui.notify(f"Your input: {inp}")

    card_table.add_button(
        "test_input",
        on_click=dialog_input,
    )

    async def proc_dialog() -> None:
        try:
            result = await dialog_box.dialog_processing(
                functools.partial(aproc_dummy, cnt=4),
                timeout=5,  # btn_cancel=None
            )
            ui.notify(f"Result: {result}")
        except Exception as e:
            ui.notify(e, type="negative")

    ui.button(
        "Test processing dialog",
        on_click=proc_dialog,
        # on_click=lambda: dialog_box.dialog_processing(proc_dummy, timeout=4),
        # on_click=lambda: dialog_box.dialog_processing(
        #     functools.partial(aproc_dummy, cnt=5), timeout=6
        # ),
        # on_click=lambda: dialog_box.dialog_processing(
        #     proc_dummy2, proc_cancel_event=True, timeout=4
        # ),
    )


ui.run(port=1111)
