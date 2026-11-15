"""DevASC IP Address App - main menu.

Run with:  python main.py

Each menu option calls a function from one module. Until a module's owner
implements it, the function raises NotImplementedError and the menu shows
"not implemented yet" instead of crashing.
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
    details = ip_info.get_ip_details()
    result = {
        "IPv4": ipv4 or "not available",
        "IPv6": ipv6 or "not available on this network",
        **details,
    }
    ui.show_table("My public IP", result)
    return result


def option_lookup():
    """2. Look up any IP address or domain name."""
    target = input("Enter an IP address or domain: ").strip()
    result = lookup.lookup(target)
    ui.show_table(f"Lookup: {target}", result)
    return result


def option_classify():
    """3. Classify an IP address (public, private, loopback, version)."""
    address = input("Enter an IP address: ").strip()
    result = subnet_tools.classify_address(address)
    ui.show_table(f"Address: {address}", result)
    return result


def option_subnet():
    """4. Calculate subnet details from CIDR notation, e.g. 192.168.10.0/26."""
    cidr = input("Enter a network in CIDR notation (e.g. 192.168.10.0/26): ").strip()
    result = subnet_tools.subnet_info(cidr)
    ui.show_table(f"Subnet: {cidr}", result)
    return result


def option_export():
    """5. Export the last result to JSON or CSV."""
    if last_result is None:
        print("Nothing to export yet. Run one of options 1-4 first.")
        return None
    fmt = input("Format (json/csv): ").strip().lower()
    if fmt == "csv":
        path = ui.export_csv(last_result)
    else:
        path = ui.export_json(last_result)
    print(f"Saved to {path}")
    return None


MENU = {
    "1": ("My public IP", option_my_ip),
    "2": ("Look up an IP or domain", option_lookup),
    "3": ("Classify an IP address", option_classify),
    "4": ("Subnet calculator", option_subnet),
    "5": ("Export last result", option_export),
}


def main():
    global last_result
    while True:
        print("\n=== DevASC IP Address App ===")
        for key, (label, _) in MENU.items():
            print(f"  {key}. {label}")
        print("  0. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Goodbye!")
            break
        if choice not in MENU:
            print("Invalid choice, try again.")
            continue

        try:
            result = MENU[choice][1]()
            if result is not None:
                last_result = result
        except NotImplementedError as exc:
            print(f"Not implemented yet: {exc}")
        except Exception as exc:  # keep the menu alive on any unexpected error
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()
