# FoxForge independent audit remediation tracker — 2026-09-04

**Source audit:** `docs/audits/2026-09-04-independent-project-audit.md`  
**Active remediation:** successive stabilization PRs from current `main`  
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
| AUD-001 | P0 | RESOLVED | PR #60 merged as `3a242a6250af923080ccc4399e2a2b1317b72a56`. Release identity preflight blocks existing/mismatched Git tags, GitHub releases and semantic GHCR tags before publication; regression tests and exact-head backend/container CI passed. |
| AUD-002 | P0 | RESOLVED | PR #60 removed `v*`/semver publication from `container.yml`; only `main` + `sha-*` development identities remain. Policy regression test and exact-head CI passed. |
| AUD-003 | P0 | IN PROGRESS | Standalone Compose now has explicit `FOXFORGE_COMMAND_TOKEN`/`.env.example`; browser uses a visible operator-access flow and fails closed when writes are unavailable. Historical alpha.3 Umbrel remains immutable/read-only for protected writes; next Umbrel package still needs representative package validation before resolution. |
| AUD-004 | P0 | IN PROGRESS | ADR 0005 defines the trust model. Production runtime rejects tokenless `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true`; browser credentials are explicit and memory-only. Exact-head CI and representative deployment validation remain pending. |
| AUD-005 | P1 | IN PROGRESS | Duplicate root `PrinterSetupLauncher` removed; one canonical topbar launcher remains and a repository regression test asserts one launcher tree. Browser/mobile acceptance coverage from AUD-018 remains pending before full resolution. |
| AUD-006 | P1 | OPEN | Add frozen frontend/backend dependency graphs and CI/release enforcement. |
| AUD-007 | P1 | IN PROGRESS | ADR 0005 supersedes ADR 0004 browser-auth deferral and documents the implemented operator-token/deployment boundary. Exact-head CI and merge evidence pending. |
| AUD-008 | P1 | OPEN | Add config + SQLite migration/version ownership, fixtures, backup/restore and diagnostics. |
| AUD-009 | P1 | IN PROGRESS | P3 is frozen and stabilization is the active workstream. `project-status`/roadmap still require canonical sequencing update before resolution. |
| AUD-010 | P2 | OPEN | Add atomic/CAS/revisioned inventory ledger mutation and concurrency tests before P3 resumes. |
| AUD-011 | P2 | OPEN | Add artifact quota/retention/orphan/cleanup/free-space policy. |
| AUD-012 | P2 | OPEN | Add bounded concurrent reconnect with per-printer backoff/jitter and deterministic tests. |
| AUD-013 | P2 | OPEN | Design Bambu LAN certificate pinning/TOFU path; physical validation required before default change. |
| AUD-014 | P2 | OPEN | Define and enforce Moonraker endpoint/redirect/address-resolution SSRF policy without blocking normal LAN printers. |
| AUD-015 | P2 | OPEN | Document `/data` credential sensitivity and introduce `SecretStore` infrastructure boundary. |
| AUD-016 | P2 | OPEN | Stop publishing public production source maps or move them to separate CI/debug artifacts. |
| AUD-017 | P2 | OPEN | Replace unconditional recursive `/data` chown with targeted/versioned ownership initialization. |
| AUD-018 | P2 | IN PROGRESS | First composition regression test now prevents duplicate Add Printer trees; real browser acceptance at desktop/tablet/mobile and authenticated flows remains to be added. |
| AUD-019 | P3 | OPEN | Add `SECURITY.md`, dependency automation/audits, image vulnerability scan and coverage governance before Beta. |

## P3 freeze record

The detailed frozen P3 implementation state is recorded in `docs/status/p3-frozen-state-2026-09-04.md`.

P3 is not discarded. The draft already contains reservation/reconciliation semantics, exact Decimal accounting, full material-plan enforcement, restart/idempotency protections and UI work. It remains intentionally unmerged until the audit blockers and P3 resume criteria are satisfied.

## Execution order

1. **Release integrity:** AUD-001, AUD-002 — resolved in PR #60.
2. **Browser/deployment security:** AUD-003, AUD-004, AUD-007 — active.
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
