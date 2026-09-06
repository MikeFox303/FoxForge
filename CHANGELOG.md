# Changelog

All notable FoxForge changes are summarized here. The Git repository remains the canonical implementation history, while `release/` contains immutable release-specific notes.

FoxForge has not published a stable release yet.

## Unreleased — Pre-Alpha 5

Target: `v0.1.0-alpha.5`. Tracking: [#115](https://github.com/MikeFox303/FoxForge/issues/115).

### Added

- Conservative Bambu LAN discovery over an explicitly selected RFC1918 IPv4 subnet, requiring the expected Bambu LAN service ports before presenting a candidate.
- Structured Bambu setup identity/model handling and normalized operator-facing setup errors.
- Secret-safe reconnect diagnostics exposed through `/api/v1/diagnostics/reconnect` and the printer Diagnostics UI.
- Per-printer reconnect context for last failure, retry state and recovery without exposing raw vendor exceptions or credentials.

### Changed

- Add Printer now validates live connectivity before creating durable printer configuration.
- Update Printer now performs the same preflight before replacing a known-good configuration.
- A failed replacement connection rolls back durable configuration, secrets and runtime adapter state to the previous working printer.
- Terminal sanitized Add/Update connection failures are replayed deterministically through durable HTTP idempotency rather than re-executing a failed setup side effect.
- The Bambu milestone is explicitly focused on real X2D + AMS 2 Pro connection/control validation before broader P3/farm work resumes.

### Validation package

The current companion Umbrel package is **`0.1.0-alpha.4.3-umbrel.2`**, a validation candidate rather than a semantic Alpha 5 release.

```text
source commit: 37b253f385c19451c7ea075a4a4d12378cf17cf2
image: ghcr.io/mikefox303/foxforge:sha-37b253f@sha256:e550c8026ed6ec80e973d91fe6d96cc1474d537ca87de7875ec54f4a03aaaa4f
Store commit: 1d7d78d7a0f3c36805071dd6d8078033c59672ac
```

Final Alpha 5 remains blocked on the physical acceptance matrix in `docs/testing/pre-alpha-5-bambu-physical-validation.md`.

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
