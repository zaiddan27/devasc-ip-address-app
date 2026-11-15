"""Tests for gui.run_action, the bridge between the window and the modules.

No window is opened: run_action is plain Python, and the network calls it
makes are mocked, so these tests run offline and on CI without a display.
"""

from unittest import mock

import pytest

import gui


def test_spaced_label():
    assert gui.spaced("subnet") == "S U B N E T"


def test_subnet_uses_subnet_tools():
    title, data = gui.run_action("subnet", " 192.168.10.0/26 ")
    assert title == "Subnet: 192.168.10.0/26"
    assert data["Netmask"] == "255.255.255.192"
    assert data["Usable hosts"] == 62


def test_classify_uses_subnet_tools():
    title, data = gui.run_action("classify", "10.0.0.5")
    assert title == "Address: 10.0.0.5"
    assert data["Type"] == "Private"


def test_lookup_calls_lookup_module():
    fake = {"Query": "8.8.8.8", "IP": "8.8.8.8", "ISP": "Google LLC"}
    with mock.patch.object(gui.lookup, "lookup", return_value=fake) as patched:
        title, data = gui.run_action("lookup", "8.8.8.8")
    patched.assert_called_once_with("8.8.8.8")
    assert title == "Lookup: 8.8.8.8"
    assert data == fake


def test_bad_input_raises_value_error():
    with pytest.raises(ValueError):
        gui.run_action("subnet", "999.1.1.1/40")


def test_my_ip_keeps_addresses_when_provider_fails():
    with mock.patch.object(gui.ip_info, "get_public_ipv4", return_value="203.0.113.7"), \
         mock.patch.object(gui.ip_info, "get_public_ipv6", return_value=None), \
         mock.patch.object(gui.ip_info, "get_ip_details", side_effect=ConnectionError("offline")):
        title, data = gui.run_action("my_ip")
    assert title == "My public IP"
    assert data["IPv4"] == "203.0.113.7"
    assert data["IPv6"] == "not available on this network"
    assert "offline" in data["Note"]


def test_unknown_feature_raises():
    with pytest.raises(ValueError):
        gui.run_action("nope")
