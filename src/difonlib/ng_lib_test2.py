from nicegui import ui

table = ui.table(
    columns=[
        {"name": "id", "label": "ID", "field": "id"},
        {"name": "name", "label": "Name", "field": "name"},
    ],
    rows=[
        {"id": "123456", "name": "NNNNN", "_used": True},
        {"id": "123456", "name": "NNNNN", "_used": False},
        {"id": "123456", "name": "NNNNN", "_used": True},
        {"id": "123456", "name": "NNNNN", "_used": False},
        {"id": "123456", "name": "NNNNN", "_used": True},
        {"id": "123456", "name": "NNNNN", "_used": True},
    ],
)

table.add_slot(
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
