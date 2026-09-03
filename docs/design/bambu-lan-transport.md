# Bambu LAN production transport

- **Status:** Implemented; CI validated, physical-printer validation pending
- **Related ADR:** [ADR 0001: PrinterAdapter architecture](../adr/0001-printer-adapter-architecture.md)
- **Related foundation:** [Bambu adapter foundation](bambu-adapter-foundation.md)
- **Related storage seam:** [Bambu project storage strategy](bambu-project-storage.md)
- **Date:** 2026-09-04

## Purpose

This document records the production-oriented Bambu LAN transport behind FoxForge's `BambuTransport` boundary.

The implementation provides standard Bambu LAN MQTT status/control plus project delivery through a Bambu-specific storage strategy without exposing Bambu protocol details to the common printer domain, fleet service, queue, or inventory layers.

Physical validation remains a separate gate. Conventional implicit FTPS is the current default storage strategy, but FoxForge does not assume it is valid for every Bambu model or firmware family. If X2D/N6 requires a different internal-eMMC transport, that transport will be implemented as new production FoxForge code behind `BambuProjectStorage` after physical validation.

## Provenance

The Phase 7 implementation under `src/foxforge/adapters/bambu/` is newly written FoxForge code and remains licensed `AGPL-3.0-only` with FoxForge copyright headers.

Protocol behavior was informed by public Bambu LAN behavior and by the upstream AGPL-3.0 Bambuddy project, especially:

- `backend/app/services/bambu_mqtt.py` for Bambu report/request topics, QoS-1 command behavior, incremental status handling, and busy-state safety;
- `backend/app/services/bambu_ftp.py` for field experience around implicit FTPS, manual `STOR` transfers, delayed `226` confirmation, and firmware variants that may return a transfer error despite a complete server-side file;
- Bambuddy scheduler regression tests documenting why a second busy check immediately before `project_file` is necessary.

No Bambuddy service file is copied into FoxForge. FoxForge uses its own native DTOs, codec, transport protocols, error model, async integration, tests, and queue semantics.

A former X2D port-6000 experiment was removed from the current repository tree on 2026-09-04 rather than being carried forward as dormant implementation code. Git history retains the historical record. Any future X2D/eMMC implementation must carry fresh provenance appropriate to the implementation actually adopted.

## Layering

```text
QueueService / FleetService / common domain
                 |
                 v
       PrintExecutionCapability
                 |
                 v
             BambuAdapter
                 |
                 v
          BambuLanTransport
           /           \
          v             v
 BambuLanCodec      BambuProjectStorage
 sticky native      |-- FTPS today
 state mapping      `-- future validated storage
        |
        `-- MQTT/TLS :8883 control/status
```

Only `foxforge.adapters.bambu` knows Bambu MQTT keys, AMS ids, tray ids, `project_file`, or Bambu-specific project-storage details.

## MQTT wire semantics

`PahoBambuMqttWire` uses MQTT 3.1.1 over TLS.

Default LAN settings are:

```text
MQTT port: 8883
username:  bblp
password:  printer access code
report:    device/<serial>/report
request:   device/<serial>/request
```

Every command publish uses QoS 1. FoxForge waits for the MQTT publish acknowledgement before treating the publish operation itself as complete.

On connect, `BambuLanTransport` starts its message pump and requests both:

- `get_version`, used to identify AMS-family modules such as AMS 2 Pro and AMS HT;
- `pushall`, used to establish a complete initial printer state.

The connection is not considered reconciled until a status containing `gcode_state` has been observed.

## Sticky incremental state

Bambu firmware can send partial `push_status` messages. A partial message must not be interpreted as a complete replacement snapshot.

`BambuLanCodec` therefore merges only fields present in each report. For example, a progress-only update cannot erase previously observed AMS trays or material identity.

Module information received through `get_version` is retained and applied to existing material units so an AMS 2 Pro remains typed as `AMS_2_PRO` across later partial reports.

## Standard implicit-FTPS storage

`FtpsBambuProjectStorage` wraps `ImplicitFtpsBambuWire`, which uses implicit TLS on the control connection, normally port 990.

The upload path intentionally does not use `ftplib.storbinary()`. Instead it:

1. opens `STOR <filename>` through `transfercmd()`;
2. writes file chunks directly with `sendall()`;
3. closes the data connection;
4. waits for the control-channel transfer confirmation;
5. if confirmation is ambiguous, queries remote `SIZE`;
6. accepts the upload only when the remote byte count matches the local artifact.

This prevents FoxForge from sending `project_file` for a known partial 3MF.

The whole-upload deadline is size-aware rather than reusing the short MQTT command timeout. It is derived from a deliberately pessimistic transfer floor with a minimum long-transfer allowance, so normal large 3MF uploads are not killed after a few seconds.

An ambiguous upload is safe to retry because the print-start command has not yet been sent. Therefore upload ambiguity is **not** mapped to print-side `INDETERMINATE`.

## Print-start safety sequence

A print dispatch follows this order:

```text
normalized queue request
        |
        v
busy guard #1
        |
        v
confirmed Bambu project storage
        |
        v
busy guard #2
        |
        v
MQTT QoS1 project_file
        |
        v
matching command response
```

The second busy guard is mandatory. A printer may become busy while a large project is uploading; sending another `project_file` after that transition can interfere with an already active job on some firmware.

Busy states currently treated as unsafe start targets are:

- `PREPARE`
- `SLICING`
- `RUNNING`
- `PAUSE`

## `project_file` translation

The Bambu adapter translates the common request into Bambu-native fields only at the adapter boundary:

- zero-based common plate selection becomes a one-based Bambu plate number;
- the storage strategy supplies the remote basename and exact Bambu-native project URL;
- common opaque material slot bindings become Bambu `ams_mapping` and `ams_mapping2` routes;
- AMS use is enabled only when routed AMS slots are present.

These wire fields remain Bambu-only and must not be promoted into the common queue contract.

## `INDETERMINATE` boundary

The critical safety boundary is the MQTT `project_file` publish.

Before that publish, failures are retryable transport/storage failures because no print start has been requested.

After the publish may have reached the printer, FoxForge must not guess. A QoS acknowledgement timeout, connection loss, or missing matching command response is surfaced as `BambuTransportErrorKind.INDETERMINATE`. `BambuPrintExecutionCapability` converts that into common `PrinterErrorCode.INDETERMINATE`, and the durable queue requires reconciliation instead of an automatic duplicate start.

## TLS policy

`tls_verify=False` is the current default because LAN printers commonly expose device-local certificates that are not rooted in a public CA. Verification can be enabled explicitly through settings.

This is a transport trust decision, not application authentication. LAN access still requires the printer access code.

## X2D/N6 boundary

FoxForge no longer contains the former port-6000 experimental implementation.

The production architecture is instead:

```text
BambuAdapter
    |
    `-- BambuLanTransport
          |-- MQTT control/status
          `-- BambuProjectStorage
                |-- FTPS default
                `-- future hardware-validated X2D/eMMC strategy
```

There is no hidden fallback to an experimental transport. A future X2D/eMMC strategy must be implemented deliberately after physical validation and selected explicitly by composition/configuration logic.

## Acceptance criteria

The merged Phase 7 transport is considered software-complete when:

1. MQTT status is reconciled through `get_version` + `pushall` and incremental reports remain sticky.
2. MQTT command publishes use QoS 1.
3. AMS, AMS 2 Pro, AMS HT, and external-spool observations remain Bambu-native below the adapter and map through common material contracts above it.
4. A busy printer is rejected before upload.
5. A printer that becomes busy during upload is rejected before `project_file`.
6. The standard FTPS path never starts a print after a known short/partial upload.
7. A verified server-side size may recover an ambiguous FTPS completion response.
8. An ambiguous failure after `project_file` is `INDETERMINATE` and is never automatically retried by the adapter.
9. `create_bambu_lan_adapter()` can be registered by the composition root without vendor branches inside `AdapterRegistry`.
10. Ruff, architecture checks, and the full suite pass on Python 3.12 and 3.13.
11. Physical Bambu validation remains explicitly pending and is not inferred from CI.

## Hardware validation plan

The first physical validation should be non-destructive and model-specific:

1. connect and observe status only;
2. verify model/AMS discovery and incremental status stability;
3. verify a small project upload without issuing `project_file`;
4. verify remote file completeness;
5. perform one controlled print-start test while the printer is known idle;
6. repeat connection-loss handling without allowing automatic re-dispatch;
7. record printer model, firmware, storage path, and observed protocol differences in the repository.

For X2D/N6, test the storage mechanisms actually exposed by the printer rather than assuming behavior from older Bambu families. If standard FTPS is insufficient, implement a new `BambuProjectStorage` strategy only from validated observations.
