from nicegui import ui
import inspect
import asyncio
from typing import Any, Callable, Awaitable, Literal

from difonlib.utils import logdbg

dbg = logdbg
# https://claude.ai/share/227ce46f-f825-4783-8e0e-9e774963ec84
#         Или точечнее — только ui.label внутри диалога:
#         python.q-dialog .q-card .q-item__label {
#             font-size: 20px !important;
#         }
#         Либо ещё проще — прямо в коде диалога:
#         ui.label(text=text).classes("text-xl")
#         text-xl — это Tailwind, соответствует 1.25rem. Если нужно крупнее — text-2xl, text-3xl.
ui.add_css(
    """
    .q-notification__message {
    font-size: 20px !important;
    }
    .q-dialog .q-card {
    font-size: 20px !important;
    }
    """,
    shared=True,
)


class DialogBox:
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
                ui.button(
                    btn_cancel, on_click=lambda: (on_click_cancel(), dialog.close())
                )
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
    ) -> ui.dialog:
        with ui.dialog().props("persistent") as dialog, ui.card():
            ui.label(text=text)
            with ui.row():
                inp: ui.input = ui.input(label="IR button").on(
                    "keydown.enter", lambda: dialog.submit(inp.value)
                )
                ui.button(text="Enter", on_click=lambda: dialog.submit(inp.value))
        return await dialog


class CardTable:
    _current_yes_handler: Callable[[], None | Awaitable[None]] | None = None

    def __init__(
        self,
        title: str,
        columns: list,
        rows: list[dict] | None = None,
        selection: Literal["single", "multiple"] | None = None,
        on_selection_change: list[Callable] | None = None,
        marked_text_color: str = "yellow",
        marked_field: str = "_marked",
    ):
        self.on_selection_change: list[Callable] = on_selection_change or []
        self.buttons_on_row_select_changed: list = []
        self.marked_text_color = marked_text_color
        self.marked_field = marked_field

        with ui.card().classes("p-4 shadow-lg") as self.card:
            with ui.row().classes("items-center justify-between w-full mb-2"):
                ui.label(f"📋 {title}").classes("text-green-700 text-lg font-bold")
                with ui.row().classes("gap-2") as self.top_table:
                    pass

            self.table = ui.table(
                columns=self._normalize_columns(columns),
                rows=self.enum_data(rows or []),
                row_key="sn",
                selection=selection,
                on_select=self._on_selection_change,
                column_defaults={
                    "align": "left",
                    "headerClasses": "uppercase",
                },
            ).classes("w-full shadow-lg bg-black-900 text-gray-200")

            with (
                ui.dialog().props("persistent") as self.confirm_dialog,
                ui.card().classes("p-4"),
            ):
                self.dialog_title = ui.label().classes("text-lg font-bold mb-4")
                with ui.row().classes("justify-end w-full gap-2"):
                    ui.button("No", color="red", on_click=self.confirm_dialog.close)
                    ui.button("Yes", color="green", on_click=self._on_yes_clicked)

            with (
                ui.dialog().props("persistent") as self.processing_dialog,
                ui.card().classes("p-4 items-center justify-center"),
            ):
                with ui.row().classes("items-center gap-3"):
                    self.processing_spinner = ui.spinner(size="md")
                    self.processing_label = ui.label("Processing...").classes(
                        "text-base"
                    )

        if self.marked_field:
            color_class = f"text-{self.marked_text_color}"
            for column in self.table.columns:
                cell = column["name"]
                self.table.add_slot(
                    f"body-cell-{cell}",
                    rf"""
                    <q-td :props="props">
                    <span :class="props.row.{self.marked_field} ? 'font-bold {color_class}' : ''">
                    {{{{props.value}}}}
                    </span>
                    </q-td>
                    """,
                )

    def _normalize_columns(self, columns: list[dict]) -> list[dict]:
        """Add field 'name', needed for Quasar GUI"""
        return [{**col, "name": col.get("name", col["field"])} for col in columns]

    def mark_row(self, mark: bool = True, **kwrds: Any) -> list[dict[str, Any]]:
        """
        card_table.mark_row(id="123456", name="ANNNNN")
        card_table.mark_row(ip="192.168.0.18", mark=False)
        """
        found = []
        for row in self.table.rows:
            if all(row.get(k) == v for k, v in kwrds.items()):
                row[self.marked_field] = mark
                found.append(row)
        if found:
            self.table.update()
        return found

    def visible(self, state: bool) -> None:
        self.table.visible = state
        self.card.visible = state

    async def _on_selection_change(self, e: Any) -> None:
        selected = bool(e.selection)
        for btn in self.buttons_on_row_select_changed:
            if selected:
                btn.classes("!bg-blue-500", remove="!bg-gray-500").enable()
            else:
                btn.classes("!bg-gray-500", remove="!bg-blue-500").disable()
        for handler in self.on_selection_change:
            await handler(e)

    async def _run_with_processing(self, handler: Callable) -> None:
        self.processing_dialog.open()
        try:
            if inspect.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
            await asyncio.sleep(0.1)
        finally:
            self.processing_dialog.close()

    async def _on_yes_clicked(self) -> None:
        handler, self._current_yes_handler = self._current_yes_handler, None
        self.confirm_dialog.close()
        if not handler:
            return
        await self._run_with_processing(handler)

    def enum_data(self, rows: list[dict]) -> list[dict]:
        return [{"sn": i + 1, **row} for i, row in enumerate(rows)]

    def set_rows(self, rows: list[dict]) -> None:
        self.table.rows = self.enum_data(rows)
        self.table.update()

    def add_button(
        self,
        btn_txt: str,
        on_click: Callable,
        default_enable: bool = True,
        color: str = "blue",
        active_on_rows_selected: bool = False,
        use_dialog_confirm: bool = False,
        confirm_title: str | None = None,
    ) -> ui.button:
        with self.top_table:
            btn = ui.button(btn_txt, color=color)

        if active_on_rows_selected:
            self.buttons_on_row_select_changed.append(btn)

        if default_enable:
            btn.classes("!bg-blue-500", remove="!bg-gray-500").enable()
        else:
            btn.classes("!bg-gray-500", remove="!bg-blue-500").disable()

        async def handle_click() -> None:
            if use_dialog_confirm:
                self.dialog_title.text = confirm_title or f"Confirm {btn_txt}?"
                self._current_yes_handler = on_click
                self.confirm_dialog.open()
            else:
                await self._run_with_processing(on_click)

        btn.on_click(handle_click)
        setattr(self, f"btn{btn_txt.replace(' ','_')}", btn)
        return btn
