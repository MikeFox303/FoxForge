# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass

import aiohttp
from aiohttp.resolver import DefaultResolver

_RFC1918_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
_IPV6_ULA = ipaddress.ip_network("fc00::/7")


class MoonrakerEndpointSecurityError(aiohttp.ClientError):
    """Raised when a configured or resolved Moonraker endpoint violates policy."""


@dataclass(frozen=True, slots=True)
class MoonrakerEndpointPolicy:
    allow_public_endpoint: bool = False
    allow_loopback_endpoint: bool = False
    allow_link_local_endpoint: bool = False

    def validate_ip(self, value: str) -> None:
        raw = value.split("%", 1)[0]
        try:
            address = ipaddress.ip_address(raw)
        except ValueError as error:
            raise MoonrakerEndpointSecurityError(f"invalid resolved Moonraker address: {value}") from error

        mapped = getattr(address, "ipv4_mapped", None)
        if mapped is not None:
            address = mapped

        if address.is_unspecified or address.is_multicast or address.is_reserved:
            raise MoonrakerEndpointSecurityError(f"Moonraker endpoint address is not permitted: {address}")
        if address.is_loopback:
            if self.allow_loopback_endpoint:
                return
            raise MoonrakerEndpointSecurityError(
                "Moonraker loopback endpoint requires allow_loopback_endpoint=true"
            )
        if address.is_link_local:
            if self.allow_link_local_endpoint:
                return
            raise MoonrakerEndpointSecurityError(
                "Moonraker link-local endpoint requires allow_link_local_endpoint=true"
            )
        if _is_private_lan(address):
            return
        if address.is_global and self.allow_public_endpoint:
            return
        raise MoonrakerEndpointSecurityError(
            "Moonraker endpoint resolved outside RFC1918/ULA LAN space; "
            "set an explicit advanced endpoint override only for a trusted target"
        )


def _is_private_lan(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(address, ipaddress.IPv4Address):
        return any(address in network for network in _RFC1918_NETWORKS)
    return address in _IPV6_ULA


class MoonrakerPolicyResolver:
    """Resolve through aiohttp's normal resolver and validate every returned IP."""

    def __init__(self, policy: MoonrakerEndpointPolicy) -> None:
        self._policy = policy
        self._inner = DefaultResolver()

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET):
        records = await self._inner.resolve(host, port, family)
        if not records:
            raise MoonrakerEndpointSecurityError(f"Moonraker endpoint did not resolve: {host}")
        for record in records:
            self._policy.validate_ip(str(record["host"]))
        return records

    async def close(self) -> None:
        await self._inner.close()
