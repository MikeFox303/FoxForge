# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass

try:
    import fcntl
except ImportError:  # pragma: no cover - production server targets Linux; keep import-safe elsewhere.
    fcntl = None  # type: ignore[assignment]

_SIOCGIFADDR = 0x8915
_SIOCGIFNETMASK = 0x891B
_MAX_INTERFACE_NAME_BYTES = 15
_MIN_SAFE_DISCOVERY_PREFIX = 22
_FALLBACK_SLICE_PREFIX = 24
_RFC1918_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


@dataclass(frozen=True, slots=True)
class LocalIPv4Interface:
    address: str
    netmask: str


def private_discovery_subnets(
    interfaces: tuple[LocalIPv4Interface, ...],
) -> tuple[str, ...]:
    """Return deterministic bounded RFC1918 CIDRs suitable as operator scan hints.

    Wide private interfaces are intentionally narrowed to the /24 containing the
    server address. This keeps every suggestion within the existing active-scan
    host limit and avoids proposing an automatic sweep of an entire /8-/16 LAN.
    """

    suggestions: set[ipaddress.IPv4Network] = set()
    for interface in interfaces:
        try:
            address = ipaddress.ip_address(interface.address)
            network = ipaddress.ip_network(f"{interface.address}/{interface.netmask}", strict=False)
        except ValueError:
            continue
        if not isinstance(address, ipaddress.IPv4Address) or not isinstance(network, ipaddress.IPv4Network):
            continue
        if not _is_rfc1918(address):
            continue

        suggestion = (
            network
            if network.prefixlen >= _MIN_SAFE_DISCOVERY_PREFIX
            else ipaddress.ip_network(f"{address}/{_FALLBACK_SLICE_PREFIX}", strict=False)
        )
        if _is_rfc1918_network(suggestion):
            suggestions.add(suggestion)

    ordered = sorted(suggestions, key=lambda item: (int(item.network_address), item.prefixlen))
    return tuple(str(network) for network in ordered)


def local_ipv4_interfaces() -> tuple[LocalIPv4Interface, ...]:
    """Read IPv4 address/netmask pairs visible to the FoxForge server process.

    On unsupported platforms or inaccessible interfaces this returns only the
    records that can be read safely. Interface names and host addresses are not
    exposed by the HTTP API; callers only publish normalized CIDR suggestions.
    """

    if fcntl is None:
        return ()

    records: list[LocalIPv4Interface] = []
    try:
        interfaces = socket.if_nameindex()
    except OSError:
        return ()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for _index, name in interfaces:
            encoded_name = name.encode("utf-8")[:_MAX_INTERFACE_NAME_BYTES]
            if not encoded_name:
                continue
            request = encoded_name.ljust(256, b"\0")
            try:
                address_data = fcntl.ioctl(sock.fileno(), _SIOCGIFADDR, request)
                netmask_data = fcntl.ioctl(sock.fileno(), _SIOCGIFNETMASK, request)
            except OSError:
                continue
            records.append(
                LocalIPv4Interface(
                    address=socket.inet_ntoa(address_data[20:24]),
                    netmask=socket.inet_ntoa(netmask_data[20:24]),
                )
            )
    return tuple(records)


def suggested_private_discovery_subnets() -> tuple[str, ...]:
    return private_discovery_subnets(local_ipv4_interfaces())


def _is_rfc1918(address: ipaddress.IPv4Address) -> bool:
    return any(address in network for network in _RFC1918_NETWORKS)


def _is_rfc1918_network(network: ipaddress.IPv4Network) -> bool:
    return any(network.subnet_of(private_network) for private_network in _RFC1918_NETWORKS)
