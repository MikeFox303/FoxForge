# FoxForge independent audit remediation tracker — 2026-09-04

**Source audit:** `docs/audits/2026-09-04-independent-project-audit.md`  
**Remediation branch:** `stabilization/audit-remediation`  
**Feature freeze:** P3 automatic filament accounting is preserved in draft PR #58 and must not merge until the stabilization/resume gate is satisfied.

This file tracks active remediation. The independent audit remains the immutable finding snapshot; this tracker records implementation progress and evidence.

## Status definitions

- `OPEN` — not yet addressed.
- `IN PROGRESS` — implementation/design work exists but acceptance evidence is incomplete.
- `VALIDATION REQUIRED` — code foundation is complete but deployment/physical evidence is still required.
- `RESOLVED` — every applicable audit acceptance criterion has repository evidence and regression coverage.

## Current tracker

| ID | Priority | Status | Active remediation |
| --- | --- | --- | --- |
| AUD-001 | P0 | IN PROGRESS | Fail-fast immutable release preflight added; duplicate/mismatched Git tag, GitHub release and existing semantic image are blocked before publication. Exact CI evidence pending. |
| AUD-002 | P0 | IN PROGRESS | `container.yml` restricted to `main` + `sha-*`; semver and `v*` tag publication removed. Exact CI evidence pending. |
| AUD-003 | P0 | OPEN | Align browser command bootstrap with every documented Docker/Umbrel deployment mode. |
| AUD-004 | P0 | OPEN | Define trusted browser-session/reverse-proxy security ADR and enforce trusted-boundary proof. |
| AUD-005 | P1 | OPEN | Remove duplicate `PrinterSetupLauncher`, retain mobile access and add browser regression coverage. |
| AUD-006 | P1 | OPEN | Add frozen frontend/backend dependency graphs and CI/release enforcement. |
| AUD-007 | P1 | OPEN | Supersede/amend ADR 0004 so canonical docs match implemented browser/config write security. |
| AUD-008 | P1 | OPEN | Add config + SQLite migration/version ownership, fixtures, backup/restore and diagnostics. |
| AUD-009 | P1 | IN PROGRESS | Roadmap sequencing corrected operationally: P3 frozen; audit stabilization is now the active workstream. Canonical roadmap/status docs still need synchronization before resolution. |
| AUD-010 | P2 | OPEN | Add atomic/CAS/revisioned inventory ledger mutation and concurrency tests before P3 resumes. |
| AUD-011 | P2 | OPEN | Add artifact quota/retention/orphan/cleanup/free-space policy. |
| AUD-012 | P2 | OPEN | Add bounded concurrent reconnect with per-printer backoff/jitter and deterministic tests. |
| AUD-013 | P2 | OPEN | Design Bambu LAN certificate pinning/TOFU path; physical validation required before default change. |
| AUD-014 | P2 | OPEN | Define and enforce Moonraker endpoint/redirect/address-resolution SSRF policy without blocking normal LAN printers. |
| AUD-015 | P2 | OPEN | Document `/data` credential sensitivity and introduce `SecretStore` infrastructure boundary. |
| AUD-016 | P2 | OPEN | Stop publishing public production source maps or move them to separate CI/debug artifacts. |
| AUD-017 | P2 | OPEN | Replace unconditional recursive `/data` chown with targeted/versioned ownership initialization. |
| AUD-018 | P2 | OPEN | Add browser acceptance tests for desktop/tablet/mobile and critical authenticated flows. |
| AUD-019 | P3 | OPEN | Add `SECURITY.md`, dependency automation/audits, image vulnerability scan and coverage governance before Beta. |

## P3 freeze record

The detailed frozen P3 implementation state is recorded in `docs/status/p3-frozen-state-2026-09-04.md`.

P3 is not discarded. The draft already contains reservation/reconciliation semantics, exact Decimal accounting, full material-plan enforcement, restart/idempotency protections and UI work. It remains intentionally unmerged until the audit blockers and P3 resume criteria are satisfied.

## Execution order

1. **Release integrity:** AUD-001, AUD-002.
2. **Browser/deployment security:** AUD-003, AUD-004, AUD-007.
3. **UI regression + reproducibility:** AUD-005, AUD-006, first slice of AUD-018/AUD-019.
4. **Persistent data foundation:** AUD-008.
5. **Representative physical/deployment validation:** X2D, Moonraker/OpenKE, Raspberry Pi 5/Umbrel.
6. **Inventory operator workflow:** complete normal create/correct/move/assign/unassign/archive/history UX.
7. **Atomic inventory concurrency:** AUD-010.
8. **Remaining P2/P3 audit hardening:** AUD-011..AUD-019 as required before Beta/farm scheduling.
9. **Resume P3:** synchronize PR #58 with current `main`, rerun all exact-head gates, finish docs, then merge only if all resume criteria pass.

## Resolution rule

Do not mark any finding `RESOLVED` solely because code was written. A resolution requires, where applicable:

- implementation fix;
- automated regression test;
- deployment/integration test for cross-process/proxy behavior;
- ADR/documentation update when a contract changes;
- physical validation evidence for printer-specific claims;
- exact final-head CI evidence before merge.
