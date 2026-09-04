# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

import pytest

from foxforge.adapters.moonraker.endpoint_policy import (
    MoonrakerEndpointPolicy,
    MoonrakerEndpointSecurityError,
    MoonrakerPolicyResolver,
)


def test_default_policy_allows_private_lan_addresses() -> None:
    policy = MoonrakerEndpointPolicy()

    policy.validate_ip("192.168.1.42")
    policy.validate_ip("10.20.30.40")
    policy.validate_ip("172.16.5.9")
    policy.validate_ip("fd12:3456:789a::42")


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "::1",
        "169.254.169.254",
        "fe80::1",
        "224.0.0.1",
        "ff02::1",
        "0.0.0.0",
        "203.0.113.9",
        "8.8.8.8",
    ],
)
def test_default_policy_rejects_non_lan_or_special_addresses(address: str) -> None:
    with pytest.raises(MoonrakerEndpointSecurityError):
        MoonrakerEndpointPolicy().validate_ip(address)


def test_explicit_advanced_overrides_are_narrow() -> None:
    MoonrakerEndpointPolicy(allow_loopback_endpoint=True).validate_ip("127.0.0.1")
    MoonrakerEndpointPolicy(allow_public_endpoint=True).validate_ip("8.8.8.8")

    with pytest.raises(MoonrakerEndpointSecurityError):
        MoonrakerEndpointPolicy(allow_public_endpoint=True).validate_ip("127.0.0.1")


def test_resolver_rejects_mixed_safe_and_unsafe_dns_results() -> None:
    class _Resolver:
        async def resolve(self, host: str, port: int = 0, family: int = 0):
            del host, family
            return [
                {"hostname": "printer.local", "host": "192.168.1.50", "port": port, "family": 2, "proto": 0, "flags": 0},
                {"hostname": "printer.local", "host": "127.0.0.1", "port": port, "family": 2, "proto": 0, "flags": 0},
            ]

        async def close(self) -> None:
            return None

    async def scenario() -> None:
        resolver = MoonrakerPolicyResolver(MoonrakerEndpointPolicy())
        resolver._inner = _Resolver()  # noqa: SLF001 - deterministic DNS-policy test seam
        try:
            with pytest.raises(MoonrakerEndpointSecurityError):
                await resolver.resolve("printer.local", 7125)
        finally:
            await resolver.close()

    asyncio.run(scenario())
