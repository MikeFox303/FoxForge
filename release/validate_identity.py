#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ReleaseIdentity:
    version: str
    python_version: str
    tag: str
    title: str
    notes: str


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def load_and_validate_manifest(root: pathlib.Path) -> ReleaseIdentity:
    manifest = json.loads((root / "release/manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    python_version = manifest["pythonVersion"]
    tag = manifest["tag"]
    title = manifest["title"]
    notes = manifest["notes"]

    if not re.fullmatch(r"\d+\.\d+\.\d+-alpha\.\d+", version):
        raise ValueError(f"Unsupported alpha release version: {version}")
    if tag != f"v{version}":
        raise ValueError(f"Tag {tag!r} does not match version {version!r}")
    if manifest.get("prerelease", False) is not True:
        raise ValueError("The current release workflow requires prerelease=true")

    with (root / "backend/pyproject.toml").open("rb") as handle:
        backend = tomllib.load(handle)
    frontend = json.loads((root / "frontend/package.json").read_text(encoding="utf-8"))

    if backend["project"]["version"] != python_version:
        raise ValueError(
            f"Backend version {backend['project']['version']!r} != manifest pythonVersion {python_version!r}"
        )
    if frontend["version"] != version:
        raise ValueError(f"Frontend version {frontend['version']!r} != manifest version {version!r}")
    if not (root / notes).is_file():
        raise ValueError(f"Release notes file does not exist: {notes}")

    return ReleaseIdentity(
        version=version,
        python_version=python_version,
        tag=tag,
        title=title,
        notes=notes,
    )


def default_runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def require_unpublished_identity(
    identity: ReleaseIdentity,
    *,
    expected_sha: str,
    repository: str,
    image: str,
    runner: CommandRunner = default_runner,
) -> None:
    tag_ref = f"refs/tags/{identity.tag}"
    tag_check = runner(("git", "show-ref", "--tags", "--verify", "--quiet", tag_ref))
    if tag_check.returncode == 0:
        tag_commit = runner(("git", "rev-list", "-n", "1", identity.tag))
        if tag_commit.returncode != 0:
            raise RuntimeError(f"Unable to resolve existing tag {identity.tag}")
        actual_sha = tag_commit.stdout.strip()
        if actual_sha != expected_sha:
            raise RuntimeError(
                f"Release tag {identity.tag} already points to {actual_sha}; expected {expected_sha}. "
                "Refusing publication."
            )
        raise RuntimeError(
            f"Release tag {identity.tag} already exists for this commit. "
            "Duplicate release execution is blocked before publication."
        )
    if tag_check.returncode not in {0, 1}:
        raise RuntimeError(f"Unable to determine whether tag {identity.tag} already exists")

    release_check = runner(("gh", "release", "view", identity.tag, "--repo", repository))
    if release_check.returncode == 0:
        raise RuntimeError(
            f"GitHub release {identity.tag} already exists. Duplicate release execution is blocked before publication."
        )

    image_ref = f"{image}:{identity.version}"
    image_check = runner(("docker", "buildx", "imagetools", "inspect", image_ref))
    if image_check.returncode == 0:
        raise RuntimeError(
            f"Container tag {image_ref} already exists. Refusing to mutate an existing semantic image tag."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one immutable FoxForge release identity before publication")
    parser.add_argument("--root", default=".")
    parser.add_argument("--sha", required=True)
    parser.add_argument("--repository", default="MikeFox303/FoxForge")
    parser.add_argument("--image", default="ghcr.io/mikefox303/foxforge")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    identity = load_and_validate_manifest(pathlib.Path(args.root))
    require_unpublished_identity(
        identity,
        expected_sha=args.sha,
        repository=args.repository,
        image=args.image,
    )
    print(json.dumps(asdict(identity), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
