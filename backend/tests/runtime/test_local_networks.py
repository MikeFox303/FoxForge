# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from foxforge.adapters.bambu.discovery import discovery_network
from foxforge.runtime.local_networks import LocalIPv4Interface, private_discovery_subnets


def test_private_discovery_subnets_preserve_safe_private_interface_networks() -> None:
    suggestions = private_discovery_subnets(
        (
            LocalIPv4Interface("192.168.50.17", "255.255.255.0"),
            LocalIPv4Interface("10.42.0.9", "255.255.252.0"),
        )
    )

    assert suggestions == ("10.42.0.0/22", "192.168.50.0/24")
    assert tuple(str(discovery_network(subnet)) for subnet in suggestions) == suggestions


def test_private_discovery_subnets_narrow_wide_networks_around_server_address() -> None:
    suggestions = private_discovery_subnets(
        (
            LocalIPv4Interface("10.12.34.56", "255.0.0.0"),
            LocalIPv4Interface("172.20.99.12", "255.255.0.0"),
        )
    )

    assert suggestions == ("10.12.34.0/24", "172.20.99.0/24")
    assert tuple(str(discovery_network(subnet)) for subnet in suggestions) == suggestions


def test_private_discovery_subnets_ignore_public_loopback_link_local_and_invalid_records() -> None:
    assert (
        private_discovery_subnets(
            (
                LocalIPv4Interface("8.8.8.8", "255.255.255.0"),
                LocalIPv4Interface("127.0.0.1", "255.0.0.0"),
                LocalIPv4Interface("169.254.1.20", "255.255.0.0"),
                LocalIPv4Interface("not-an-ip", "255.255.255.0"),
                LocalIPv4Interface("192.168.1.20", "not-a-mask"),
            )
        )
        == ()
    )


def test_private_discovery_subnets_are_deduplicated_and_deterministic() -> None:
    assert private_discovery_subnets(
        (
            LocalIPv4Interface("192.168.10.50", "255.255.255.0"),
            LocalIPv4Interface("192.168.10.99", "255.255.255.0"),
            LocalIPv4Interface("10.0.5.7", "255.255.255.0"),
        )
    ) == ("10.0.5.0/24", "192.168.10.0/24")
