# Application-managed printer setup

- **Status:** implemented in current `main`
- **Updated:** 2026-09-06
- **Related:** ADR 0004, ADR 0005, [printer setup security](printer-setup-security.md), [reconnect supervision](reconnect-supervision.md)

## Purpose

FoxForge owns printer configuration as an application workflow. `/data/config.json` and SecretStore are private restart persistence, not the primary operator interface.

The governing setup invariant is:

> **Validate the effective printer configuration before durable state is created or a known-good configuration is replaced.**

## Bambu Lab workflow

1. Open **Add Printer**.
2. Choose **Bambu Lab (LAN)**.
3. Optionally discover candidates on an explicitly selected private IPv4 subnet, or use manual entry.
4. Confirm printer ID/name, host, normalized serial/model and LAN access code.
5. Run the live connection preflight.
6. Persist and attach the adapter only after preflight succeeds.

Discovery is candidate-only. It does not authenticate or configure a printer by itself.

Current discovery is deliberately conservative:

- IPv4 RFC1918 networks only;
- `/22` or smaller;
- bounded concurrency/timeouts;
- expected Bambu MQTT 8883 and FTPS 990 ports must both be reachable;
- SSDP metadata may provide serial, display name and model;
- manual setup remains available when container/LAN topology prevents discovery.

## Moonraker/Klipper workflow

1. Open **Add Printer**.
2. Choose **Klipper / Moonraker**.
3. Enter the Moonraker base URL and API key only when required.
4. Run the same live preflight.
5. Persist and attach only after validation succeeds.

Moonraker destination policy remains governed by the production endpoint security contract in [moonraker-http-transport.md](moonraker-http-transport.md).

## Add safety

`RuntimePrinterManager.add()` performs a disposable connection test before creating durable printer state.

If the preflight fails:

- no printer configuration is appended to runtime persistence;
- no dead adapter remains in the fleet;
- credentials are not left behind as a configured printer;
- the API returns a normalized, sanitized setup failure.

After preflight, the real runtime adapter is attached and connected. Persistence occurs only after that live attach succeeds.

## Update safety

Update uses the same standard as Add.

- omitted credentials may reuse the existing stored secret;
- the effective replacement is preflighted before the current configuration is changed;
- replacement persistence/secrets and runtime adapter are applied as one guarded workflow;
- if the replacement cannot attach/connect, FoxForge restores the previous config, secrets and adapter and attempts to reconnect the prior working printer.

A bad host, serial, access code or API key must not destroy a known-good configuration simply because the operator pressed Update.

## Idempotency and errors

State-changing setup commands use the normal authenticated/idempotent command boundary.

Terminal sanitized Add/Update connection failures are durable replay results. Repeating the same HTTP idempotency key and unchanged request returns the same logical failure without running the failed setup again. Reusing a key with a changed fingerprint remains an idempotency conflict.

Unexpected adapter implementation exceptions are normalized before they reach operator-facing responses. Raw Python tracebacks, access codes, API keys and vendor payloads are not public setup diagnostics.

## Runtime lifecycle

```text
React setup UI
      |
authenticated /api/v1/printers commands
      |
PrinterManagementService / RuntimePrinterManager
      |
preflight -> AdapterRegistry -> temporary adapter
      |
persist SecretStore/config + attach dynamic FleetService adapter
      |
reconnect supervisor + normalized fleet read model
```

Configured printers may be reconnected, updated or removed without restarting FoxForge. Removing a printer changes FoxForge state only; it does not modify the physical printer.

## Credentials

Printer credentials are write-only from the browser perspective. Configuration reads expose only whether a secret is configured. See [printer-setup-security.md](printer-setup-security.md).

## Current scope

Implemented:

- Bambu and Moonraker live connection testing;
- Bambu discovery/manual fallback;
- Add/Update/Remove/Reconnect without server restart;
- restart-safe persistence;
- Add test-before-save;
- Update test-before-save and rollback;
- deterministic terminal failure replay;
- normalized live fleet/material-system state;
- common job control through separate capability-driven commands;
- reconnect supervision and diagnostics.

Not yet claimed as physically validated:

- complete X2D/AMS 2 Pro physical acceptance;
- complete OpenKE/Moonraker physical acceptance;
- Bambu cloud login;
- Virtual Printer;
- deep AMS drying/K-profile/HMS/dual-nozzle workflows.

## Acceptance criteria

- failed Add does not create durable printer state;
- failed Update preserves/restores the previous working configuration;
- successful Add/Update survives restart;
- same-key failed setup replay does not re-execute the connection attempt;
- credentials never appear in configuration reads or sanitized diagnostics;
- discovery cannot persist an unauthenticated candidate;
- vendor protocol types do not cross the application boundary;
- backend, browser and deployment-auth regression suites remain green.
