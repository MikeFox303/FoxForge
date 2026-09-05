# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
from collections.abc import Sequence

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SCRIPT = _ROOT / "release" / "validate_identity.py"
_SPEC = importlib.util.spec_from_file_location("foxforge_release_identity", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
release_identity = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = release_identity
_SPEC.loader.exec_module(release_identity)


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], tuple[int, str]]) -> None:
        self.responses = responses
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        normalized = tuple(command)
        self.commands.append(normalized)
        returncode, stdout = self.responses.get(normalized, (1, ""))
        return subprocess.CompletedProcess(normalized, returncode, stdout=stdout, stderr="")


def _identity():
    return release_identity.ReleaseIdentity(
        version="0.1.0-alpha.4",
        python_version="0.1.0a4",
        tag="v0.1.0-alpha.4",
        title="FoxForge v0.1.0-alpha.4",
        notes="release/v0.1.0-alpha.4.md",
    )


def test_alpha_hotfix_version_format_is_supported() -> None:
    assert release_identity._ALPHA_VERSION_RE.fullmatch("0.1.0-alpha.4")
    assert release_identity._ALPHA_VERSION_RE.fullmatch("0.1.0-alpha.4.1")
    assert not release_identity._ALPHA_VERSION_RE.fullmatch("0.1.0-alpha.4.1.2")


def test_existing_tag_on_different_commit_is_rejected_before_release_or_image_checks() -> None:
    runner = FakeRunner(
        {
            ("git", "show-ref", "--tags", "--verify", "--quiet", "refs/tags/v0.1.0-alpha.4"): (0, ""),
            ("git", "rev-list", "-n", "1", "v0.1.0-alpha.4"): (0, "old-sha\n"),
        }
    )

    with pytest.raises(RuntimeError, match="already points to old-sha"):
        release_identity.require_unpublished_identity(
            _identity(),
            expected_sha="new-sha",
            repository="MikeFox303/FoxForge",
            image="ghcr.io/mikefox303/foxforge",
            runner=runner,
        )

    assert not any(command[:3] == ("gh", "release", "view") for command in runner.commands)
    assert not any(command[:3] == ("docker", "buildx", "imagetools") for command in runner.commands)


def test_existing_tag_on_same_commit_still_blocks_duplicate_publication() -> None:
    runner = FakeRunner(
        {
            ("git", "show-ref", "--tags", "--verify", "--quiet", "refs/tags/v0.1.0-alpha.4"): (0, ""),
            ("git", "rev-list", "-n", "1", "v0.1.0-alpha.4"): (0, "same-sha\n"),
        }
    )

    with pytest.raises(RuntimeError, match="Duplicate release execution"):
        release_identity.require_unpublished_identity(
            _identity(),
            expected_sha="same-sha",
            repository="MikeFox303/FoxForge",
            image="ghcr.io/mikefox303/foxforge",
            runner=runner,
        )


def test_existing_github_release_blocks_before_image_publication() -> None:
    runner = FakeRunner(
        {
            ("git", "show-ref", "--tags", "--verify", "--quiet", "refs/tags/v0.1.0-alpha.4"): (1, ""),
            ("gh", "release", "view", "v0.1.0-alpha.4", "--repo", "MikeFox303/FoxForge"): (0, "exists"),
        }
    )

    with pytest.raises(RuntimeError, match="GitHub release v0.1.0-alpha.4 already exists"):
        release_identity.require_unpublished_identity(
            _identity(),
            expected_sha="new-sha",
            repository="MikeFox303/FoxForge",
            image="ghcr.io/mikefox303/foxforge",
            runner=runner,
        )

    assert not any(command[:3] == ("docker", "buildx", "imagetools") for command in runner.commands)


def test_existing_semantic_image_blocks_mutation() -> None:
    runner = FakeRunner(
        {
            ("git", "show-ref", "--tags", "--verify", "--quiet", "refs/tags/v0.1.0-alpha.4"): (1, ""),
            ("gh", "release", "view", "v0.1.0-alpha.4", "--repo", "MikeFox303/FoxForge"): (1, ""),
            (
                "docker",
                "buildx",
                "imagetools",
                "inspect",
                "ghcr.io/mikefox303/foxforge:0.1.0-alpha.4",
            ): (0, "exists"),
        }
    )

    with pytest.raises(RuntimeError, match="Refusing to mutate an existing semantic image tag"):
        release_identity.require_unpublished_identity(
            _identity(),
            expected_sha="new-sha",
            repository="MikeFox303/FoxForge",
            image="ghcr.io/mikefox303/foxforge",
            runner=runner,
        )


def test_unpublished_identity_passes_all_preflight_checks() -> None:
    runner = FakeRunner({})

    release_identity.require_unpublished_identity(
        _identity(),
        expected_sha="new-sha",
        repository="MikeFox303/FoxForge",
        image="ghcr.io/mikefox303/foxforge",
        runner=runner,
    )

    assert runner.commands[-1] == (
        "docker",
        "buildx",
        "imagetools",
        "inspect",
        "ghcr.io/mikefox303/foxforge:0.1.0-alpha.4",
    )


def test_container_workflow_cannot_publish_semver_or_tag_triggered_images() -> None:
    workflow = (_ROOT / ".github/workflows/container.yml").read_text(encoding="utf-8")

    assert "refs/tags/v" not in workflow
    assert "type=semver" not in workflow
    assert "branches:\n      - main" in workflow
    assert "type=raw,value=main" in workflow
    assert "type=sha,prefix=sha-" in workflow
