"""Output formatting and export for IP_PAPI.

Owner: Elijah (branch: feature/ui-output)
Library: rich (https://rich.readthedocs.io) for styling and layout.

Front-end note: this module is the "view layer" for the whole app. A bad
render or a disconnected/non-colour terminal should never crash the menu, so
every function here falls back to plain print() instead of letting an
exception escape.

Look ("paper"): a quiet, editorial, Bauhaus-inspired monochrome. Ink is the
terminal's own text colour, labels are dimmed, thin rules and gauge tracks
are a warm taupe, and section labels are letter-spaced small caps. There is
no bright accent colour: emphasis comes from weight, spacing and inversion
(errors are shown as an inverted ERROR badge). Because ink is the terminal's
default colour, the app reads correctly on light and dark terminals; the
intended demo look is a paper-coloured terminal (see docs/terminal-theme.md).
"""

import csv
import json
from datetime import datetime
from pathlib import Path

APP_NAME = "IP_PAPI"
TAGLINE = "Public IP, lookup and subnet toolkit for network technicians."
SUBTITLE = "NETWORK TOOLKIT"

# Palette (from the team's reference board: 111111 333333 777777 BEB8AD
# E6E1D7 F6F4EE). Only the taupe is hard-coded; ink uses the terminal's own
# foreground so nothing disappears on a dark background.
TAUPE = "#beb8ad"   # rules, gauge tracks
LABEL = "dim"       # field labels and secondary text
INDENT = "  "

_STYLE_BY_LEVEL = {
    "info": "dim",
    "success": "bold",
    "warning": "bold",
    "error": "bold",
}


def _console():
    """A rich Console with automatic number/URL highlighting turned off, so
    the monochrome palette is the only styling on screen."""
    from rich.console import Console

    return Console(highlight=False)


def spaced(text):
    """'SUBNET' -> 'S U B N E T' (letter-spaced small-caps label)."""
    return " ".join(str(text).upper())


def _is_informational(key, value):
    """True when a Field/Value pair is a soft note rather than real data.

    Covers values like "N/A" or "not available ..." and any field literally
    called "Note" (e.g. lookup.py's "Private address - no public provider
    details"). These are shown dim and italic instead of looking like data.
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

    With rich: a letter-spaced section label with the subject beside it, a
    short taupe rule, then a borderless key/value list with dim labels and
    bold values. Informational values (see `_is_informational`) are dim
    italic. Falls back to plain aligned text if rich is unavailable or
    rendering fails. Never raises.
    """
    try:
        from rich.padding import Padding
        from rich.table import Table
        from rich.text import Text

        console = _console()
        label, subject = _split_title(title)
        heading = Text(INDENT)
        heading.append(spaced(label), style="bold")
        if subject:
            heading.append("     " + subject)

        grid = Table.grid(padding=(0, 4))
        grid.add_column(style=LABEL, no_wrap=True)
        grid.add_column()
        if not data:
            grid.add_row("(no data)", "")
        else:
            for key, value in data.items():
                if _is_informational(key, value):
                    grid.add_row(str(key), Text(str(value), style="dim italic"))
                else:
                    grid.add_row(str(key), Text(str(value), style="bold"))

        console.print()
        console.print(heading)
        console.print(INDENT + "──", style=TAUPE)
        console.print(Padding(grid, (0, 0, 0, len(INDENT))))
    except Exception:
        # rich isn't installed, or the terminal/data upset it somehow -
        # fall back to plain text rather than crashing the menu.
        _plain_table(title, data)


def show_gauge(label, filled, total, caption="", width=32):
    """Print a horizontal gauge, e.g. network bits vs host bits of a subnet.

    `filled` of `total` cells are drawn solid in ink, the rest as a taupe
    track. The bar is scaled to `width` cells (IPv6 /64 still fits). Prints
    nothing useful but never raises if rich is unavailable.
    """
    try:
        from rich.text import Text

        total = max(int(total), 1)
        filled = min(max(int(filled), 0), total)
        cells = round(width * filled / total)
        bar = Text(INDENT)
        bar.append(spaced(label), style="dim")
        bar.append("\n" + INDENT)
        bar.append("█" * cells)
        bar.append("█" * (width - cells), style=TAUPE)
        if caption:
            bar.append("   " + caption, style="dim")
        console = _console()
        console.print()
        console.print(bar)
    except Exception:
        print(f"{INDENT}{label}: {filled}/{total} {caption}")


def show_message(text, level="info"):
    """Print a short status line.

    `level` is one of "info" (default, dim), "success" (bold), "warning"
    (bold) or "error" (an inverted ERROR badge followed by the text).
    Never raises.
    """
    try:
        from rich.text import Text

        line = Text(INDENT)
        if level == "error":
            line.append(" ERROR ", style="reverse bold")
            line.append("  " + str(text), style="bold")
        elif level == "warning":
            line.append(" NOTE ", style="reverse")
            line.append("  " + str(text))
        else:
            line.append(str(text), style=_STYLE_BY_LEVEL.get(level, "dim"))
        console = _console()
        console.print()
        console.print(line)
    except Exception:
        print(text)


def show_header():
    """Print the app name, a letter-spaced subtitle, the tagline and a short
    rule - the "title block" of the reference board. Never raises."""
    try:
        from rich.text import Text

        console = _console()
        block = Text(INDENT)
        block.append(" ".join(APP_NAME), style="bold")
        block.append("\n" + INDENT)
        block.append(spaced(SUBTITLE).replace("   ", "     "), style="dim")
        block.append("\n\n" + INDENT)
        block.append(TAGLINE)
        console.print()
        console.print(block)
        console.print(INDENT + "──", style=TAUPE)
    except Exception:
        print(f"=== {APP_NAME} - {TAGLINE} ===")


def show_menu(items):
    """Print the numbered menu. `items` is a list of (key, label) pairs;
    key "0" (Exit) is shown dim. Never raises."""
    try:
        from rich.padding import Padding
        from rich.table import Table
        from rich.text import Text

        grid = Table.grid(padding=(0, 3))
        grid.add_column(justify="right", style="bold", no_wrap=True)
        grid.add_column()
        for key, label in items:
            grid.add_row(key, label, style="dim" if key == "0" else None)
        console = _console()
        console.print()
        console.print(Text(INDENT + spaced("menu"), style="dim"))
        console.print(Padding(grid, (0, 0, 0, len(INDENT))))
    except Exception:
        print()
        for key, label in items:
            print(f"  {key}. {label}")


def ask(prompt):
    """Show a prompt ("→ Choose an option") and return what the user types.

    The prompt is printed with rich, then plain input() reads the answer, so
    Ctrl+C / EOF still raise KeyboardInterrupt / EOFError for main.py.
    """
    try:
        from rich.text import Text

        line = Text("\n" + INDENT)
        line.append("→  ", style=TAUPE)
        line.append(prompt + " ", style="dim")
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
