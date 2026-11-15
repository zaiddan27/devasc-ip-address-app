"""Offline IP tools using Python's built-in ipaddress module (no internet needed).

Owner: Francis (branch: feature/subnet-tools)
Docs: https://docs.python.org/3/library/ipaddress.html

This module is the team's "networking authority": every number it prints
(netmasks, host counts, address classifications) must be correct, because the
rest of the app and the people reading its output trust it without checking.
"""

import ipaddress

# RFC 6598 "Shared Address Space" (a.k.a. CGNAT range), used by ISPs between
# customer routers and their carrier-grade NAT. It is NOT globally routable,
# but Python's ipaddress module does not consider it ``is_private`` either
# (see the CONTRACT NOTE in classify_address below), so we detect it by hand.
CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")

# For a network technician, "Private" means the address blocks you are
# actually allowed to assign on a private LAN: RFC 1918 (IPv4) and RFC 4193
# Unique Local Addresses (IPv6). We check membership in this explicit list
# instead of trusting Python's is_private, because recent Python versions
# also mark many *other* IANA special-purpose blocks (documentation/TEST-NET
# ranges, benchmarking space, Class E, the limited broadcast address, etc.)
# as is_private even though nobody configures those on a private network.
# Those other blocks are reported as "Reserved" instead - see the Type
# precedence notes in classify_address below.
PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("fc00::/7"),
)


def classify_address(address):
    """Classify a single IP address (IPv4 or IPv6).

    Returns an ordered dict:
        {"Address": <as given>, "Version": "IPv4"|"IPv6", "Type": <see below>}
    IPv6 addresses get an extra "Expanded" key with the fully written-out
    (non-compressed) form, e.g. "2001:0db8:0000:...:0001", which is useful
    for technicians comparing addresses by eye.

    Type precedence (checked in this order - the first match wins):
        1. Loopback    - loops back to the same host (127.0.0.0/8, ::1)
        2. Unspecified - "no address" placeholder (0.0.0.0, ::)
        3. Link-local  - only valid on the local segment (169.254.0.0/16,
                         fe80::/10); routers never forward these
        4. Multicast   - one-to-many delivery (224.0.0.0/4, ff00::/8)
        5. Shared (CGNAT) - RFC 6598 100.64.0.0/10, carrier-grade NAT space
        6. Private     - only the blocks a technician would actually call
                         private: RFC 1918 IPv4 (10/8, 172.16/12, 192.168/16)
                         and RFC 4193 IPv6 Unique Local (fc00::/7). Checked
                         against the explicit PRIVATE_NETWORKS list above,
                         NOT Python's is_private (see CONTRACT NOTE).
        7. Reserved    - everything else that isn't globally routable
                         (not is_global), plus anything IETF-reserved
                         (is_reserved) that is_global still happens to call
                         global (e.g. the IPv6 NAT64 well-known prefix
                         64:ff9b::/96). This is where the IANA
                         documentation/TEST-NET ranges (192.0.2.0/24,
                         198.51.100.0/24, 203.0.113.0/24, IPv6
                         2001:db8::/32), benchmarking space (198.18.0.0/15),
                         Class E (240.0.0.0/4), the limited broadcast
                         address (255.255.255.255) and other IETF
                         protocol-assignment blocks (192.0.0.0/24) land -
                         real, defined special-purpose space, but nothing a
                         technician would configure as a "private" LAN.
        8. Public      - everything else; globally routable

    CONTRACT NOTE (for the team, confirmed by the integrator): docs/
    INTERFACES.md lists Type values as Loopback, Private, Link-local,
    Multicast, Reserved, Unspecified, Public. This implementation adds one
    extra value, "Shared (CGNAT)", for 100.64.0.0/10 - that block is neither
    is_private() nor is_global() in current Python (routable inside an ISP,
    not on the public Internet), so it doesn't fit "Private" or "Public".
    The integrator has approved keeping this value and will add it to
    docs/INTERFACES.md.

    "Private" deliberately does NOT use Python's is_private property: recent
    Python versions also mark many other IANA special-purpose blocks (TEST-
    NET/documentation ranges, benchmarking space, Class E, limited
    broadcast, etc.) as is_private, which would be misleading for a network
    technician. Those blocks are classified as "Reserved" instead, per the
    precedence above.

    Raises ValueError with a friendly message for anything that is not a
    valid IPv4 or IPv6 address (extra whitespace is stripped first).
    """
    text = address.strip()
    if not text:
        raise ValueError("Address cannot be empty")

    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        raise ValueError(f"{text} is not a valid IPv4 or IPv6 address") from None

    if ip.is_loopback:
        ip_type = "Loopback"
    elif ip.is_unspecified:
        ip_type = "Unspecified"
    elif ip.is_link_local:
        ip_type = "Link-local"
    elif ip.is_multicast:
        ip_type = "Multicast"
    elif ip.version == 4 and ip in CGNAT_NETWORK:
        ip_type = "Shared (CGNAT)"
    elif any(ip in net for net in PRIVATE_NETWORKS):
        ip_type = "Private"
    elif not ip.is_global or ip.is_reserved:
        ip_type = "Reserved"
    else:
        ip_type = "Public"

    result = {
        "Address": text,
        "Version": "IPv4" if ip.version == 4 else "IPv6",
        "Type": ip_type,
    }
    if ip.version == 6:
        result["Expanded"] = ip.exploded
    return result


def subnet_info(cidr):
    """Return subnet details for a network in CIDR notation.

    Accepts either "network/prefix" (e.g. "192.168.10.0/26") or a bare
    address with no prefix (e.g. "192.168.10.5"), which is treated as a
    single-host network: /32 for IPv4, /128 for IPv6. This matches what
    ipaddress.ip_network() does by default and lets a technician paste a
    plain address to see "this one host" subnet info instead of an error.

    Host bits may be set (e.g. "192.168.10.5/26"): we use strict=False, so
    the address is rounded down to its network, e.g. "192.168.10.0/26".
    This is the normal real-world case (typing a host's own address plus
    its mask) rather than an error.

    Returns an ordered dict:
        Network         - "<network address>/<prefix length>", e.g.
                           "192.168.10.0/26"
        Version         - "IPv4" or "IPv6"
        Prefix length    - the prefix length as an int, e.g. 26
        Netmask          - the subnet mask, e.g. "255.255.255.192". For
                           IPv6 this is shown in its normal (compressed)
                           form, e.g. "ffff:ffff:ffff:ffff::".
        Wildcard         - the "inverse mask" some Cisco commands want
                           (access-lists, OSPF network statements): it has
                           a 1 bit everywhere the netmask has a 0 bit, e.g.
                           netmask 255.255.255.192 -> wildcard 0.0.0.63.
        Broadcast        - the IPv4 broadcast address (highest address in
                           the network, used to reach every host on the
                           segment at once). IPv6 has no broadcast concept
                           (it uses multicast instead), so this is always
                           the literal string "N/A (IPv6)" for IPv6 input.
        First host       - lowest usable host address
        Last host        - highest usable host address
        Usable hosts     - how many addresses hosts can actually use, as
                           an int
        Total addresses  - size of the whole network (2 ** host-bits), as
                           an int. IPv6 /64 and shorter can be astronomically
                           large (e.g. 2**64); Python ints handle that fine.

    Host counting and RFC 3021 (/31 and /32, and their IPv6 analogues /127
    and /128):
        Normally the first address in a network is the "network address"
        (identifies the subnet itself) and, for IPv4, the last address is
        the broadcast address - neither is assignable to a host, so usable
        hosts = total addresses - 2.
        /31 and /127 are point-to-point links with only two addresses total.
        RFC 3021 (IPv4) and RFC 6164 (IPv6) say: skip the network/broadcast
        reservation and let both addresses be used as host addresses, since
        reserving 2 out of only 2 addresses would leave nothing to assign.
        /32 and /128 describe a single host (e.g. a loopback or a route to
        one address): there is only one address, and it is that one host.

    Raises ValueError with a friendly message for invalid CIDR text or a
    prefix length outside the valid range for the address family (e.g. /33
    for IPv4).
    """
    text = cidr.strip()
    if not text:
        raise ValueError("Enter a network in CIDR notation, e.g. 192.168.10.0/26")

    try:
        network = ipaddress.ip_network(text, strict=False)
    except ValueError:
        raise ValueError(
            f"{text} is not a valid network in CIDR notation (e.g. 192.168.10.0/26)"
        ) from None

    is_ipv4 = network.version == 4
    total_addresses = network.num_addresses

    # network[0] is the first address in the range, network[-1] the last.
    # These are O(1) lookups (no need to materialise every address), which
    # matters for huge IPv6 networks such as /64 (2**64 addresses).
    first_address = network[0]
    last_address = network[-1]

    if total_addresses <= 2:
        # /31, /32 (IPv4) or /127, /128 (IPv6): RFC 3021 / single host.
        first_host = first_address
        last_host = last_address
        usable_hosts = total_addresses
    else:
        first_host = first_address + 1
        last_host = last_address - 1
        usable_hosts = total_addresses - 2

    return {
        "Network": f"{network.network_address}/{network.prefixlen}",
        "Version": "IPv4" if is_ipv4 else "IPv6",
        "Prefix length": network.prefixlen,
        "Netmask": str(network.netmask),
        "Wildcard": str(network.hostmask),
        "Broadcast": str(network.broadcast_address) if is_ipv4 else "N/A (IPv6)",
        "First host": str(first_host),
        "Last host": str(last_host),
        "Usable hosts": usable_hosts,
        "Total addresses": total_addresses,
    }
