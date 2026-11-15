"""Public IP detection and provider details.

Owner: Jerome (branch: feature/ip-info)

APIs (free, no key):
    https://api.ipify.org?format=json    -> {"ip": "<IPv4>"}
    https://api6.ipify.org?format=json   -> {"ip": "<IPv6>"}  (fails if the network has no IPv6)
    https://ipapi.co/json/               -> details for this computer's IP
    http://ip-api.com/json/              -> fallback if ipapi.co fails or is rate-limited

Design notes for future maintainers:
    - Every network call goes through a tiny `_get_json()` helper so the
      timeout, headers and error handling stay consistent in one place.
    - `get_public_ipv4`/`get_public_ipv6` never raise: any problem (network
      error, bad JSON, garbage value) results in `None`, per the contract in
      docs/INTERFACES.md.
"""

import ipaddress

import requests

TIMEOUT = 5  # seconds for every HTTP request

# Generic, non-identifying User-Agent. Some free APIs throttle or reject
# requests that have no User-Agent header at all.
USER_AGENT = "devasc-ip-address-app/1.0"

_HEADERS = {"User-Agent": USER_AGENT}


def _get_json(url):
    """GET `url` and return the parsed JSON body, or None on any failure.

    Centralises the timeout, User-Agent header and error handling used by
    every HTTP call in this module. Never raises: network errors, non-2xx
    status codes and invalid JSON are all treated as "no data".
    """
    try:
        response = requests.get(url, timeout=TIMEOUT, headers=_HEADERS)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        # RequestException covers connection errors, timeouts, DNS failures,
        # bad status codes (raise_for_status), etc. ValueError covers a body
        # that isn't valid JSON.
        return None


def get_public_ipv4():
    """Return this computer's public IPv4 address as a string, or None on failure.

    Calls https://api.ipify.org?format=json. The returned value is validated
    with the `ipaddress` module so a malformed or unexpected response never
    gets returned as if it were a real address.
    """
    data = _get_json("https://api.ipify.org?format=json")
    if not isinstance(data, dict):
        return None

    ip = data.get("ip")
    try:
        ipaddress.IPv4Address(ip)
    except (ValueError, TypeError):
        return None
    return ip


def get_public_ipv6():
    """Return this computer's public IPv6 address, or None if the network has no IPv6.

    Calls https://api6.ipify.org?format=json. A network without IPv6
    connectivity simply fails to reach api6.ipify.org, which `_get_json`
    turns into None - that is the expected, non-error outcome here.
    """
    data = _get_json("https://api6.ipify.org?format=json")
    if not isinstance(data, dict):
        return None

    ip = data.get("ip")
    try:
        ipaddress.IPv6Address(ip)
    except (ValueError, TypeError):
        return None
    return ip


def get_ip_details(ip=None):
    """Return a dict of details for `ip` (or this computer's IP when None).

    Keys: ISP, ASN, Country, Country code, Region, City, Timezone.
    Try ipapi.co first; if it fails or returns an error, use ip-api.com.
    """
    # TODO: call ipapi.co, fall back to ip-api.com, map both to the same keys
    raise NotImplementedError("ip_info.get_ip_details")
