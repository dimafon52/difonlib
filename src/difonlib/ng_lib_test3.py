from typing import Any, Callable, Awaitable, Literal
from nicegui import ui
from ng_lib import CardTable


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
        ):
            super().__init__(title, columns, rows, selection, on_selection_change)
            color = "yellow"
            cell = "id"
            for cell in self.table.rows[0].keys():
                self.table.add_slot(
                    f"body-cell-{cell}",
                    rf"""
                    <q-td :props="props">
                    <span :class="props.row._marked ? 'font-bold text-{color}' : ''">
                    {{{{props.value}}}}
                    </span>
                    </q-td>
                    """,
                )

        def enum_data(self, data: list[dict]) -> list[dict]:
            return [
                {"sn": i + 1, **row, "_marked": False} for i, row in enumerate(data)
            ]

    card_table = CardTableM(
        title="Connected Devices",
        columns=[
            {"name": "id", "label": "id", "field": "id"},
            {"name": "name", "label": "Name", "field": "name"},
        ],
        selection="single",
        rows=[
            {"id": "123456", "name": "ANNNNN"},
            {"id": "987654", "name": "VNNNNN"},
            {"id": "123456", "name": "BNNNNN"},
            {"id": "003456", "name": "SNNNNN"},
            {"id": "129956", "name": "QNNNNN"},
        ],
    )

    print(f"card_table.table.rows:{card_table.table.rows}")  # //Dima

    card_table.table.rows[1]["_marked"] = True

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
