# ADR 0005: Browser command authentication and deployment trust

- **Status:** Accepted and implemented
- **Date:** 2026-09-04
- **Implementation update:** 2026-09-06
- **Supersedes:** ADR 0004's original browser-auth deferral and tokenless trusted-browser interpretations
- **Related:** AUD-003, AUD-004, AUD-007

## Context

FoxForge exposes browser mutations for printer configuration, queue, inventory and common printer controls. Deployment proxy authentication is useful defense in depth but is not, by itself, cryptographic proof that a request is authorized as a FoxForge operator.

## Decision

### Explicit operator credential

Production browser writes use the deployment-owned `FOXFORGE_COMMAND_TOKEN`.

The browser:

- stores the credential only in JavaScript memory for the current tab;
- never writes it to `localStorage`, `sessionStorage`, IndexedDB, URLs, public DTOs or logs;
- sends it in `Authorization: Bearer`;
- clears it on explicit Lock or HTTP 401;
- returns to locked state after reload/tab lifecycle.

Standalone Docker without a configured token is intentionally read-only for protected commands.

### Tokenless trusted-proxy bootstrap remains disabled

`FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is rejected by production runtime settings.

Umbrel App Proxy, forwarded headers and private container networking are not FoxForge principals. Tokenless `/api/v1/operator-session` does not anonymously issue write credentials.

Any future tokenless bootstrap requires a new/amended ADR defining unspoofable proxy proof, replay/rotation/revocation and representative integration tests.

### Umbrel credential path

Current Umbrel packaging maps the per-app `APP_PASSWORD` to `FOXFORGE_COMMAND_TOKEN`.

For the current Pre-Alpha 5 validation candidate, Umbrel also exposes the app credential through its UI, allowing GUI-only Operator Access without terminal lookup.

The operator enters that same app credential in **Operator Access / Unlock writes**. App Proxy remains an independent outer boundary rather than becoming the application principal.

### Session primitive

The internal short-lived session primitive may remain available for tests/future authenticated providers, but session issuance requires an explicitly authenticated bootstrap credential. Production anonymous bootstrap remains unavailable.

## Current deployment modes

| Deployment | Write behavior |
| --- | --- |
| Standalone Docker + token | explicit memory-only unlock |
| Standalone Docker without token | protected commands disabled |
| Reverse proxy + token | same explicit FoxForge Bearer requirement |
| Umbrel current package | `APP_PASSWORD` -> `FOXFORGE_COMMAND_TOKEN`, shown via Umbrel UI, then memory-only FoxForge unlock |
| Tokenless trusted-browser mode | unsupported |

## Consequences

Positive:

- directly reachable runtime cannot become an anonymous token dispenser;
- Docker/Umbrel use one consistent application authorization model;
- browser credential is not persistently stored by FoxForge;
- future OIDC/proxy providers can resolve into FoxForge principals without changing domain services.

Costs:

- operator unlock is required again after reload until a stronger authenticated session provider exists;
- App Proxy login alone does not silently grant FoxForge write authority;
- physical Umbrel proxy/network behavior remains a separate validation requirement.

## Acceptance criteria

- production rejects tokenless trusted-browser configuration;
- anonymous `/operator-session` cannot issue a credential;
- protected browser commands fail before/at the server boundary when not unlocked;
- browser writes leave no operator credential in persistent web storage;
- 401/Lock clears in-memory authority;
- standalone read-only mode is truthful;
- Umbrel package maps its per-app credential explicitly and exposes it through the intended UI path;
- proxy headers alone cannot authorize a command;
- AUD-003 remains validation-bound until real Raspberry Pi/Umbrel behavior is proven.
