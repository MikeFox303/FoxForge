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
| AUD-003 | P0 | **VALIDATION REQUIRED** | Explicit FoxForge token model and Candidate 5 Umbrel bootstrap are implemented/tested; real Raspberry Pi/Umbrel install, proxy-write, persistence, network/realtime evidence remains. |
| AUD-004 | P0 | RESOLVED | ADR 0005 explicit-token model; proxy headers are not application principals; unsafe trusted-browser mode rejected. |
| AUD-005 | P1 | RESOLVED | One canonical responsive Add Printer entry point with production-browser regression coverage; Candidate 5 additionally uses the staged exact-payload Verify flow. |
| AUD-006 | P1 | RESOLVED | Frozen frontend/backend dependency inputs and reproducible install/audit gates. |
| AUD-007 | P1 | RESOLVED | Browser/deployment trust deferral superseded by ADR 0005. |
| AUD-008 | P1 | RESOLVED | Versioned config/SQLite migrations, backups, schema validation and recovery coverage. |
| AUD-009 | P1 | RESOLVED | Roadmap stabilized; normal inventory workflow completed; P3 remains behind physical gate. |
| AUD-010 | P2 | RESOLVED | Atomic/idempotent inventory adjustment persistence. |
| AUD-011 | P2 | RESOLVED | Artifact quota/free-space/retention/orphan cleanup with queue-reference safety. |
| AUD-012 | P2 | RESOLVED | Per-printer reconnect supervision with bounded concurrency/backoff/jitter and secret-safe reconnect diagnostics. |
| AUD-013 | P2 | **VALIDATION REQUIRED** | Independent optional Bambu MQTT/FTPS certificate pins and strict evidence tooling implemented; real X2D stability/correct-pin/incorrect-pin/recovery evidence remains. |
| AUD-014 | P2 | RESOLVED | Moonraker resolved-address/redirect/userinfo endpoint security policy implemented. |
| AUD-015 | P2 | RESOLVED | `SecretStore` separates printer credentials from ordinary runtime config. |
| AUD-016 | P2 | RESOLVED | Production public source maps disabled and regression-tested. |
| AUD-017 | P2 | RESOLVED | Targeted mounted-data ownership initialization replaces unconditional recursive ownership changes. |
| AUD-018 | P2 | RESOLVED | Production-container browser acceptance covers responsive/setup/operator/queue/realtime/inventory regressions; Alpha 4 hotfixes expanded WebKit/runtime coverage. |
| AUD-019 | P3 | RESOLVED | Security policy, dependency/update scanning, final-image vulnerability scanning and measured branch-coverage governance implemented. |

## Current physical-validation target

**Candidate 5 is published and is the current immutable Pre-Alpha 5 validation target. The no-print physical gate is pending.**

```text
package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.5
application source: 0351c659f2d2845fb83bc0b1802c4d9ebeeef1f2
Store: 16d57c486ce8e2b26abd5c7e9480188d95f080cb
image: ghcr.io/mikefox303/foxforge:sha-0351c65@sha256:00c699effbe9b245a4916a8c301df5b67435d75dd42fad02cc5bbf0ca51aec39
```

Candidate 4 remains **retired for first-print acceptance** because the release-readiness audit found that some present-but-invalid 3MF toolhead metadata could be treated like absent metadata before the routing compiler saw it. PR #145 closed that fail-closed gap and aligned browser review with selected-plate routing semantics. Candidate 5 contains that fix plus the later capability-driven interface work and staged Add Printer workflow through PR #150.

Store Candidate 5 passed its exact-head package contract/public runtime checks for `linux/amd64` and `linux/arm64`, the Store Release Gate and upstream-version audit before merge. Those checks prove packaging/reproducibility only; they do not substitute for Raspberry Pi 5/Umbrel/X2D evidence.

New physical evidence must use [`../testing/pre-alpha-5-bambu-physical-validation.md`](../testing/pre-alpha-5-bambu-physical-validation.md) and the Candidate 5 identity above. Candidate 1/2/3/4 evidence remains historical and must not be relabeled or silently carried to Candidate 5.

## Post-audit hardening relevant to the current gate

Candidate 5 source provides:

- GUI-visible Umbrel operator credential path;
- bounded Bambu LAN discovery with server-visible private subnet suggestions plus manual fallback;
- staged Add Printer **Provider → Connection → Identity → Verify** with exact-current-payload verification invalidation;
- Add Printer backend test-before-save;
- Update Printer preflight and rollback to the prior working configuration;
- deterministic durable replay of terminal sanitized Add/Update setup failures;
- per-printer reconnect supervision and secret-safe diagnostics API/UI;
- normalized X2D/AMS 2 Pro/external material telemetry;
- typed `foxforge.material_topology`;
- immutable staged-3MF inspection;
- explicit source binding review;
- fail-closed compiler-owned toolhead routing;
- Bambu adapter-side source/topology revalidation;
- `ams_mapping`, `ams_mapping2` and compiler-derived `nozzle_mapping` encoding;
- selected-plate browser/server routing semantics;
- explicit present-vs-invalid toolhead metadata distinction with `TOOLHEAD_METADATA_INVALID` remaining blocking even against a fixed physical route;
- capability-driven AppShell, printer cards and Printer Detail Control/Materials presentation.

These changes reduce software-side risk but do not close AUD-003/AUD-013 without physical evidence.

## P3 freeze

P3 is preserved, not discarded. It remains intentionally unmerged while the Bambu Alpha 5 milestone is validated.

The normal inventory prerequisite is complete. Resume still requires reviewing then-current physical/deployment evidence, synchronizing/reimplementing the preserved P3 plan against then-current `main`, rerunning exact-head backend/frontend/container/security/browser gates and preserving all stabilization changes.

## Current execution order

1. Run the complete no-print X2D + AMS 2 Pro gate on exact Candidate 5.
2. Only after sections 1–6 pass, run the first real print and guarded job-control acceptance on that same digest.
3. If a physical defect changes application code, publish another immutable candidate and repeat affected evidence.
4. Review AUD-003/AUD-013 evidence; update statuses only when requirements actually pass.
5. Publish final Alpha 5 only after the exact candidate gate passes.
6. Reassess/synchronize P3 after Alpha 5 stabilization.

## Resolution rule

No finding is resolved solely because code, mocks, CI or package definitions exist. Where applicable, resolution requires implementation, regression coverage, representative deployment/integration evidence, architecture documentation and physical validation tied to the exact immutable target.
