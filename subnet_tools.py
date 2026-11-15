"""Offline IP tools using Python's built-in ipaddress module (no internet needed).

Owner: Francis (branch: feature/subnet-tools)
Docs: https://docs.python.org/3/library/ipaddress.html
"""


def classify_address(address):
    """Return a dict describing an IP address.

    Example for "10.0.0.5":
        {"Address": "10.0.0.5", "Version": "IPv4", "Type": "Private"}
    Types to detect: Loopback, Private, Link-local, Multicast, Public.
    Raise ValueError for an invalid address.
    """
    # TODO: use ipaddress.ip_address() and its is_loopback / is_private / ... properties
    raise NotImplementedError("subnet_tools.classify_address")


def subnet_info(cidr):
    """Return a dict of subnet details for a network in CIDR notation.

    Example for "192.168.10.0/26":
        Network 192.168.10.0, Broadcast 192.168.10.63, Mask 255.255.255.192,
        Wildcard 0.0.0.63, First host .1, Last host .62, Usable hosts 62
    Raise ValueError for invalid input.
    """
    # TODO: use ipaddress.ip_network(cidr, strict=False)
    raise NotImplementedError("subnet_tools.subnet_info")
