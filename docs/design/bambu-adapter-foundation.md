# Bambu adapter foundation

- **Status:** functional alpha foundation; physical X2D/AMS acceptance in progress
- **Updated:** 2026-09-06
- **Related:** [ADR 0001](../adr/0001-printer-adapter-architecture.md), [Bambu LAN transport](bambu-lan-transport.md), [project storage](bambu-project-storage.md)

## Purpose

The Bambu adapter is the reference deep-vendor implementation behind FoxForge's vendor-neutral printer contracts. Bambu-native state, protocol DTOs and model quirks stay inside `foxforge.adapters.bambu` and related infrastructure.

## Provenance

Current Bambu adapter code is newly written FoxForge code. Behavior is informed by public Bambu/Bambuddy behavior, especially Bambuddy's MQTT/printer-management implementation. No Bambuddy source file is treated as the FoxForge common architecture.

The retired port-6000/X2D experiment remains only in Git history. Future X2D/eMMC behavior, if required by hardware evidence, must be newly implemented behind the production project-storage boundary with explicit provenance.

## Layering

```text
FoxForge application/domain
        |
PrinterAdapter + common capabilities
        |
BambuAdapter
  |-- PrintExecutionCapability
  |-- JobControlCapability
  |-- MaterialSystemCapability
        |
  +-- LAN MQTT/TLS
  +-- project storage / FTPS
  +-- LAN discovery candidate lookup
  `-- future typed Bambu extensions
```

## State mapping

Bambu native printer/job state is normalized at the adapter boundary. Raw MQTT payloads, Bambu gcode-state strings, AMS IDs/tray IDs and transport exceptions are not common-domain contracts.

## Material-system mapping

AMS, AMS 2 Pro and AMS HT are observed as common multi-slot material units; external feed is observed as an external unit. Opaque slot IDs are constructed/parsed only by the Bambu adapter.

The current material capability can report, when present in native state:

- active source;
- remaining fraction;
- material identity;
- tag/RFID identity.

FoxForge inventory `spool_id` remains separate from physical material observation.

Deep operations such as drying, filament backup commands, K profiles, HMS actions and dual-nozzle workflows remain Bambu-specific typed capability work.

## Print execution and job control

The Bambu execution capability accepts supported 3MF requests, translates plate/material routes at the adapter boundary and delegates project delivery/start to the Bambu transport/project-storage seam.

Confirmed dispatch receipts may be cached in-process, while durable exactly-once/reconciliation semantics remain in the queue.

Common Pause/Resume/Cancel map to Bambu commands only when the exact observed active vendor job identity remains valid. Ambiguous side effects are not automatically retried.

## LAN discovery

Current source includes a conservative discovery helper:

- explicit operator-selected RFC1918 IPv4 subnet;
- `/22` or smaller / maximum 1022 usable hosts;
- bounded concurrent probes;
- MQTT 8883 and FTPS 990 must be reachable;
- targeted SSDP may provide serial/name/model;
- result is a **candidate only**;
- normal MQTT authentication/initial-state preflight remains mandatory before persistence.

Discovery does not weaken test-before-save or credential requirements.

## Connection/reconnect

Application setup preflights effective credentials/reachability before Add/Update persistence. The vendor-independent reconnect supervisor retries disconnected printers independently with bounded backoff/jitter and exposes only normalized secret-safe diagnostics.

## Certificate trust

Bambu MQTT and FTPS may be configured with independent optional SHA-256 certificate pins. Mismatch fails closed before the corresponding authenticated transport step. Default trust policy must not be tightened solely from CI; real X2D certificate stability evidence is required.

## Still outside the validated production surface

- final physical X2D/AMS 2 Pro acceptance;
- validated X2D/eMMC-specific project storage if standard FTPS is insufficient;
- Bambu cloud authentication;
- camera transport;
- HMS detail/actions;
- AMS drying controls;
- K profiles/calibration;
- dual-nozzle controls;
- Virtual Printer.

## Acceptance criteria

- common application/domain code receives no Bambu protocol types;
- state/material/job data maps through FoxForge contracts;
- discovery never persists an unauthenticated candidate;
- Add/Update remain test-before-save;
- ambiguous print/control outcomes remain reconciliation/observation problems, not blind retries;
- material slot IDs remain opaque outside the adapter;
- printer credentials and raw exceptions do not enter public diagnostics;
- physical support claims require the Pre-Alpha 5 real-device gate.
