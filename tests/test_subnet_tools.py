"""Tests for subnet_tools.py (Francis's module).

All expected values below were hand-verified against RFC 1918, RFC 3927,
RFC 4291/4193, RFC 3021 and the standard IPv4/IPv6 special-address tables -
not derived by reading what the implementation happens to produce.
"""

import pytest

from subnet_tools import classify_address, subnet_info


# ---------------------------------------------------------------------------
# subnet_info
# ---------------------------------------------------------------------------

def test_subnet_info_presentation_example():
    """The exact example used in the team's presentation."""
    result = subnet_info("192.168.10.0/26")
    assert result == {
        "Network": "192.168.10.0/26",
        "Version": "IPv4",
        "Prefix length": 26,
        "Netmask": "255.255.255.192",
        "Wildcard": "0.0.0.63",
        "Broadcast": "192.168.10.63",
        "First host": "192.168.10.1",
        "Last host": "192.168.10.62",
        "Usable hosts": 62,
        "Total addresses": 64,
    }


def test_subnet_info_host_bits_set():
    """A host address + mask (host bits set) rounds down to its network."""
    result = subnet_info("192.168.10.5/26")
    assert result["Network"] == "192.168.10.0/26"
    assert result["Broadcast"] == "192.168.10.63"
    assert result["First host"] == "192.168.10.1"
    assert result["Last host"] == "192.168.10.62"
    assert result["Usable hosts"] == 62


def test_subnet_info_slash_24():
    result = subnet_info("192.168.1.0/24")
    assert result["Network"] == "192.168.1.0/24"
    assert result["Netmask"] == "255.255.255.0"
    assert result["Wildcard"] == "0.0.0.255"
    assert result["Broadcast"] == "192.168.1.255"
    assert result["First host"] == "192.168.1.1"
    assert result["Last host"] == "192.168.1.254"
    assert result["Usable hosts"] == 254
    assert result["Total addresses"] == 256


def test_subnet_info_slash_30():
    """A /30 is the classic 2-usable-host point-to-point subnet."""
    result = subnet_info("10.0.0.0/30")
    assert result["Netmask"] == "255.255.255.252"
    assert result["Wildcard"] == "0.0.0.3"
    assert result["Broadcast"] == "10.0.0.3"
    assert result["First host"] == "10.0.0.1"
    assert result["Last host"] == "10.0.0.2"
    assert result["Usable hosts"] == 2
    assert result["Total addresses"] == 4


def test_subnet_info_slash_31_rfc3021():
    """RFC 3021: a /31 has no network/broadcast reservation - both
    addresses are usable point-to-point host addresses."""
    result = subnet_info("10.0.0.0/31")
    assert result["Netmask"] == "255.255.255.254"
    assert result["Broadcast"] == "10.0.0.1"
    assert result["First host"] == "10.0.0.0"
    assert result["Last host"] == "10.0.0.1"
    assert result["Usable hosts"] == 2
    assert result["Total addresses"] == 2


def test_subnet_info_slash_32_single_host():
    """A /32 describes exactly one host address."""
    result = subnet_info("192.168.1.5/32")
    assert result["Network"] == "192.168.1.5/32"
    assert result["Netmask"] == "255.255.255.255"
    assert result["Broadcast"] == "192.168.1.5"
    assert result["First host"] == "192.168.1.5"
    assert result["Last host"] == "192.168.1.5"
    assert result["Usable hosts"] == 1
    assert result["Total addresses"] == 1


def test_subnet_info_bare_address_treated_as_slash_32():
    """A bare address with no prefix is treated as a single-host /32."""
    result = subnet_info("192.168.1.5")
    assert result["Network"] == "192.168.1.5/32"
    assert result["Prefix length"] == 32
    assert result["Usable hosts"] == 1


def test_subnet_info_slash_8():
    result = subnet_info("10.0.0.0/8")
    assert result["Netmask"] == "255.0.0.0"
    assert result["Wildcard"] == "0.255.255.255"
    assert result["Broadcast"] == "10.255.255.255"
    assert result["First host"] == "10.0.0.1"
    assert result["Last host"] == "10.255.255.254"
    assert result["Usable hosts"] == 16777214
    assert result["Total addresses"] == 16777216


def test_subnet_info_ipv6_slash_64():
    result = subnet_info("2001:db8::/64")
    assert result["Network"] == "2001:db8::/64"
    assert result["Version"] == "IPv6"
    assert result["Prefix length"] == 64
    assert result["Broadcast"] == "N/A (IPv6)"
    assert result["First host"] == "2001:db8::1"
    # Last address of the /64 minus 1.
    assert result["Last host"] == "2001:db8::ffff:ffff:ffff:fffe"
    assert result["Total addresses"] == 2 ** 64
    assert result["Usable hosts"] == 2 ** 64 - 2


def test_subnet_info_ipv6_slash_127_rfc6164():
    """RFC 6164: IPv6 /127 point-to-point links, both addresses usable."""
    result = subnet_info("2001:db8::10/127")
    assert result["Network"] == "2001:db8::10/127"
    assert result["First host"] == "2001:db8::10"
    assert result["Last host"] == "2001:db8::11"
    assert result["Usable hosts"] == 2
    assert result["Total addresses"] == 2


def test_subnet_info_ipv6_slash_128_single_host():
    result = subnet_info("2001:db8::1/128")
    assert result["First host"] == "2001:db8::1"
    assert result["Last host"] == "2001:db8::1"
    assert result["Usable hosts"] == 1
    assert result["Broadcast"] == "N/A (IPv6)"


def test_subnet_info_invalid_cidr_raises_value_error():
    with pytest.raises(ValueError):
        subnet_info("999.1.1.1/24")


def test_subnet_info_prefix_out_of_range_raises_value_error():
    with pytest.raises(ValueError):
        subnet_info("192.168.1.0/33")


def test_subnet_info_empty_string_raises_value_error():
    with pytest.raises(ValueError):
        subnet_info("   ")


# ---------------------------------------------------------------------------
# classify_address
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "address, expected_type, expected_version",
    [
        ("10.0.0.5", "Private", "IPv4"),
        ("172.16.5.1", "Private", "IPv4"),
        ("172.16.5.4", "Private", "IPv4"),
        ("172.31.255.255", "Private", "IPv4"),
        ("172.32.0.1", "Public", "IPv4"),
        ("192.168.1.1", "Private", "IPv4"),
        ("127.0.0.1", "Loopback", "IPv4"),
        ("8.8.8.8", "Public", "IPv4"),
        ("169.254.1.1", "Link-local", "IPv4"),
        ("224.0.0.1", "Multicast", "IPv4"),
        ("0.0.0.0", "Unspecified", "IPv4"),
        ("192.0.2.10", "Reserved", "IPv4"),
        ("203.0.113.5", "Reserved", "IPv4"),
        ("198.18.0.1", "Reserved", "IPv4"),
        ("240.0.0.1", "Reserved", "IPv4"),
        ("255.255.255.255", "Reserved", "IPv4"),
        ("100.64.0.1", "Shared (CGNAT)", "IPv4"),
        ("::1", "Loopback", "IPv6"),
        ("fe80::1", "Link-local", "IPv6"),
        ("2001:4860:4860::8888", "Public", "IPv6"),
        ("2001:db8::1", "Reserved", "IPv6"),
        ("fd00::1", "Private", "IPv6"),
        ("ff02::1", "Multicast", "IPv6"),
        ("::", "Unspecified", "IPv6"),
    ],
)
def test_classify_address(address, expected_type, expected_version):
    result = classify_address(address)
    assert result["Address"] == address
    assert result["Version"] == expected_version
    assert result["Type"] == expected_type


def test_classify_address_cgnat_shared_space():
    """100.64.0.0/10 (RFC 6598) is neither private nor globally routable in
    Python's ipaddress module - we label it explicitly as an extra Type
    value, documented in subnet_tools.classify_address."""
    result = classify_address("100.64.1.1")
    assert result["Type"] == "Shared (CGNAT)"


def test_classify_address_ipv6_has_expanded_form():
    result = classify_address("::1")
    assert result["Expanded"] == "0000:0000:0000:0000:0000:0000:0000:0001"


def test_classify_address_ipv4_has_no_expanded_key():
    result = classify_address("8.8.8.8")
    assert "Expanded" not in result


def test_classify_address_strips_whitespace():
    result = classify_address("  10.0.0.5  ")
    assert result["Address"] == "10.0.0.5"
    assert result["Type"] == "Private"


def test_classify_address_invalid_raises_friendly_value_error():
    with pytest.raises(ValueError, match="999.1.1.1 is not a valid IPv4 or IPv6 address"):
        classify_address("999.1.1.1")


def test_classify_address_empty_raises_value_error():
    with pytest.raises(ValueError):
        classify_address("   ")
