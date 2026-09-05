# P3 automatic filament accounting — frozen implementation state

**Recorded:** 2026-09-04  
**Status:** FROZEN / DRAFT — do not merge before audit stabilization gate  
**Working PR:** #58 (`feature/p3-filament-accounting`)  
**Canonical production branch:** `main`  
**Reason for freeze:** independent audit remediation takes precedence over roadmap feature progression.

This document records the current P3 implementation so work is not lost while FoxForge addresses the findings in `docs/audits/2026-09-04-independent-project-audit.md`.

## What is already implemented in the P3 draft

- durable filament reservations keyed by `queueId + materialIndex`;
- exact `Decimal` material estimates instead of binary floating-point accounting;
- resolution of a reservation through `printerId + slotId -> FoxForge spool_id`;
- overcommit checks against remaining mass and already-held reservations;
- full-plan requirement for every queue `materialBinding` before dispatch;
- pre-dispatch revalidation that the reserved spool is still assigned to the same physical slot;
- accounting-aware queue dispatch for both HTTP commands and the automatic queue runner;
- automatic estimated consumption only after a confirmed queue `COMPLETED` state;
- safe release for receipt-free pre-start failures;
- `FAILED` / `CANCELLED` after confirmed start -> `reconciliation_required`;
- `INDETERMINATE` retains reservations and does not infer zero or full consumption;
- explicit actual-mass reconciliation;
- deterministic inventory idempotency keys for completion/reconciliation;
- SQLite persistence for reservations and restart settlement;
- accounting API routes for plan/release/reconcile plus read snapshot;
- command-audit coverage and application-level realtime accounting invalidation;
- frontend work for slot selection, exact gram estimates, reservation-before-dispatch and reconciliation UI;
- EN/RU/UK user-facing strings and initial frontend/backend tests.

## P3 safety invariants already established

1. FoxForge does not derive consumed grams from printer progress or opaque vendor telemetry.
2. A queue entry with material bindings cannot dispatch with a partial or absent filament plan.
3. Printer slot IDs remain physical opaque identifiers; FoxForge spool identity remains inventory-owned.
4. A reservation must still resolve to the same `spool_id` at the same slot immediately before dispatch.
5. `INDETERMINATE` never causes automatic retry, automatic release or automatic consumption.
6. Confirmed completion may settle the estimate exactly once through inventory idempotency.
7. Started failed/cancelled jobs require explicit reconciliation instead of guessed consumption.
8. Restart/replay must not duplicate a consumption ledger adjustment.
9. P3 application/API code must not import Bambu or Moonraker transport/protocol types.

## Validation state at freeze

P3 is **not complete** and must not be described as merged or release-ready.

At the freeze point:

- draft PR #58 exists and remains unmerged;
- early Web UI and unified-container CI runs were green on intermediate heads;
- backend Ruff lint reached green on a later intermediate head;
- the latest examined backend run stopped at `ruff format --check` for two new P3 Python files, so the complete Python 3.12/3.13 pytest suite had not yet executed on the full P3 head;
- exact final-head CI has therefore **not** been proven green;
- P3 documentation and release-status synchronization were not complete;
- no physical X2D/OpenKE/Raspberry Pi validation exists for P3;
- P3 has not been rebased/merged onto the audit-remediation work.

## Audit blockers and prerequisite progress

The independent audit changed the development sequence. P3 resumes only after the stabilization gate is completed sufficiently to make automatic accounting safe to merge.

The software blockers identified at freeze have now been addressed in current `main`/stabilization work:

- **AUD-001 / AUD-002:** release publication integrity — resolved;
- **AUD-004 / AUD-007:** browser/deployment trust boundary and matching ADR — resolved;
- **AUD-005 / AUD-018:** duplicate launcher/UI browser regression coverage — resolved;
- **AUD-006:** reproducible dependency graphs — resolved;
- **AUD-008:** persistent configuration/database migration foundation — resolved;
- **AUD-010:** atomic inventory mutation contract and concurrency coverage — resolved;
- normal inventory operator workflow — implemented with create/correct/empty-spool-mass/move/assign/unassign/archive/history UI and production-browser acceptance.

The remaining audit-specific validation blockers are:

- **AUD-003:** representative future Umbrel/package write/read-only validation;
- **AUD-013:** physical X2D MQTT/FTPS certificate observations before any Bambu trust-default change.

Broader P3 readiness still requires representative X2D, Moonraker/OpenKE and Raspberry Pi/Umbrel lifecycle validation. Software completion does not substitute for those physical/deployment observations.

## Resume criteria

P3 may return to active implementation only when all of the following are true:

- applicable stabilization findings are marked resolved with repository evidence, or their remaining validation requirements are completed and recorded;
- inventory mutations use the stabilized atomic persistence contract and concurrency tests remain green;
- migration/version ownership exists for persistent SQLite/config state used by P3;
- the normal UI supports the spool operations needed for planning and reconciliation — **satisfied by the inventory operator workflow merged from PR #91 once that merge reaches `main`**;
- representative X2D, Moonraker/OpenKE and Raspberry Pi/Umbrel validation has been recorded where required;
- PR #58 is synchronized with the then-current `main` without discarding remediation changes;
- Ruff, Python 3.12/3.13 tests, measured coverage floor, frontend typecheck/Vitest/build, production-container browser acceptance, unified-container smoke and security gates are green on the exact final P3 head;
- P3 design, project status and changelog documentation are synchronized before merge.

Until these conditions are satisfied, PR #58 is an implementation archive and reviewable draft, not a release candidate.
