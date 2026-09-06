# Secret storage boundary

- **Status:** implemented
- **Updated:** 2026-09-06
- **Related:** AUD-015, [printer setup security](printer-setup-security.md), [persistence migrations](persistence-migrations.md)

## Purpose

Bambu LAN access codes and optional Moonraker API keys are required to construct vendor transports but must not become ordinary public/runtime configuration data.

FoxForge therefore uses an application-facing `SecretStore` port. Vendor adapters remain unaware of the concrete secret backend; runtime composition hydrates credentials only when constructing/testing an adapter.

## Default backend

`FileSecretStore` stores versioned private state under `/data/secrets.json` using atomic replacement and restrictive file permissions where supported.

This is separation/portability, **not encryption at rest** against a host administrator or anyone who can read the FoxForge data volume.

Future Docker secrets, keyrings or Vault-like providers can implement the same port without changing printer/domain/application contracts.

## Public boundary

Printer config read DTOs expose only whether a credential is configured. Secrets must not appear in:

- fleet/configuration reads;
- setup/reconnect diagnostics;
- normalized errors;
- command audit;
- browser persistent storage;
- logs.

## Migration

Historical inline `access_code` / `api_key` values are moved to SecretStore at startup. Recovery backups created during migration may still contain plaintext credentials and must be treated as sensitive.

The entire `/data` directory and every backup/snapshot of it should therefore be treated as credential-bearing data.

## Mutation semantics

Printer Add/Update/Remove coordinate redacted config and secret state in the serialized runtime printer manager.

Current Pre-Alpha 5 setup adds an additional safety layer:

- effective Add/Update credentials are preflighted before durable replacement;
- update without a replacement secret reuses the existing stored secret;
- failed replacement restores prior config/secret/adapter state;
- remove deletes the printer secret while preserving rollback behavior on persistence failure.

## Acceptance criteria

- domain/application code depends on `SecretStore`, not `FileSecretStore`;
- new printer credentials are absent from normal `config.json` settings;
- legacy inline credentials migrate with a recovery path;
- config read models expose only configured/not-configured state;
- setup/update rollback cannot orphan a replacement secret;
- diagnostics/audit/logging remain secret-safe;
- full `/data` backups are documented as sensitive;
- external/encrypted provider support remains optional future work rather than a production-readiness claim.
