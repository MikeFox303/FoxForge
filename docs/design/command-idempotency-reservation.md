# Command idempotency reservation

- **Status:** implemented durable command boundary
- **Updated:** 2026-09-06
- **Related:** [ADR 0004](../adr/0004-command-api-security.md)

## Purpose

HTTP command idempotency prevents retries, browser reconnects or proxy uncertainty from re-executing the same FoxForge mutation when the caller is attempting to observe the original command result.

## Durable model

For commands that require external idempotency, FoxForge durably binds:

```text
(principal, operation, Idempotency-Key)
    -> canonical request fingerprint
    -> command lifecycle/result
```

A key is only valid within its principal/operation scope.

Rules:

- same key + same canonical request -> replay the original logical result;
- same key + different request fingerprint -> conflict;
- a command reservation exists before the protected operation is executed where the route contract requires it;
- terminal normalized failures may be stored/replayed when repeating the operation itself would be wrong;
- raw idempotency keys are not written to audit logs.

Current printer Add/Update setup uses this boundary so a terminal sanitized connection failure can be replayed deterministically without performing the same connection side effect again.

## Separation from feature identities

HTTP `Idempotency-Key` is not a substitute for domain/application identities:

- queue `dispatchId` identifies the logical printer-side print dispatch;
- job-control `controlId` identifies one logical Pause/Resume/Cancel action;
- inventory adjustment idempotency protects the ledger operation.

These identities can coexist because they protect different replay boundaries.

## Ambiguous remote effects

Idempotent HTTP replay must not convert an ambiguous printer-side side effect into a resend. Queue/job-control `INDETERMINATE` semantics remain authoritative; the client observes/reconciles rather than generating a fresh physical action automatically.

## Acceptance criteria

- same-key/same-request replay is deterministic across restart where the command contract is durable;
- changed request under the same key conflicts;
- terminal setup failures can replay without a second connection attempt;
- audit records store a digest/reference, not the raw key;
- feature-level dispatch/control/ledger identities remain separate;
- browser retry behavior cannot weaken physical-side-effect safety.
