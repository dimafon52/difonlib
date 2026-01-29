from nicegui import ui
import inspect
import asyncio
from typing import Any, Callable, Awaitable, Dict, List, Optional, Union, Literal

from difonlib.utils import logdbg

dbg = logdbg


class CardTable:
    _current_yes_handler: Optional[Callable[[], Union[None, Awaitable[None]]]] = None

    def __init__(
        self,
        title: str,
        columns: list,
        rows: list = [],
        selection: Optional[Literal["single", "multiple"]] = None,  # single, multiple or None
        on_selection_change: List[Callable] = [],  # Handlers on_selection_change event
    ):
        self.on_selection_change: list = on_selection_change
        # A list of buttons that change state (active, inactive) when table rows are selected or deselected.
        self.buttons_on_row_select_changed: list = []

        """Карточка с таблицей и встроенным диалогом подтверждения."""
        with ui.card().classes("p-4 shadow-lg") as self.card:
            # --- Заголовок ---
            with ui.row().classes("items-center justify-between w-full mb-2"):
                ui.label(f"📋 {title}").classes("text-green-700 text-lg font-bold")
                with ui.row().classes("gap-2") as self.top_table:
                    pass

            # --- Таблица ---
            self.table = ui.table(
                columns=columns,
                rows=self.enum_data(rows),
                row_key="sn",
                selection=selection,
                on_select=self._on_selection_change,
                column_defaults={
                    "align": "left",
                    "headerClasses": "uppercase",
                },
            ).classes("w-full shadow-lg bg-black-900 text-gray-200")

            # --- Диалог подтверждения ---
            with ui.dialog() as self.confirm_dialog, ui.card().classes("p-4"):
                self.dialog_title = ui.label().classes("text-lg font-bold mb-4")
                with ui.row().classes("justify-end w-full gap-2"):
                    ui.button("No", color="gray", on_click=self.confirm_dialog.close)
                    ui.button("Yes", color="red", on_click=self._on_yes_clicked)

            # --- Диалог "Processing..." ---
            with (
                ui.dialog() as self.processing_dialog,
                ui.card().classes("p-4 items-center justify-center"),
            ):
                with ui.row().classes("items-center gap-3"):
                    self.processing_spinner = ui.spinner(size="md")
                    self.processing_label = ui.label("Processing...").classes("text-base")

    def visible(self, state: Literal[True, False]) -> None:
        if state:
            self.table.visible = True
            self.card.visible = True
        else:
            self.table.visible = False
            self.card.visible = False

    async def _on_selection_change(self, e: Any) -> None:
        for btn in self.buttons_on_row_select_changed:
            if e.selection:
                dbg("Da")  # //Dima
                btn.classes("!bg-blue-500", remove="!bg-gray-500").enable()
            else:
                dbg("Net")  # //Dima
                btn.classes("!bg-gray-500", remove="!bg-blue-500").disable()
        dbg(f"** self.on_selection_change: {self.on_selection_change}")  # //Dima
        for handler in self.on_selection_change:
            await handler(e)

    async def _on_yes_clicked(self) -> None:
        """Обработка подтверждения с показом диалога 'Processing...'."""
        handler: Optional[Callable[[], Union[None, Awaitable[None]]]] = self._current_yes_handler
        self._current_yes_handler = None
        self.confirm_dialog.close()

        if not handler:
            return

        # --- Показать диалог "Processing..." ---
        self.processing_dialog.open()

        try:
            if inspect.iscoroutinefunction(handler):
                await handler()
                await asyncio.sleep(0.3)  # плавность UX
            else:
                handler()
        finally:
            self.processing_dialog.close()

    def enum_data(self, data: List[Dict]) -> List[Dict]:
        return [{"sn": i + 1, **row} for i, row in enumerate(data)]

    def set_rows(self, rows: List[Dict]) -> None:
        self.table.rows = self.enum_data(rows)
        self.table.update()

    # def add_handler_on_selection_change(self, handler: Callable[[Any]]) -> None:
    #     if handler in self.on_selection_change:
    #         return
    #     self.on_selection_change.append(handler)

    def add_button(
        self,
        btn_txt: str,
        on_click: Callable,
        default_enable: bool = True,  # enable the added button by default
        color: str = "blue",
        active_on_rows_selected: bool = False,  # activate button when row(s) is selected, if True - always actived
        use_dialog_confirm: bool = False,
        confirm_title: Optional[str] = None,
    ) -> ui.button:
        """Добавляет кнопку в заголовок таблицы, с опциональным подтверждением."""
        with self.top_table:
            btn = ui.button(btn_txt, color=color)

        if active_on_rows_selected:
            self.buttons_on_row_select_changed.append(btn)
        if default_enable:
            btn.classes("!bg-blue-500", remove="!bg-gray-500").enable()
        else:
            btn.classes("!bg-gray-500", remove="!bg-blue-500").disable()

        dbg(f"btns: {self.buttons_on_row_select_changed}")  # //Dima

        # --- Без диалога ---
        if not use_dialog_confirm:
            btn.on_click(on_click)
            return btn

        # --- С подтверждением ---
        async def handle_click() -> None:
            self.dialog_title.text = confirm_title or f"Confirm {btn_txt}?"
            self._current_yes_handler = on_click
            self.confirm_dialog.open()

        btn.on_click(handle_click)
        return btn
