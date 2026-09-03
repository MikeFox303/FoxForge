# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

"""Bambu-specific project storage boundary.

Project delivery is intentionally separate from MQTT print control. Standard
printers can use implicit FTPS while newer Bambu families may use a different
storage transport without changing FoxForge common printer contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

from .lan_wire import BambuFtpsWire
from .transport import BambuTransportError, BambuTransportErrorKind


class BambuProjectStorageKind(StrEnum):
    FTPS = "ftps"
    INTERNAL_EMMC = "internal_emmc"


@dataclass(frozen=True, slots=True)
class BambuStoredProject:
    remote_filename: str
    project_url: str
    storage_kind: BambuProjectStorageKind

    def __post_init__(self) -> None:
        filename = _validated_remote_filename(self.remote_filename)
        url = self.project_url.strip()
        parts = urlsplit(url)
        if parts.scheme not in {"ftp", "brtc"}:
            raise ValueError("Bambu project_url must use ftp:// or brtc://")
        if parts.query or parts.fragment:
            raise ValueError("Bambu project_url must not contain query parameters or fragments")
        if Path(parts.path).name != filename:
            raise ValueError("Bambu project_url path must end with remote_filename")
        if self.storage_kind == BambuProjectStorageKind.FTPS and parts.scheme != "ftp":
            raise ValueError("FTPS storage requires an ftp:// project_url")
        if self.storage_kind == BambuProjectStorageKind.INTERNAL_EMMC:
            if parts.scheme != "brtc" or parts.netloc.lower() != "emmc":
                raise ValueError("internal eMMC storage requires a brtc://emmc/... project_url")
        object.__setattr__(self, "remote_filename", filename)
        object.__setattr__(self, "project_url", url)


class BambuProjectStorage(Protocol):
    async def upload(self, local_path: Path, remote_filename: str) -> BambuStoredProject: ...


class FtpsBambuProjectStorage:
    """Project storage strategy backed by the standard Bambu implicit-FTPS wire."""

    def __init__(self, wire: BambuFtpsWire) -> None:
        self._wire = wire

    async def upload(self, local_path: Path, remote_filename: str) -> BambuStoredProject:
        try:
            filename = _validated_remote_filename(remote_filename)
        except ValueError as error:
            raise BambuTransportError(BambuTransportErrorKind.REJECTED, str(error)) from error
        await self._wire.upload(local_path, filename)
        return BambuStoredProject(
            remote_filename=filename,
            project_url=f"ftp:///{filename}",
            storage_kind=BambuProjectStorageKind.FTPS,
        )


def _validated_remote_filename(filename: str) -> str:
    basename = Path(filename).name
    if not basename or basename != filename or basename in {".", ".."}:
        raise ValueError("Bambu remote filename must be a plain basename")
    return basename
