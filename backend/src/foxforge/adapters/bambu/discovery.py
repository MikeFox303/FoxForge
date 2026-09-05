# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Conservative Bambu LAN discovery primitives for self-hosted deployments.

Discovery only produces candidates. A candidate is never treated as a configured
printer until the normal Bambu MQTT authentication + initial-state preflight
succeeds through ``RuntimePrinterManager``.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

BAMBU_MQTT_PORT = 8883
BAMBU_FTPS_PORT = 990
BAMBU_SSDP_PORT = 2021
BAMBU_SSDP_TARGET = "urn:bambulab-com:device:3dprinter:1"

_MAX_DISCOVERY_HOSTS = 1022  # /22 minus network/broadcast for IPv4
_DEFAULT_CONCURRENCY = 32
_DEFAULT_TIMEOUT_SECONDS = 0.35


@dataclass(frozen=True, slots=True)
class BambuDiscoveryCandidate:
    host: str
    serial_number: str | None = None
    display_name: str | None = None
    model: str | None = None
    mqtt_port: int = BAMBU_MQTT_PORT
    ftps_port: int = BAMBU_FTPS_PORT


ProbeHost = Callable[[str, float], Awaitable[bool]]
DescribeHost = Callable[[str, float], Awaitable[tuple[str | None, str | None, str | None]]]


def parse_bambu_ssdp_response(payload: str) -> tuple[str | None, str | None, str | None]:
    """Extract Bambu serial/name/model from one SSDP response without trusting it."""

    if BAMBU_SSDP_TARGET not in payload and "bambulab" not in payload.lower():
        return None, None, None

    serial = _header_value(payload, "USN")
    if serial is not None:
        serial = re.sub(r"^uuid:", "", serial, flags=re.IGNORECASE).strip().upper() or None
    name = _header_value(payload, "DevName.bambu.com")
    model = _header_value(payload, "DevModel.bambu.com")
    return serial, name, model


def discovery_network(subnet: str) -> ipaddress.IPv4Network:
    """Validate a user-selected LAN subnet before any active probing occurs."""

    try:
        network = ipaddress.ip_network(subnet, strict=False)
    except ValueError as error:
        raise ValueError("subnet must be valid IPv4 CIDR notation") from error
    if not isinstance(network, ipaddress.IPv4Network):
        raise ValueError("Bambu subnet discovery currently supports IPv4 only")
    if network.prefixlen < 22:
        raise ValueError("Bambu subnet discovery is limited to /22 or smaller networks")
    if network.num_addresses - 2 > _MAX_DISCOVERY_HOSTS:
        raise ValueError("Bambu subnet discovery is limited to 1022 usable hosts")

    address = network.network_address
    if (
        not address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise ValueError("Bambu subnet discovery is restricted to private LAN ranges")
    return network


async def scan_bambu_subnet(
    subnet: str,
    *,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    concurrency: int = _DEFAULT_CONCURRENCY,
    port_probe: Callable[[str, int, float], Awaitable[bool]] | None = None,
    describe_host: DescribeHost | None = None,
) -> tuple[BambuDiscoveryCandidate, ...]:
    """Find conservative Bambu candidates by requiring both LAN service ports.

    The scan is intentionally bounded and only accepts private IPv4 CIDRs. Open
    ports are a discovery hint, not proof of printer identity; callers must run
    the authenticated Bambu setup preflight before persisting anything.
    """

    network = discovery_network(subnet)
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if concurrency <= 0 or concurrency > 128:
        raise ValueError("concurrency must be between 1 and 128")

    probe = port_probe or _tcp_port_open
    describe = describe_host or _query_bambu_ssdp
    semaphore = asyncio.Semaphore(concurrency)

    async def inspect(host: str) -> BambuDiscoveryCandidate | None:
        async with semaphore:
            ftps_open = await probe(host, BAMBU_FTPS_PORT, timeout_seconds)
            if not ftps_open:
                return None
            mqtt_open = await probe(host, BAMBU_MQTT_PORT, timeout_seconds)
            if not mqtt_open:
                return None
            serial, name, model = await describe(host, timeout_seconds)
            return BambuDiscoveryCandidate(
                host=host,
                serial_number=serial.strip().upper() if serial and serial.strip() else None,
                display_name=name.strip() if name and name.strip() else None,
                model=model.strip() if model and model.strip() else None,
            )

    results = await asyncio.gather(*(inspect(str(host)) for host in network.hosts()))
    return tuple(candidate for candidate in results if candidate is not None)


async def _tcp_port_open(host: str, port: int, timeout_seconds: float) -> bool:
    writer: asyncio.StreamWriter | None = None
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout_seconds,
        )
        return True
    except (TimeoutError, ConnectionRefusedError, OSError):
        return False
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass


async def _query_bambu_ssdp(host: str, timeout_seconds: float) -> tuple[str | None, str | None, str | None]:
    return await asyncio.to_thread(_query_bambu_ssdp_sync, host, timeout_seconds)


def _query_bambu_ssdp_sync(host: str, timeout_seconds: float) -> tuple[str | None, str | None, str | None]:
    message = (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {host}:{BAMBU_SSDP_PORT}\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 1\r\n"
        f"ST: {BAMBU_SSDP_TARGET}\r\n"
        "\r\n"
    ).encode("ascii")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.settimeout(timeout_seconds)
        sock.sendto(message, (host, BAMBU_SSDP_PORT))
        payload, _address = sock.recvfrom(4096)
    except OSError:
        return None, None, None
    finally:
        sock.close()
    return parse_bambu_ssdp_response(payload.decode("utf-8", errors="ignore"))


def _header_value(payload: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}\s*:\s*(.*?)\s*$", payload, re.IGNORECASE | re.MULTILINE)
    if match is None:
        return None
    value = match.group(1).strip().rstrip("\r")
    return value or None
