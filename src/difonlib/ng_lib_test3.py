from typing import Callable
from nicegui import ui
from ng_lib import CardTable
import functools

from difonlib.bt_utils import logdbg

dbg = logdbg


class DialogBox:

    def __init__(self) -> None:
        self.dialog: ui.dialog | None = None
        # https://claude.ai/share/227ce46f-f825-4783-8e0e-9e774963ec84
        #         Или точечнее — только ui.label внутри диалога:
        #         python.q-dialog .q-card .q-item__label {
        #             font-size: 20px !important;
        #         }
        #         Либо ещё проще — прямо в коде диалога:
        #         ui.label(text=text).classes("text-xl")
        #         text-xl — это Tailwind, соответствует 1.25rem. Если нужно крупнее — text-2xl, text-3xl.

        ui.add_css("""
            .q-notification__message {
            font-size: 20px !important;
            }
            .q-dialog .q-card {
            font-size: 20px !important;
            }
            """)

    async def dialog_ok(self, text: str = "Hello!)") -> None:
        with ui.dialog().props("persistent") as dialog, ui.card():
            ui.label(text=text)
            ui.button("Close", on_click=dialog.close)
        dialog.open()

    async def dialog_ok_cancel(
        self,
        text: str,
        on_click_ok: Callable,
        on_click_cancel: Callable = lambda: None,
        btn_ok: str = "OK",
        btn_cancel: str = "Cancel",
    ) -> None:
        with ui.dialog().props("persistent") as dialog, ui.card():
            ui.label(text=text)
            with ui.row():
                ui.button(
                    btn_ok,
                    on_click=lambda: (on_click_ok(), dialog.close()),
                )
                ui.button(btn_cancel, on_click=lambda: (on_click_cancel(), dialog.close()))
        dialog.open()

    async def dialog_confirm(
        self, text: str = "Are you sure?", btn_ok: str = "Yes", btn_cancel: str = "No"
    ) -> ui.dialog:
        with ui.dialog().props("persistent") as dialog, ui.card():
            ui.label(text=text)
            with ui.row():
                ui.button(btn_ok, on_click=lambda: dialog.submit(btn_ok))
                ui.button(btn_cancel, on_click=lambda: dialog.submit(btn_cancel))
        return await dialog

    async def dialog_input(
        self,
        text: str,
        on_click_ok: Callable,
        btn_ok: str = "OK",
        btn_cancel: str = "Cancel",
    ) -> None:
        with ui.dialog().props("persistent") as dialog, ui.card():
            ui.label(text=text)
            with ui.row():
                ui.button(
                    text=btn_ok,
                    on_click=lambda: (on_click_ok(), dialog.close()),
                )
                ui.button(btn_cancel, on_click=dialog.close)
        dialog.open()


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
    print(f" ==> found: {found}")  # //Dima

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


ui.run(port=1111)
