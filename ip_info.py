"""Public IP detection and provider details.

Owner: Jerome (branch: feature/ip-info)

APIs (free, no key):
    https://api.ipify.org?format=json    -> {"ip": "<IPv4>"}
    https://api6.ipify.org?format=json   -> {"ip": "<IPv6>"}  (fails if the network has no IPv6)
    https://ipapi.co/json/               -> details for this computer's IP
    https://ipapi.co/<ip>/json/          -> details for a specific IP
    http://ip-api.com/json/              -> fallback if ipapi.co fails or is rate-limited
    http://ip-api.com/json/<ip>          -> fallback for a specific IP

Design notes for future maintainers:
    - Every network call goes through a tiny `_get_json()` helper so the
      timeout, headers and error handling stay consistent in one place.
    - `get_public_ipv4`/`get_public_ipv6` never raise: any problem (network
      error, bad JSON, garbage value) results in `None`, per the contract in
      docs/INTERFACES.md.
    - `get_ip_details` tries ipapi.co first, then falls back to ip-api.com.
      Both providers report errors differently (see `_ipapi_co_details` and
      `_ip_api_com_details` below), so each has its own small parser that
      returns `None` on failure and a fully-populated dict on success. Only
      if *both* fail does `get_ip_details` raise `ConnectionError`.
"""

import ipaddress

import requests

TIMEOUT = 5  # seconds for every HTTP request

# Generic, non-identifying User-Agent. Some free APIs throttle or reject
# requests that have no User-Agent header at all.
USER_AGENT = "devasc-ip-address-app/1.0"

_HEADERS = {"User-Agent": USER_AGENT}

# The exact, ordered keys that get_ip_details() must always return.
_DETAIL_KEYS = (
    "IP",
    "ISP",
    "ASN",
    "Country",
    "Country code",
    "Region",
    "City",
    "Timezone",
    "Source",
)


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


def _clean(value):
    """Return `value` as-is, or 'N/A' if it is missing/empty."""
    if value is None or value == "":
        return "N/A"
    return value


def _ipapi_co_details(ip):
    """Fetch and map details from ipapi.co. Return None if it failed.

    ipapi.co signals an error inside the JSON body itself (HTTP 200 with
    {"error": true, "reason": "..."}) and can also return HTTP 429 when
    rate-limited; `_get_json` already turns a 429 into None via
    raise_for_status(), and here we additionally check the in-body error
    flag.
    """
    url = "https://ipapi.co/json/" if ip is None else f"https://ipapi.co/{ip}/json/"
    data = _get_json(url)
    if not isinstance(data, dict):
        return None
    if data.get("error"):
        # e.g. {"error": true, "reason": "RateLimited"} or "Reserved IP Address"
        return None

    asn = data.get("asn")  # already just the number/ID for ipapi.co, e.g. "AS15169"

    return {
        "IP": _clean(data.get("ip")),
        "ISP": _clean(data.get("org")),
        "ASN": _clean(asn),
        "Country": _clean(data.get("country_name")),
        "Country code": _clean(data.get("country_code")),
        "Region": _clean(data.get("region")),
        "City": _clean(data.get("city")),
        "Timezone": _clean(data.get("timezone")),
        "Source": "ipapi.co",
    }


def _ip_api_com_details(ip):
    """Fetch and map details from ip-api.com. Return None if it failed.

    ip-api.com signals an error with {"status": "fail", "message": "..."}
    instead of an HTTP error code.
    """
    url = "http://ip-api.com/json/" if ip is None else f"http://ip-api.com/json/{ip}"
    data = _get_json(url)
    if not isinstance(data, dict):
        return None
    if data.get("status") == "fail":
        # e.g. {"status": "fail", "message": "invalid query"}
        return None

    # ip-api.com's "as" field looks like "AS15169 Google LLC"; we only want
    # the leading AS number for the ASN column.
    as_field = data.get("as") or ""
    asn = as_field.split(" ")[0] if as_field else ""

    return {
        "IP": _clean(data.get("query")),
        "ISP": _clean(data.get("isp")),
        "ASN": _clean(asn),
        "Country": _clean(data.get("country")),
        "Country code": _clean(data.get("countryCode")),
        "Region": _clean(data.get("regionName")),
        "City": _clean(data.get("city")),
        "Timezone": _clean(data.get("timezone")),
        "Source": "ip-api.com",
    }


def get_ip_details(ip=None):
    """Return a dict of provider details for `ip`, or this computer's IP when None.

    Keys, in order: IP, ISP, ASN, Country, Country code, Region, City,
    Timezone, Source. Missing individual fields are "N/A".

    Tries ipapi.co first; if it fails, errors, or is rate-limited, falls
    back to ip-api.com. If both fail, raises ConnectionError with a
    friendly message (per docs/INTERFACES.md).
    """
    details = _ipapi_co_details(ip)
    if details is None:
        details = _ip_api_com_details(ip)
    if details is None:
        raise ConnectionError(
            "Could not get IP details: both ipapi.co and ip-api.com are "
            "unreachable or returned an error. Check your internet "
            "connection and try again in a moment."
        )

    # Defensive: guarantee the exact key order/shape the contract promises,
    # even if a provider mapping above is ever changed carelessly.
    return {key: details.get(key, "N/A") for key in _DETAIL_KEYS}
