# Changelog

All notable FoxForge changes are summarized here. The Git repository remains the canonical implementation history, while `release/` contains immutable release-specific notes.

FoxForge has not published a stable release yet.

## Unreleased — Pre-Alpha 5

Target: `v0.1.0-alpha.5`. Tracking: [#115](https://github.com/MikeFox303/FoxForge/issues/115) and replacement-candidate validation [#154](https://github.com/MikeFox303/FoxForge/issues/154).

### Added

- Conservative Bambu LAN discovery over explicit RFC1918 IPv4 subnets, with bounded server-visible private subnet suggestions and the expected Bambu LAN service ports required before presenting a candidate.
- Typed `foxforge.material_topology` read models and Printer Detail routing UI with explicit fixed/dynamic/unknown/stale states.
- Immutable staged-3MF print-plan inspection, plate-scoped toolhead expectations, explicit queue material-binding review and fail-closed material routing compilation.
- Structured Bambu setup identity/model handling and normalized operator-facing setup errors.
- Secret-safe reconnect diagnostics exposed through `/api/v1/diagnostics/reconnect` and the printer Diagnostics UI.
- Per-printer reconnect context for last failure, retry state and recovery without exposing raw vendor exceptions or credentials.
- Capability-driven application shell, printer-card density and Printer Detail Control/Materials presentation.
- Staged Add Printer **Provider → Connection → Identity → Verify** workflow with exact-current-payload verification gating.
- Provider-scoped `bambu-validation` filament-accounting mode for the controlled Alpha 5 physical gate.

### Changed

- PR #184 hardened the real Bambu Add Printer connection lifecycle after Candidate 6 physical testing: Add now uses the exact live fleet adapter as the single backend-authoritative connection before durable persistence instead of opening a disposable Add preflight followed immediately by another live connection.
- Bambu MQTT now uses a short per-session client ID so UI Verify, Add, reconnect and parallel process sessions do not deliberately reuse one serial-derived broker identity.
- Unexpected adapter exceptions are logged server-side while setup API/UI errors remain normalized and secret-safe.
- Add Printer still requires exact-payload UI Verify; any payload change after Verify disables Save until the changed payload is verified again.
- Update Printer retains a separate preflight and rollback path so invalid replacement connectivity cannot destroy a known-good configuration.
- Terminal sanitized Add/Update connection failures are replayed deterministically through durable HTTP idempotency rather than re-executing a failed setup side effect.
- Queue assessment persists compiler-owned toolhead bindings, Bambu dispatch revalidates source/topology immediately before submit, and `project_file.nozzle_mapping` is emitted only from a complete proven route.
- Present-but-invalid 3MF toolhead metadata remains explicitly fail-closed as `TOOLHEAD_METADATA_INVALID`; a fixed physical source route cannot mask corrupt slicer intent.
- Browser routing readiness follows the selected plate while preserving global and selected-plate blockers, so an unrelated blocked plate does not poison an otherwise safe selected plate.
- External Bambu 254/255 sources remain `-1` in flat `ams_mapping` and retain their real source identity in `ams_mapping2`.
- The Bambu milestone remains focused on real X2D + AMS 2 Pro connection/control/accounting validation before broader farm work resumes.

### Validation package

The active companion Umbrel package is **Candidate 7: `0.1.0-alpha.4.3-umbrel.7`**, a physical-validation candidate rather than the semantic Alpha 5 release.

```text
FoxForge application source: 4f769ca89d466d2cbe41360848b6343ec5a8eb36
image tag: ghcr.io/mikefox303/foxforge:sha-4f769ca
OCI digest: sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7
exact image: ghcr.io/mikefox303/foxforge:sha-4f769ca@sha256:0000e7a6c74056a0fff2e019c31a8cffc6d7fb2d3ec1fefdf587354a4d64c9b7
Umbrel package: 0.1.0-alpha.4.3-umbrel.7
Store commit: 6e69e4005ae9529eeee5c376c8769393b056ee0d
semantic target: v0.1.0-alpha.5 (unpublished)
```

The frozen source passed the full exact-source gate in run `34616523326`. Candidate 7 publication recovery run `34630673497` verified the immutable multi-architecture index and independent public pulls for `linux/amd64` and `linux/arm64`. Companion Store PR #39 passed package contract, App Password bootstrap, both public runtime smokes, upstream version audit and Store Release Gate before merge.

Candidate 5 is historical after partial-status/dual-external X2D findings. Candidate 6 is historical/failed after the real X2D could pass UI Verify and then fail during Add Printer with `internal_adapter_error`. Because #184 changed application code after Candidate 6 publication, Candidate 7 was required and older candidate evidence cannot be relabeled.

Candidate 7 no-print physical validation on Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro is now authorized. The first mandatory regression is **Verify → Add** on the exact X2D payload without the Candidate 6 internal adapter failure. Physical Start remains forbidden until no-print sections 1–7 in `docs/testing/pre-alpha-5-bambu-physical-validation.md` all pass.

Any application/image/package-definition change after Candidate 7 evidence begins requires Candidate 8. Documentation-only status/evidence commits do not change the frozen application identity.

## [0.1.0-alpha.4.3] - 2026-09-05

Third Alpha 4 hotfix. Fixed command flows in iOS Safari/WebKit over plain HTTP LAN deployments by providing a cryptographically secure UUIDv4 fallback when `crypto.randomUUID()` is unavailable. Persistence schemas and printer transports were unchanged.

See [`release/v0.1.0-alpha.4.3.md`](release/v0.1.0-alpha.4.3.md).

## [0.1.0-alpha.4.2] - 2026-09-05

Second Alpha 4 hotfix. Stabilized responsive layout, Add Printer modal ownership/stacking, Operator Access placement, browser-runtime error coverage and production-container viewport acceptance.

See [`release/v0.1.0-alpha.4.2.md`](release/v0.1.0-alpha.4.2.md).

## [0.1.0-alpha.4.1] - 2026-09-05

First Alpha 4 hotfix. Improved responsive Operator Access, Add Printer placement, narrow-phone navigation and ultra-wide bounds.

See [`release/v0.1.0-alpha.4.1.md`](release/v0.1.0-alpha.4.1.md).

## [0.1.0-alpha.4] - 2026-09-05

Fourth public FoxForge pre-release. Added common guarded Pause/Resume/Cancel, FoxForge-owned SSE application events, the complete normal inventory operator workflow, persistence/security hardening and independent-audit stabilization.

Key foundations included:

- typed `foxforge.job_control` v1 with exact vendor-job identity guards;
- Bambu and Moonraker common job-control mappings;
- SSE replay/resync invalidation over canonical HTTP snapshots;
- exact-Decimal inventory operator workflow and atomic/idempotent adjustment persistence;
- versioned persistence migrations and `SecretStore` credential separation;
- optional Bambu MQTT/FTPS certificate pins;
- hardened Moonraker endpoint policy;
- artifact quota/retention/cleanup and reconnect supervision;
- production-container browser, dependency and image-security gates.

See [`release/v0.1.0-alpha.4.md`](release/v0.1.0-alpha.4.md).

## [0.1.0-alpha.3] - 2026-09-04

Third public pre-release. Added authenticated/idempotent command APIs, application-managed printer setup, inventory mutations, content-addressed artifact staging and the safe browser queue workflow while preserving `INDETERMINATE` reconciliation semantics.

See [`release/v0.1.0-alpha.3.md`](release/v0.1.0-alpha.3.md).

## [0.1.0-alpha.2] - 2026-09-04

Second public pre-release. Made the runnable alpha more truthful through live runtime/error/empty states, independent read lifecycles, durable inventory presentation and the first immutable Umbrel Community App package.

See [`release/v0.1.0-alpha.2.md`](release/v0.1.0-alpha.2.md).

## [0.1.0-alpha.1] - 2026-09-04

First public runnable pre-release. Introduced the unified backend + React runtime, Bambu and Moonraker adapter foundations, durable queue and inventory, read API, EN/RU/UK localization, Docker packaging and guarded `amd64`/`arm64` publication.

See [`release/v0.1.0-alpha.1.md`](release/v0.1.0-alpha.1.md).

## Historical development milestones

Git remains canonical for commit-by-commit history. Durable design rationale is retained in ADRs and `docs/design/`.

Major pre-release milestones include the printer-domain foundation, Bambu adapter, `AdapterRegistry`/`FleetService`, durable queue dispatch, Moonraker adapter and HTTP/WebSocket transport, Bambu LAN/project-storage transport, queue lifecycle/retry policy, inventory foundation/SQLite persistence and the ADR 0002 repository-layout migration.

The retired X2D/N6 port-6000 experiment remains only in Git history. Any future X2D/eMMC implementation must be newly validated behind the production `BambuProjectStorage` boundary.
