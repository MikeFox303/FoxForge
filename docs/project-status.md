# FoxForge project status

**Snapshot date:** 2026-09-06  
**Canonical branch:** `main`  
**Latest semantic pre-release:** `v0.1.0-alpha.4.3`  
**Active milestone:** Pre-Alpha 5 / Bambu Lab connection and control ([#115](https://github.com/MikeFox303/FoxForge/issues/115))  
**Current installable Umbrel validation candidate:** `0.1.0-alpha.4.3-umbrel.3`  
**Maturity:** runnable/installable alpha; not production-ready

This page is the concise current-state snapshot. ADRs/design documents remain normative for architecture. `release/` remains immutable release history, and dated Alpha 4.x status/evidence documents remain historical records.

## Release versus validation candidate

FoxForge has **not** published final `v0.1.0-alpha.5` yet.

The latest semantic GitHub pre-release remains `v0.1.0-alpha.4.3`, released from commit `6845bd1329739c03d766fd86fa8fa308032b1bab`.

The current physical-validation package is deliberately separate:

```text
Umbrel package: 0.1.0-alpha.4.3-umbrel.3
candidate source: 37d1cbed8f73d62acdc1994545bc2f5ee57e816a
Store commit: cc6010fdff4823b671a92be3b307155f26db85bc
exact image: ghcr.io/mikefox303/foxforge:sha-37d1cbe@sha256:4e652006212db2527804abbd478b7b64fde127414b1dbe22703854280ccfce82
target release: v0.1.0-alpha.5
```

Candidate 3 supersedes candidate 2 for current physical evidence because the material-routing compiler, queue routing integration and Bambu native nozzle-mapping path changed after candidate 2. Candidate 1/2 evidence remains historical and must not be carried forward without explicit revalidation.

Documentation-only commits may advance `main` beyond the candidate source without changing the immutable package under test.

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Common printer domain | Implemented | FoxForge-owned identities, snapshots/events/errors and typed capabilities. |
| Bambu adapter | Functional alpha | MQTT/TLS state, project storage, material-system/topology observation, compiled nozzle routing and common job control; physical X2D validation in progress. |
| Bambu discovery | Implemented foundation | Explicit RFC1918 IPv4 subnet scan, bounded `/22` or smaller, candidate-only until normal authenticated setup succeeds. |
| Bambu Add Printer | Implemented | Test-before-save prevents invalid connectivity/credentials from creating durable dead configuration. |
| Bambu Update Printer | Implemented | Preflight before replacement; failed replacement restores previous durable config, secrets and adapter state. |
| Material topology | Implemented foundation | Vendor-neutral source/toolhead reachability; Bambu external and AMS routes remain proven/dynamic/unknown rather than guessed. |
| Immutable 3MF print plan | Implemented foundation | Staged `.3mf` inspection exposes plate/material requirements and toolhead intent without mutating the artifact. |
| Material routing compiler | Implemented | Explicit physical bindings are fail-closed against print-plan, material-system and topology evidence. |
| Bambu native mapping | Implemented | Final one-snapshot revalidation plus compiler-owned `nozzle_mapping`; external 254/255 use real `ams_mapping2` identities. |
| Moonraker adapter | Functional alpha | Production HTTP/WebSocket/control foundation implemented; physical OpenKE validation pending. |
| Fleet management | Implemented | Dynamic composition and normalized lifecycle/events. |
| Reconnect supervision | Implemented foundation | Per-printer workers, bounded concurrency/backoff/jitter and secret-safe diagnostics. |
| Durable print queue | Implemented foundation | SQLite dispatch/retry/reconciliation with explicit `INDETERMINATE`; routed 3MF requests persist compiled toolhead bindings before adapter assessment and are prepared again before dispatch. |
| Artifact staging | Implemented | Content-addressed storage, quota/min-free reserve and safe GC. |
| Filament/spool inventory | Operator workflow implemented | Exact `Decimal` ledger plus create/correct/empty-mass/assignment/archive/history. |
| Command security | Implemented foundation | Explicit bearer auth, permissions, durable idempotency, normalized errors and audit. |
| Printer credentials | Implemented | `SecretStore` separates Bambu access codes and Moonraker API keys from ordinary config. |
| Pause/Resume/Cancel | Implemented | Exact observed vendor-job guard; physical Bambu/Moonraker validation remains. |
| Realtime application events | Implemented | SSE replay/resync invalidation plus canonical HTTP snapshots. |
| Web UI | Functional alpha | Live API, setup/discovery, queue, inventory, job control and reconnect diagnostics. |
| Docker/ARM64 | Published alpha foundation | Linux `amd64` + `arm64`; Candidate 3 image is published and package-smoked on both architectures. |
| Umbrel | Candidate 3 published | `APP_PASSWORD` maps to `FOXFORGE_COMMAND_TOKEN`; Candidate 3 package/runtime/release-audit gates are green. |
| Automatic filament accounting | **Frozen / not merged** | P3 remains behind physical/deployment gate. |
| Persistent farm scheduler | Not implemented | Deferred until printer/deployment and P3 foundations are stable. |

## Pre-Alpha 5 milestone state

Issue #115 is intentionally Bambu-first. Current source has already closed the main software-side setup/reconnect and safe-routing gaps:

- normalized setup failures instead of raw internal exceptions;
- stable setup identity/model handling;
- conservative discovery plus manual fallback;
- Add and Update test-before-save;
- rollback-safe failed updates;
- durable replay of terminal failed setup requests;
- reconnect diagnostics API/UI;
- live Bambu material-system foundation;
- vendor-neutral material topology and X2D external-source routing semantics;
- immutable `.3mf` material-requirement inspection;
- fail-closed compiler-owned source→toolhead routing persisted by the queue;
- Bambu final source/topology/toolhead revalidation from one native snapshot;
- `project_file` `ams_mapping` / `ams_mapping2` / `nozzle_mapping` generation from the compiled route;
- GUI-visible Umbrel app password/operator-token path.

What remains before final Alpha 5 is primarily **real Raspberry Pi 5 + Umbrel + X2D + AMS 2 Pro evidence**, including the actual material fixture, safe routed print dispatch and guarded job control.

## Current physical release gate

Use [`testing/pre-alpha-5-bambu-physical-validation.md`](testing/pre-alpha-5-bambu-physical-validation.md) for the exact package and sequence.

Required evidence includes:

1. Candidate 3 install/update on Raspberry Pi 5/Umbrel;
2. GUI-only Operator Access using the Umbrel-displayed app password;
3. real X2D Add Printer, including negative host/access-code/serial cases without persistence;
4. safe Update behavior that preserves a working printer after invalid replacement values;
5. restart and network-loss reconnect/recovery with sanitized diagnostics;
6. live X2D state plus AMS 2 Pro A1-A4 PETG and both external-source observations;
7. truthful source→toolhead topology for external left/right and any authoritative AMS routing;
8. immutable `.3mf` print-plan inspection, explicit physical material bindings and eligible compiled toolhead routes;
9. final Bambu source/topology revalidation and sanitized `ams_mapping` / `ams_mapping2` / `nozzle_mapping` evidence;
10. real project delivery and exactly-once intended print start;
11. guarded Pause/Resume/Cancel or completion path against the same observed job;
12. secret-safe evidence and no raw credentials/tracebacks.

If implementation changes are required by physical findings, a new immutable candidate must be published and affected evidence repeated.

## Audit and P3 state

The immutable audit snapshot remains [`audits/2026-09-04-independent-project-audit.md`](audits/2026-09-04-independent-project-audit.md). Active status is in [`audits/2026-09-04-remediation-tracker.md`](audits/2026-09-04-remediation-tracker.md).

Software-only audit remediation is complete. AUD-003 and AUD-013 remain validation-bound and must not be closed from CI-only evidence.

P3 automatic filament accounting remains preserved in its frozen implementation branch/record and does not resume during the Bambu Alpha 5 milestone.

## Development order

1. Complete the Candidate 3 Pre-Alpha 5 Bambu physical acceptance matrix.
2. Fix any real-device/deployment defect and publish a new immutable candidate if the tested code changes.
3. Prepare and publish final `v0.1.0-alpha.5` only after the exact candidate passes.
4. Update audit evidence/status only from reviewed real-device evidence.
5. Reassess P3 resume after Alpha 5 stabilization.
6. Continue broader Moonraker physical validation, deep Bambu capabilities and persistent farm scheduling behind the existing typed boundaries.

## Persistence and safety

Persistent `/data` remains sensitive and contains configuration, SQLite state, SecretStore data and staged artifacts. Back up the complete directory before early-alpha upgrades.

Binding invariants include:

- common application/domain code does not depend on vendor transports;
- deep Bambu behavior remains typed and vendor-specific when it is not genuinely common;
- print material routing is fail-closed and does not guess physical sources or toolheads;
- Bambu wire mapping stays inside the Bambu adapter and consumes compiler-owned routing decisions;
- ambiguous remote side effects are not blindly retried;
- realtime events invalidate canonical HTTP state rather than becoming a second source of truth;
- printer credentials are never returned by setup read models;
- browser credentials remain memory-only;
- Docker and Umbrel package the same FoxForge application behavior.

## Key current documents

- [Pre-Alpha 5 Bambu physical validation](testing/pre-alpha-5-bambu-physical-validation.md)
- [Material topology](design/material-topology.md)
- [Immutable 3MF print plan](design/immutable-3mf-print-plan.md)
- [Material routing compiler](design/material-routing-compiler.md)
- [Queue routing integration](design/queue-routing-integration.md)
- [Bambu compiled nozzle mapping](design/bambu-compiled-nozzle-mapping.md)
- [Application-managed printer setup](design/app-managed-printer-setup.md)
- [Reconnect supervision](design/reconnect-supervision.md)
- [Deployment authentication](testing/deployment-auth-contract.md)
- [Documentation index](README.md)
