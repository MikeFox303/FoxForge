# FoxForge independent audit remediation tracker — 2026-09-04

- **Source audit:** [`2026-09-04-independent-project-audit.md`](2026-09-04-independent-project-audit.md) — immutable finding snapshot
- **Tracker status:** active
- **Updated:** 2026-09-06
- **Feature freeze:** P3 automatic filament accounting remains frozen until the current physical/deployment resume gate is satisfied

This file tracks current remediation/evidence state. It does not rewrite the original audit.

## Status definitions

- `OPEN` — not addressed;
- `IN PROGRESS` — implementation exists but software acceptance is incomplete;
- `VALIDATION REQUIRED` — software foundation is complete, real deployment/device evidence still required;
- `RESOLVED` — applicable acceptance criteria have repository evidence/regression coverage.

## Current tracker

| ID | Priority | Status | Current evidence/status |
| --- | --- | --- | --- |
| AUD-001 | P0 | RESOLVED | Guarded release identity preflight prevents conflicting tags/releases/semantic images. |
| AUD-002 | P0 | RESOLVED | Development container workflow no longer publishes semantic release tags. |
| AUD-003 | P0 | **VALIDATION REQUIRED** | Explicit FoxForge token model and Umbrel bootstrap are implemented/tested; real Raspberry Pi/Umbrel install, proxy-write, persistence, network/realtime evidence remains. Current target is Pre-Alpha 5 candidate 2. |
| AUD-004 | P0 | RESOLVED | ADR 0005 explicit-token model; proxy headers are not application principals; unsafe trusted-browser mode rejected. |
| AUD-005 | P1 | RESOLVED | One canonical responsive Add Printer entry point with production-browser regression coverage. |
| AUD-006 | P1 | RESOLVED | Frozen frontend/backend dependency inputs and reproducible install/audit gates. |
| AUD-007 | P1 | RESOLVED | Browser/deployment trust deferral superseded by ADR 0005. |
| AUD-008 | P1 | RESOLVED | Versioned config/SQLite migrations, backups, schema validation and recovery coverage. |
| AUD-009 | P1 | RESOLVED | Roadmap stabilized; normal inventory workflow completed; P3 remains behind physical gate. |
| AUD-010 | P2 | RESOLVED | Atomic/idempotent inventory adjustment persistence. |
| AUD-011 | P2 | RESOLVED | Artifact quota/free-space/retention/orphan cleanup with queue-reference safety. |
| AUD-012 | P2 | RESOLVED | Per-printer reconnect supervision with bounded concurrency/backoff/jitter; current source also exposes secret-safe reconnect diagnostics. |
| AUD-013 | P2 | **VALIDATION REQUIRED** | Independent optional Bambu MQTT/FTPS certificate pins and strict evidence tooling implemented; real X2D stability/correct-pin/incorrect-pin/recovery evidence remains. |
| AUD-014 | P2 | RESOLVED | Moonraker resolved-address/redirect/userinfo endpoint security policy implemented. |
| AUD-015 | P2 | RESOLVED | `SecretStore` separates printer credentials from ordinary runtime config. |
| AUD-016 | P2 | RESOLVED | Production public source maps disabled and regression-tested. |
| AUD-017 | P2 | RESOLVED | Targeted mounted-data ownership initialization replaces unconditional recursive ownership changes. |
| AUD-018 | P2 | RESOLVED | Production-container browser acceptance covers responsive/setup/operator/queue/realtime/inventory regressions; Alpha 4 hotfixes expanded WebKit/runtime coverage. |
| AUD-019 | P3 | RESOLVED | Security policy, dependency/update scanning, final-image vulnerability scanning and measured branch-coverage governance implemented. |

## Current validation target

The former Alpha 4.2 package was a valid historical audit baseline. It is no longer the active physical-validation target.

Current Bambu/Pre-Alpha 5 target:

```text
package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.2
source: 37b253f385c19451c7ea075a4a4d12378cf17cf2
Store: 1d7d78d7a0f3c36805071dd6d8078033c59672ac
image: ghcr.io/mikefox303/foxforge:sha-37b253f@sha256:e550c8026ed6ec80e973d91fe6d96cc1474d537ca87de7875ec54f4a03aaaa4f
```

See [`../testing/pre-alpha-5-bambu-physical-validation.md`](../testing/pre-alpha-5-bambu-physical-validation.md).

## Post-audit hardening relevant to the current gate

After the original stabilization work, current source additionally provides:

- GUI-visible Umbrel operator credential path;
- Bambu LAN discovery with manual fallback;
- Add Printer test-before-save;
- Update Printer preflight and rollback to the prior working configuration;
- deterministic durable replay of terminal sanitized Add/Update setup failures;
- secret-safe reconnect diagnostics API/UI;
- current Bambu material-system observation foundation.

These changes reduce software-side risk but do not close AUD-003/AUD-013 without physical evidence.

## P3 freeze

P3 is preserved, not discarded. It remains intentionally unmerged while the Bambu Alpha 5 milestone is validated.

The normal inventory prerequisite is complete. Resume still requires reviewing then-current physical/deployment evidence, synchronizing the P3 branch with `main`, rerunning exact-head backend/frontend/container/security/browser gates and preserving all stabilization changes.

## Current execution order

1. Complete the Pre-Alpha 5 Raspberry Pi 5/Umbrel + X2D + AMS 2 Pro physical matrix.
2. If a physical defect changes code, publish a new immutable candidate and repeat affected evidence.
3. Review AUD-003/AUD-013 evidence; update statuses only when requirements actually pass.
4. Publish final Alpha 5 only after the exact candidate gate passes.
5. Reassess/synchronize P3 after Alpha 5 stabilization.

## Resolution rule

No finding is resolved solely because code, mocks, CI or package definitions exist. Where applicable, resolution requires implementation, regression coverage, representative deployment/integration evidence, architecture documentation and physical validation tied to the exact immutable target.
