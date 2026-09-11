# Pre-Alpha 5 Candidate 6 software gate

**Status:** C6-10 PASS; replacement Candidate 7 reuses the same exact-source gate after #184  
**Target:** replacement physical-validation candidate inside `v0.1.0-alpha.5`  
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

## C6-11 publication mechanism

Candidate 6 publication uses `.github/workflows/candidate-publish.yml`, not the semantic `release.yml` workflow.

The publisher is intentionally split from the semantic release path:

- a publication marker on `pre-alpha-5/candidate6-publish` names one full 40-character FoxForge source SHA;
- that source must still be the exact current `main` head when publication begins;
- the exact source must already have a successful post-merge `Candidate 6 software gate` run;
- open FoxForge PR count must be zero at publication time;
- `release/manifest.json` must still identify `v0.1.0-alpha.4.3` and `v0.1.0-alpha.5` must not already exist;
- publication creates only `ghcr.io/mikefox303/foxforge:sha-<7-char-source>` for `linux/amd64` + `linux/arm64` and records its immutable OCI digest;
- an existing source tag is never overwritten;
- the published image must be anonymously pullable for both target platforms;
- publication emits a retained `candidate6-publication.json` artifact containing the exact source, image tag, digest, platforms and intended `0.1.0-alpha.4.3-umbrel.6` package identity;
- this workflow does **not** create a Git tag, GitHub Release, Alpha 5 release manifest, Store commit or physical-validation claim.

The companion Store update happens only after the image digest has been retrieved and verified. Its PR must pin the exact `sha-<source>@sha256:<digest>` image and must pass the Store package contract plus amd64/arm64 runtime gates before merge.

## Candidate 7 replacement use

Real Candidate 6 physical validation later exposed the X2D Add Printer MQTT connection-lifecycle defect fixed by PR #184. Because that fix changes application code, the published Candidate 6 source/image/package identity is historical for Alpha 5 physical acceptance and its evidence cannot be carried forward.

The replacement is **Candidate 7 inside the same `v0.1.0-alpha.5` milestone**. Candidate 7 deliberately reuses the complete non-publishing matrix above; the existing workflow name `Candidate 6 software gate` is retained as a legacy CI identifier so prior run history and release tooling remain auditable. A Candidate 7 source is eligible for immutable publication only after this full gate succeeds on that exact merged `main` SHA with zero other open FoxForge PRs.

Candidate 7 publication is separate from the historical Candidate 6 publisher:

- `.github/workflows/candidate7-publish.yml` owns the new immutable publication path;
- `pre-alpha-5/candidate7-publish` plus `.candidate7/source.json` freeze the exact replacement source;
- the intended Umbrel package identity is `0.1.0-alpha.4.3-umbrel.7`;
- semantic `v0.1.0-alpha.5` remains unpublished until the replacement physical acceptance matrix passes;
- Candidate 6 tags, markers, images and evidence are never overwritten or relabeled.

## Physical validation remains separate

CI proves software contracts only. It does not prove the Raspberry Pi networking path, Umbrel runtime, real X2D MQTT/FTPS behavior, AMS 2 Pro state, dual external feed topology, thermal readings, or physical print/job-control behavior.

Those observations belong only to the post-publication physical runbook and must reference the exact immutable source/image/package identity they validate.
