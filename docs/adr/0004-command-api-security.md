# ADR 0004: Command API security and idempotency

- **Status:** Accepted
- **Date:** 2026-09-04
- **Decision owners:** FoxForge maintainers
- **Related:** ADR 0001, ADR 0002, `docs/design/public-api-v1.md`, queue dispatch/idempotency design, inventory foundation

## Context

FoxForge `v0.1.0-alpha.2` exposes a deliberately read-only HTTP API. The backend already contains application services that can enqueue and dispatch prints, reconcile uncertain queue entries, and mutate filament inventory, but those operations are intentionally not exposed over HTTP.

Remote writes have a materially different risk profile from snapshots. A duplicated request can start a second print or corrupt accounting; an unauthenticated request can control physical equipment; a timeout can leave the caller unsure whether a side effect occurred; and a browser deployment can sit behind Umbrel App Proxy while standalone Docker deployments may be reachable directly on a LAN.

The next API phase therefore needs a security and command contract before any printer, queue or inventory mutation is enabled.

## Decision

### 1. Existing read API remains compatible; command API is separately protected

`GET /healthz` and the existing `/api/v1` read endpoints keep their current alpha behavior so the shipped frontend remains compatible.

Every HTTP operation that can mutate FoxForge state or cause an external side effect is a **command** and must pass the command-security boundary before an application service is called.

Command routes must never become implicitly enabled merely because the server can reach a printer.

### 2. Command authentication is explicit and fail-closed

The first implementation uses a deployment-supplied bearer token.

- Configuration name: `FOXFORGE_COMMAND_TOKEN`.
- The token is a runtime secret, not part of `config.json`, SQLite business data, API DTOs, diagnostics responses or logs.
- Empty/unset token means the command API is disabled.
- Tokens are accepted only through `Authorization: Bearer <token>`.
- Query-string tokens and form-field tokens are rejected by design.
- Token comparison uses a constant-time comparison primitive.
- A command request with no configured command credential receives a normalized `503 command_api_disabled` response.
- Missing/invalid credentials receive `401 unauthorized` with `WWW-Authenticate: Bearer`.

Umbrel App Proxy authentication remains an additional outer deployment boundary. FoxForge does **not** treat forwarded headers as proof of authentication in this phase. A future trusted-proxy/OIDC/session provider requires its own explicit decision because trusting spoofable proxy headers would weaken standalone deployments.

### 3. Authentication and authorization are represented by FoxForge principals

HTTP authentication resolves a request to a FoxForge-owned principal instead of passing raw tokens into application services.

The first bearer-token provider produces an operator principal with a stable non-secret identifier and an explicit permission set. Initial permission names are:

- `queue.write`
- `printer.control`
- `inventory.write`
- `admin.config`

The static alpha operator token may grant the first three permissions, but remote printer credential/configuration mutation remains out of scope and `admin.config` is not enabled merely by having the operator token.

Handlers declare the permission they require. Authorization failure is `403 forbidden`. Application/domain services remain usable internally without HTTP credentials; authentication is an inbound API concern, not a dependency injected into queue or printer-domain code.

### 4. Every command has a request ID

Each command request receives a FoxForge request ID.

- A syntactically valid client `X-Request-Id` may be preserved; otherwise FoxForge generates a UUID.
- The request ID is returned in `X-Request-Id` and in normalized error payloads.
- Request IDs are diagnostic correlation identifiers, **not** idempotency keys.

Secrets, bearer credentials and complete printer credential payloads must never be included in request logging.

### 5. Side-effecting commands require durable idempotency

Every externally callable command that can create a durable resource, mutate accounting or trigger a printer side effect must define an idempotency policy.

The default HTTP mechanism is `Idempotency-Key`:

- required for non-read commands unless a route documents a stronger intrinsic idempotency identity;
- scoped to authenticated principal + command operation;
- length/character bounded and treated as opaque;
- persisted before the command crosses a side-effect boundary;
- associated with a canonical request fingerprint;
- retained with the committed normalized result long enough for safe retry across process restart.

Replay rules:

1. same key + same command + same fingerprint -> return/reconcile the same logical result; do not repeat the side effect;
2. same key + changed request fingerprint -> `409 idempotency_conflict`;
3. same key while a previous execution is durably in progress -> do not start a second execution; return a normalized conflict/in-progress result;
4. process failure after an external side effect but before a confirmed outcome must preserve an uncertain state rather than permitting blind retry.

Queue dispatch keeps its stronger existing `dispatch_id`, persisted `DISPATCHING` state and `INDETERMINATE` reconciliation semantics. The HTTP idempotency layer must compose with those invariants rather than replace them.

Inventory adjustment commands may pass the HTTP idempotency identity into the existing durable inventory ledger, which already rejects conflicting replays.

### 6. Commands validate JSON before calling application services

Command handlers accept only explicit JSON schemas owned by the API layer.

- `Content-Type: application/json` is required when a JSON body is expected.
- Unknown or malformed required fields are rejected before side effects.
- IDs are parsed as typed UUIDs where the application contract uses UUIDs.
- Decimal filament mass is received as decimal strings, never binary JSON floats as the authoritative value.
- Body and selected header sizes are bounded.
- Vendor transport DTOs, filesystem paths and secrets are never accepted merely because an internal adapter understands them.

Uploads/print artifacts require a separate bounded upload contract; a client-provided server filesystem path is never accepted as a public print command.

### 7. HTTP errors are normalized and do not leak vendor exceptions

Command failures use a stable envelope:

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "safe human-readable summary",
    "requestId": "uuid",
    "retryable": false
  }
}
```

Optional structured `details` may contain safe validation fields, but never raw credentials, stack traces, MQTT topics, FTPS paths or vendor exception objects.

Baseline status mapping:

- `400` invalid request / malformed command;
- `401` unauthenticated;
- `403` authenticated but not permitted;
- `404` target resource not found;
- `409` state conflict, busy/reconciliation/idempotency conflict;
- `413` request/upload too large;
- `415` unsupported media type;
- `422` well-formed but unsupported command semantics when appropriate;
- `503` command API disabled or required service unavailable;
- `504` normalized upstream timeout when no safer application-state response exists;
- `500` only for unexpected FoxForge failures, with no traceback in the response.

A command whose outcome is `INDETERMINATE` is represented by the durable application resource/state that requires reconciliation; the HTTP layer must not turn it into a retryable generic error.

### 8. Audit is a command invariant, not ordinary debug logging

Before broad remote writes are considered complete, command execution must produce structured audit records containing at least:

- request ID;
- principal ID;
- action;
- target resource identity where applicable;
- idempotency identity or a non-secret digest of it;
- accepted/completed/conflict/denied outcome;
- normalized error code where applicable;
- UTC timestamp.

Audit records must not store bearer tokens or printer credentials. The initial implementation may introduce the audit store alongside the first mutation endpoints, but no mutation phase is considered complete without tests for its required audit behavior.

### 9. Browser write controls remain disabled until browser authentication is defined

A bearer token is suitable for API clients and automation, but FoxForge will not silently place a long-lived command token into frontend source, build artifacts, URLs or public read responses.

Therefore the React UI keeps mutation controls disabled until a browser-safe authentication/session flow is explicitly implemented. Umbrel App Proxy alone is not converted into an application principal by trusting arbitrary forwarded headers.

### 10. Write API remains narrow and application-service driven

When commands are added, they call FoxForge application services and typed capabilities. They do not call concrete Bambu/Moonraker transports, SQLite tables or frontend models directly.

The planned sequence is:

1. command auth/request/error/idempotency foundation;
2. inventory mutations with durable accounting idempotency;
3. queue enqueue/dispatch/reconcile operations using existing queue safety invariants;
4. common printer pause/resume/cancel only where a common typed capability exists;
5. deep Bambu controls through explicit vendor-extension APIs and permissions;
6. printer credential/configuration writes only after a separate secret-management/admin contract.

## Alternatives considered

### Rely only on Umbrel App Proxy

Rejected as the application security model. It would not protect standalone Docker/API use, would couple command semantics to one deployment platform and could encourage unsafe trust of forwarded headers.

Umbrel App Proxy remains valuable defense in depth.

### Enable commands without application authentication on private LANs

Rejected. LAN reachability is not an authorization boundary for physical printer control or durable inventory changes.

### Put the bearer token in `config.json`

Rejected for the first implementation. Printer configuration and API authentication have different lifecycles and exposure risks. The command token stays in deployment secret/environment configuration.

### Use browser cookies immediately

Deferred. Cookie sessions require login/bootstrap, CSRF rules, expiration/rotation and secure proxy semantics. They should be designed as a browser-auth phase rather than improvised to unblock commands.

### Treat retries as harmless because POST failed

Rejected. Network failure does not prove that a printer or database side effect did not occur. Durable idempotency and explicit uncertain states are required.

## Consequences

### Positive

- Remote writes become opt-in and fail closed.
- Existing alpha read UI remains compatible.
- Standalone Docker and Umbrel share the same FoxForge command semantics.
- Queue `INDETERMINATE` safety is preserved end to end.
- Inventory and future queue commands get a common replay/error model.
- Security does not leak vendor concerns into application/domain layers.
- Future OIDC/session/trusted-proxy providers can replace authentication without changing command services.

### Costs

- Browser mutations remain disabled until a session design exists.
- Durable HTTP idempotency/audit infrastructure adds persistence and tests before user-visible write features.
- Static bearer tokens require operators to provision and rotate secrets manually in the alpha phase.
- Write routes must implement stricter validation than internal service calls.

## Acceptance criteria for the next implementation phase

- command security code has no imports from concrete Bambu/Moonraker adapter packages;
- unset `FOXFORGE_COMMAND_TOKEN` fails closed for command routes;
- valid/invalid bearer token behavior is tested without logging the secret;
- constant-time credential comparison is used;
- request IDs are generated/preserved and returned consistently;
- stable normalized error envelopes are tested;
- a durable command-idempotency store has replay/conflict/restart tests before non-intrinsically-idempotent HTTP mutations are exposed;
- existing read endpoints and frontend remain backward compatible;
- no wildcard CORS is introduced;
- command routes never accept local filesystem paths or vendor transport payloads;
- Python 3.12 and 3.13 backend gates remain green.

## Migration plan

1. Merge this ADR and make it discoverable from the docs index.
2. Add API security primitives: principal/permissions, bearer-token provider, request ID and normalized error response helpers.
3. Add durable command idempotency + audit persistence boundaries with SQLite implementations and restart tests.
4. Expose the first narrow inventory command endpoints and map existing inventory idempotency/conflict errors.
5. Add queue mutation endpoints that reuse durable queue `dispatch_id` and reconciliation semantics; never add a generic blind `retry print` route.
6. Define a browser-safe session/bootstrap design before enabling React mutation controls.
7. Add common printer control routes only for typed capabilities; add Bambu-specific controls under explicit vendor extension namespaces.
8. Keep physical X2D/OpenKE/Raspberry Pi validation as a separate evidence track; this ADR does not claim hardware validation.
