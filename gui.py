"""IP_PAPI desktop window (Tkinter).

Run with:  python gui.py
Build the Windows app with:  pyinstaller --onefile --windowed --name IP_PAPI gui.py

The window is a second front end for the same tested modules the terminal
app uses (ip_info, lookup, subnet_tools, ui). All networking and maths stay
in those modules; this file only collects input, runs one feature at a time
and lays out the result.

Layout ("paper"): a sidebar with the app name and the five features, and a
main sheet with a big feature number, the input row, the result as a
label/value list, and a status line at the bottom. Network calls run on a
background thread so the window never freezes while an API answers.
"""

import os
import sys
import threading

import ip_info
import lookup
import subnet_tools
import ui

try:  # tkinter ships with Python on Windows/macOS; tests never open a window
    import tkinter as tk
    import tkinter.font as tkfont
except ImportError:  # pragma: no cover - only on Pythons built without Tk
    tk = None

APP_NAME = "IP_PAPI"

# Palette shared with the terminal "paper" look and the presentation.
PAPER = "#F6F4EE"
PAPER_2 = "#E6E1D7"
SHEET = "#FBFAF7"
INK = "#111111"
INK_2 = "#333333"
MUTED = "#6F6B64"
TAUPE = "#BEB8AD"
HAIR = "#D6D0C4"

# (number, label, action, prompt, example input)
FEATURES = [
    ("1", "My public IP", "my_ip", "", ""),
    ("2", "Look up an IP or domain", "lookup", "IP address or domain", "8.8.8.8"),
    ("3", "Classify an IP address", "classify", "IP address", "10.0.0.5"),
    ("4", "Subnet calculator", "subnet", "Network in CIDR notation", "192.168.10.0/26"),
    ("5", "Export last result", "export", "", ""),
]

HINTS = {
    "lookup": "Type an IP address, a domain such as cisco.com, or paste a URL, then press Enter.",
    "classify": "Type an IPv4 or IPv6 address, then press Enter.",
    "subnet": "Type a network such as 192.168.10.0/26, then press Enter.",
}

SECTION_LABELS = {
    "my_ip": "public ip",
    "lookup": "lookup",
    "classify": "classify",
    "subnet": "subnet",
    "export": "export",
}

DESCRIPTIONS = {
    "my_ip": "Reads this computer's public IPv4 and IPv6 address and asks the provider APIs who owns it.",
    "lookup": "Looks up any IP address, domain name or pasted URL. Private addresses are answered without calling an API.",
    "classify": "Works offline. Says whether an address is private (RFC 1918), public, loopback, link-local and so on.",
    "subnet": "Works offline. Mask, wildcard, broadcast, host range and how many hosts fit.",
    "export": "Saves the last result as a JSON or CSV file in the exports folder, ready to attach to a ticket.",
}


def spaced(text):
    """'SUBNET' -> 'S U B N E T' (letter-spaced label, as in the terminal UI)."""
    return " ".join(str(text).upper()).replace("   ", "     ")


def run_action(action, value=""):
    """Run one feature and return (title, result dict).

    This is the whole bridge between the window and the tested modules, and
    the part tests/test_gui.py checks. Errors are raised exactly as the
    modules raise them (ValueError for bad input, ConnectionError when the
    APIs fail) so the window can show them as messages.
    """
    value = (value or "").strip()
    if action == "my_ip":
        ipv4 = ip_info.get_public_ipv4()
        ipv6 = ip_info.get_public_ipv6()
        try:
            details = ip_info.get_ip_details()
        except ConnectionError as exc:
            # Same behaviour as the terminal app: keep the addresses we have.
            details = {"Note": f"Provider details unavailable - {exc}"}
        return "My public IP", {
            "IPv4": ipv4 or "not available",
            "IPv6": ipv6 or "not available on this network",
            **details,
        }
    if action == "lookup":
        return f"Lookup: {value}", lookup.lookup(value)
    if action == "classify":
        return f"Address: {value}", subnet_tools.classify_address(value)
    if action == "subnet":
        return f"Subnet: {value}", subnet_tools.subnet_info(value)
    raise ValueError(f"Unknown feature: {action}")


def _pick(families, *names):
    """First font family from `names` that is installed, else Tk's default."""
    for name in names:
        if name in families:
            return name
    return "TkDefaultFont"


class App:
    """The IP_PAPI window. Composition over a Tk root (no subclassing), so
    importing this module never needs a display."""

    def __init__(self, root):
        self.root = root
        self.last_result = None
        self.last_title = ""
        self.busy = False
        self.current = None

        fam = set(tkfont.families(root))
        display = _pick(fam, "Bahnschrift", "Arial Narrow", "Helvetica Neue", "Arial")
        body = _pick(fam, "Segoe UI", "Helvetica Neue", "Arial")
        mono = _pick(fam, "Cascadia Mono", "Consolas", "Menlo", "Courier New")
        self.f_big = (display, 46, "bold")
        self.f_title = (display, 17, "bold")
        self.f_brand = (display, 15, "bold")
        self.f_label = (body, 8, "bold")
        self.f_body = (body, 10)
        self.f_body_b = (body, 10, "bold")
        self.f_nav = (body, 10)
        self.f_mono = (mono, 11)
        self.f_mono_b = (mono, 11, "bold")
        self.f_small = (body, 9)

        root.title(APP_NAME)
        root.configure(bg=PAPER)
        root.geometry("1120x820")
        root.minsize(940, 760)

        self._build_sidebar()
        self._build_main()
        self._bind_keys()
        self.select("my_ip")

    # ---------- layout ----------
    def _build_sidebar(self):
        side = tk.Frame(self.root, bg=PAPER_2, width=290)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text=" ".join(APP_NAME), font=self.f_brand, fg=INK, bg=PAPER_2,
                 anchor="w").pack(fill="x", padx=28, pady=(34, 0))
        tk.Label(side, text=spaced("network toolkit"), font=self.f_label, fg=MUTED, bg=PAPER_2,
                 anchor="w").pack(fill="x", padx=28, pady=(4, 0))
        tk.Frame(side, bg=TAUPE, height=2, width=26).pack(anchor="w", padx=28, pady=(16, 26))

        tk.Label(side, text=spaced("menu"), font=self.f_label, fg=MUTED, bg=PAPER_2,
                 anchor="w").pack(fill="x", padx=28, pady=(0, 8))

        self.nav = {}
        for number, label, action, _prompt, _example in FEATURES:
            row = tk.Frame(side, bg=PAPER_2, cursor="hand2")
            row.pack(fill="x", padx=16, pady=1)
            num = tk.Label(row, text=number, font=self.f_body_b, fg=INK, bg=PAPER_2, width=3, anchor="e")
            num.pack(side="left", pady=8)
            txt = tk.Label(row, text=label, font=self.f_nav, fg=INK, bg=PAPER_2, anchor="w")
            txt.pack(side="left", fill="x", expand=True, padx=(10, 12), pady=8)
            for widget in (row, num, txt):
                widget.bind("<Button-1>", lambda _e, a=action: self.select(a))
            self.nav[action] = (row, num, txt)

        foot = tk.Label(side, text="Team NEVER GROW OLD\nDEVASC · Project Activity 3",
                        font=self.f_small, fg=MUTED, bg=PAPER_2, justify="left", anchor="w")
        foot.pack(side="bottom", fill="x", padx=28, pady=26)
        tk.Label(side, text="Ctrl+1 to Ctrl+5 switch features.\nEnter runs the current one.",
                 font=self.f_small, fg=MUTED, bg=PAPER_2, anchor="w", justify="left").pack(side="bottom", fill="x", padx=28)

    def _build_main(self):
        main = tk.Frame(self.root, bg=SHEET)
        main.pack(side="left", fill="both", expand=True)
        self.main = main

        head = tk.Frame(main, bg=SHEET)
        head.pack(fill="x", padx=48, pady=(22, 0))
        self.big = tk.Label(head, text="01", font=self.f_big, fg=INK, bg=SHEET)
        self.big.pack(side="left", anchor="s")
        titles = tk.Frame(head, bg=SHEET)
        titles.pack(side="left", anchor="s", padx=(16, 0), pady=(0, 10))
        self.section = tk.Label(titles, text="", font=self.f_label, fg=MUTED, bg=SHEET, anchor="w")
        self.section.pack(anchor="w")
        self.title = tk.Label(titles, text="", font=self.f_title, fg=INK, bg=SHEET, anchor="w")
        self.title.pack(anchor="w")

        self.desc = tk.Label(main, text="", font=self.f_body, fg=INK_2, bg=SHEET, anchor="w",
                             justify="left", wraplength=620)
        self.desc.pack(fill="x", padx=48, pady=(10, 14))

        # input row (hidden for features without input)
        self.input_row = tk.Frame(main, bg=SHEET)
        self.prompt = tk.Label(self.input_row, text="", font=self.f_label, fg=MUTED, bg=SHEET, anchor="w")
        self.prompt.pack(anchor="w", pady=(0, 6))
        line = tk.Frame(self.input_row, bg=SHEET)
        line.pack(fill="x")
        box = tk.Frame(line, bg=INK, padx=1, pady=1)
        box.pack(side="left")
        self.entry = tk.Entry(box, font=self.f_mono, width=30, relief="flat", bg="#FFFFFF", fg=INK,
                              insertbackground=INK, highlightthickness=0)
        self.entry.pack(ipady=7, ipadx=8)
        self.run_btn = self._button(line, "Run", self.run)
        self.run_btn.pack(side="left", padx=(10, 0))

        # export row (only for feature 5)
        self.export_row = tk.Frame(main, bg=SHEET)
        self._button(self.export_row, "Save as JSON", lambda: self.export("json")).pack(side="left")
        self._button(self.export_row, "Save as CSV", lambda: self.export("csv"), ghost=True).pack(side="left", padx=(10, 0))
        self._button(self.export_row, "Open exports folder", self.open_exports, ghost=True).pack(side="left", padx=(10, 0))

        # my-ip row (only for feature 1)
        self.myip_row = tk.Frame(main, bg=SHEET)
        self._button(self.myip_row, "Check my IP", self.run).pack(side="left")

        tk.Frame(main, bg=HAIR, height=1).pack(fill="x", padx=48, pady=(16, 0))

        # status line (packed before the result so it always keeps its place)
        self.status = tk.Frame(main, bg=SHEET)
        self.status.pack(fill="x", side="bottom", padx=48, pady=(6, 20))

        # result area
        self.result = tk.Frame(main, bg=SHEET)
        self.result.pack(fill="both", expand=True, padx=48, pady=(12, 0))
        self.badge = tk.Label(self.status, text="", font=self.f_label, bg=SHEET, fg=SHEET, padx=6, pady=2)
        self.badge.pack(side="left")
        self.status_text = tk.Label(self.status, text="", font=self.f_body, fg=MUTED, bg=SHEET, anchor="w")
        self.status_text.pack(side="left", padx=(8, 0))

    def _button(self, parent, text, command, ghost=False):
        """A flat, square button in the paper style: solid ink, or outlined."""
        fg, bg = (INK, SHEET) if ghost else (SHEET, INK)
        frame = tk.Frame(parent, bg=INK, padx=1, pady=1, cursor="hand2")
        lab = tk.Label(frame, text=text, font=self.f_body_b, fg=fg, bg=bg, padx=16, pady=7, cursor="hand2")
        lab.pack()
        for widget in (frame, lab):
            widget.bind("<Button-1>", lambda _e: command())
            widget.bind("<Enter>", lambda _e: lab.configure(bg=INK_2 if not ghost else PAPER_2))
            widget.bind("<Leave>", lambda _e: lab.configure(bg=bg))
        frame.label = lab
        return frame

    def _bind_keys(self):
        self.root.bind("<Return>", lambda _e: self.run() if self.current not in ("export",) else None)
        for number, _label, action, _p, _x in FEATURES:
            self.root.bind(f"<Control-Key-{number}>", lambda _e, a=action: self.select(a))

    # ---------- behaviour ----------
    def select(self, action):
        if self.busy:
            return
        self.current = action
        number, label, _a, prompt, example = next(f for f in FEATURES if f[2] == action)
        for key, (row, num, txt) in self.nav.items():
            on = key == action
            colour_bg = INK if on else PAPER_2
            colour_fg = SHEET if on else INK
            for widget in (row, num, txt):
                widget.configure(bg=colour_bg)
            num.configure(fg=colour_fg)
            txt.configure(fg=colour_fg, font=self.f_body_b if on else self.f_nav)

        self.big.configure(text=f"0{number}")
        self.section.configure(text=spaced(SECTION_LABELS[action]))
        self.title.configure(text=label)
        self.desc.configure(text=DESCRIPTIONS[action])

        for frame in (self.input_row, self.export_row, self.myip_row):
            frame.pack_forget()
        anchor = self.desc
        if prompt:
            self.prompt.configure(text=spaced(prompt))
            self.input_row.pack(fill="x", padx=48, after=anchor)
            self.entry.delete(0, "end")
            self.entry.insert(0, example)
            self.entry.focus_set()
            self.entry.select_range(0, "end")
            self._clear_result(HINTS[action])
        elif action == "my_ip":
            self.myip_row.pack(fill="x", padx=48, after=anchor)
            self._clear_result("Press Check my IP to read your public address and provider.")
        else:
            self.export_row.pack(fill="x", padx=48, after=anchor)
            if self.last_result is None:
                self._clear_result("Nothing to export yet. Run one of features 1 to 4 first.")
            else:
                self._show_result(self.last_title, self.last_result)
        self._set_status("", "")

    def run(self):
        if self.busy or self.current == "export":
            return
        action = self.current
        value = self.entry.get() if action not in ("my_ip",) else ""
        self.busy = True
        what = "your public IP" if action == "my_ip" else value.strip() or "input"
        self._set_status("info", f"Working on {what} …")

        def work():
            try:
                outcome = ("ok", run_action(action, value))
            except ValueError as exc:
                outcome = ("error", f"Invalid input: {exc}")
            except ConnectionError as exc:
                outcome = ("error", f"Network error: {exc}")
            except Exception as exc:  # keep the window alive on anything unexpected
                outcome = ("error", f"Error: {exc}")
            self.root.after(0, lambda: self._finish(action, outcome))

        threading.Thread(target=work, daemon=True).start()

    def _finish(self, action, outcome):
        self.busy = False
        if action != self.current:
            return  # the user switched feature while waiting
        kind, payload = outcome
        if kind == "ok":
            title, data = payload
            self.last_title, self.last_result = title, data
            self._show_result(title, data)
            if action == "subnet":
                self._draw_gauge(data)
            self._set_status("ok", "Done. Feature 5 can save this result.")
        else:
            self._show_error(payload)
            self._set_status("", "Fix the input or check the connection, then run again.")

    def _show_error(self, message):
        for child in self.result.winfo_children():
            child.destroy()
        row = tk.Frame(self.result, bg=SHEET)
        row.pack(anchor="w")
        tk.Label(row, text=" ERROR ", font=self.f_label, fg=SHEET, bg=INK, padx=6, pady=3).pack(side="left")
        tk.Label(row, text=message, font=self.f_body_b, fg=INK, bg=SHEET, anchor="w", justify="left",
                 wraplength=560).pack(side="left", padx=(10, 0))

    def export(self, fmt):
        if self.last_result is None:
            self._set_status("error", "Nothing to export yet. Run one of features 1 to 4 first.")
            return
        try:
            path = ui.export_csv(self.last_result) if fmt == "csv" else ui.export_json(self.last_result)
        except OSError as exc:
            self._set_status("error", f"Could not save the file: {exc}")
            return
        self._set_status("ok", f"Saved to {path}")

    def open_exports(self):
        folder = os.path.abspath("exports")
        os.makedirs(folder, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # noqa: S606 - opens the user's own folder
            else:
                self._set_status("info", f"Exports are in {folder}")
        except OSError:
            self._set_status("info", f"Exports are in {folder}")

    # ---------- drawing ----------
    def _clear_result(self, message):
        for child in self.result.winfo_children():
            child.destroy()
        tk.Label(self.result, text=message, font=self.f_body, fg=MUTED, bg=SHEET, anchor="w",
                 justify="left").pack(anchor="w")

    def _show_result(self, title, data):
        for child in self.result.winfo_children():
            child.destroy()
        label, _sep, subject = str(title).partition(": ")
        head = tk.Frame(self.result, bg=SHEET)
        head.pack(anchor="w", fill="x", pady=(0, 10))
        tk.Label(head, text=spaced(label), font=self.f_label, fg=INK, bg=SHEET).pack(side="left")
        if subject:
            tk.Label(head, text=subject, font=self.f_mono, fg=INK_2, bg=SHEET).pack(side="left", padx=(14, 0))

        grid = tk.Frame(self.result, bg=SHEET)
        grid.pack(anchor="w")
        for r, (key, value) in enumerate(data.items()):
            info = ui._is_informational(key, value)
            tk.Label(grid, text=str(key), font=self.f_body, fg=MUTED, bg=SHEET, anchor="w").grid(
                row=r, column=0, sticky="w", padx=(0, 34), pady=1)
            tk.Label(grid, text=str(value), font=self.f_mono if info else self.f_mono_b,
                     fg=MUTED if info else INK, bg=SHEET, anchor="w").grid(row=r, column=1, sticky="w", pady=1)

    def _draw_gauge(self, data):
        prefix = int(data["Prefix length"])
        bits = 32 if data["Version"] == "IPv4" else 128
        cells, size, gap = 32, 13, 3
        filled = round(cells * prefix / bits)
        wrap = tk.Frame(self.result, bg=SHEET)
        wrap.pack(anchor="w", pady=(12, 0))
        tk.Label(wrap, text=spaced("network bits"), font=self.f_label, fg=MUTED, bg=SHEET).pack(anchor="w")
        canvas = tk.Canvas(wrap, width=cells * (size + gap), height=size + 2, bg=SHEET, highlightthickness=0)
        canvas.pack(anchor="w", pady=(6, 4))
        for i in range(cells):
            x = i * (size + gap)
            canvas.create_rectangle(x, 1, x + size, size + 1, outline="", fill=INK if i < filled else TAUPE)
        tk.Label(wrap, text=f"{prefix} network  ·  {bits - prefix} host", font=self.f_small,
                 fg=MUTED, bg=SHEET).pack(anchor="w")

    def _set_status(self, kind, text):
        styles = {
            "error": (" ERROR ", INK, SHEET),
            "ok": (" DONE ", INK, SHEET),
            "info": (" … ", PAPER_2, INK),
        }
        if kind in styles:
            label, bg, fg = styles[kind]
            self.badge.configure(text=label, bg=bg, fg=fg)
        else:
            self.badge.configure(text="", bg=SHEET)
        self.status_text.configure(text=text, fg=INK if kind == "error" else MUTED)


def _sharp_on_windows():
    """Tell Windows this app handles display scaling itself, so text is crisp
    instead of blurred on laptops set to 125% or 150%."""
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def main():
    if tk is None:
        print("This Python has no Tkinter. Use the terminal app instead: python main.py")
        return
    _sharp_on_windows()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
