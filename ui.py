"""Output formatting and export for IP_PAPI.

Owner: Elijah (branch: feature/ui-output)
Library: rich (https://rich.readthedocs.io) for colour and layout.

Front-end note: this module is the "view layer" for the whole app. A bad
render or a disconnected/non-colour terminal should never crash the menu, so
every function here falls back to plain print() instead of letting an
exception escape.

Look ("network console"): calm and dark-terminal friendly, like a router or
NOC tool. One signal colour (teal) marks the app name, menu numbers and
success; amber marks informational values such as "N/A"; red is reserved for
errors. Results are borderless key/value lists so the values carry the screen.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

APP_NAME = "IP_PAPI"
TAGLINE = "public IP, lookup & subnet toolkit"

# Palette, kept in one place so the header, menu, results and messages match.
ACCENT = "#3cc8b4"   # teal signal colour
INFO = "#e0a43a"     # amber: informational / not-available values
ERROR = "#ef5f56"    # red: errors only
MUTED = "grey62"     # labels and secondary text
RULE = "grey35"      # thin divider lines
INDENT = "  "

_STYLE_BY_LEVEL = {
    "info": MUTED,
    "success": f"bold {ACCENT}",
    "warning": f"bold {INFO}",
    "error": f"bold {ERROR}",
}


def _console():
    """A rich Console with automatic number/URL highlighting turned off, so
    the palette above is the only colour on screen."""
    from rich.console import Console

    return Console(highlight=False)


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


def _split_title(title):
    """'Subnet: 192.168.10.0/26' -> ('SUBNET', '192.168.10.0/26');
    'My public IP' -> ('MY PUBLIC IP', '')."""
    label, sep, subject = str(title).partition(": ")
    return label.upper(), subject if sep else ""


def _plain_table(title, data):
    """Plain aligned text - used when rich is missing or misbehaves."""
    print(f"\n{INDENT}{title}")
    if not data:
        print(f"{INDENT}(no data to show)")
        return
    label_width = max(len(str(key)) for key in data.keys())
    for key, value in data.items():
        note = "  (info)" if _is_informational(key, value) else ""
        print(f"{INDENT}{str(key):<{label_width}}   {value}{note}")


def show_table(title, data):
    """Print `data` (a dict of Field -> Value, in display order) as a result.

    With rich: a heading line (section label in teal, subject in bold), a
    thin rule, then a borderless key/value list. Keys are muted so the
    values stand out; informational values (see `_is_informational`) are
    amber italic so they read as a note, not an error. Falls back to plain
    aligned text if rich is unavailable or rendering fails. Never raises.
    """
    try:
        from rich.padding import Padding
        from rich.table import Table
        from rich.text import Text

        console = _console()
        label, subject = _split_title(title)
        heading = Text(INDENT)
        heading.append(label, style=f"bold {ACCENT}")
        if subject:
            heading.append("   " + subject, style="bold")

        grid = Table.grid(padding=(0, 3))
        grid.add_column(style=MUTED, no_wrap=True)
        grid.add_column()
        if not data:
            grid.add_row("(no data)", "")
        else:
            for key, value in data.items():
                if _is_informational(key, value):
                    grid.add_row(str(key), Text(str(value), style=f"italic {INFO}"))
                else:
                    grid.add_row(str(key), Text(str(value), style="bold"))

        console.print()
        console.print(heading)
        console.print(INDENT + "─" * max(len(heading.plain) - len(INDENT), 24), style=RULE)
        console.print(Padding(grid, (0, 0, 0, len(INDENT))))
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
        console = _console()
        console.print()
        console.print(INDENT + str(text), style=_STYLE_BY_LEVEL.get(level, MUTED), markup=False)
    except Exception:
        print(text)


def show_header():
    """Print the app name, tagline and a thin rule. Never raises."""
    try:
        from rich.text import Text

        console = _console()
        line = Text(INDENT)
        line.append(APP_NAME, style=f"bold {ACCENT}")
        line.append("  ·  " + TAGLINE, style=MUTED)
        console.print()
        console.print(line)
        console.print(INDENT + "─" * (len(line.plain) - len(INDENT)), style=RULE)
    except Exception:
        print(f"=== {APP_NAME} - {TAGLINE} ===")


def show_menu(items):
    """Print the numbered menu. `items` is a list of (key, label) pairs;
    key "0" (Exit) is shown muted. Never raises."""
    try:
        from rich.padding import Padding
        from rich.table import Table

        grid = Table.grid(padding=(0, 2))
        grid.add_column(justify="right", style=f"bold {ACCENT}", no_wrap=True)
        grid.add_column()
        for key, label in items:
            grid.add_row(key, label, style=MUTED if key == "0" else None)
        console = _console()
        console.print()
        console.print(Padding(grid, (0, 0, 0, len(INDENT) + 1)))
    except Exception:
        print()
        for key, label in items:
            print(f"  {key}. {label}")


def ask(prompt):
    """Show a prompt ("› Choose an option") and return what the user types.

    The prompt is printed with rich, then plain input() reads the answer, so
    Ctrl+C / EOF still raise KeyboardInterrupt / EOFError for main.py.
    """
    try:
        from rich.text import Text

        line = Text("\n" + INDENT)
        line.append("› ", style=f"bold {ACCENT}")
        line.append(prompt + " ", style="bold")
        _console().print(line, end="")
        return input()
    except (KeyboardInterrupt, EOFError):
        raise
    except Exception:
        return input(f"{prompt} ")


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
