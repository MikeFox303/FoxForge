# Deployment authentication acceptance contract

- **Status:** implemented current contract
- **Updated:** 2026-09-06
- **Related:** AUD-003, AUD-004, ADR 0005

FoxForge treats deployment authentication as one product contract spanning runtime configuration, browser behavior and packaging.

## Supported modes

| Mode | FoxForge write credential | Browser behavior |
| --- | --- | --- |
| Standalone Docker, token configured | `FOXFORGE_COMMAND_TOKEN` | Protected writes unlock after explicit in-memory Operator Access. |
| Standalone Docker, token omitted | none | Reads remain available; protected writes fail closed as disabled. |
| Reverse proxy + explicit token | `FOXFORGE_COMMAND_TOKEN` | Proxy auth is defense in depth; FoxForge still requires its Bearer. |
| Tokenless trusted-browser mode | none | Unsupported; production rejects `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true`. |
| Umbrel current package | `APP_PASSWORD` mapped to `FOXFORGE_COMMAND_TOKEN` | Operator enters the app credential shown by Umbrel; browser state remains memory-only. |

Tokenless `/api/v1/operator-session` does not anonymously mint credentials.

## Production-container contract

The deployment-auth workflow proves representative production behavior:

1. read-only runtime starts without a command token and rejects protected writes;
2. write-enabled runtime rejects an incorrect bearer and accepts the configured bearer/idempotency identity;
3. representative proxy headers/authenticated-user metadata do not become FoxForge application principals;
4. unsafe trusted-browser configuration fails startup.

The browser acceptance layer separately checks that operator credentials remain memory-only and protected UI paths fail closed when locked.

## Umbrel contract

The current Store package is Pre-Alpha 5 validation Candidate 5:

```text
my3d-foxforge 0.1.0-alpha.4.3-umbrel.5
source 0351c659f2d2845fb83bc0b1802c4d9ebeeef1f2
image ghcr.io/mikefox303/foxforge:sha-0351c65@sha256:00c699effbe9b245a4916a8c301df5b67435d75dd42fad02cc5bbf0ca51aec39
Store commit 16d57c486ce8e2b26abd5c7e9480188d95f080cb
```

The package:

- maps the Umbrel per-app password to `FOXFORGE_COMMAND_TOKEN`;
- exposes the app credential through the Umbrel UI for GUI-only operator unlock;
- keeps App Proxy enabled as a separate boundary;
- does not require host networking, privileged mode or Docker socket access;
- pins the immutable Candidate 5 image digest;
- passed package-contract and public-runtime smoke checks on both `linux/amd64` and `linux/arm64` before Store merge.

This proves package/bootstrap intent and reproducibility. It does not prove real Raspberry Pi/network/printer behavior, and therefore does not by itself close AUD-003 or authorize a physical print.

## AUD-004 conclusion

AUD-004 remains resolved for the explicit-token model: forwarding/proxy identity does not authorize FoxForge commands. Any future tokenless proxy bootstrap requires a new/amended ADR and representative cryptographically authenticated tests.

## AUD-003 boundary

AUD-003 remains `VALIDATION REQUIRED` until exact Candidate 5 demonstrates on representative Raspberry Pi/Umbrel:

- install/restart/persistence;
- protected browser writes through the actual App Proxy path;
- direct-backend protected writes fail closed without the FoxForge credential;
- X2D and required printer-network reachability;
- upgrade behavior where applicable;
- representative SSE reconnect/resync.

The Pre-Alpha 5 runbook requires this deployment/auth evidence inside the no-print gate before the first physical Start.

## Package/release requirements

Every write-capable deployment package must:

- declare the application credential source;
- keep browser credentials memory-only;
- pin or otherwise identify the exact immutable image under test/release;
- validate Compose/runtime startup on published architectures;
- prove tokenless operator-session remains disabled;
- preserve FoxForge authorization independently of proxy identity;
- record real physical/deployment evidence separately from CI.
