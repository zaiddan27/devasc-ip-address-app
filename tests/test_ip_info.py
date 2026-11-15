"""Offline tests for ip_info.py.

All HTTP calls are mocked with unittest.mock so these tests never touch
the network (per docs/INTERFACES.md: "Tests must not need the internet").
"""

from unittest.mock import patch

import pytest
import requests

import ip_info


class FakeResponse:
    """Minimal stand-in for requests.Response used by the tests below."""

    def __init__(self, json_data=None, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        if self._json_data is None:
            raise ValueError("no JSON body")
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


# ---------------------------------------------------------------------------
# get_public_ipv4 / get_public_ipv6
# ---------------------------------------------------------------------------

def test_get_public_ipv4_success():
    with patch("ip_info.requests.get", return_value=FakeResponse({"ip": "203.0.113.5"})) as mock_get:
        assert ip_info.get_public_ipv4() == "203.0.113.5"
    # Confirm it called ipify's IPv4 endpoint with the required timeout.
    args, kwargs = mock_get.call_args
    assert "api.ipify.org" in args[0]
    assert kwargs.get("timeout") == ip_info.TIMEOUT


def test_get_public_ipv4_invalid_value_returns_none():
    """A garbage/non-IP value from ipify must not be returned as-is."""
    with patch("ip_info.requests.get", return_value=FakeResponse({"ip": "not-an-ip"})):
        assert ip_info.get_public_ipv4() is None


def test_get_public_ipv6_unavailable_returns_none():
    """No IPv6 connectivity -> the request fails -> None (expected, not an error)."""
    with patch("ip_info.requests.get", side_effect=requests.ConnectionError("no route")):
        assert ip_info.get_public_ipv6() is None


def test_get_public_ipv6_success():
    with patch("ip_info.requests.get", return_value=FakeResponse({"ip": "2001:db8::1"})):
        assert ip_info.get_public_ipv6() == "2001:db8::1"


# ---------------------------------------------------------------------------
# get_ip_details - ipapi.co success
# ---------------------------------------------------------------------------

def test_get_ip_details_ipapi_co_success():
    payload = {
        "ip": "8.8.8.8",
        "org": "Google LLC",
        "asn": "AS15169",
        "country_name": "United States",
        "country_code": "US",
        "region": "California",
        "city": "Mountain View",
        "timezone": "America/Los_Angeles",
    }
    with patch("ip_info.requests.get", return_value=FakeResponse(payload)):
        result = ip_info.get_ip_details("8.8.8.8")

    assert list(result.keys()) == [
        "IP", "ISP", "ASN", "Country", "Country code", "Region", "City", "Timezone", "Source",
    ]
    assert result["IP"] == "8.8.8.8"
    assert result["ISP"] == "Google LLC"
    assert result["ASN"] == "AS15169"
    assert result["Country"] == "United States"
    assert result["Country code"] == "US"
    assert result["Region"] == "California"
    assert result["City"] == "Mountain View"
    assert result["Timezone"] == "America/Los_Angeles"
    assert result["Source"] == "ipapi.co"


def test_get_ip_details_ipapi_co_missing_fields_become_na():
    payload = {"ip": "8.8.8.8"}  # everything else missing
    with patch("ip_info.requests.get", return_value=FakeResponse(payload)):
        result = ip_info.get_ip_details("8.8.8.8")

    assert result["Source"] == "ipapi.co"
    assert result["ISP"] == "N/A"
    assert result["ASN"] == "N/A"
    assert result["Timezone"] == "N/A"


# ---------------------------------------------------------------------------
# get_ip_details - ipapi.co fails/rate-limited -> ip-api.com fallback
# ---------------------------------------------------------------------------

def test_get_ip_details_falls_back_on_ipapi_co_error_flag():
    """ipapi.co's in-body error (e.g. Reserved IP Address) triggers fallback."""
    ipapi_co_error = FakeResponse({"error": True, "reason": "Reserved IP Address"})
    ip_api_com_payload = FakeResponse({
        "status": "success",
        "query": "8.8.8.8",
        "isp": "Google LLC",
        "as": "AS15169 Google LLC",
        "country": "United States",
        "countryCode": "US",
        "regionName": "California",
        "city": "Mountain View",
        "timezone": "America/Los_Angeles",
    })

    with patch("ip_info.requests.get", side_effect=[ipapi_co_error, ip_api_com_payload]):
        result = ip_info.get_ip_details("8.8.8.8")

    assert result["Source"] == "ip-api.com"
    assert result["IP"] == "8.8.8.8"
    assert result["ISP"] == "Google LLC"
    assert result["ASN"] == "AS15169"  # parsed out of "AS15169 Google LLC"
    assert result["Country"] == "United States"
    assert result["Country code"] == "US"
    assert result["Region"] == "California"
    assert result["City"] == "Mountain View"
    assert result["Timezone"] == "America/Los_Angeles"


def test_get_ip_details_falls_back_on_ipapi_co_429():
    """ipapi.co returning HTTP 429 (rate limited) triggers fallback."""
    rate_limited = FakeResponse({"error": True, "reason": "RateLimited"}, status_code=429)
    ip_api_com_payload = FakeResponse({
        "status": "success",
        "query": "1.1.1.1",
        "isp": "Cloudflare, Inc.",
        "as": "AS13335 Cloudflare, Inc.",
        "country": "Australia",
        "countryCode": "AU",
        "regionName": "Queensland",
        "city": "South Brisbane",
        "timezone": "Australia/Brisbane",
    })

    with patch("ip_info.requests.get", side_effect=[rate_limited, ip_api_com_payload]):
        result = ip_info.get_ip_details("1.1.1.1")

    assert result["Source"] == "ip-api.com"
    assert result["ASN"] == "AS13335"


# ---------------------------------------------------------------------------
# get_ip_details - both providers fail
# ---------------------------------------------------------------------------

def test_get_ip_details_both_fail_raises_connection_error():
    with patch("ip_info.requests.get", side_effect=requests.ConnectionError("no network")):
        with pytest.raises(ConnectionError):
            ip_info.get_ip_details("8.8.8.8")


def test_get_ip_details_both_report_failure_status_raises_connection_error():
    ipapi_co_error = FakeResponse({"error": True, "reason": "RateLimited"})
    ip_api_com_error = FakeResponse({"status": "fail", "message": "invalid query"})

    with patch("ip_info.requests.get", side_effect=[ipapi_co_error, ip_api_com_error]):
        with pytest.raises(ConnectionError):
            ip_info.get_ip_details("8.8.8.8")
