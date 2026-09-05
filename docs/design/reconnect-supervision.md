# Printer reconnect supervision and diagnostics

- **Status:** implemented foundation
- **Date:** 2026-09-06
- **Related:** ADR 0001, Pre-Alpha 5 issue #115

## Purpose

FoxForge must recover disconnected printers without allowing one unhealthy device to block the rest of the fleet. Reconnect behavior also needs enough operator-visible context to explain why a printer remains offline, but must not expose access codes, API keys, raw vendor exceptions or transport-specific payloads.

This design applies to every adapter hosted by `FleetService`. Bambu Lab remains the first physical validation target, but the reconnect supervisor itself is vendor-independent.

## Runtime ownership

`foxforge.runtime.reconnect` owns the process-local reconnect policy and worker lifecycle. `FleetService` remains responsible only for normalized printer lifecycle operations and snapshots.

The supervisor maintains one worker per currently configured printer and discovers dynamic additions/removals while the process is running.

Each worker:

1. observes the normalized `PrinterSnapshot.connection` state;
2. attempts `FleetService.connect(printer_id)` only while the printer is disconnected;
3. applies independent exponential backoff with bounded jitter after failures;
4. shares a global semaphore so many offline printers cannot create unbounded concurrent reconnect attempts;
5. immediately stops when its printer is removed from the runtime fleet.

A slow or failing printer must not prevent another printer from reconnecting.

## Backoff contract

`ReconnectPolicy` defines:

- base retry delay;
- maximum retry delay;
- global maximum concurrent connection attempts;
- jitter ratio;
- dynamic fleet discovery interval.

Backoff grows exponentially per printer and is capped by the configured maximum. Successful recovery resets the consecutive failure count for that printer only.

The supervisor deliberately does not retry through a separate vendor-specific scheduler. Adapter implementations normalize transport failures into `PrinterAdapterError` before they reach this boundary.

## Secret-safe diagnostics

`ReconnectDiagnostics` stores only process-local operational context:

- printer ID;
- consecutive failure count;
- last attempt timestamp;
- last failure timestamp;
- normalized `PrinterErrorCode`;
- normalized retryable flag;
- next retry timestamp;
- recovery timestamp.

It must never store:

- Bambu LAN access codes;
- Moonraker API keys;
- raw adapter exception messages;
- vendor error payloads or MQTT/HTTP bodies;
- vendor codes whose contents have not been explicitly normalized as safe.

The runtime event relay also captures adapter-originated disconnect errors only after the adapter has normalized them to `PrinterAdapterError`. Bambu and Moonraker transports currently surface these as `SNAPSHOT_RECONCILED` events carrying the normalized common error object. The relay stores only the common error code and retryable flag; it deliberately discards the raw message and vendor code. This means a spontaneous transport drop still leaves useful context even if the first automatic reconnect succeeds.

The last normalized failure context is retained after recovery so operators can understand a recent disconnect. `consecutiveFailures` returns to zero and `nextRetryAt` is cleared when the printer recovers.

Diagnostics for printers removed from the active fleet are discarded.

## Read API

The runtime exposes:

```text
GET /api/v1/diagnostics/reconnect
```

The endpoint is read-only and returns FoxForge-owned fields only. Example shape:

```json
{
  "apiVersion": "1",
  "printers": [
    {
      "printerId": "bambu-01p00example",
      "consecutiveFailures": 2,
      "lastAttemptAt": "2026-09-06T00:00:00Z",
      "lastFailureAt": "2026-09-06T00:00:00Z",
      "lastErrorCode": "authentication_failed",
      "lastErrorRetryable": false,
      "nextRetryAt": "2026-09-06T00:00:30Z",
      "recoveredAt": null
    }
  ]
}
```

The API is diagnostic evidence, not a command surface. It does not weaken ADR 0004/0005 command authentication requirements.

## Failure semantics

Known `PrinterAdapterError` failures preserve the normalized common error code and retryable bit. Unexpected exceptions are recorded only as `internal_adapter_error`; their original message is logged server-side but is not copied into the diagnostics read model.

Reconnect attempts continue according to runtime policy even when an individual normalized error reports `retryable=false`. The retryable field describes the failure returned by the adapter; the always-on runtime supervisor remains the higher-level availability policy. This distinction is intentional so a temporary configuration/network correction can recover without restarting FoxForge.

## Physical validation requirements

Software tests are not sufficient to claim reconnect behavior validated on a real printer. Pre-Alpha 5 physical acceptance must prove on Raspberry Pi 5 + Umbrel + X2D that:

1. FoxForge connects to the real printer after valid setup;
2. restarting FoxForge reconnects without re-adding the printer;
3. temporarily making the printer unreachable produces a sanitized reconnect diagnostic record;
4. restoring network reachability recovers the printer and resets consecutive failures;
5. the last normalized disconnect context remains visible after recovery;
6. no access code, raw MQTT exception or printer credential appears in the diagnostics response or UI.

## Acceptance criteria and tests

Automated coverage must prove:

1. exponential backoff is bounded and jittered;
2. reconnect concurrency is globally bounded;
3. a slow printer does not block another printer;
4. a repeatedly failing printer can later recover without restarting the supervisor;
5. dynamically added printers get workers and removed printers lose workers/diagnostics;
6. spontaneous adapter disconnect errors are reduced to normalized common fields before diagnostics storage;
7. the diagnostics HTTP read model cannot expose raw messages or vendor codes;
8. recovery resets consecutive failures but preserves the last failure category;
9. runtime/API/container/security/browser gates remain green.
