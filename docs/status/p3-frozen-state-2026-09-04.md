# P3 automatic filament accounting — Candidate 6 reactivation

**Originally recorded:** 2026-09-04  
**Reactivated:** 2026-09-08  
**Status:** ACTIVE REBUILD — required before Candidate 6 publication  
**Historical implementation archive:** PR #58 (`feature/p3-filament-accounting`)  
**Canonical production branch:** `main`

The earlier freeze policy in this document is superseded by Candidate 6 issue #154. P3 automatic filament accounting must now be rebuilt, validated and resolved before C6-11 publishes an immutable Candidate 6 image/package.

PR #58 remains an implementation archive and must **not** be merged or mechanically rebased as one large change. Its useful vendor-independent accounting ideas are being reviewed and transplanted/reimplemented in small PRs against the current QueueService, material topology, immutable print-plan and exactly-once dispatch contracts.

## Reactivation progress

- **P3-R1 COMPLETE** — PR #165 merged into `main` as `38531028f4882797db32544d30162a9ad179d2f8`; reservation value objects, exact `Decimal`, in-memory/SQLite persistence and restart/conflict coverage are canonical.
- **P3-R2 COMPLETE** — PR #168 merged into `main` as `9fcdbca512d077858cb98522c5e1dd11380edb92`; atomic planning, capacity holds, exactly-once settlement, reconciliation and crash/restart recovery are canonical.
- **P3-R3 ACTIVE** — current QueueService integration is being rebuilt on `pre-alpha-5/p3-accounting-dispatch-guard`; no runtime/provider enablement is introduced by this slice.
- **P3-R4..R5 PENDING** — operator/API workflow and provider evidence remain blocked on R3.

## Safety invariants that remain mandatory

1. FoxForge never derives consumed grams from print progress or opaque vendor telemetry.
2. Estimates and actual masses use exact `Decimal` arithmetic end to end.
3. Printer slot IDs remain opaque physical identifiers; `spool_id` remains inventory-owned.
4. A reservation is keyed by durable `queue_id + material_index` and binds one inventory spool to one physical source.
5. A complete automatic-accounting plan must cover every material binding before dispatch can cross the accounting gate.
6. The reserved spool must still be assigned to the same physical source immediately before dispatch.
7. `INDETERMINATE` never releases reservations, consumes an estimate or authorizes an automatic retry.
8. A started failed/cancelled print with unknown actual usage enters `reconciliation_required`; FoxForge does not guess zero or full consumption.
9. Confirmed completion may settle an estimate exactly once through deterministic inventory idempotency.
10. Explicit actual-mass reconciliation is auditable and idempotent.
11. Restart/replay cannot duplicate an inventory debit.
12. Accounting application/domain code cannot depend on Bambu or Moonraker transport/protocol types.
13. Routing evidence and accounting evidence are separate: a valid source/toolhead route does not by itself authorize a filament debit.
14. A multi-material reservation plan is durable all-or-nothing; a conflict cannot leave a partial plan behind.
15. Missing receipt is not proof that a print never started once a dispatch attempt crossed the durable start boundary; any receipt-free terminal failure with `attempt_count > 0` remains reconciliation-required unless future common evidence explicitly proves no side effect occurred.
16. Queue remains independent of concrete accounting code; accounting participates only through queue-owned vendor-neutral policy contracts.
17. Secondary accounting settlement failure cannot roll back an already-durable queue lifecycle transition or terminate queue event tracking.

## Why the historical QueueService wrapper is not restored

Current `QueueService.assess()` recompiles and revalidates material routing immediately before dispatch. The historical P3 `AccountingQueueService` checked accounting before that modern routing compilation and therefore has the wrong integration point.

The rebuilt pre-dispatch sequence is:

```text
immutable artifact / plate intent
        -> fresh routing compilation + printer assessment
        -> optional queue-owned accounting policy
        -> accounting plan completeness
        -> physical slot -> reserved spool revalidation
        -> capacity revalidation
        -> durable DISPATCHING write
        -> adapter side effect
```

Accounting must not change the existing `DISPATCHING` durability ordering, hidden-retry prohibition, adapter idempotency or `INDETERMINATE` behavior. The queue package must not import the accounting package.

## Reactivation sequence

### P3-R1 — reservation model and persistence — COMPLETE (#165)

Canonical `main` contains:

- reservation/value models;
- exact `Decimal` validation;
- in-memory store contract;
- SQLite reservation persistence;
- restart/conflict/missing-write coverage;
- `reconciliation_required` remains a capacity-holding state.

No runtime enablement, queue guard or inventory debit was introduced by R1.

### P3-R2 — settlement and inventory idempotency — COMPLETE (#168)

Canonical `main` now contains:

- atomic all-or-nothing multi-material reservation creation;
- reservation capacity calculation and overcommit prevention;
- immutable/idempotent plan replay;
- deterministic completion/reconciliation idempotency keys;
- completed estimate settlement exactly once;
- receipt-free release only when no dispatch attempt crossed the durable start boundary;
- attempted or confirmed-start failed/cancelled outcomes -> explicit reconciliation;
- `INDETERMINATE` retains reservations;
- explicit reconciliation is service-level idempotent and conflicting mass replays fail closed;
- restart/replay tests cover the crash window between inventory ledger commit and reservation-state save.

R2 remains disconnected from printer dispatch by itself and does not authorize automatic accounting in a release.

### P3-R3 — current QueueService integration — ACTIVE

The R3 design uses queue-owned vendor-neutral seams instead of a P3 subclass/wrapper:

- `QueuePreDispatchGate` runs only after fresh routing compilation and printer assessment;
- a blocker is persisted as ordinary `BLOCKED` assessment before `DISPATCHING` and before any adapter submit;
- `FilamentAccountingQueuePolicy` requires complete reservations for all material bindings;
- every reservation must still be `reserved`, point to the same printer/physical slot and match the current inventory assignment;
- current remaining mass must still cover the full active hold for every involved spool;
- route/toolhead safety remains owned by the routing compiler/adapter;
- `QueueLifecycleObserver` sees only already-durable queue states and replays restored entries on startup;
- observer failures are isolated per entry so queue event tracking continues and restart can retry settlement;
- no Bambu/Moonraker transport type or model-name check enters the accounting policy;
- ordinary QueueService behavior is unchanged when no policy is explicitly supplied.

R3 tests must cover missing plan, valid dispatch, assignment/capacity drift, fresh compiler ordering, completion exactly-once, failed/indeterminate outcomes and durable restart settlement.

### P3-R4 — API, audit, realtime and operator UI

Restore/update the old read/write workflows against current APIs:

- accounting read model;
- guarded plan/release/reconcile commands;
- command audit;
- realtime cache invalidation;
- queue UI showing source, spool, estimated grams, provenance and reservation state;
- explicit reconciliation UI for uncertain/failed/cancelled started jobs;
- EN/RU/UK strings and browser coverage.

### P3-R5 — evidence/provider enablement

Automatic accounting enablement remains evidence-gated and provider-specific while the accounting core stays common.

- Bambu may be first after an exact Candidate 6 X2D weighed-spool validation.
- Moonraker/Klipper remains disabled until its own estimator/evidence and physical validation are proven.
- Provider enablement must be explicit; generic UI/application code must not infer it from printer model names.

## Candidate 6 closure gate

P3 is complete for Candidate 6 publication only when:

- R1-R5 applicable software work is integrated on current `main`;
- Python 3.12/3.13, frontend, browser, security/deployment-auth and container gates are green on the exact integrated heads;
- no P3 implementation PR remains unresolved;
- the milestone dependency/toolchain closure is also complete;
- C6-10 passes once more on clean `main`.

C6-11 may then freeze and publish one immutable source/image/Umbrel identity. Real Raspberry Pi 5 + Umbrel + X2D physical validation occurs only against that frozen identity. Weighed-spool accounting evidence is part of provider enablement evidence and cannot be reused across changed application/image digests.

## Provenance

The P3 archive is historical FoxForge code written under AGPL-3.0-only. Reactivation may reuse or rewrite that FoxForge code while preserving its license notices. No Bambuddy/PrintBuddy/PrintOps implementation code is copied by this accounting core.
