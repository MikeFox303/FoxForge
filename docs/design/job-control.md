# Common job-control capability

- **Status:** implemented and released; physical printer validation pending
- **Updated:** 2026-09-06
- **Capability:** `foxforge.job_control` / v1
- **Related:** [ADR 0001](../adr/0001-printer-adapter-architecture.md), [ADR 0004](../adr/0004-command-api-security.md)

## Purpose

Pause, Resume and Cancel are common only when they target the exact currently observed remote job and preserve uncertainty safely. They are therefore a typed capability rather than methods on the base `PrinterAdapter`.

## Eligibility

A control request is allowed only when:

- the printer exposes `JobControlCapability`;
- snapshot state is fresh/connected;
- an active job exists;
- that job has a non-empty vendor job identity;
- requested action is valid for the observed job state;
- the request's expected vendor job identity matches the current observed job exactly.

Stale/mismatched state fails closed before a command is sent.

Typical action state rules:

- Pause: active printing/preparing states supported by the adapter;
- Resume: paused;
- Cancel: active/preparing/printing/paused states supported by the adapter.

The adapter remains responsible for mapping common action to vendor protocol semantics.

## Identities

`controlId` identifies one logical job-control action and is distinct from HTTP `Idempotency-Key`.

The HTTP command layer may replay the original result for one request, while the capability-level `controlId` prevents an accidental new logical control action from being inferred from transport retries.

## Outcomes

The capability reports a normalized outcome such as acknowledged/accepted or `INDETERMINATE` when the side effect may have occurred but cannot be confirmed.

`INDETERMINATE` is non-retryable by default. The browser refreshes/observes printer state; it does not silently resend Pause/Resume/Cancel.

## Vendor mapping

Current implementations:

- Bambu adapter maps the common action to Bambu MQTT command behavior;
- Moonraker adapter maps it to Moonraker control endpoints;
- unsupported printers expose no common capability.

Vendor-native response DTOs/errors do not leave their adapter.

## HTTP/UI boundary

Protected job-control routes require `printer.control`, explicit Operator Access authentication and idempotency/audit handling from ADR 0004/0005.

The UI:

- shows controls only for supported/current state;
- sends the exact observed vendor job identity;
- requires confirmation for Cancel;
- refreshes state after success or ambiguity;
- does not downgrade `INDETERMINATE` into Retry.

## Physical validation

Real Bambu X2D and Moonraker/OpenKE tests must prove action/state mapping and stale-job protection before production-ready support is claimed. For the active Bambu milestone see [Pre-Alpha 5 validation](../testing/pre-alpha-5-bambu-physical-validation.md).
