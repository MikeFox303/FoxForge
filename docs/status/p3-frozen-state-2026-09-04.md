# P3 automatic filament accounting — Candidate 6 reactivation

**Originally recorded:** 2026-09-04  
**Reactivated:** 2026-09-08  
**Status:** ACTIVE REBUILD — required before Candidate 6 publication  
**Historical implementation archive:** PR #58 (`feature/p3-filament-accounting`)  
**Canonical production branch:** `main`

The earlier freeze policy in this document is superseded by Candidate 6 issue #154. P3 automatic filament accounting must now be rebuilt, validated and resolved before C6-11 publishes an immutable Candidate 6 image/package.

PR #58 remains an implementation archive and must **not** be merged or mechanically rebased as one large change. Its useful vendor-independent accounting ideas are being reviewed and transplanted/reimplemented in small PRs against the current QueueService, material topology, immutable print-plan and exactly-once dispatch contracts.

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

## Why the historical QueueService wrapper is not restored

Current `QueueService.assess()` recompiles and revalidates material routing immediately before dispatch. The historical P3 `AccountingQueueService` checked accounting before that modern routing compilation and therefore has the wrong integration point.

The rebuilt pre-dispatch sequence must be:

```text
immutable artifact / plate intent
        -> fresh routing compilation + printer assessment
        -> accounting plan completeness
        -> physical slot -> reserved spool revalidation
        -> capacity revalidation
        -> durable DISPATCHING write
        -> adapter side effect
```

Accounting must not change the existing `DISPATCHING` durability ordering, hidden-retry prohibition, adapter idempotency or `INDETERMINATE` behavior.

## Reactivation sequence

### P3-R1 — reservation model and persistence

Reintroduce only the vendor-independent core:

- reservation/value models;
- exact `Decimal` validation;
- in-memory store contract;
- SQLite reservation persistence;
- restart/conflict/missing-write coverage;
- `reconciliation_required` remains a capacity-holding state.

No runtime enablement, queue guard or inventory debit occurs in this slice.

### P3-R2 — settlement and inventory idempotency

Rebuild the service layer around the current Inventory API:

- reservation capacity calculation and overcommit prevention;
- deterministic completion/reconciliation idempotency keys;
- completed estimate settlement exactly once;
- receipt-free pre-start release only;
- started failed/cancelled -> explicit reconciliation;
- `INDETERMINATE` retains reservations;
- restart/replay settlement tests.

### P3-R3 — current QueueService integration

Integrate after fresh routing compilation/assessment and before `DISPATCHING`:

- complete plan required for all material bindings;
- reserved `spool_id` must still match the selected physical `slot_id`;
- current remaining mass must still cover the reservation;
- route/toolhead safety remains owned by the routing compiler/adapter;
- accounting failure blocks dispatch before any external side effect.

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
