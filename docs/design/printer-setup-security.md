# Printer setup security boundary

- **Status:** implemented production-alpha contract
- **Updated:** 2026-09-06
- **Related:** ADR 0004, ADR 0005, [application-managed setup](app-managed-printer-setup.md)

Printer setup changes durable runtime state and printer credentials, so it uses the same fail-closed command-security boundary as other FoxForge mutations.

## Application authentication

Protected setup commands require a valid FoxForge Bearer credential backed by `FOXFORGE_COMMAND_TOKEN`.

For Umbrel, the package maps the per-app password to:

```text
FOXFORGE_COMMAND_TOKEN=${APP_PASSWORD}
```

The operator enters that password in **Operator Access / Unlock writes**. The browser keeps it only in JavaScript memory for the current tab.

FoxForge does **not** treat reverse-proxy headers or a private Docker network as an application principal. `FOXFORGE_TRUSTED_BROWSER_SESSIONS=true` is rejected by production startup, and tokenless `/api/v1/operator-session` does not mint a credential.

## Printer credentials

Bambu LAN access codes and Moonraker API keys:

- are accepted only on protected setup commands;
- are persisted behind the private `SecretStore` boundary;
- are hydrated only at runtime adapter boundaries;
- are never returned by public configuration read models;
- are represented to the UI only by `...Configured` booleans;
- must not appear in command audit, reconnect diagnostics or normalized setup failures.

## Setup error hygiene

Known adapter failures are mapped to normalized FoxForge error codes and retryability. Unexpected implementation exceptions are reduced to an internal adapter error before they reach the browser.

The operator-facing path must not expose:

- Python tracebacks;
- raw MQTT/HTTP/FTPS exceptions;
- access codes or API keys;
- raw vendor request/response payloads;
- certificate pin values in error text.

## Test-before-save

Security includes protecting existing durable state from invalid replacement input:

- Add preflights before any printer config is persisted;
- Update preflights the effective replacement before known-good state is changed;
- a failed post-persist runtime replacement rolls configuration/secrets/adapter state back;
- terminal failed Add/Update responses are durable idempotent results, preventing accidental repeated connection attempts from the same command identity.

## Discovery boundary

Bambu discovery is an operator-requested candidate lookup, not authentication.

- only RFC1918 IPv4 subnets are accepted;
- scan size is bounded;
- candidates still require normal serial/credential validation through test-before-save;
- discovery results do not expose credentials and cannot create durable printer state.

## Acceptance criteria

- missing/wrong operator credential fails closed;
- browser credential remains memory-only and clears on Lock/401/page lifecycle;
- tokenless proxy identity cannot authorize setup;
- printer secrets never appear in read DTOs, audits or diagnostics;
- failed Add/Update cannot leave a weaker or dead persistent configuration;
- repeated same-key terminal setup failure does not execute twice;
- discovery never bypasses authenticated setup preflight.
