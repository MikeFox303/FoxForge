# Deployment authentication acceptance contract

**Related:** AUD-003, AUD-004, ADR 0005  
**Applies to:** `v0.1.0-alpha.4` release line and current source unless superseded by a later ADR

FoxForge treats deployment authentication as one product contract spanning runtime settings, the browser UI and packaging. A green unit test for the API alone is not enough evidence that an installed deployment has usable write workflows.

## Supported deployment modes

| Mode | Application write credential | Browser protected writes | Expected behavior |
| --- | --- | --- | --- |
| Standalone Docker, token configured | `FOXFORGE_COMMAND_TOKEN` | Available after explicit in-memory unlock | Authorized writes succeed; missing/wrong bearer fails closed. |
| Standalone Docker, token omitted | none | Deliberately unavailable | Reads remain available; protected writes return `command_api_disabled`; browser explains read-only state. |
| Reverse proxy + explicit token | `FOXFORGE_COMMAND_TOKEN` | Same as standalone token mode | Proxy authentication is defense in depth; FoxForge still requires its own bearer. Proxy/forwarding identity headers are not application principals. |
| Tokenless trusted-browser mode | none | Unsupported | Production runtime rejects `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true`; `/api/v1/operator-session` does not anonymously mint credentials. |
| Umbrel `v0.1.0-alpha.4` package | Umbrel `APP_PASSWORD` mapped to `FOXFORGE_COMMAND_TOKEN` | Available after the operator enters the app password in **Unlock writes** | Package definition supplies an explicit ADR-0005-compatible application credential while App Proxy remains a separate defense-in-depth boundary. |

The historical `alpha.3` Umbrel package remains a historical read-only packaging state and is not rewritten. Current deployment documentation describes the `alpha.4` package contract.

## Production-container CI evidence

`.github/workflows/deployment-auth.yml` builds the actual production Dockerfile and validates the runtime contract in containers:

1. **Read-only runtime** — starts without `FOXFORGE_COMMAND_TOKEN`; `/healthz` and reads stay available; a protected inventory mutation returns HTTP 503 with `command_api_disabled`; tokenless `/api/v1/operator-session` returns HTTP 503 with `browser_session_disabled`.
2. **Write-enabled runtime** — starts with an explicit high-entropy command token; a wrong bearer returns HTTP 401; the correct bearer plus idempotency key can execute a real inventory create command; tokenless `/operator-session` remains unavailable.
3. **Representative reverse-proxy boundary** — starts a separate proxy process in front of the production runtime. Representative `X-Forwarded-*` and authenticated-user metadata alone still produce HTTP 401 on protected writes; tokenless `/operator-session` remains disabled; only a valid FoxForge bearer enables the protected write.
4. **Unsafe trusted-session configuration** — a production container started with `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` must fail startup rather than silently becoming a token dispenser.

The browser production-container acceptance suite separately proves that operator credentials remain memory-only and that protected UI paths fail closed when no credential is unlocked.

## Umbrel package software evidence

The companion Store package for `alpha.4` adds a package-level contract on top of the runtime tests:

- exact version `0.1.0-alpha.4` and immutable multi-architecture image digest are pinned;
- Store Compose maps `${APP_PASSWORD}` to `FOXFORGE_COMMAND_TOKEN`;
- representative Compose rendering verifies that the mapping resolves to the supplied app password;
- Umbrel App Proxy remains enabled;
- host networking, privileged mode and Docker socket access are not introduced;
- anonymous image pull and runtime smoke pass for Linux `amd64` and `arm64`;
- first-start config is validated against current schema version 2.

This proves the **software/package bootstrap contract**. It does not prove the actual Umbrel deployment environment on physical Raspberry Pi hardware.

## AUD-004 conclusion

The current FoxForge security model deliberately does **not** trust a reverse proxy as an application principal. ADR 0005 requires an explicit FoxForge bearer for protected browser commands and rejects tokenless trusted-session mode in production. The representative cross-process proxy test proves that forwarding/authentication-style headers do not weaken that boundary.

This satisfies AUD-004 for the current explicit-token model. A future design that introduces cryptographically authenticated tokenless proxy bootstrap would be a new security contract and must receive a new/amended ADR plus its own representative tests before replacing this decision.

## AUD-003 boundary

The `alpha.4` package removes the previous missing-bootstrap software gap, but **AUD-003 remains `VALIDATION REQUIRED`**.

CI does not prove:

- physical Raspberry Pi 5/UmbrelOS install, restart and persistence behavior;
- successful protected browser writes through the actual deployed Umbrel App Proxy path;
- direct-backend fail-closed behavior in the real deployment topology;
- X2D/OpenKE reachability from the actual Umbrel container/network environment;
- upgrade behavior between the relevant installed package versions;
- representative SSE reconnect/resync through the real proxy path.

Those observations must be recorded through the physical/deployment evidence gate before AUD-003 can be resolved.

## Release/package gate

For the `alpha.4` Umbrel package and future package releases:

- identify the package as **write-capable** or **read-only** explicitly;
- if write-capable, document the FoxForge application credential/bootstrap source;
- pin the exact guarded FoxForge release image by immutable digest;
- run package/Compose validation with representative platform variables;
- prove the application credential mapping at Compose-render time without relying on App Proxy identity as the principal;
- exercise anonymous pull/runtime smoke on every published architecture;
- verify tokenless `/api/v1/operator-session` remains unavailable;
- record real physical/deployment evidence separately before changing AUD-003 to `RESOLVED`.
