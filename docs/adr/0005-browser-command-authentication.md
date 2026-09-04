# ADR 0005: Browser command authentication and deployment trust

- **Status:** Accepted
- **Date:** 2026-09-04
- **Decision owners:** FoxForge maintainers
- **Supersedes:** ADR 0004 sections that deferred browser mutations and any interpretation that `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` alone is sufficient proof of a trusted proxy
- **Related audit findings:** AUD-003, AUD-004, AUD-007

## Context

FoxForge now exposes authenticated browser mutations for printer configuration, queue operations, inventory and common printer controls. The first browser implementation issued a short-lived bearer from `/api/v1/operator-session` whenever `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` was enabled. That flag expressed operator intent but did not cryptographically prove that the request had crossed an authenticating reverse proxy.

A directly reachable LAN client could therefore obtain an operator session if a deployment enabled the flag incorrectly. Standard standalone Compose also did not configure a browser write credential, so the UI could look write-capable while the runtime could not authenticate it.

## Decision

### 1. Production browser writes use an explicit operator command token

`FOXFORGE_COMMAND_TOKEN` remains the deployment-owned command credential. A browser operator explicitly unlocks write controls by entering this token.

The browser:

- stores the token only in JavaScript memory for the current tab;
- never writes it to `localStorage`, `sessionStorage`, IndexedDB, URLs, public API DTOs or logs;
- sends it only in the `Authorization: Bearer` header;
- clears it when the operator locks the UI or after an HTTP 401 response;
- fails closed before network access when no in-memory credential is available.

A standalone Docker deployment that omits `FOXFORGE_COMMAND_TOKEN` is intentionally read-only. The UI must say so when an operator attempts to unlock writes.

### 2. Tokenless trusted-proxy bootstrap is disabled in the production runtime

`FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is rejected by `RuntimeSettings` until FoxForge has a cryptographically authenticated reverse-proxy assertion contract.

Merely being behind Umbrel App Proxy, receiving forwarding headers, or being on a private Docker network is not enough evidence to mint an application operator credential.

Future tokenless bootstrap requires a new or amended ADR that defines at minimum:

- the exact proxy assertion format;
- a secret/signature or equivalent unspoofable proof;
- direct-backend reachability rules;
- replay/rotation/revocation behavior;
- representative Umbrel proxy integration tests.

### 3. `/api/v1/operator-session` is not an anonymous credential dispenser

The session primitive remains available to application tests and future authenticated bootstrap providers, but `BearerCommandSecurity.issue_browser_session()` requires an explicit operator bootstrap token. The existing HTTP route does not supply one, so production tokenless calls fail closed.

This avoids silently trusting deployment metadata while preserving a narrow path for a later explicit session bootstrap design.

### 4. Official deployment modes must state write availability truthfully

Standalone Docker:

- `deployment/docker/.env.example` documents `FOXFORGE_COMMAND_TOKEN`;
- Compose passes it to the runtime;
- omitting it is a supported read-only mode.

Umbrel:

- the currently published immutable `v0.1.0-alpha.3` package remains historical and is not rewritten;
- the next FoxForge package must either configure a real operator bootstrap accepted by this ADR or explicitly ship as read-only for writes;
- App Proxy authentication is defense in depth, not an application principal.

### 5. Session/token lifecycle

The alpha operator token is deployment-managed and rotated by changing `FOXFORGE_COMMAND_TOKEN` and restarting the runtime. Browser copies are memory-only and disappear on tab close/reload or explicit Lock.

Short-lived application sessions may be reintroduced after authenticated bootstrap exists. Multi-user identities/OIDC remain future work and must continue to resolve into FoxForge principals rather than entering domain services directly.

## Alternatives considered

### Trust `X-Forwarded-*` headers

Rejected. A directly reachable client can spoof them unless a cryptographic or network-enforced trust boundary is proven.

### Keep tokenless `TRUSTED_BROWSER_SESSIONS=true`

Rejected. The flag proves configuration intent, not request authenticity.

### Store the command token in localStorage

Rejected. Long-lived browser persistence increases exposure to XSS and shared-browser leakage.

### Disable browser writes entirely

Rejected for standalone use because an explicit in-memory operator credential provides a workable fail-closed path without weakening API authentication.

## Consequences

### Positive

- Directly exposed runtimes cannot become anonymous operator-token dispensers by toggling one flag.
- Standalone Docker has a complete documented write-authentication path.
- Browser credentials are not persisted by the application.
- Existing command permissions/idempotency/audit semantics remain unchanged.
- Future Umbrel/OIDC integration can add a provider without changing printer/queue/inventory domain contracts.

### Costs

- Operators must enter the command token after page reload until a stronger authenticated session provider exists.
- The next Umbrel package needs an explicit decision for write bootstrap rather than assuming App Proxy is sufficient.
- The legacy `/operator-session` route remains present but intentionally unavailable to anonymous production requests.

## Acceptance criteria

- production runtime rejects `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true`;
- tokenless `/api/v1/operator-session` does not issue credentials;
- an explicitly authenticated session can only be minted after the correct static operator bootstrap token is supplied at the security boundary;
- browser commands fail before network access when no token is unlocked;
- the browser stores no operator credential in persistent web storage;
- 401 clears the in-memory credential;
- standalone Compose exposes `FOXFORGE_COMMAND_TOKEN` configuration and documents read-only behavior when absent;
- exactly one Add Printer launcher tree is rendered and remains available on narrow layouts;
- backend/frontend/container tests remain green;
- Umbrel write availability is not claimed until its package has a tested bootstrap compatible with this ADR.
