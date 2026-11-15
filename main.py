"""IP_PAPI - main menu.

Run with:  python main.py

Each menu option calls a function from one module. Until a module's owner
implements it, the function raises NotImplementedError and the menu shows
"not implemented yet" instead of crashing. The menu is also written to
survive bad input, network failures and the user quitting with Ctrl+C or
piped input running out (EOF) - none of that should ever print a traceback.
"""

import ip_info
import lookup
import subnet_tools
import ui

# Holds the most recent result so option 5 can export it.
last_result = None


def option_my_ip():
    """1. Show this computer's public IPv4/IPv6 and provider details."""
    ipv4 = ip_info.get_public_ipv4()
    ipv6 = ip_info.get_public_ipv6()

    # get_ip_details() can fail (ConnectionError) even when the address
    # lookups above succeeded, e.g. every provider API is down. Still show
    # the IPv4/IPv6 we do have instead of losing the whole result.
    try:
        details = ip_info.get_ip_details()
    except ConnectionError as exc:
        details = {"Note": f"Provider details unavailable - {exc}"}

    result = {
        "IPv4": ipv4 or "not available",
        "IPv6": ipv6 or "not available on this network",
        **details,
    }
    ui.show_table("My public IP", result)
    return result


def option_lookup():
    """2. Look up any IP address or domain name."""
    target = ui.ask("Enter an IP address or domain:").strip()
    result = lookup.lookup(target)
    ui.show_table(f"Lookup: {target}", result)
    return result


def option_classify():
    """3. Classify an IP address (public, private, loopback, version)."""
    address = ui.ask("Enter an IP address:").strip()
    result = subnet_tools.classify_address(address)
    ui.show_table(f"Address: {address}", result)
    return result


def option_subnet():
    """4. Calculate subnet details from CIDR notation, e.g. 192.168.10.0/26."""
    cidr = ui.ask("Enter a network in CIDR notation (e.g. 192.168.10.0/26):").strip()
    result = subnet_tools.subnet_info(cidr)
    ui.show_table(f"Subnet: {cidr}", result)

    # Visual of the mask: how many bits are network vs host.
    prefix = int(result["Prefix length"])
    max_bits = 32 if result["Version"] == "IPv4" else 128
    ui.show_gauge(
        "network bits",
        prefix,
        max_bits,
        f"{prefix} network  ·  {max_bits - prefix} host",
    )
    return result


def option_export():
    """5. Export the last result to JSON or CSV."""
    if last_result is None:
        ui.show_message("Nothing to export yet. Run one of options 1-4 first.", "warning")
        return None

    fmt = ui.ask("Format (json/csv):").strip().lower()
    if fmt == "csv":
        path = ui.export_csv(last_result)
    else:
        if fmt != "json":
            ui.show_message("Unrecognised format, defaulting to json.", "warning")
        path = ui.export_json(last_result)

    ui.show_message(f"Saved to {path}", "success")
    return None


MENU = {
    "1": ("My public IP", option_my_ip),
    "2": ("Look up an IP or domain", option_lookup),
    "3": ("Classify an IP address", option_classify),
    "4": ("Subnet calculator", option_subnet),
    "5": ("Export last result", option_export),
}


def show_menu():
    """Print the numbered list of options below the header."""
    ui.show_menu([(key, label) for key, (label, _) in MENU.items()] + [("0", "Exit")])


def main():
    global last_result
    ui.show_header()

    while True:
        show_menu()
        try:
            choice = ui.ask("Choose an option:").strip()
        except (KeyboardInterrupt, EOFError):
            # Ctrl+C, or piped input ran out - exit cleanly, no traceback.
            ui.show_message("Goodbye.")
            break

        if choice == "0":
            ui.show_message("Goodbye.")
            break
        if choice not in MENU:
            ui.show_message("Invalid choice, try again.", "warning")
            continue

        try:
            result = MENU[choice][1]()
            if result is not None:
                last_result = result
        except (KeyboardInterrupt, EOFError):
            # Can also happen inside an option, e.g. while typing an address.
            ui.show_message("Goodbye.")
            break
        except NotImplementedError as exc:
            # Expected while a teammate's module is still a stub.
            ui.show_message(f"Not implemented yet: {exc}", "warning")
        except ValueError as exc:
            # Bad input the user typed (invalid IP, bad CIDR, etc.).
            ui.show_message(f"Invalid input: {exc}", "error")
        except ConnectionError as exc:
            # A network/API call failed.
            ui.show_message(f"Network error: {exc}", "error")
        except Exception as exc:  # keep the menu alive on any unexpected error
            ui.show_message(f"Error: {exc}", "error")


if __name__ == "__main__":
    main()
