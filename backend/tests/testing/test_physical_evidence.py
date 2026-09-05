# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import json
from pathlib import Path

import pytest

from foxforge.testing import physical_evidence

_SOURCE_COMMIT = "a" * 40
_PACKAGE_IDENTITY = "ghcr.io/mikefox303/foxforge@sha256:" + "b" * 64


def _probe(
    kind: str,
    *,
    target: str = "redacted",
    ok: bool = True,
    mqtt_fingerprint: str = "a" * 64,
    ftps_fingerprint: str = "b" * 64,
) -> dict[str, object]:
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
                "mqttCertificateSha256": mqtt_fingerprint,
                "ftpsCertificateSha256": ftps_fingerprint,
                "sameCertificate": mqtt_fingerprint == ftps_fingerprint,
            }
        )
    elif kind == "moonraker":
        base.update({"status": 200, "jsonResponse": True})
    return base


def _write_probe(
    path: Path,
    *kinds: str,
    target: str = "redacted",
    ok: bool = True,
    mqtt_fingerprint: str = "a" * 64,
    ftps_fingerprint: str = "b" * 64,
) -> None:
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "generatedAt": "2026-09-05T00:00:00Z",
                "secretValuesIncluded": False,
                "probes": [
                    _probe(
                        kind,
                        target=target,
                        ok=ok,
                        mqtt_fingerprint=mqtt_fingerprint,
                        ftps_fingerprint=ftps_fingerprint,
                    )
                    for kind in kinds
                ],
            }
        ),
        encoding="utf-8",
    )


def _observation_group(names: tuple[str, ...], value: bool = True) -> dict[str, bool]:
    return {name: value for name in names}


def _write_manifest(
    path: Path,
    *,
    bambu_value: bool = True,
    moonraker_value: bool = True,
    source_commit: str = _SOURCE_COMMIT,
    package_identity: str = _PACKAGE_IDENTITY,
    probe_files: tuple[str, ...] = ("probes.json",),
) -> None:
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
                "sourceCommit": source_commit,
                "packageIdentity": package_identity,
                "validationDate": "2026-09-05",
                "probeFiles": list(probe_files),
                "observations": observations,
            }
        ),
        encoding="utf-8",
    )


def _write_stable_tls_pair(tmp_path: Path) -> tuple[str, str]:
    first = "probes.json"
    second = "x2d-after-restart.json"
    _write_probe(tmp_path / first, "foxforge", "bambu_tls", "moonraker")
    _write_probe(tmp_path / second, "bambu_tls")
    return first, second


def test_complete_manifest_satisfies_all_gates(tmp_path: Path) -> None:
    probe_files = _write_stable_tls_pair(tmp_path)
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, probe_files=probe_files)

    result = physical_evidence.validate_manifest(manifest)

    assert result["bambuTlsSampleFiles"] == 2
    assert result["bambuTlsStableAcrossSamples"] is True
    assert result["aud003Ready"] is True
    assert result["aud013Ready"] is True
    assert result["p3PhysicalGateReady"] is True


def test_expected_release_identity_match_passes(tmp_path: Path) -> None:
    probe_files = _write_stable_tls_pair(tmp_path)
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, probe_files=probe_files)

    result = physical_evidence.validate_manifest(
        manifest,
        expected_source_commit=_SOURCE_COMMIT,
        expected_package_identity=_PACKAGE_IDENTITY,
    )

    assert result["sourceCommit"] == _SOURCE_COMMIT
    assert result["packageIdentity"] == _PACKAGE_IDENTITY
    assert result["p3PhysicalGateReady"] is True


def test_expected_source_commit_mismatch_is_rejected(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", "bambu_tls", "moonraker")
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)

    with pytest.raises(ValueError, match="sourceCommit .* does not match expected"):
        physical_evidence.validate_manifest(
            manifest,
            expected_source_commit="c" * 40,
            expected_package_identity=_PACKAGE_IDENTITY,
        )


def test_expected_package_identity_mismatch_is_rejected(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", "bambu_tls", "moonraker")
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)

    with pytest.raises(ValueError, match="packageIdentity .* does not match expected"):
        physical_evidence.validate_manifest(
            manifest,
            expected_source_commit=_SOURCE_COMMIT,
            expected_package_identity="ghcr.io/mikefox303/foxforge@sha256:" + "c" * 64,
        )


def test_invalid_expected_source_commit_is_rejected(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", "bambu_tls", "moonraker")
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)

    with pytest.raises(ValueError, match="expected source commit must be"):
        physical_evidence.validate_manifest(manifest, expected_source_commit="main")


def test_aud013_requires_two_tls_probe_files(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", "bambu_tls", "moonraker")
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest)

    result = physical_evidence.validate_manifest(manifest)

    assert result["bambuTlsSampleFiles"] == 1
    assert result["bambuTlsStableAcrossSamples"] is False
    assert result["aud003Ready"] is True
    assert result["aud013Ready"] is False
    assert result["p3PhysicalGateReady"] is False


def test_aud013_rejects_mismatched_tls_fingerprints_across_samples(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", "bambu_tls", "moonraker")
    _write_probe(tmp_path / "x2d-after-restart.json", "bambu_tls", mqtt_fingerprint="c" * 64)
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, probe_files=("probes.json", "x2d-after-restart.json"))

    result = physical_evidence.validate_manifest(manifest)

    assert result["bambuTlsSampleFiles"] == 2
    assert result["bambuTlsStableAcrossSamples"] is False
    assert result["aud013Ready"] is False
    assert result["p3PhysicalGateReady"] is False


def test_aud013_can_be_incomplete_without_hiding_other_evidence(tmp_path: Path) -> None:
    probe_files = _write_stable_tls_pair(tmp_path)
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, bambu_value=False, probe_files=probe_files)

    result = physical_evidence.validate_manifest(manifest)

    assert result["bambuTlsStableAcrossSamples"] is True
    assert result["aud003Ready"] is True
    assert result["aud013Ready"] is False
    assert result["p3PhysicalGateReady"] is False


def test_p3_gate_requires_moonraker_operator_observations(tmp_path: Path) -> None:
    probe_files = _write_stable_tls_pair(tmp_path)
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, moonraker_value=False, probe_files=probe_files)

    result = physical_evidence.validate_manifest(manifest)

    assert result["aud003Ready"] is True
    assert result["aud013Ready"] is True
    assert result["p3PhysicalGateReady"] is False


def test_probe_files_must_be_unique(tmp_path: Path) -> None:
    _write_probe(tmp_path / "probes.json", "foxforge", "bambu_tls", "moonraker")
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, probe_files=("probes.json", "probes.json"))

    with pytest.raises(ValueError, match="probeFiles entries must be unique"):
        physical_evidence.validate_manifest(manifest)


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
