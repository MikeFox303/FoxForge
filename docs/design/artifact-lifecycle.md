# Artifact lifecycle and storage policy

Status: stabilization contract for AUD-011

## Context

FoxForge stages print payloads in content-addressed storage under `/data/artifacts`. Per-upload size limits protect individual requests, but a long-lived print farm also needs a bound on aggregate storage and deterministic cleanup rules.

The queue remains the source of truth for whether a committed artifact is referenced by durable application state. Artifact cleanup must never infer safety from printer connectivity or vendor job state.

## Decision

FoxForge keeps content-addressed artifact storage and adds four lifecycle controls:

1. A configurable total committed-artifact quota.
2. A configurable minimum filesystem free-space reserve.
3. Startup cleanup of stale temporary upload directories.
4. Startup garbage collection of old artifacts that are not referenced by any durable queue entry.

Defaults:

- `FOXFORGE_ARTIFACT_QUOTA_BYTES`: 20 GiB.
- `FOXFORGE_ARTIFACT_MIN_FREE_BYTES`: 1 GiB.
- `FOXFORGE_ARTIFACT_ORPHAN_RETENTION_SECONDS`: 7 days.
- `FOXFORGE_ARTIFACT_TEMP_RETENTION_SECONDS`: 1 hour.

A content-addressed replay of an already committed SHA-256 does not consume quota again and remains valid when the store is otherwise at capacity.

## Safety rules

- A new upload is hash-verified before capacity checks and before publication into the committed artifact namespace.
- Quota/free-space rejection deletes the temporary upload and returns a normalized `507 artifact_storage_full` command error.
- The single-process runtime serializes staging so two concurrent uploads cannot both authorize against the same committed quota snapshot.
- Garbage collection preserves every artifact referenced by any durable queue entry, regardless of whether that queue entry is pending, accepted, printing, failed, cancelled, completed or indeterminate.
- Only unreferenced artifacts older than the configured orphan-retention interval are deleted.
- Temporary upload cleanup touches only directories below `/data/artifacts/.tmp` that are older than the configured temp-retention interval.
- Unknown directories that do not look like SHA-256 artifact IDs are ignored rather than deleted.
- Artifact storage diagnostics expose counts/byte totals/quota/free-space values only; they do not expose local file paths, filenames, payloads or printer secrets.

## Operational recovery

If staging returns `artifact_storage_full`, an operator may increase the configured quota, free disk space, or remove durable queue entries through a future explicit queue-retention workflow so their old artifacts can become eligible for GC. FoxForge does not delete a queue-referenced payload merely to satisfy quota.

## Deferred work

The current alpha runtime performs lifecycle cleanup at process startup. A future farm-scale implementation may add an authenticated/manual cleanup command and periodic background GC, but it must preserve the same durable-reference safety rule.

## Acceptance criteria

- Two distinct uploads cannot exceed the configured committed-artifact quota.
- Existing content-addressed replay works without duplicating storage.
- Capacity failure leaves no committed or temporary partial artifact.
- Old referenced artifacts survive GC.
- Old unreferenced artifacts are removed only after retention expires.
- Fresh orphan artifacts are retained.
- Stale temporary directories are removed without touching unrelated paths.
- Storage counters and free-space reserve are available in diagnostics.
- Container/browser/security/backend CI remains green.
