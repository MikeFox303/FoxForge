# P3 automatic filament accounting — frozen implementation and reactivation plan

**Originally recorded:** 2026-09-04  
**Updated:** 2026-09-06  
**Status:** FROZEN / DRAFT — do not merge into Pre-Alpha 5  
**Historical working PR:** #58 (`feature/p3-filament-accounting`)  
**Canonical production branch:** `main`

P3 automatic filament accounting remains intentionally frozen while FoxForge completes the Bambu-first `v0.1.0-alpha.5` printer/deployment gate. The historical PR is retained so validated accounting ideas and tests are not lost, but it is no longer treated as a branch that will be merged wholesale after the freeze.

Since P3 was frozen, `main` has gained immutable 3MF print-plan inspection, typed material topology, explicit source bindings, compiler-owned `toolhead_id`, queue-time routing compilation/recompilation and Bambu adapter-side route revalidation. P3 must therefore be reactivated against those current contracts instead of rebasing old integration code mechanically.

## What is already implemented in the historical P3 draft

The draft contains useful implementation work that should be reviewed and selectively transplanted:

- durable filament reservations keyed by `queueId + materialIndex`;
- exact `Decimal` material estimates instead of binary floating-point accounting;
- resolution of a reservation through `printerId + slotId -> FoxForge spool_id`;
- overcommit checks against remaining mass and already-held reservations;
- full-plan requirement for every queue material binding before dispatch;
- pre-dispatch revalidation that the reserved spool is still assigned to the same physical slot;
- automatic estimated consumption only after a confirmed queue `COMPLETED` state;
- safe release for receipt-free pre-start failures;
- `FAILED` / `CANCELLED` after confirmed start -> `reconciliation_required`;
- `INDETERMINATE` retains reservations and does not infer zero or full consumption;
- explicit actual-mass reconciliation;
- deterministic inventory idempotency keys for completion/reconciliation;
- SQLite persistence for reservations and restart settlement;
- accounting API/read models/realtime invalidation;
- frontend planning and reconciliation UI;
- EN/RU/UK strings and backend/frontend tests.

## Safety invariants that remain valid

These rules survive the reactivation unchanged unless a later ADR explicitly supersedes them:

1. FoxForge does not derive consumed grams from print progress or opaque vendor telemetry.
2. A queue entry cannot dispatch with a partial accounting plan when automatic accounting is enabled for that job.
3. Printer slot IDs remain opaque physical identifiers; `spool_id` remains inventory-owned.
4. A reservation must still resolve to the same `spool_id` at the same physical source immediately before dispatch.
5. `INDETERMINATE` never causes automatic retry, automatic release or automatic consumption.
6. Confirmed completion may settle an estimate exactly once through deterministic inventory idempotency.
7. A started failed/cancelled job requires explicit reconciliation rather than guessed consumption.
8. Restart/replay cannot duplicate a consumption ledger adjustment.
9. Accounting application/domain code cannot depend on Bambu or Moonraker transport/protocol types.
10. Routing evidence and accounting evidence are separate concerns: successful material routing does not by itself authorize a filament debit.

## Why PR #58 will not be merged directly

PR #58 remains an implementation archive. Its base predates the current QueueService/material-routing contracts, and its integration points were written before FoxForge added:

- immutable staged-artifact inspection;
- plate-scoped 3MF requirements;
- `foxforge.material_topology`;
- compiler-owned `MaterialBinding.toolhead_id`;
- queue recompilation before dispatch;
- adapter-side Bambu source/toolhead revalidation;
- the current `INDETERMINATE` and exactly-once dispatch protections.

A direct merge or large conflict-resolution rebase would make it too easy to preserve stale assumptions. Reactivation must start from then-current `main` and transplant/reimplement reviewed pieces in small PRs.

## Current prerequisite: complete Alpha 5 first

P3 remains frozen throughout the Bambu Alpha 5 milestone.

Before P3 implementation resumes, FoxForge must complete the exact immutable replacement-candidate gate:

1. Raspberry Pi 5 + Umbrel install/update and GUI-only Operator Access;
2. real X2D Add/Update/discovery/reconnect/diagnostics validation;
3. real AMS 2 Pro + external-source material-system/topology validation;
4. one explicitly reviewed immutable 3MF with explicit source/toolhead routing;
5. exactly one physical Bambu print start from that reviewed intent;
6. guarded Pause/Resume/Cancel or completion against the exact observed job;
7. exact-head release gates and final `v0.1.0-alpha.5` publication.

Candidate 4 is historical and retired for first-print acceptance; its evidence is not a substitute for the replacement candidate.

## P3 Reactivation Audit

After Alpha 5 is physically accepted, create a clean branch from the then-current `main` and review PR #58 by layer.

### Phase 1 — accounting core and persistence

Review/transplant only vendor-neutral pieces first:

- reservation and settlement models;
- exact `Decimal` calculations;
- SQLite persistence/migrations;
- deterministic idempotency;
- reconciliation state machine;
- inventory ledger integration.

Acceptance criteria:

- no adapter imports;
- restart/replay cannot double-debit;
- old persisted state has an explicit migration path;
- unit/infrastructure tests cover completion, cancel/fail and `INDETERMINATE`.

### Phase 2 — current QueueService integration

Reimplement the old queue integration around the current routing pipeline rather than restoring the old wrapper unchanged.

The accounting reservation must bind to the operator-selected physical source/spool and coexist with the compiler-owned toolhead decision. Before dispatch FoxForge must independently prove both:

- routing is still safe for the selected source/toolhead; and
- the reserved inventory spool is still assigned to that same source.

Accounting must not change the existing durable dispatch ordering, hidden-retry prohibition or reconciliation-only handling of ambiguous side effects.

### Phase 3 — consumption evidence

Introduce a vendor-independent estimate/evidence contract with explicit provenance.

Examples may include:

- Bambu 3MF estimated/used mass metadata after conservative validation;
- a future Moonraker/Klipper estimator through a separate provider.

Artifact parsing alone must never mutate inventory. An estimate is evidence used by P3 settlement, not permission to debit a spool.

### Phase 4 — provider enablement

The accounting core remains vendor-independent, but automatic enablement is provider-specific and evidence-gated.

- **Bambu:** may be the first enabled provider after the real X2D Alpha 5 gate and dedicated weighed-spool accounting validation.
- **Moonraker/Klipper:** can keep automatic accounting disabled until its own OpenKE/Moonraker physical validation is complete, even if the common P3 core has already resumed.

This avoids blocking safe Bambu progress on unrelated provider hardware while preserving one common accounting architecture.

### Phase 5 — operator UI and reconciliation

The UI must show before dispatch:

- selected physical source;
- inventory spool;
- estimated grams;
- estimate provenance;
- reservation state.

For cancelled, failed or uncertain jobs it must provide explicit reconciliation rather than silently deciding consumed mass.

## Reactivation acceptance gates

P3 cannot be enabled by default until all applicable gates pass:

- exact `Decimal` arithmetic end to end;
- no double debit after retry, replay or restart;
- no automatic full debit on failed/cancelled/`INDETERMINATE` jobs;
- source/spool reassignment before dispatch blocks or requires a new explicit accounting plan;
- completion settlement is exactly once;
- reconciliation is explicit, reversible/auditable and idempotent;
- queue schema/migrations remain backward compatible;
- Docker `amd64`/`arm64` and Umbrel persistence/migration gates pass;
- backend/frontend/browser/container/security CI is green on the exact final head;
- at least one real weighed-spool Bambu validation compares expected and observed consumption;
- provider enablement state is explicit rather than inferred from printer model names.

## Milestone boundary

Automatic filament accounting is **not part of `v0.1.0-alpha.5`**. The earliest sensible activation milestone is post-Alpha-5 (for example an Alpha 6 workstream), after the Reactivation Audit above.

Until then PR #58 is a reference archive, not a release candidate and not a merge source of record.
