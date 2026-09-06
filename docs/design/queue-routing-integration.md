# Queue routing integration

Status: Pre-Alpha 5 implementation contract.

## Decision

FoxForge must not pass a routable 3MF request to a printer adapter until the queue has compiled and durably persisted the physical material route.

The queue integration remains vendor-neutral. It uses the existing `PrintExecutionCapability`, `MaterialSystemCapability`, `MaterialTopologyCapability`, immutable `ArtifactPrintPlan`, and the application-level material routing compiler. It does not import Bambu adapter types or construct Bambu-native nozzle mappings.

## Routing boundary

Routing compilation is required when both conditions are true:

1. the staged artifact is `3mf`;
2. the target `PrintExecutionCapability` advertises material-binding support.

This keeps the existing G-code path unchanged. In particular, Moonraker/Klipper G-code execution is not forced through the Bambu-style 3MF inspection contract.

For a routed 3MF, the queue requires current material-system and material-topology capabilities. Missing capabilities are fail-closed assessment blockers.

## Assessment ordering

`QueueService.assess()` performs the following ordering:

1. restore the durable queue entry;
2. resolve the printer's common print-execution capability;
3. inspect the immutable staged 3MF;
4. read current material-system and topology snapshots;
5. compile the explicit source bindings into compiler-owned `toolhead_id` values;
6. persist the updated `PrintExecutionRequest` when compilation succeeds;
7. only after persistence, call `PrintExecutionCapability.assess()`;
8. persist the normalized queue assessment/state.

Step 6 is normative. The compiled route must survive a process restart before any later submit side effect is possible.

A blocked compilation never calls adapter assessment and never exposes partial compiled bindings.

## Dispatch ordering

`QueueService.dispatch()` already calls `assess()` on every dispatch attempt before moving the entry to `DISPATCHING`. Because routing compilation now lives inside `assess()`, every dispatch attempt re-inspects the staged artifact and revalidates the current material/topology evidence.

If a previously compiled binding now resolves to another toolhead, the compiler returns `compiled_route_changed`. The queue remains blocked and keeps the previously persisted toolhead for diagnostics; it does not silently rewrite the dispatch decision.

Only after a successful revalidation may the queue persist `DISPATCHING` and invoke adapter `submit()`.

## Normalized blockers

Queue routing blockers map into the existing `PrintAssessmentBlockerCode` boundary:

- plate selection errors -> `unsupported_selection`;
- blocked/unsafe print-plan evidence -> `unsupported_artifact`;
- stale/missing source/topology evidence -> `material_source_unavailable`;
- binding/material/toolhead incompatibilities -> `material_binding_invalid`.

The vendor adapter still performs its own final common-contract assessment after routing succeeds.

## Enqueue idempotency

`toolhead_id` is compiler-owned and is not part of client enqueue intent.

HTTP enqueue replay comparison therefore uses:

- dispatch id;
- artifact identity;
- plate selection;
- requested name;
- logical material index -> physical source slot bindings.

It deliberately ignores only the server-added `toolhead_id`.

This does **not** weaken dispatch idempotency. The Bambu dispatch fingerprint continues to include the compiled toolhead identity, so reusing one `dispatch_id` with a materially different compiled route remains a conflict.

## Non-goals of this slice

This integration does not:

- encode Bambu `nozzle_mapping`;
- change Bambu transport start commands;
- automatically select AMS/external slots;
- automatically substitute filament by color/type;
- start P3 filament accounting;
- enable a new physical print path by itself.

The next Bambu-specific slice must revalidate compiler-owned toolhead identities immediately before native request construction and encode the required nozzle/toolhead mapping without weakening durable idempotency.

## Acceptance criteria

- [x] 3MF routing is compiled before adapter assessment;
- [x] compiled bindings are persisted before adapter assessment;
- [x] missing explicit source bindings block before adapter assessment;
- [x] missing material/topology capabilities block routed 3MF;
- [x] dispatch revalidates persisted routes through the normal assessment gate;
- [x] changed toolhead evidence blocks without rewriting the old compiled route;
- [x] G-code execution remains outside this 3MF routing gate;
- [x] enqueue replay ignores compiler-owned `toolhead_id` but not client-owned source slots;
- [ ] Ruff + Python 3.12/3.13 contract/unit suite green;
- [ ] security, deployment-auth, container and Browser acceptance green;
- [ ] Bambu native nozzle/toolhead mapping gate implemented in the following slice;
- [ ] physical X2D validation remains forbidden until the Bambu native gate is merged and reviewed.
