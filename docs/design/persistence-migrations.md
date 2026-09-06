# Persistent data migration contract

- **Status:** implemented
- **Updated:** 2026-09-06
- **Related:** AUD-008, [secret storage](secret-storage.md)

FoxForge owns durable runtime state under `/data`. Schema changes must be explicit, versioned, recoverable and tested; store constructors must not hide destructive migration behavior.

## Current owned versions

- `config.json`: `schemaVersion` **2**;
- `foxforge.sqlite3`: SQLite `PRAGMA user_version` **1**;
- `secrets.json`: SecretStore format version **1**.

Queue/inventory row payload versions are separate serialization contracts and do not replace database schema ownership.

`GET /api/v1/diagnostics/persistence` exposes only non-secret version/backend information.

## Configuration and secret migration

Historical config v1 is migrated to schema v2 with an explicit pre-change backup. Historical inline Bambu `access_code` / Moonraker `api_key` values are subsequently moved behind `SecretStore`, with an additional recovery backup when required.

Those backups may contain plaintext printer credentials. They are intentionally preserved for recovery and must be protected like the complete `/data` volume.

Newer unsupported schema versions fail closed rather than being silently downgraded.

## SQLite migration

Existing pre-versioned alpha databases are migrated from `user_version=0` to version 1 through one explicit transaction:

1. open with foreign keys/busy timeout;
2. create a SQLite Backup API recovery copy when existing state is present;
3. acquire `BEGIN IMMEDIATE`;
4. establish/validate the current queue, inventory, command-idempotency and audit schema;
5. run required column/foreign-key checks;
6. set `user_version=1` only after validation succeeds;
7. commit.

Failure rolls back without pretending migration completed. Newer database versions fail closed.

## Corruption/recovery

FoxForge does not silently recreate corrupt/incompatible persistence. Existing migration recovery files are not automatically overwritten.

For early-alpha upgrades, the safest operator procedure remains:

1. stop FoxForge;
2. back up the entire `/data` directory to access-controlled storage;
3. upgrade/start;
4. confirm persistence diagnostics and printer/queue/inventory state;
5. retain the backup until validation completes.

Do not mix `config.json` and `secrets.json` from unrelated backup points.

## Future changes

Any destructive/transforming migration requires explicit migration code, pre-change backup semantics, fixtures/tests and release notes describing compatibility/rollback limitations.

## Acceptance evidence

Automated tests cover historical config/database fixtures, secret migration/hydration, restart/idempotent migration, newer-schema fail-closed behavior, incompatible/corrupt-state handling and non-secret diagnostics.
