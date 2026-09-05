# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
from pathlib import Path

import pytest

from foxforge.testing import physical_evidence


def _probe(kind: str, *, target: str = "redacted", ok: bool = True) -> dict[str, object]:
    base: dict[str, object] = {"kind": kind, "target": target, "ok": ok}
    if kind == "foxforge":
        base.update(
            {
                "healthStatus": 200,
                "healthOk": True,
                "authBoundaryStatus": 400,
                "authBoundaryCode": "invalid_request",
                "authBoundaryOk": True,
            }
        )
    elif kind == "bambu_tls":
        base.update(
            {
                "mqttCertificateSha256": "a" * 64,
                "ftpsCertificateSha256": "b" * 64,
                "sameCertificate": False,
            }
        )
    elif kind == "moonraker":
        base.update({"status": 200, "jsonResponse": True})
    return base


def _write_probe(path: Path, *kinds: str, target: str = "redacted", ok: bool = True) -> None:
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "generatedAt": "2026-09-05T00:00:00Z",
                "secretValuesIncluded": False,
                "probes": [_probe(kind, target=target, ok=ok) for kind in kinds],
            }
        ),
        encoding="utf-8",
    )


def _observation_group(names: tuple[str, ...], value: bool = True) -> dict[str, bool]:
    return {name: value for name in names}


def _write_manifest(path: Path, *, bambu_value: bool = True, moonraker_value: bool = True) -> None:
    observations = {
        group: _observation_group(names) for group, names in physical_evidence._REQUIRED_OBSERVATIONS.items()
    }
    if not bambu_value:
        observations["bambu"]["correctPinsSucceed"] = False
    if not moonraker_value:
        observations["moonraker"]["completionFailure"] = False
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "sourceCommit": "a" * 40,
                "packageIdentity": "ghcr.io/mikefox303/foxforge@sha256:" + "b" * 64,
                "validationDate": "2026-09-05",
                "probeFiles": ["probes.json"],
                "observations": observations,
            }
        ),
        encoding="utf-8",
    )


def test_complete_manifest_satisfies_all_gates(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", "bambu_tls", "moonraker")
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)

    result = physical_evidence.validate_manifest(manifest)

    assert result["aud003Ready"] is True
    assert result["aud013Ready"] is True
    assert result["p3PhysicalGateReady"] is True


def test_aud013_can_be_incomplete_without_hiding_other_evidence(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", "bambu_tls", "moonraker")
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, bambu_value=False)

    result = physical_evidence.validate_manifest(manifest)

    assert result["aud003Ready"] is True
    assert result["aud013Ready"] is False
    assert result["p3PhysicalGateReady"] is False


def test_p3_gate_requires_moonraker_operator_observations(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", "bambu_tls", "moonraker")
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, moonraker_value=False)

    result = physical_evidence.validate_manifest(manifest)

    assert result["aud003Ready"] is True
    assert result["aud013Ready"] is True
    assert result["p3PhysicalGateReady"] is False


def test_probe_targets_must_be_redacted_by_default(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", target="http://192.168.1.5:8000")
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)

    with pytest.raises(ValueError, match="target must remain redacted"):
        physical_evidence.validate_manifest(manifest)


def test_probe_must_be_secret_safe(tmp_path: Path) -> None:
    probe = tmp_path / "probes.json"
    probe.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "secretValuesIncluded": True,
                "probes": [_probe("foxforge")],
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)

    with pytest.raises(ValueError, match="not marked secret-safe"):
        physical_evidence.validate_manifest(manifest)


def test_probe_kind_must_have_canonical_shape(tmp_path: Path) -> None:
    probe = tmp_path / "probes.json"
    probe.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "secretValuesIncluded": False,
                "probes": [{"kind": "bambu_tls", "target": "redacted", "ok": True}],
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)

    with pytest.raises(ValueError, match="mqttCertificateSha256"):
        physical_evidence.validate_manifest(manifest)


def test_unknown_probe_kind_is_rejected(tmp_path: Path) -> None:
    probe = tmp_path / "probes.json"
    probe.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "secretValuesIncluded": False,
                "probes": [{"kind": "custom", "target": "redacted", "ok": True}],
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)

    with pytest.raises(ValueError, match="unknown probe kind custom"):
        physical_evidence.validate_manifest(manifest)


def test_manifest_rejects_unknown_observation_fields(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", "bambu_tls", "moonraker")
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    raw["observations"]["umbrel"]["secretToken"] = True
    manifest.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown observations"):
        physical_evidence.validate_manifest(manifest)


def test_probe_file_cannot_escape_manifest_directory(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    _write_probe(tmp_path / "outside.json", "foxforge", "bambu_tls", "moonraker")
    manifest = evidence_dir / "manifest.json"
    _write_manifest(manifest)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    raw["probeFiles"] = ["../outside.json"]
    manifest.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="must stay inside the manifest directory"):
        physical_evidence.validate_manifest(manifest)


def test_probe_file_must_be_relative(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", "bambu_tls", "moonraker")
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    raw["probeFiles"] = [str((tmp_path / "probes.json").resolve())]
    manifest.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="must be non-empty relative paths"):
        physical_evidence.validate_manifest(manifest)
