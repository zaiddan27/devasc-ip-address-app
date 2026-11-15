"""Output formatting and export.

Owner: Elijah (branch: feature/ui-output)
Library: rich (https://rich.readthedocs.io) for coloured tables.

Front-end note: this module is the "view layer" for the whole app. A bad
render or a disconnected/non-colour terminal should never crash the menu, so
show_table() and show_message() always fall back to plain print() instead of
letting an exception escape.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

# Rich styles used across the module, kept in one place so the look stays
# consistent between the table, the banner and status messages.
_STYLE_BY_LEVEL = {
    "info": "cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
}


def _is_informational(key, value):
    """True when a Field/Value pair is a soft note rather than real data.

    Covers values like "N/A" or "not available ..." and any field literally
    called "Note" (e.g. lookup.py's "Private address - no public provider
    details"). These are highlighted subtly instead of looking like an error.
    """
    if str(key).strip().lower() == "note":
        return True
    text = str(value).strip().lower()
    return text == "n/a" or text.startswith("not available")


def _plain_table(title, data):
    """Plain aligned text table - used when rich is missing or misbehaves."""
    print(f"\n=== {title} ===")
    if not data:
        print("(no data to show)")
        return
    label_width = max(len(str(key)) for key in data.keys())
    for key, value in data.items():
        note = "  (info)" if _is_informational(key, value) else ""
        print(f"{str(key):<{label_width}} : {value}{note}")


def show_table(title, data):
    """Print `data` (a dict of Field -> Value, in display order) as a table.

    Uses a `rich` Table with a Field/Value column pair when rich is
    available, subtly highlighting informational values (see
    `_is_informational`). Falls back to a plain aligned text table if rich
    is not installed, or if anything else goes wrong while rendering.
    Never raises.
    """
    try:
        from rich.console import Console
        from rich.table import Table

        table = Table(title=title, header_style="bold white on blue", expand=False)
        table.add_column("Field", style="bold cyan", no_wrap=True)
        table.add_column("Value", style="white")

        if not data:
            table.add_row("(no data)", "")
        else:
            for key, value in data.items():
                row_style = "italic grey70" if _is_informational(key, value) else None
                table.add_row(str(key), str(value), style=row_style)

        Console().print(table)
    except Exception:
        # rich isn't installed, or the terminal/data upset it somehow -
        # fall back to plain text rather than crashing the menu.
        _plain_table(title, data)


def show_message(text, level="info"):
    """Print a short status line, coloured by `level` when rich is available.

    `level` is one of "info" (default), "success", "warning" or "error".
    Never raises.
    """
    try:
        from rich.console import Console

        Console().print(text, style=_STYLE_BY_LEVEL.get(level, "cyan"))
    except Exception:
        print(text)


def show_header():
    """Print the app's title banner. Falls back to plain text. Never raises."""
    try:
        from rich.console import Console
        from rich.panel import Panel

        Console().print(Panel.fit("DevASC IP Address App", style="bold white on blue"))
    except Exception:
        print("=== DevASC IP Address App ===")


def _default_export_path(extension):
    """Build exports/result_YYYYMMDD_HHMMSS.<extension>, creating the folder."""
    folder = Path("exports")
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return folder / f"result_{stamp}.{extension}"


def export_json(data, path=None):
    """Save `data` to a JSON file and return the path written, as a string.

    With `path=None`, writes to exports/result_YYYYMMDD_HHMMSS.json
    (the folder is created if missing). Raises OSError if it can't write.
    """
    target = Path(path) if path else _default_export_path("json")
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return str(target)


def export_csv(data, path=None):
    """Save `data` to a CSV file (Field,Value header) and return the path.

    With `path=None`, writes to exports/result_YYYYMMDD_HHMMSS.csv
    (the folder is created if missing). Raises OSError if it can't write.
    """
    target = Path(path) if path else _default_export_path("csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Field", "Value"])
        for key, value in data.items():
            writer.writerow([key, value])
    return str(target)
