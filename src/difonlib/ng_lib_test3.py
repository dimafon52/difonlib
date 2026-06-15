from nicegui import ui
from ng_lib import CardTable


@ui.page("/", dark=True)
def main() -> None:
    card_table = CardTable(
        title="Connected Devices",
        columns=[
            {"name": "id", "label": "ID", "field": "id"},
            {"name": "name", "label": "Name", "field": "name"},
        ],
        selection="single",
        rows=[
            {"id": "123456", "name": "NNNNN", "_used": True},
            {"id": "123456", "name": "NNNNN", "_used": False},
            {"id": "123456", "name": "NNNNN", "_used": True},
            {"id": "123456", "name": "NNNNN", "_used": False},
            {"id": "123456", "name": "NNNNN", "_used": True},
            {"id": "123456", "name": "NNNNN", "_used": True},
        ],
    )

    card_table.table.add_slot(
        "body-cell-name",
        r"""
        <q-td :props="props">
        <span :class="props.row._used ? 'text-green' : ''">
    {{ props.value }}
        </span>
        </q-td>
        """,
    )


ui.run()
