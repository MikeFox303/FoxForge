# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass

from aiohttp.resolver import DefaultResolver


class MoonrakerEndpointSecurityError(ValueError):
    """Raised when a configured or resolved Moonraker endpoint violates policy."""


@dataclass(frozen=True, slots=True)
class MoonrakerEndpointPolicy:
    allow_public_endpoint: bool = False
    allow_loopback_endpoint: bool = False

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
        if address.is_link_local:
            raise MoonrakerEndpointSecurityError(f"Moonraker link-local endpoint is not permitted: {address}")
        if address.is_loopback:
            if self.allow_loopback_endpoint:
                return
            raise MoonrakerEndpointSecurityError(
                "Moonraker loopback endpoint requires allow_loopback_endpoint=true"
            )
        if address.is_private:
            return
        if address.is_global and self.allow_public_endpoint:
            return
        raise MoonrakerEndpointSecurityError(
            "Moonraker endpoint resolved outside private LAN space; set allow_public_endpoint=true only for a trusted target"
        )


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
