# Secret storage boundary

Status: implemented stabilization design for AUD-015.

## Context

FoxForge needs Bambu LAN access codes and optional Moonraker API keys in order to create vendor transports. Those credentials must not leak into read DTOs, diagnostics, logs or common printer/application contracts. Earlier alpha configuration stored them inline inside `/data/config.json`, protected only by the private application-data boundary and file permissions.

File permissions remain important, but they are not encryption and they do not provide a replaceable secret-management abstraction.

## Decision

FoxForge introduces an application-facing `SecretStore` port with `get`, `set` and `delete` operations. Vendor adapters are unchanged: runtime composition hydrates the required credential into adapter settings only when constructing or testing an adapter.

The default self-hosted implementation is `FileSecretStore` at `/data/secrets.json`:

- versioned JSON format;
- atomic temporary-file + `os.replace` updates;
- mode `0600` where supported;
- no secret values in diagnostics;
- deterministic keys such as `printer/<printer-id>/access_code` and `printer/<printer-id>/api_key`.

This file backend is intentionally an infrastructure implementation, not a domain contract. Future Docker secrets, system keyrings, Vault-like providers or platform-specific stores can implement the same port without changing `PrinterAdapter`, FleetService or application printer models.

## Runtime configuration

`/data/config.json` continues to own non-secret printer composition such as host/base URL, ports, model and adapter settings. New or updated printer credentials are removed from the persisted settings and written through `SecretStore` instead.

Internal printer configuration operations may hydrate a secret when required to reconstruct an adapter. Public/read DTOs continue to expose only non-secret state such as whether a credential is configured.

## Legacy migration

At startup, FoxForge detects historical inline secret fields:

- Bambu: `access_code`;
- Moonraker: `api_key`.

When found, it:

1. writes the values to `SecretStore`;
2. creates `/data/config.json.backup-pre-secret-store` if that recovery file does not already exist;
3. rewrites `config.json` atomically with those fields removed;
4. hydrates the migrated secret only at the adapter-composition boundary.

The migration backup deliberately preserves the pre-migration file for recovery and therefore **contains plaintext printer credentials**. It is sensitive data.

## Backup and restore security

Treat the **entire `/data` volume and every copy of it as credential-bearing sensitive data**. In particular, the following may contain secrets:

- `/data/secrets.json`;
- `/data/config.json.backup-pre-secret-store`;
- historical `config.json.backup-vN` files created before the secret split;
- external/manual snapshots or archives of `/data`.

Do not publish these files in bug reports, repository issues, logs or diagnostics. Backups should be stored with access controls appropriate for printer credentials.

The file-backed SecretStore improves separation and future portability; it does **not** claim encryption at rest against a host administrator or someone who can read the FoxForge data volume.

## Mutation semantics

Printer add/update/remove keeps config and secret state coordinated inside the serialized runtime printer-manager mutation path:

- add writes the secret before committing redacted config and removes it on rollback;
- update preserves an existing secret when the request intentionally omits a replacement;
- changing adapter kind accounts for both old and new secret-key sets so rollback cannot leave a newly introduced orphan credential;
- remove deletes the printer's secret after the redacted config update and restores config if secret deletion itself fails.

This is a single-process consistency contract. A future external SecretStore with distributed transactions may require stronger provider-specific recovery semantics.

## Security boundaries

- Printer/domain/application code does not depend on `FileSecretStore`.
- Secret values are never returned by persistence diagnostics.
- Browser/API read models must never echo credentials.
- Vendor transports receive credentials only through runtime adapter construction.
- Logs and normalized errors must not interpolate secret values.
- A SecretStore backend is not an authentication system for FoxForge users; command authentication remains governed separately by ADR 0005.

## Acceptance criteria

- [x] `SecretStore` is an application-facing port independent of vendor transports.
- [x] default file implementation uses atomic writes and restrictive permissions where supported.
- [x] new/updated Bambu access codes and Moonraker API keys are not stored in normal `config.json` settings.
- [x] historical inline credentials migrate without losing the ability to reconstruct adapters.
- [x] migration creates an explicit sensitive recovery backup.
- [x] update without a replacement secret preserves the existing credential.
- [x] printer removal deletes its secret.
- [x] diagnostics disclose the backend class only, not secret paths, keys or values.
- [ ] exact final-head CI for the remediation PR.
- [ ] optional encrypted/external secret provider; deferred and not required for the current self-hosted alpha boundary.
