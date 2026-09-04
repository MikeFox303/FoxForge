# Deployment authentication acceptance contract

**Related:** AUD-003, AUD-004, ADR 0005  
**Applies to current source after `v0.1.0-alpha.3`**

FoxForge treats deployment authentication as one product contract spanning runtime settings, the browser UI and packaging. A green unit test for the API alone is not enough evidence that an installed deployment has usable write workflows.

## Supported source deployment modes

| Mode | Application write credential | Browser protected writes | Expected behavior |
| --- | --- | --- | --- |
| Standalone Docker, token configured | `FOXFORGE_COMMAND_TOKEN` | Available after explicit in-memory unlock | Authorized writes succeed; missing/wrong bearer fails closed. |
| Standalone Docker, token omitted | none | Deliberately unavailable | Reads remain available; protected writes return `command_api_disabled`; browser must explain read-only state. |
| Reverse proxy + explicit token | `FOXFORGE_COMMAND_TOKEN` | Same as standalone token mode | Proxy authentication is defense in depth; FoxForge still requires its own bearer. |
| Tokenless trusted-browser mode | none | Unsupported | Production runtime rejects `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true`; `/api/v1/operator-session` does not anonymously mint credentials. |
| Published Umbrel `v0.1.0-alpha.3` package | no ADR-0005-compatible bootstrap in Store Compose | Not claimed as a validated write-capable deployment | Historical install remains available for controlled alpha testing; protected browser writes are not a supported deployment claim. |
| Future Umbrel package | TBD by package/release work | Must be explicit | It must either configure/test an ADR-0005-compatible application credential/bootstrap or deliberately expose a truthful read-only mode. |

## CI evidence

`.github/workflows/deployment-auth.yml` builds the actual production Dockerfile and validates the runtime contract in containers:

1. **Read-only runtime** — starts without `FOXFORGE_COMMAND_TOKEN`; `/healthz` and reads stay available; a protected inventory mutation returns HTTP 503 with `command_api_disabled`; tokenless `/api/v1/operator-session` returns HTTP 503 with `browser_session_disabled`.
2. **Write-enabled runtime** — starts with an explicit high-entropy command token; a wrong bearer returns HTTP 401; the correct bearer plus idempotency key can execute a real inventory create command; tokenless `/operator-session` still remains unavailable.
3. **Unsafe trusted-session configuration** — a production container started with `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` must fail startup rather than silently becoming a token dispenser.

The browser production-container acceptance suite separately proves that operator credentials remain memory-only and that protected UI paths fail closed when no credential is unlocked.

## What CI does not prove

This workflow is not evidence that Umbrel App Proxy itself is an application authentication principal. It also does not prove physical Raspberry Pi networking or real-printer reachability.

AUD-003/AUD-004 may be closed only after a representative future Umbrel/package path is exercised with the exact packaged environment and its write/read-only behavior matches this matrix. Until then those findings remain deployment validation work, not software-design gaps.

## Release/package gate

Before publishing a future FoxForge Umbrel package:

- identify whether the package is **write-capable** or **read-only**;
- if write-capable, document where the FoxForge application credential/bootstrap comes from;
- run package validation with the exact environment/proxy assumptions used by the Store Compose;
- exercise Add Printer and at least one other protected command through the packaged browser path;
- verify direct tokenless `/api/v1/operator-session` does not issue a credential;
- record the evidence in the remediation tracker and project status before changing AUD-003/AUD-004 to `RESOLVED`.
