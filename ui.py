"""Output formatting and export.

Owner: Elijah (branch: feature/ui-output)
Library: rich (https://rich.readthedocs.io) for coloured tables.
"""


def show_table(title, data):
    """Print `data` (a dict) as a two-column table: Field | Value.

    Starter version: plain text, so the app works before rich is added.
    TODO: replace with a rich.table.Table with colours.
    """
    print(f"\n--- {title} ---")
    for key, value in data.items():
        print(f"{key:<16} {value}")


def export_json(data, path="result.json"):
    """Save `data` to a JSON file and return the file path."""
    # TODO: json.dump(data, f, indent=2)
    raise NotImplementedError("ui.export_json")


def export_csv(data, path="result.csv"):
    """Save `data` to a CSV file (Field,Value rows) and return the file path."""
    # TODO: use csv.writer
    raise NotImplementedError("ui.export_csv")
