"""Public IP detection and provider details.

Owner: Jerome (branch: feature/ip-info)

APIs (free, no key):
    https://api.ipify.org?format=json    -> {"ip": "<IPv4>"}
    https://api6.ipify.org?format=json   -> {"ip": "<IPv6>"}  (fails if the network has no IPv6)
    https://ipapi.co/json/               -> details for this computer's IP
    http://ip-api.com/json/              -> fallback if ipapi.co fails or is rate-limited
"""

TIMEOUT = 5  # seconds for every HTTP request


def get_public_ipv4():
    """Return this computer's public IPv4 address as a string, or None on failure."""
    # TODO: GET https://api.ipify.org?format=json with requests and return data["ip"]
    raise NotImplementedError("ip_info.get_public_ipv4")


def get_public_ipv6():
    """Return this computer's public IPv6 address, or None if the network has no IPv6."""
    # TODO: GET https://api6.ipify.org?format=json; on a connection error return None
    raise NotImplementedError("ip_info.get_public_ipv6")


def get_ip_details(ip=None):
    """Return a dict of details for `ip` (or this computer's IP when None).

    Keys: ISP, ASN, Country, Country code, Region, City, Timezone.
    Try ipapi.co first; if it fails or returns an error, use ip-api.com.
    """
    # TODO: call ipapi.co, fall back to ip-api.com, map both to the same keys
    raise NotImplementedError("ip_info.get_ip_details")
