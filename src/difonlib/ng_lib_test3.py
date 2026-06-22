from nicegui import ui
from ng_lib import CardTable, DialogBox
import functools

from difonlib.bt_utils import logdbg

dbg = logdbg


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

    print(f"card_table.table.rows: {card_table.table.rows}")

    card_table.add_checkbox(chbox_txt="Used Only", on_change=lambda v: ui.notify(v))

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


ui.run(port=1111)
