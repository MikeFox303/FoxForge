# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_SHA256_RE = re.compile(r"^[0-9a-f]{40,64}$")

_REQUIRED_OBSERVATIONS = {
    "umbrel": (
        "installSucceeded",
        "restartPersistence",
        "browserProxyWriteAuth",
        "directBackendNoAnonymousBootstrap",
        "x2dReachableFromDeployment",
        "moonrakerReachableFromDeployment",
        "sseReconnectResync",
    ),
    "bambu": (
        "connectReconnect",
        "stateSynchronization",
        "projectStorage",
        "printStartAcknowledgement",
        "pause",
        "resume",
        "cancel",
        "completion",
        "ambiguousOutcomeHandling",
        "fingerprintsStableAcrossRestart",
        "correctPinsSucceed",
        "wrongMqttPinFailsClosed",
        "wrongFtpsPinFailsClosed",
        "pinRecovery",
    ),
    "moonraker": (
        "connectReconnect",
        "uploadChecksumStart",
        "pause",
        "resume",
        "cancel",
        "completionFailure",
        "ambiguousOutcomeHandling",
    ),
}


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_bool_map(value: object, names: tuple[str, ...], *, label: str) -> dict[str, bool]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    unknown = sorted(set(value) - set(names))
    if unknown:
        raise ValueError(f"{label} contains unknown observations: {', '.join(unknown)}")
    missing = [name for name in names if name not in value]
    if missing:
        raise ValueError(f"{label} is missing observations: {', '.join(missing)}")
    result: dict[str, bool] = {}
    for name in names:
        item = value[name]
        if not isinstance(item, bool):
            raise ValueError(f"{label}.{name} must be boolean")
        result[name] = item
    return result


def _resolve_probe_path(manifest_path: Path, value: str) -> Path:
    if not value or Path(value).is_absolute():
        raise ValueError("probeFiles entries must be non-empty relative paths")
    evidence_root = manifest_path.parent.resolve()
    candidate = (evidence_root / value).resolve()
    try:
        candidate.relative_to(evidence_root)
    except ValueError as exc:
        raise ValueError("probeFiles entries must stay inside the manifest directory") from exc
    return candidate


def _validate_probe(path: Path, *, allow_targets: bool) -> dict[str, Any]:
    raw = _load_json(path)
    if not isinstance(raw, dict) or raw.get("schemaVersion") != 1:
        raise ValueError(f"{path}: unsupported physical-validation report")
    if raw.get("secretValuesIncluded") is not False:
        raise ValueError(f"{path}: report is not marked secret-safe")
    probes = raw.get("probes")
    if not isinstance(probes, list) or not probes:
        raise ValueError(f"{path}: report has no probes")
    for probe in probes:
        if not isinstance(probe, dict):
            raise ValueError(f"{path}: invalid probe entry")
        if not allow_targets and probe.get("target") != "redacted":
            raise ValueError(f"{path}: target must remain redacted")
        if probe.get("ok") is not True:
            raise ValueError(f"{path}: probe {probe.get('kind', 'unknown')} did not pass")
    return raw


def validate_manifest(path: Path, *, allow_targets: bool = False) -> dict[str, object]:
    raw = _load_json(path)
    if not isinstance(raw, dict):
        raise ValueError("manifest must be an object")
    allowed = {
        "schemaVersion",
        "sourceCommit",
        "packageIdentity",
        "validationDate",
        "probeFiles",
        "observations",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"manifest contains unknown fields: {', '.join(unknown)}")
    if raw.get("schemaVersion") != 1:
        raise ValueError("manifest schemaVersion must be 1")
    source_commit = raw.get("sourceCommit")
    if not isinstance(source_commit, str) or not _SHA256_RE.fullmatch(source_commit):
        raise ValueError("sourceCommit must be a 40-64 character lowercase hex identity")
    for field in ("packageIdentity", "validationDate"):
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")

    probe_files = raw.get("probeFiles")
    if not isinstance(probe_files, list) or not probe_files or not all(isinstance(item, str) for item in probe_files):
        raise ValueError("probeFiles must be a non-empty string array")
    probe_reports = [
        _validate_probe(_resolve_probe_path(path, item), allow_targets=allow_targets) for item in probe_files
    ]
    probe_kinds = {
        probe.get("kind") for report in probe_reports for probe in report.get("probes", []) if isinstance(probe, dict)
    }

    observations_raw = raw.get("observations")
    if not isinstance(observations_raw, dict):
        raise ValueError("observations must be an object")
    unknown_groups = sorted(set(observations_raw) - set(_REQUIRED_OBSERVATIONS))
    if unknown_groups:
        raise ValueError(f"observations contains unknown groups: {', '.join(unknown_groups)}")
    observations = {
        group: _require_bool_map(observations_raw.get(group), names, label=f"observations.{group}")
        for group, names in _REQUIRED_OBSERVATIONS.items()
    }

    aud003_ready = all(observations["umbrel"].values()) and "foxforge" in probe_kinds
    aud013_ready = (
        all(
            observations["bambu"][name]
            for name in (
                "fingerprintsStableAcrossRestart",
                "correctPinsSucceed",
                "wrongMqttPinFailsClosed",
                "wrongFtpsPinFailsClosed",
                "pinRecovery",
            )
        )
        and "bambu_tls" in probe_kinds
    )
    p3_ready = (
        aud003_ready
        and aud013_ready
        and all(observations["bambu"].values())
        and all(observations["moonraker"].values())
        and "moonraker" in probe_kinds
    )
    return {
        "schemaVersion": 1,
        "sourceCommit": source_commit,
        "packageIdentity": raw["packageIdentity"],
        "validationDate": raw["validationDate"],
        "probeKinds": sorted(str(kind) for kind in probe_kinds if isinstance(kind, str)),
        "aud003Ready": aud003_ready,
        "aud013Ready": aud013_ready,
        "p3PhysicalGateReady": p3_ready,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify FoxForge physical/deployment validation evidence.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--allow-targets",
        action="store_true",
        help="Allow probe evidence that intentionally includes host/URL targets.",
    )
    parser.add_argument(
        "--require",
        choices=("aud003", "aud013", "p3"),
        help="Exit non-zero unless the selected evidence gate is complete.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate_manifest(args.manifest, allow_targets=args.allow_targets)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({"ok": True, **result}, indent=2, sort_keys=True))
    if args.require == "aud003" and not result["aud003Ready"]:
        return 1
    if args.require == "aud013" and not result["aud013Ready"]:
        return 1
    if args.require == "p3" and not result["p3PhysicalGateReady"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
