# Pre-Alpha 5 Candidate 6 software gate

**Status:** C6-10 pre-publication verification contract  
**Target:** Candidate 6 inside `v0.1.0-alpha.5`  
**Physical validation:** not part of this gate

## Purpose

Candidate 6 must be validated as release-quality software before FoxForge creates an immutable Candidate 6 image or matching Umbrel package. C6-10 is therefore deliberately **non-publishing**.

The gate verifies the exact integrated source that would become Candidate 6 while keeping all publication side effects reserved for C6-11.

## Exact-source identity

C6-10 has two required execution contexts:

- in `pull_request`, every checkout/build/test must use the exact PR head SHA; the branch must be **0 behind** `main` before the final green result is accepted;
- after merge, the same gate must pass on the exact merged `main` SHA.

A synthetic pull-request merge SHA must not become the recorded Candidate 6 source identity. When the PR branch is current with `main`, testing the exact head also tests the integrated source tree that is eligible to merge.

## Hard boundary

C6-10 must not:

- change `release/manifest.json` to Alpha 5;
- create or move a Git tag;
- create a GitHub release or pre-release;
- log in to GHCR or push a Candidate 6 image;
- mutate the companion Umbrel Store;
- claim Raspberry Pi, Umbrel or printer physical validation.

The workflow uses read-only repository/package inputs and builds local disposable images only.

## Required matrix

The exact source must pass:

1. backend Ruff + complete pytest on Python 3.12 and 3.13;
2. frontend frozen-lock install, typecheck, unit tests and production build;
3. Playwright browser acceptance against a locally built exact-source image;
4. production dependency audit and high/critical final-image vulnerability scan;
5. deployment authentication invariants:
   - read-only mode remains fail-closed;
   - explicit bearer token enables writes;
   - wrong credentials fail;
   - reverse-proxy identity headers do not become an application principal;
   - unsafe trusted-browser mode is rejected;
6. local runtime smoke for both `linux/amd64` and `linux/arm64`, using QEMU for the non-native platform and without pushing either image;
7. Umbrel structural compatibility against `MikeFox303/umbrel-3d-printing-store`:
   - App Proxy deployment, no host network/privileged/docker socket;
   - `${APP_PASSWORD}` maps to `FOXFORGE_COMMAND_TOKEN`;
   - `${APP_DATA_DIR}/data:/data` remains persistent;
   - healthcheck remains `/healthz`;
   - package remains a `pre-alpha-5-validation-candidate` contract targeting `0.1.0-alpha.5`;
8. milestone closure: no other open FoxForge PR may remain. During the C6-10 PR itself, only that PR is excluded from the blocker set; on merged `main`, open PR count must be zero.

## Umbrel identity rule

The companion Store currently contains the historical Candidate 5 package with its own immutable source/image digest. C6-10 must **not** rewrite that identity and must not run the Store's hard-pinned Candidate 5 identity test as if Candidate 6 were already published.

C6-10 therefore validates only structural/package-bootstrap compatibility. C6-11 owns the new Candidate 6 source SHA, multi-architecture OCI digest, package version, Store commit and exact package identity/runtime tests.

## Exact-main acceptance

The C6-10 implementation PR proves that the workflow itself and the proposed source tree satisfy the gate, but Candidate 6 publication remains blocked until the same non-publishing gate completes successfully on the resulting merged `main` commit with no other open FoxForge PRs.

If any application/runtime code changes after that exact-main PASS, C6-10 must run again on the new source before C6-11.

## Relationship to C6-11

Only after C6-10 passes on clean integrated `main` may C6-11:

1. freeze the exact FoxForge source SHA;
2. publish the matching `linux/amd64` + `linux/arm64` image and immutable digest;
3. publish/update the matching Umbrel package;
4. run the exact package contract/runtime smoke against that new identity;
5. update current-state/runbook documents to that one Candidate 6 identity;
6. begin the real Raspberry Pi 5 + Umbrel + X2D + AMS 2 Pro no-print gate.

No Candidate 5 physical evidence may be relabeled as Candidate 6 evidence.

## Physical validation remains separate

CI proves software contracts only. It does not prove the Raspberry Pi networking path, Umbrel runtime, real X2D MQTT/FTPS behavior, AMS 2 Pro state, dual external feed topology, thermal readings, or physical print/job-control behavior.

Those observations belong only to the post-C6-11 physical runbook and must reference the exact Candidate 6 source/image/package identity they validate.
