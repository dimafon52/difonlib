from nicegui import ui
import inspect
import asyncio
from typing import Any, Callable, Awaitable, Literal
import threading
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

    async def dialog_processing(
        self,
        proc: Callable,
        proc_cancel_event: bool = False,
        label_txt: str = "Processing...",
        label_txt_color: str = "green",
        timeout: int | None = None,
        btn_cancel: str | None = "Cancel",
    ) -> Any | None:
        """
        See examples in ng_lib_test3.py
        def proc_dummy2(cancel_event: threading.Event) -> None:
            for i in range(10, 0, -1):
                if cancel_event.is_set():
                    print(f"Exit")
                    return
                print(f"Remaining: {i}")
                time.sleep(1)
        async def aproc_dummy(cnt: int = 20):
            for i in range(cnt, 0, -1):
                print(f"aRemaining: {i}")
                await asyncio.sleep(1)
            return 125

        async def proc_dialog():
            result = await dialog_box.dialog_processing(
                functools.partial(aproc_dummy, cnt=4), timeout=5
            )
        ui.button(
           "Test processing dialog",
           on_click=proc_dialog,
        )
        """
        task_proc: asyncio.Task | None = None
        cancel_event = None
        if proc_cancel_event:
            cancel_event = threading.Event()

        async def countdown(timeout: int, label: ui.label) -> None:
            for counter in range(timeout, 0, -1):
                label.text = f"{label_txt}{counter}"
                await asyncio.sleep(1)

        canceled = False
        ret_value: Any | None = None

        async def on_cancel() -> None:
            nonlocal canceled
            canceled = True
            if cancel_event:
                cancel_event.set()
            if task_proc:
                task_proc.cancel()
            dialog.close()

        text_color = f"text-{label_txt_color}-500"
        with (
            ui.dialog().props("persistent") as dialog,
            ui.card().classes("p-4 items-center justify-center"),
        ):
            with ui.row().classes("items-center gap-3"):
                ui.spinner(size="md")
                label = ui.label(f"{label_txt}").classes(f"{text_color} text-2xl")
                if btn_cancel:
                    ui.button(btn_cancel, on_click=on_cancel)
        dialog.open()
        task_count: asyncio.Task | None = None
        if timeout:
            task_count = asyncio.create_task(countdown(timeout=timeout, label=label))

        if proc_cancel_event:
            if inspect.iscoroutinefunction(getattr(proc, "func", proc)):
                task_proc = asyncio.create_task(proc(cancel_event))
            else:
                task_proc = asyncio.create_task(asyncio.to_thread(proc, cancel_event))
        else:
            if inspect.iscoroutinefunction(getattr(proc, "func", proc)):
                task_proc = asyncio.create_task(proc())
            else:
                task_proc = asyncio.create_task(asyncio.to_thread(proc))

        try:
            ret_value = await asyncio.wait_for(task_proc, timeout=timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            if cancel_event:
                cancel_event.set()
            status = "Canceled" if canceled else "Timeout"
            ui.notify(status, type="warning")
        except Exception as e:
            ui.notify(str(e), type="negative", position="center")

        finally:
            if task_count and not task_count.cancelled():
                task_count.cancel()
            dialog.close()

        return ret_value

    async def dialog_msg(self, msg_text: str) -> None:
        with ui.dialog().props("persistent") as dialog, ui.card():
            ui.label(text=msg_text)
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
        input_prefix: str = "",
        **kwrds: Any,
    ) -> ui.dialog:
        with ui.dialog().props("persistent") as dialog, ui.card():
            ui.label(text=text)
            with ui.row():
                inp: ui.input = ui.input(value=input_prefix, **kwrds).on(
                    "keydown.enter", lambda: dialog.submit(inp.value)
                )
                ui.button(text="Enter", on_click=lambda: dialog.submit(inp.value))
                ui.button(text="Cancel", on_click=dialog.close)
        return await dialog


class CardTable:
    # _current_yes_handler: Callable[[], None | Awaitable[None]] | None = None

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
        self.filter_value: str | bool = ""
        self._current_yes_handler: Callable[[], None | Awaitable[None]] | None = None

        with ui.card().classes("p-4 shadow-lg") as self.card:
            with ui.row().classes("items-center justify-between w-full mb-2"):
                with ui.row().classes("gap-2") as self.left_table:
                    pass
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
                    self.processing_label = ui.label("Processing...").classes("text-base")

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

    def set_row_display_filter(self, **field: str | bool) -> None:
        """
        card_table.set_row_display_filter(id="123456")
        card_table.set_row_display_filter(_marked=True)
        """
        assert len(field) == 1, "❌ Exactly one field expected"
        field_name, field_value = next(iter(field.items()))
        if isinstance(field_value, bool):
            self.filter_value = str(field_value).lower()  # "true" / "false" для JS
        else:
            self.filter_value = f"\\'{field_value}\\'"
        self.table.props(rf"""
            :filter-method="(rows, terms) => !terms ? rows : rows.filter(r => r.{field_name} === terms)"
            """)

    def row_display_filter(self, state_on: bool = False) -> None:
        """
          Show rows with field id='123456' :
        card_table.set_row_display_filter(id="123456")
        card_table.row_display_filter(state_on=True)
          Show rows with field _marked=True :
        card_table.set_row_display_filter(_marked=True)
        card_table.row_display_filter(True)
          Show all rows:
        card_table.row_display_filter()
        """
        if state_on:
            self.table.props(f':filter="{self.filter_value}"')
        else:
            self.table.props(':filter=""')
        self.table.update()

    def mark_row(self, mark: bool = True, **kwrds: Any) -> list[dict[str, Any]]:
        """
        card_table.mark_row(id="123456", name="IRDevice.Lounge1")
        card_table.mark_row(ip="192.168.0.18", mark=False) #Unmark
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
        # for handler in self.on_selection_change:
        #     await handler(e)
        for handler in self.on_selection_change:
            if inspect.iscoroutinefunction(handler):
                await handler()
            else:
                handler()

    async def _run_with_processing(self, handler: Callable) -> None:
        self.processing_dialog.open()
        try:
            if inspect.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
            # await asyncio.sleep(0.1)
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

    def add_checkbox(
        self,
        chbox_txt: str,
        on_change: Callable,
        default_enable: bool = False,
    ) -> ui.checkbox:
        """
        card_table.add_checkbox(chbox_txt="Used Only", on_change=lambda v: ui.notify(v))
        """
        with self.top_table:
            chbox = ui.checkbox(chbox_txt, value=default_enable).classes("font-bold")

        async def handle_change(e: Any) -> None:
            if inspect.iscoroutinefunction(on_change):
                await on_change(e.sender.value)
            else:
                on_change(e.sender.value)

        # chbox.on("click", handle_change)
        chbox.on("update:model-value", handle_change)
        setattr(self, f"chbox{chbox_txt.replace(' ', '_')}", chbox)
        return chbox

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
