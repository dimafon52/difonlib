from typing import Any, Callable, Awaitable, Literal
from nicegui import ui
from ng_lib import CardTable
import time


@ui.page("/", dark=True)
def main() -> None:

    class CardTableM(CardTable):
        # def color_marked_rows(self, text_color:str='yellow', bg_color:str=''):
        #     for col in self.columns
        #     self.table.add
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
            self.marked_text_color = marked_text_color
            self.marked_field = marked_field
            super().__init__(title, columns, rows, selection, on_selection_change)
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

        # def enum_data(self, data: list[dict]) -> list[dict]:
        #     return [
        #         {"sn": i + 1, **row, self.marked_field: False}
        #         for i, row in enumerate(data)
        #     ]

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
    # card_table.mark_row("id", "003456")
    found = card_table.mark_row(id="123456", name="ANNNNN", mark=False)
    print(f" ==> found: {found}")  # //Dima
    # card_table.table.update()

    # # await asyncio.sleep(3)
    # time.sleep(3)

    # card_table.table.rows[1]["_marked"] = False
    # card_table.table.rows[3]["_marked"] = False

    # card_table.table.rows[0]["_marked"] = True
    # card_table.table.rows[4]["_marked"] = True
    # card_table.table.update()

    # card_table.table.add_slot(
    #     "body",
    #     r"""
    #     <q-tr :props="props"
    #       :class="props.row._marked ? 'bg-red text-yellow' : ''">

    #     <!-- selection checkbox -->
    #     <q-td auto-width>
    #         <q-checkbox
    #             v-model="props.selected"
    #         />
    #     </q-td>

    #     <q-td key="id" :props="props">
    #         {{ props.row.id }}
    #     </q-td>

    #     <q-td key="name" :props="props">
    #         {{ props.row.name }}
    #     </q-td>

    #     <q-td key="_used" :props="props">
    #         {{ props.row._used }}
    #     </q-td>

    #     </q-tr>
    #     """,
    # )

    # card_table.table.update()

    # card_table.table.add_slot(
    #     "body-cell-name",
    #     r"""
    #     <q-td :props="props">
    #     <span :class="props.row._used ? 'text-green' : ''">
    # {{ props.value }}
    #     </span>
    #     </q-td>
    #     """,
    # )


ui.run(port=1111)
