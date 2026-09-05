# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import asyncio

import pytest

from foxforge.adapters.bambu.discovery import (
    BAMBU_FTPS_PORT,
    BAMBU_MQTT_PORT,
    BambuDiscoveryCandidate,
    discovery_network,
    parse_bambu_ssdp_response,
    scan_bambu_subnet,
)


def test_parse_bambu_ssdp_response_extracts_and_normalizes_identity() -> None:
    serial, name, model = parse_bambu_ssdp_response(
        "HTTP/1.1 200 OK\r\n"
        "ST: urn:bambulab-com:device:3dprinter:1\r\n"
        "USN: uuid:01p00abc123\r\n"
        "DevName.bambu.com: Workshop X2D\r\n"
        "DevModel.bambu.com: X2D\r\n\r\n"
    )

    assert serial == "01P00ABC123"
    assert name == "Workshop X2D"
    assert model == "X2D"


def test_parse_bambu_ssdp_response_ignores_unrelated_devices() -> None:
    assert parse_bambu_ssdp_response("HTTP/1.1 200 OK\r\nUSN: not-bambu\r\n") == (None, None, None)


def test_discovery_network_is_private_ipv4_and_bounded() -> None:
    assert str(discovery_network("192.168.50.44/24")) == "192.168.50.0/24"

    with pytest.raises(ValueError, match="private LAN"):
        discovery_network("203.0.113.0/24")
    with pytest.raises(ValueError, match="/22"):
        discovery_network("10.0.0.0/21")
    with pytest.raises(ValueError, match="IPv4"):
        discovery_network("fd00::/120")


def test_scan_requires_both_bambu_service_ports_and_enriches_candidates() -> None:
    async def scenario() -> None:
        probes: list[tuple[str, int]] = []

        async def probe(host: str, port: int, timeout: float) -> bool:
            assert timeout == 0.1
            probes.append((host, port))
            if host == "192.168.77.1":
                return port in {BAMBU_FTPS_PORT, BAMBU_MQTT_PORT}
            if host == "192.168.77.2":
                return port == BAMBU_FTPS_PORT
            return False

        async def describe(host: str, timeout: float) -> tuple[str | None, str | None, str | None]:
            assert host == "192.168.77.1"
            assert timeout == 0.1
            return " 01p00x2d ", " X2D ", " X2D "

        candidates = await scan_bambu_subnet(
            "192.168.77.0/30",
            timeout_seconds=0.1,
            concurrency=2,
            port_probe=probe,
            describe_host=describe,
        )

        assert candidates == (
            BambuDiscoveryCandidate(
                host="192.168.77.1",
                serial_number="01P00X2D",
                display_name="X2D",
                model="X2D",
            ),
        )
        assert ("192.168.77.1", BAMBU_FTPS_PORT) in probes
        assert ("192.168.77.1", BAMBU_MQTT_PORT) in probes
        assert ("192.168.77.2", BAMBU_FTPS_PORT) in probes
        assert ("192.168.77.2", BAMBU_MQTT_PORT) in probes

    asyncio.run(scenario())


def test_scan_does_not_describe_hosts_that_fail_port_gate() -> None:
    async def scenario() -> None:
        described: list[str] = []

        async def probe(host: str, port: int, timeout: float) -> bool:
            return False

        async def describe(host: str, timeout: float) -> tuple[str | None, str | None, str | None]:
            described.append(host)
            return None, None, None

        assert await scan_bambu_subnet(
            "10.20.30.0/30",
            port_probe=probe,
            describe_host=describe,
        ) == ()
        assert described == []

    asyncio.run(scenario())


def test_scan_validates_runtime_limits_before_network_io() -> None:
    async def scenario() -> None:
        async def never_probe(host: str, port: int, timeout: float) -> bool:
            raise AssertionError("network probe must not run")

        with pytest.raises(ValueError, match="timeout_seconds"):
            await scan_bambu_subnet("192.168.1.0/30", timeout_seconds=0, port_probe=never_probe)
        with pytest.raises(ValueError, match="concurrency"):
            await scan_bambu_subnet("192.168.1.0/30", concurrency=129, port_probe=never_probe)

    asyncio.run(scenario())
