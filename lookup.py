"""Look up any IP address or domain name.

Owner: John Patrick (branch: feature/lookup)
"""


def resolve_target(target):
    """Return an IP address for `target`.

    If `target` is already a valid IP, return it unchanged.
    If it is a domain name (e.g. cisco.com), resolve it with socket.gethostbyname().
    Raise ValueError with a clear message if it is neither.
    """
    # TODO: validate with ipaddress.ip_address(); otherwise try socket.gethostbyname()
    raise NotImplementedError("lookup.resolve_target")


def lookup(target):
    """Return a dict of details for an IP address or domain name.

    Use resolve_target() first, then ip_info.get_ip_details(ip).
    Include the resolved IP in the result, e.g. {"IP": "8.8.8.8", "ISP": ...}.
    """
    # TODO: implement using resolve_target() and ip_info.get_ip_details()
    raise NotImplementedError("lookup.lookup")
