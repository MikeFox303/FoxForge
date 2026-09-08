# P3 automatic filament accounting — Candidate 6 reactivation

**Originally recorded:** 2026-09-04  
**Reactivated:** 2026-09-08  
**Status:** ACTIVE — R1-R4 integrated; R5 provider validation capability in progress  
**Historical implementation archive:** PR #58 (`feature/p3-filament-accounting`)  
**Canonical production branch:** `main`

The earlier freeze policy in this document is superseded by Candidate 6 issue #154. P3 is being rebuilt against the current QueueService, material topology, immutable print-plan and exactly-once dispatch contracts. Historical PR #58 remains an implementation archive and must not be merged or mechanically rebased as one large change.

## Reactivation progress

- **P3-R1 COMPLETE** — PR #165, merge `38531028f4882797db32544d30162a9ad179d2f8`: reservation values, exact `Decimal`, in-memory/SQLite persistence and restart/conflict coverage.
- **P3-R2 COMPLETE** — PR #168, merge `9fcdbca512d077858cb98522c5e1dd11380edb92`: atomic planning, capacity holds, exactly-once settlement, explicit reconciliation and crash/restart recovery.
- **P3-R3 COMPLETE** — PR #169, merge `6a96f770c6fb98535a972d2de090b0b9b7a18152`: queue-owned dispatch/lifecycle policy seams and fail-closed accounting guard semantics.
- **P3-R4a COMPLETE** — PR #170, merge `17438221f570a7f8035800f3e904e4ca0c63ae45`: guarded accounting API, audit, realtime invalidation and durable runtime lifecycle composition.
- **P3-R4b COMPLETE** — PR #171, merge `e700edbe7cb37fc85c99202ab6bf24215499d408`: Queue operator UI, routing-evidence preservation, EN/RU/UK, assignment-drift visibility and browser coverage.
- **P3-R5 ACTIVE** — provider-scoped pre-dispatch enablement is being added for controlled Bambu Candidate 6 validation while ordinary deployments remain disabled by default.

## Mandatory safety invariants

1. FoxForge never derives consumed grams from print progress or opaque vendor telemetry.
2. Estimates and actual masses use exact `Decimal` arithmetic end to end.
3. Printer slot IDs remain opaque physical identifiers; `spool_id` remains inventory-owned.
4. A reservation is keyed by durable `queue_id + material_index` and binds one inventory spool to one physical source.
5. A complete enforced accounting plan must cover every material binding before dispatch can cross the accounting gate.
6. The reserved spool must still be assigned to the same physical source immediately before dispatch.
7. `INDETERMINATE` never releases reservations, consumes an estimate or authorizes an automatic retry.
8. A started failed/cancelled print with unknown actual usage enters `reconciliation_required`; FoxForge does not guess zero or full consumption.
9. Confirmed completion may settle an estimate exactly once through deterministic inventory idempotency.
10. Explicit actual-mass reconciliation is auditable and idempotent.
11. Restart/replay cannot duplicate an inventory debit.
12. Accounting application/domain code cannot depend on Bambu or Moonraker transport/protocol types.
13. Routing evidence and accounting evidence are separate: a valid source/toolhead route does not by itself authorize a filament debit.
14. A multi-material reservation plan is durable all-or-nothing; a conflict cannot leave a partial plan behind.
15. Missing receipt is not proof that a print never started once a dispatch attempt crossed the durable start boundary; receipt-free terminal failure with `attempt_count > 0` remains reconciliation-required unless future common evidence explicitly proves no side effect occurred.
16. Queue remains independent of concrete accounting code; accounting participates only through queue-owned vendor-neutral policy contracts.
17. Secondary accounting settlement failure cannot roll back an already-durable queue lifecycle transition or terminate queue event tracking.
18. Once a reservation leaves `reserved`, the same queue entry cannot create a new accounting plan; a new plan requires a new queue entry.
19. Provider enforcement is explicit and closed; generic UI/application code cannot infer enablement from model names.
20. Moonraker/Klipper automatic enforcement remains disabled until its own provider-specific evidence exists.

## Current pre-dispatch ordering

The historical P3 QueueService wrapper is not restored. Current QueueService recompiles and revalidates material routing immediately before dispatch, so accounting participates only after fresh routing assessment:

```text
immutable artifact / selected plate intent
        -> fresh routing compilation + printer assessment
        -> optional provider-scoped accounting policy
        -> complete accounting plan
        -> physical slot -> reserved spool revalidation
        -> full active-hold capacity revalidation
        -> durable DISPATCHING write
        -> adapter side effect
```

Accounting must not change the existing `DISPATCHING` durability ordering, hidden-retry prohibition, adapter idempotency or `INDETERMINATE` behavior.

## R1-R4 canonical behavior

Current `main` now contains:

- durable reservation/persistence contracts;
- atomic all-or-nothing multi-material planning;
- active spool-capacity holds and overcommit prevention;
- completion settlement using deterministic inventory idempotency;
- explicit reconciliation for started failed/cancelled jobs;
- queue-owned `QueuePreDispatchGate` and `QueueLifecycleObserver` seams;
- guarded `filament-plan`, `filament-release` and `filament-reconcile` commands;
- accounting read model, command audit and normalized realtime invalidation;
- production SQLite accounting store and startup lifecycle replay;
- Queue UI showing physical source, reserved/current spool, estimate, reservation state and actual reconciliation;
- assignment-drift detection that preserves the original reserved spool identity when a physical slot later changes;
- EN/RU/UK and responsive browser coverage.

R4 intentionally leaves ordinary runtime pre-dispatch enforcement disabled. Explicitly created reservations can still settle through the lifecycle observer, but a provider is not globally forced through accounting until R5 enables that provider/workflow.

## P3-R5 — provider validation capability

R5 separates **software capability** from **physical evidence** so Candidate 6 does not contain an impossible circular gate.

### Software requirement before C6-11

The Candidate 6 source/image must be able to run one of a closed set of accounting enforcement modes:

```text
disabled
bambu-validation
```

Rules:

- `disabled` is the normal/default mode;
- `bambu-validation` delegates the existing vendor-independent `FilamentAccountingQueuePolicy` only for `adapter_kind == "bambu"`;
- Moonraker and unknown/future provider kinds bypass this validation gate and are not implicitly enabled;
- a missing printer identity at the provider-scoped gate fails closed;
- diagnostics reports the active mode and enforced adapter kinds;
- unsupported mode names fail startup instead of silently falling back;
- no transport command, Bambu payload or model-name rule enters accounting application/domain code.

This software capability, its tests, deployment contract and documentation must be merged before C6-10/C6-11.

### Physical evidence after C6-11

The earlier wording created a cycle by requiring weighed-spool evidence before Candidate 6 publication while also requiring all physical evidence to bind to the immutable Candidate 6 identity. The corrected sequence is:

```text
R5 software capability integrated and default-disabled
        -> C6-10 clean-main software gate
        -> C6-11 freeze exact source/image/Umbrel package
        -> install exact Candidate 6 package on Raspberry Pi 5 + Umbrel
        -> verify diagnostics reports the intended Bambu validation mode
        -> execute no-print gate
        -> execute exactly one controlled first-print/accounting validation
        -> weigh/reconcile evidence against the same immutable image digest
```

Candidate 6's validation package may intentionally select `bambu-validation` while the generic Docker/runtime default remains `disabled`. That package setting is part of the immutable C6-11 deployment identity and must not be edited after evidence begins.

If physical validation requires any application code, image or package-definition change, the evidence is invalid for Candidate 6 and the replacement becomes Candidate 7.

### Bambu validation evidence

For the first accounting-enabled Bambu print, evidence must prove at minimum:

- the queue entry has explicit material bindings compiled from the immutable staged artifact;
- every binding has a durable reservation before dispatch;
- the reserved FoxForge spool is still assigned to the same physical source immediately before dispatch;
- diagnostics reports `bambu-validation` and enforced adapter kind `bambu`;
- the queue crosses the accounting gate before `DISPATCHING` and before the Bambu adapter side effect;
- exactly one physical print starts;
- completion settles the estimate exactly once;
- weighed-spool/explicit actual-mass evidence is recorded for comparison/reconciliation without guessing from progress;
- restart/replay cannot duplicate the inventory debit.

Moonraker/Klipper remains outside this provider acceptance until separate estimator/workflow evidence and physical OpenKE validation are defined.

## Candidate 6 P3 closure gate

P3 software work is complete for Candidate 6 publication only when:

- R1-R5 software capability is integrated on current `main`;
- exact-head Python 3.12/3.13, frontend, browser, security, deployment-auth and container gates are green as applicable;
- no P3 implementation PR remains unresolved;
- historical PR #58 is closed as superseded by the reviewed R1-R5 rebuild, not merged;
- milestone dependency/toolchain closure is complete;
- C6-10 passes once more on clean `main`.

C6-11 may then freeze and publish one immutable source/image/Umbrel identity. Physical Bambu accounting evidence is collected only against that exact identity and cannot be reused across changed application/image/package digests.

## Provenance

The P3 archive is historical FoxForge code written under AGPL-3.0-only. Reactivation may reuse or rewrite that FoxForge code while preserving required notices. No Bambuddy/PrintBuddy/PrintOps implementation code is copied by this accounting core.
