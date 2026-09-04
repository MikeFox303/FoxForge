# Persistent data migration contract

Status: implemented stabilization design for AUD-008.

FoxForge owns durable runtime configuration and SQLite state under `/data`. Schema changes must be explicit, versioned, recoverable and testable before additional accounting/farm data is introduced.

## Owned versions

- `config.json`: `schemaVersion`, current version **2**.
- `foxforge.sqlite3`: SQLite `PRAGMA user_version`, current version **1**.
- `secrets.json`: file SecretStore format version **1**.
- JSON payload versions inside queue/inventory rows remain separate serialization contracts and do not replace the database schema version.

`GET /api/v1/diagnostics/persistence` exposes only non-secret persistence version/backend information. It never exposes secret keys or values.

## Runtime configuration migration

The historical alpha configuration format is version 1. Migration `1 -> 2` is intentionally non-destructive: printer identities and settings remain unchanged while migration ownership is established.

Before replacing a v1 file, FoxForge creates:

`/data/config.json.backup-v1`

The backup is an exact copy of the pre-migration file and therefore **contains any stored printer credentials**. It must be protected with the same care as the whole `/data` volume.

The replacement config is written through the existing temporary-file + atomic `os.replace` path. A future schema version is rejected by older FoxForge code rather than silently downgraded.

## Secret-store migration

Current runtime composition separates credential values from ordinary printer settings through the `SecretStore` port. Historical schema-v2 configs may still contain inline Bambu `access_code` or Moonraker `api_key` fields.

At startup FoxForge migrates those values to `/data/secrets.json`, creates `/data/config.json.backup-pre-secret-store` as a recovery point, and rewrites `config.json` without the secret fields. The config schema remains version 2 because the JSON printer-settings shape remains extensible; secret storage has its own versioned contract.

The pre-secret-store backup is intentionally sensitive and is never overwritten automatically. See `docs/design/secret-storage.md` for the security boundary and provider design.

## SQLite migration

All current durable stores share `/data/foxforge.sqlite3`. Existing alpha databases predate database-level migration ownership and therefore have `PRAGMA user_version = 0`.

Migration `0 -> 1`:

1. opens the database with foreign keys and a busy timeout enabled;
2. when an existing database has state, creates `/data/foxforge.sqlite3.backup-v0` using the SQLite Backup API so WAL state is captured consistently;
3. acquires `BEGIN IMMEDIATE`;
4. establishes the current queue, inventory, command-idempotency and command-audit tables/indexes;
5. verifies required table columns and runs `PRAGMA foreign_key_check`;
6. sets `PRAGMA user_version = 1` only after validation succeeds;
7. commits the transaction.

If validation or DDL fails, the transaction is rolled back and `user_version` remains unchanged. The backup is retained as the recovery point. A database whose `user_version` is newer than the running FoxForge version fails closed.

## Corruption and incompatible legacy state

FoxForge does not silently recreate a corrupt database, incompatible table or invalid secret-store file. Startup fails explicitly so the operator can inspect/restore data rather than losing it.

An existing migration backup is never overwritten automatically. This protects the original pre-migration recovery point after an interrupted first attempt.

## Backup and restore procedure

Before an upgrade, copying the whole persistent `/data` volume while FoxForge is stopped remains the safest operator backup. **Every such copy must be treated as credential-bearing sensitive data.**

For migration-generated recovery files:

1. stop FoxForge;
2. copy the current `/data` directory somewhere access-controlled before changing it;
3. for config restore, restore the matching `config.json` recovery copy;
4. restore the matching `secrets.json` from the same backup set when the configuration depends on externalized printer credentials;
5. for SQLite restore, remove/relocate the current `foxforge.sqlite3`, `foxforge.sqlite3-wal` and `foxforge.sqlite3-shm`, then copy the desired SQLite backup to `foxforge.sqlite3`;
6. start FoxForge and allow the versioned migration runners to retry;
7. confirm `/api/v1/diagnostics/persistence` reports the expected current versions/backend and verify printers/queue/inventory before deleting any recovery copy.

Do not mix `config.json` and `secrets.json` from unrelated backup points when restoring printer configuration, and do not restore persistence from a newer FoxForge schema into older code.

## Destructive changes

No destructive migration may be hidden inside `CREATE TABLE IF NOT EXISTS` or a store constructor. A future destructive/transforming migration must have explicit migration code, pre-change backup semantics, fixtures/tests, and release notes describing rollback limitations.

## Acceptance evidence

Automated tests cover:

- historical config v1 fixture -> v2 migration with exact backup and credential preservation;
- restart after config migration;
- historical inline printer credentials -> SecretStore migration with redacted active config and sensitive recovery backup;
- secret hydration after migration;
- historical SQLite v0 fixture -> v1 migration with SQLite backup and row preservation;
- restart/idempotent SQLite migration;
- newer schema fail-closed behavior;
- incompatible legacy table rollback without raising the recorded schema version;
- corrupt persistence failing without silent replacement;
- runtime diagnostics exposing only non-secret config/SQLite/secret-backend information.
