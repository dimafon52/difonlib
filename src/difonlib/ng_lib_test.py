from nicegui import ui


@ui.page("/", dark=True)
def page():

    columns = [
        {"name": "name", "label": "Name", "field": "name"},
        {"name": "age", "label": "Age", "field": "age"},
    ]

    rows = [
        {"name": "Alice", "age": 18},
        {"name": "Bob", "age": 21},
        {"name": "Carol", "age": 42},
    ]

    table = ui.table(columns=columns, rows=rows, row_key="name")

    with table.add_slot("body-cell-age"):
        with table.cell("age"):
            ui.badge().props(
                """
            :color="props.value < 21 ? 'red' : 'green'"
            :label="props.value"
            """
            )


ui.run()
