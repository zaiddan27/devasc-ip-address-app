"""Look up any IP address or domain name.

Owner: John Patrick (branch: feature/lookup)

Public API (see docs/INTERFACES.md for the binding contract):
    resolve_target(target) -> IP address string
    lookup(target)         -> dict: Query, IP, then provider details

Design notes for the next team:
    - `ip_info` is imported at module level (not inside functions) so that
      tests - and any future caller - can patch `lookup.ip_info.get_ip_details`
      with unittest.mock and have it take effect here.
    - Addresses that are not globally routable (private, loopback, link-local,
      reserved, multicast, unspecified, or shared/CGNAT space) are never sent
      to the provider APIs in ip_info.py. There is nothing useful an IP
      geolocation API could say about 192.168.1.1, and it would be wasteful
      (and sometimes privacy-leaking) to try.
"""

import ipaddress
import socket
from urllib.parse import urlsplit

import ip_info


def _strip_url_wrapper(text):
    """Strip a leading http(s):// scheme and any path/port/credentials.

    Lets a technician paste a full URL (e.g. "https://www.cisco.com/c/en/us")
    and still get a usable host, instead of making them clean it up first.
    Plain hostnames/IPs without a scheme (e.g. "cisco.com") pass through
    unchanged, since urlsplit only recognises "//" as a netloc marker when a
    scheme is present.
    """
    if "://" in text:
        parsed = urlsplit(text)
        host = parsed.hostname  # drops port, userinfo, path, query, fragment
        if host:
            return host
        # Scheme present but nothing usable after it (e.g. "https://").
        return text
    return text


def resolve_target(target):
    """Resolve `target` (an IP address, domain name, or pasted URL) to an IP.

    Steps:
        1. Strip surrounding whitespace; reject empty input.
        2. If `target` looks like a URL, strip the scheme and any
           path/port/credentials down to the bare host.
        3. If the remainder is a valid IPv4/IPv6 address, return it
           normalised (e.g. "08.8.8.8" is rejected, "::1" stays "::1").
        4. Otherwise, treat it as a domain name and resolve it with
           socket.getaddrinfo(), preferring an IPv4 result and falling back
           to IPv6.

    Args:
        target: user-supplied string - an IP, a domain, or a URL.

    Returns:
        str: a normalised IP address (IPv4 or IPv6).

    Raises:
        ValueError: if `target` is empty, is an obviously invalid IP
            (e.g. "999.1.1.1" - four dotted groups but out of range), or is a
            domain name that cannot be resolved.
    """
    if target is None:
        raise ValueError("Please enter an IP address or domain name.")

    target = target.strip()
    if not target:
        raise ValueError("Please enter an IP address or domain name.")

    host = _strip_url_wrapper(target).strip()
    if not host:
        raise ValueError(f"Could not find a host in '{target}'.")

    # Already a valid IP address? Return it normalised and skip DNS entirely.
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        pass

    # Looks like a dotted-quad but isn't a valid IPv4 address (e.g. an octet
    # over 255, like "999.1.1.1"). Reject it with a clear message rather than
    # sending it to DNS, where it would just fail resolution with a more
    # confusing error.
    octets = host.split(".")
    if len(octets) == 4 and all(part.isdigit() for part in octets):
        raise ValueError(f"'{target}' is not a valid IP address.")

    # Otherwise, treat it as a domain name and resolve it with DNS.
    try:
        results = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise ValueError(f"Could not resolve '{host}'.")

    if not results:
        raise ValueError(f"Could not resolve '{host}'.")

    # Prefer an IPv4 result (family == socket.AF_INET); fall back to
    # whatever came back first (typically IPv6) if there is no IPv4 entry.
    ipv4_addresses = [
        info[4][0] for info in results if info[0] == socket.AF_INET
    ]
    if ipv4_addresses:
        return ipv4_addresses[0]
    return results[0][4][0]


def lookup(target):
    """Resolve `target` and return provider details about the resulting IP.

    Private/loopback/link-local/reserved/multicast/unspecified/CGNAT
    addresses are never sent to ip_info.get_ip_details(): there is no public
    provider data for them, so a short note is returned instead.

    Args:
        target: user-supplied string - an IP, a domain, or a URL.

    Returns:
        dict: "Query" (the original input), "IP" (the resolved address),
        then either "Note" (for non-routable addresses) or the
        ip_info.get_ip_details() keys with any duplicate "IP" key removed,
        in their original order.

    Raises:
        ValueError: propagated from resolve_target() for bad input.
        ConnectionError: propagated from ip_info.get_ip_details() if every
            provider API fails.
    """
    ip = resolve_target(target)
    result = {"Query": target, "IP": ip}

    ip_obj = ipaddress.ip_address(ip)
    # ip_obj.is_global already covers private (RFC 1918), loopback,
    # link-local, reserved, unspecified, and shared address space / CGNAT
    # (100.64.0.0/10) - Python marks all of these as not is_global.
    # Multicast is checked separately: CPython's ipaddress module quirkily
    # reports is_global=True for multicast addresses (e.g. 224.0.0.1,
    # ff02::1), even though they are not something an IP-geolocation API can
    # usefully answer about, so it is excluded explicitly here.
    if not ip_obj.is_global or ip_obj.is_multicast:
        # No API call is made for any of these addresses.
        result["Note"] = "Private address - no public provider details"
        return result

    details = ip_info.get_ip_details(ip)
    for key, value in details.items():
        if key == "IP":
            continue  # already present as the second key of `result`
        result[key] = value
    return result
