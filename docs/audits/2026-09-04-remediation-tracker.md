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
| AUD-003 | P0 | **VALIDATION REQUIRED** | Explicit FoxForge token model and Umbrel bootstrap are implemented/tested; real Raspberry Pi/Umbrel install, proxy-write, persistence, network/realtime evidence remains. |
| AUD-004 | P0 | RESOLVED | ADR 0005 explicit-token model; proxy headers are not application principals; unsafe trusted-browser mode rejected. |
| AUD-005 | P1 | RESOLVED | One canonical responsive Add Printer entry point with production-browser regression coverage. |
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

**Physical validation is paused pending a replacement immutable Pre-Alpha 5 candidate.**

Candidate 4 was the canonical target before the 2026-09-06 release-readiness routing audit:

```text
package: my3d-foxforge 0.1.0-alpha.4.3-umbrel.4
application source: c11f7145b4354aa79c8f0fad223648240e652bac
Store: 07b8e8087ac9897d4c2f5dc45944b48dfb0938e1
image: ghcr.io/mikefox303/foxforge:sha-c11f714@sha256:75d656bafcafb4e0e566548f6cca941244d29fef1bbc5be98e425f375246056a
```

Candidate 4 is now **retired for first-print acceptance** because the audit found that some present-but-invalid 3MF toolhead metadata could be treated like absent metadata before the routing compiler saw it. PR #145 closes that fail-closed gap and aligns browser review with selected-plate routing semantics.

Do not start or continue the physical print gate on Candidate 4. After #145 passes exact-head software gates and merges, publish a new immutable source/image/Umbrel candidate and update [`../testing/pre-alpha-5-bambu-physical-validation.md`](../testing/pre-alpha-5-bambu-physical-validation.md) to that exact identity before collecting new evidence.

Candidate 1/2/3/4 evidence remains historical and must not be relabeled or silently carried to a new digest.

## Post-audit hardening relevant to the current gate

Current source provides:

- GUI-visible Umbrel operator credential path;
- bounded Bambu LAN discovery with server-visible private subnet suggestions plus manual fallback;
- Add Printer test-before-save;
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
- selected-plate browser/server routing semantics and present-vs-invalid toolhead metadata distinction after PR #145.

These changes reduce software-side risk but do not close AUD-003/AUD-013 without physical evidence.

## P3 freeze

P3 is preserved, not discarded. It remains intentionally unmerged while the Bambu Alpha 5 milestone is validated.

The normal inventory prerequisite is complete. Resume still requires reviewing then-current physical/deployment evidence, synchronizing the P3 branch with `main`, rerunning exact-head backend/frontend/container/security/browser gates and preserving all stabilization changes.

## Current execution order

1. Complete PR #145 and exact-head software gates.
2. Publish a new immutable Raspberry Pi 5/Umbrel validation candidate; do not reuse Candidate 4 identity/evidence.
3. Run the no-print X2D + AMS 2 Pro gate on the exact new candidate.
4. Only after that gate passes, run the first real print and guarded job-control acceptance.
5. If a physical defect changes code, publish another immutable candidate and repeat affected evidence.
6. Review AUD-003/AUD-013 evidence; update statuses only when requirements actually pass.
7. Publish final Alpha 5 only after the exact candidate gate passes.
8. Reassess/synchronize P3 after Alpha 5 stabilization.

## Resolution rule

No finding is resolved solely because code, mocks, CI or package definitions exist. Where applicable, resolution requires implementation, regression coverage, representative deployment/integration evidence, architecture documentation and physical validation tied to the exact immutable target.
