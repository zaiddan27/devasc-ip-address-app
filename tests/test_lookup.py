"""Tests for lookup.py.

Owner: John Patrick (branch: feature/lookup)

Fully offline: socket.getaddrinfo (DNS) and ip_info.get_ip_details (the
provider APIs) are both patched with unittest.mock, so these tests never
touch the network and never need real internet access.
"""

import socket

import pytest
from unittest.mock import patch

import lookup


# ---------------------------------------------------------------------------
# resolve_target
# ---------------------------------------------------------------------------


def test_resolve_target_plain_ipv4():
    """A bare IPv4 address is returned unchanged and DNS is never touched."""
    with patch("lookup.socket.getaddrinfo") as mock_getaddrinfo:
        assert lookup.resolve_target("8.8.8.8") == "8.8.8.8"
        mock_getaddrinfo.assert_not_called()


def test_resolve_target_plain_ipv6():
    """A bare IPv6 address is returned unchanged and DNS is never touched."""
    with patch("lookup.socket.getaddrinfo") as mock_getaddrinfo:
        assert lookup.resolve_target("2001:4860:4860::8888") == "2001:4860:4860::8888"
        mock_getaddrinfo.assert_not_called()


def test_resolve_target_domain_resolves_via_dns():
    """A domain name is resolved with socket.getaddrinfo, preferring IPv4."""
    fake_results = [
        (socket.AF_INET6, None, None, "", ("2001:db8::1", 0, 0, 0)),
        (socket.AF_INET, None, None, "", ("93.184.216.34", 0)),
    ]
    with patch("lookup.socket.getaddrinfo", return_value=fake_results) as mock_getaddrinfo:
        assert lookup.resolve_target("cisco.com") == "93.184.216.34"
        mock_getaddrinfo.assert_called_once_with("cisco.com", None)


def test_resolve_target_domain_ipv6_only_falls_back():
    """If the only DNS results are IPv6, an IPv6 address is returned."""
    fake_results = [
        (socket.AF_INET6, None, None, "", ("2001:db8::1", 0, 0, 0)),
    ]
    with patch("lookup.socket.getaddrinfo", return_value=fake_results):
        assert lookup.resolve_target("ipv6-only.example") == "2001:db8::1"


def test_resolve_target_strips_url_scheme_and_path():
    """A pasted URL is reduced to its host before DNS resolution."""
    fake_results = [(socket.AF_INET, None, None, "", ("93.184.216.34", 0))]
    with patch("lookup.socket.getaddrinfo", return_value=fake_results) as mock_getaddrinfo:
        ip = lookup.resolve_target("https://www.cisco.com/c/en/us")
        assert ip == "93.184.216.34"
        mock_getaddrinfo.assert_called_once_with("www.cisco.com", None)


def test_resolve_target_strips_whitespace():
    """Leading/trailing whitespace around a domain is ignored."""
    fake_results = [(socket.AF_INET, None, None, "", ("93.184.216.34", 0))]
    with patch("lookup.socket.getaddrinfo", return_value=fake_results) as mock_getaddrinfo:
        ip = lookup.resolve_target(" cisco.com ")
        assert ip == "93.184.216.34"
        mock_getaddrinfo.assert_called_once_with("cisco.com", None)


def test_resolve_target_empty_raises_value_error():
    with pytest.raises(ValueError):
        lookup.resolve_target("")


def test_resolve_target_whitespace_only_raises_value_error():
    with pytest.raises(ValueError):
        lookup.resolve_target("   ")


def test_resolve_target_invalid_dotted_quad_raises_value_error():
    """A four-group dotted number that isn't a valid IP (octet > 255)."""
    with patch("lookup.socket.getaddrinfo") as mock_getaddrinfo:
        with pytest.raises(ValueError):
            lookup.resolve_target("999.1.1.1")
        # Must not be treated as a domain and sent to DNS.
        mock_getaddrinfo.assert_not_called()


def test_resolve_target_unresolvable_domain_raises_value_error():
    with patch("lookup.socket.getaddrinfo", side_effect=socket.gaierror("not found")):
        with pytest.raises(ValueError):
            lookup.resolve_target("nosuchdomain.invalid")


# ---------------------------------------------------------------------------
# lookup
# ---------------------------------------------------------------------------


def test_lookup_public_ip_calls_get_ip_details():
    """A public IP is sent to ip_info.get_ip_details and its details merged in."""
    details = {
        "IP": "8.8.8.8",
        "ISP": "Google LLC",
        "ASN": "AS15169",
        "Country": "United States",
        "Country code": "US",
        "Region": "California",
        "City": "Mountain View",
        "Timezone": "America/Los_Angeles",
        "Source": "ipapi.co",
    }
    with patch("lookup.ip_info.get_ip_details", return_value=details) as mock_details:
        result = lookup.lookup("8.8.8.8")

    mock_details.assert_called_once_with("8.8.8.8")
    assert result["Query"] == "8.8.8.8"
    assert result["IP"] == "8.8.8.8"
    assert result["ISP"] == "Google LLC"
    assert result["Source"] == "ipapi.co"


def test_lookup_output_key_order_no_duplicate_ip():
    """Query, IP come first; the rest keeps get_ip_details' order; IP isn't duplicated."""
    details = {
        "IP": "8.8.8.8",
        "ISP": "Google LLC",
        "ASN": "AS15169",
        "Country": "United States",
        "Country code": "US",
        "Region": "California",
        "City": "Mountain View",
        "Timezone": "America/Los_Angeles",
        "Source": "ipapi.co",
    }
    with patch("lookup.ip_info.get_ip_details", return_value=details):
        result = lookup.lookup("8.8.8.8")

    assert list(result.keys()) == [
        "Query",
        "IP",
        "ISP",
        "ASN",
        "Country",
        "Country code",
        "Region",
        "City",
        "Timezone",
        "Source",
    ]
    assert list(result.keys()).count("IP") == 1


def test_lookup_private_address_returns_note_and_skips_api():
    with patch("lookup.ip_info.get_ip_details") as mock_details:
        result = lookup.lookup("10.0.0.5")

    mock_details.assert_not_called()
    assert result["Query"] == "10.0.0.5"
    assert result["IP"] == "10.0.0.5"
    assert "Note" in result
    assert "ISP" not in result


def test_lookup_loopback_address_returns_note_and_skips_api():
    with patch("lookup.ip_info.get_ip_details") as mock_details:
        result = lookup.lookup("127.0.0.1")

    mock_details.assert_not_called()
    assert "Note" in result


def test_lookup_link_local_address_returns_note_and_skips_api():
    with patch("lookup.ip_info.get_ip_details") as mock_details:
        result = lookup.lookup("169.254.1.1")

    mock_details.assert_not_called()
    assert "Note" in result


def test_lookup_cgnat_address_returns_note_and_skips_api():
    """100.64.0.0/10 (shared address space / CGNAT) is not sent to the APIs."""
    with patch("lookup.ip_info.get_ip_details") as mock_details:
        result = lookup.lookup("100.64.0.1")

    mock_details.assert_not_called()
    assert "Note" in result


def test_lookup_multicast_address_returns_note_and_skips_api():
    with patch("lookup.ip_info.get_ip_details") as mock_details:
        result = lookup.lookup("224.0.0.1")

    mock_details.assert_not_called()
    assert "Note" in result


def test_lookup_connection_error_propagates():
    with patch("lookup.ip_info.get_ip_details", side_effect=ConnectionError("all providers failed")):
        with pytest.raises(ConnectionError):
            lookup.lookup("8.8.8.8")


def test_lookup_domain_resolves_then_queries_details():
    fake_results = [(socket.AF_INET, None, None, "", ("93.184.216.34", 0))]
    details = {"IP": "93.184.216.34", "ISP": "N/A", "ASN": "N/A", "Country": "N/A",
               "Country code": "N/A", "Region": "N/A", "City": "N/A",
               "Timezone": "N/A", "Source": "ip-api.com"}
    with patch("lookup.socket.getaddrinfo", return_value=fake_results), \
         patch("lookup.ip_info.get_ip_details", return_value=details) as mock_details:
        result = lookup.lookup("cisco.com")

    mock_details.assert_called_once_with("93.184.216.34")
    assert result["Query"] == "cisco.com"
    assert result["IP"] == "93.184.216.34"
