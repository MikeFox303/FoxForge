# Common printer job control

**Status:** implemented as P1 and released in `v0.1.0-alpha.4`; automated validation green, physical validation pending  
**Capability:** `foxforge.job_control` v1  
**Actions:** pause, resume, cancel

## Context

FoxForge needs common operator controls for an already-running print without allowing the web UI or application layer to know Bambu MQTT commands, Moonraker HTTP endpoints, or vendor model names. Pause/resume/cancel are genuinely common operations, but they are safety-sensitive remote side effects: a stale UI must never pause or cancel whichever job happens to be running now.

The P1 design therefore treats job control as a typed capability attached to a concrete `PrinterAdapter`, and every command names the exact vendor job identity observed by FoxForge before the operator acts.

## Domain contract

`JobControlCapability` exposes:

- a `JobControlDescriptor` advertising supported common actions;
- `assess(JobControlRequest)` for fail-closed eligibility;
- `execute(JobControlRequest)` returning a `JobControlReceipt` only after the adapter transport reports acceptance.

`JobControlRequest` contains two durable pieces of intent:

- `control_id`: logical FoxForge identity for one control command;
- `expected_vendor_job_id`: the exact active vendor job the operator saw.

A command is blocked when the printer is offline, the snapshot is stale, there is no active job, the active job lacks a vendor identity, the identity changed, the action is unsupported, or the job state does not allow that action.

State rules in v1 are:

| Action | Allowed job states |
| --- | --- |
| Pause | `PRINTING` |
| Resume | `PAUSED` |
| Cancel | `PREPARING`, `PRINTING`, `PAUSED` |

The common capability does not infer vendor behavior from a model name. Adapters explicitly advertise the capability.

## Adapter mapping

### Bambu Lab

`BambuJobControlCapability` maps:

- pause → Bambu print command `pause`;
- resume → Bambu print command `resume`;
- cancel → Bambu print command `stop`.

`BambuLanTransport` checks the current native vendor job identity again immediately before publishing the command. MQTT publish/response ambiguity is normalized to `PrinterErrorCode.INDETERMINATE` and is never marked retryable.

### Moonraker/Klipper

`MoonrakerJobControlCapability` maps:

- pause → `POST /printer/print/pause`;
- resume → `POST /printer/print/resume`;
- cancel → `POST /printer/print/cancel`.

The controlled HTTP transport checks the current filename/vendor job identity before the request. Network errors, timeouts, or server-side failures after the request may have reached Moonraker are treated as `INDETERMINATE` rather than as safe retries.

## HTTP command contract

P1 exposes:

```text
POST /api/v1/printers/{printer_id}/job-control
Authorization: Bearer ...
Idempotency-Key: <HTTP command identity>
Content-Type: application/json

{
  "controlId": "<UUID>",
  "action": "pause | resume | cancel",
  "expectedVendorJobId": "<opaque vendor job id>"
}
```

The route requires ADR 0004 permission `printer.control` and participates in the same fail-closed command audit as printer configuration, inventory, and queue writes.

`controlId` and HTTP `Idempotency-Key` are intentionally different identities. `controlId` identifies the logical device-side command. `Idempotency-Key` identifies one externally callable HTTP attempt/replay identity.

For a conclusive result the idempotency reservation becomes `COMPLETED`. Replaying the same HTTP key does not execute the adapter again. Reusing one HTTP key with a different payload is rejected as an idempotency conflict.

## Ambiguous outcomes

Job-control side effects are not blindly retried.

If a transport cannot prove whether pause/resume/cancel reached the printer, the adapter returns `INDETERMINATE`. The HTTP idempotency reservation deliberately remains `STARTED`. A replay with the same HTTP key returns `job_control_reconciliation_required` and does not invoke the adapter again.

The browser reacts by invalidating the fleet snapshot and locking the current controls behind an uncertainty warning. Ordinary polling or a changed `observedAt` timestamp is not enough to unlock another side effect; controls remain locked until the observed job state or vendor job identity changes conclusively. It does not automatically generate a new command identity or silently resend the side effect.

This is deliberately stricter than treating a timeout as a normal retryable failure. For cancel in particular, uncertainty must be resolved by live/physical state before another intentional control command.

## Frontend contract

The fleet read model advertises `foxforge.job_control` v1 with `supportedActions` and `requiresVendorJobIdentity`. The React cockpit renders controls from this capability only:

- printing: Pause and Cancel when advertised;
- paused: Resume and Cancel when advertised;
- preparing: Cancel when advertised;
- stale/offline/no vendor job identity: no actionable control is sent.

Cancel requires explicit operator confirmation. The UI does not add Bambu-only controls to Moonraker printers or vice versa.

## Release status

P1 was shipped in `v0.1.0-alpha.4`. The guarded release workflow validated the exact frozen release commit before publishing the multi-architecture image and pre-release.

Release inclusion is not physical validation. The same hardware evidence requirements below remain binding.

## Acceptance criteria

P1 is code-complete because all of the following hold:

1. Bambu and Moonraker adapters expose the same typed `JobControlCapability` without application/API imports of vendor transport types.
2. Pause/resume/cancel are guarded by exact vendor job identity and current normalized state.
3. Bambu LAN and Moonraker transports implement the corresponding native commands and normalize ambiguous outcomes to non-retryable `INDETERMINATE`.
4. `/api/v1/fleet` advertises job-control capability metadata rather than requiring frontend vendor inference.
5. The authenticated command endpoint requires `printer.control`, `Idempotency-Key`, request validation, durable idempotency, normalized errors and command audit.
6. Same-key completed replay executes the remote side effect at most once.
7. Same-key unresolved replay never executes the remote side effect again.
8. The React printer cockpit exposes only state/capability-valid controls and requires confirmation for cancel.
9. EN/RU/UK job-control copy remains key-identical.
10. Backend tests/Ruff and frontend typecheck/Vitest/build plus unified-container smoke remain green.
11. Documentation distinguishes automated/code validation from physical X2D and OpenKE validation.

## Physical validation still required

Code-complete and released P1 does not by itself prove printer-side behavior on real hardware. Before production-ready claims, the hardware validation matrix must cover pause, observed paused state, resume, observed resumed state, cancel, completion/cancellation state, network loss during each command, and server restart/reconnect on both a representative Bambu target and a Moonraker/OpenKE target.
