# Bambu project storage strategy

- **Status:** Implemented seam; FTPS default, X2D/eMMC physical validation pending
- **Related ADR:** [ADR 0001: PrinterAdapter architecture](../adr/0001-printer-adapter-architecture.md)
- **Related design:** [Bambu LAN production transport](bambu-lan-transport.md)
- **Date:** 2026-09-04

## Context

Phase 7 established a Bambu LAN transport that combines MQTT control/status with the conventional implicit-FTPS project upload path. That is appropriate for Bambu families that expose the standard FTPS storage service, but it is too strong an architectural assumption for every Bambu printer.

Phase 8 therefore separated project delivery from MQTT print control. The production architecture no longer needs any preserved experimental uploader in order to support a future X2D/N6 storage implementation.

The former `integrations/bambuddy/x2d_port6000/` experiment was removed from the current repository tree on 2026-09-04. Git history remains available for historical provenance, but FoxForge will not promote that implementation into production. If X2D/N6 requires internal-eMMC transfer, it will be implemented as new production FoxForge code behind this storage boundary after physical validation.

## Decision

Separate **project delivery** from **print control** inside the Bambu adapter package.

`BambuLanTransport` owns:

- MQTT connection and status reconciliation;
- Bambu-native state/event handling;
- busy guards;
- `project_file` command dispatch;
- response matching and `INDETERMINATE` semantics.

A Bambu-specific `BambuProjectStorage` strategy owns:

- delivering a local project artifact to printer-accessible storage;
- returning the remote basename used by `project_file`;
- returning the exact Bambu-native project URL used by `project_file`.

The boundary is intentionally **not** promoted to a common FoxForge `FileStorageCapability`. This storage operation exists to support Bambu print execution and its protocol semantics; it is not yet a proven cross-vendor application capability.

## Contract

```text
BambuProjectStorage.upload(local_path, remote_filename)
        |
        v
BambuStoredProject
  remote_filename
  project_url
  storage_kind
```

Initial storage kinds are:

- `FTPS` — standard implicit-FTPS delivery, returning `ftp:///<name>`;
- `INTERNAL_EMMC` — reserved contract shape for a future validated internal-storage implementation, returning `brtc://emmc/<name>`.

`INTERNAL_EMMC` in the value model does **not** mean an X2D production uploader exists. It proves that MQTT control is independent from upload transport and leaves a typed extension point for hardware-led implementation.

## Default implementation

`FtpsBambuProjectStorage` wraps the Phase 7 `BambuFtpsWire` implementation. Existing production factory behavior remains:

```text
create_bambu_lan_adapter()
        |
        v
BambuLanTransport
        |
        +-- PahoBambuMqttWire
        `-- FtpsBambuProjectStorage
                 |
                 `-- ImplicitFtpsBambuWire
```

No automatic model detection or silent FTPS-to-alternate-transport fallback exists.

## Future X2D/N6 implementation

After physical validation, a production X2D storage strategy may implement the same Bambu-specific contract:

```text
X2dEmmcProjectStorage.upload(...)
        |
        +-- newly implemented, hardware-validated transfer
        `-- BambuStoredProject(
              remote_filename="job.3mf",
              project_url="brtc://emmc/job.3mf",
              storage_kind=INTERNAL_EMMC,
            )
```

The existing `BambuLanTransport` can then send the returned URL through `project_file` without changing `QueueService`, `FleetService`, `PrintExecutionCapability`, or the common printer domain.

The implementation must be selected explicitly. Production Bambu code must not import historical integration experiments.

## Safety consequences

The project-storage boundary sits **before** the print-start side effect.

- Storage failures remain safe pre-start failures.
- The second busy guard still runs after project storage completes and before MQTT `project_file`.
- `INDETERMINATE` remains reserved for ambiguity after `project_file` may have reached the printer.
- A storage strategy must not itself start a print.

A storage strategy must return a validated project reference. `BambuStoredProject` rejects mismatched filenames, unsupported URL schemes, query/fragment-bearing URLs, and invalid internal-eMMC references.

## Alternatives considered

### Keep FTPS hard-coded in `BambuLanTransport`

Rejected. It makes a storage difference look like a completely different printer adapter and would force X2D-specific branches into control logic.

### Carry the former port-6000 experiment forward as a dormant fallback

Rejected and removed. Dormant experimental production-adjacent code increases maintenance and provenance burden without improving current behavior. Hardware validation should drive a fresh implementation of the exact protocol path FoxForge actually needs.

### Add a common `FileStorageCapability`

Deferred. Moonraker and Bambu file handling currently have different application semantics, and the queue does not need a generic user-facing file manager to dispatch prints. A common capability can be introduced later if multiple vendors demonstrate the same stable use case.

## Acceptance criteria

1. Standard FTPS dispatch behavior is unchanged.
2. `BambuLanTransport` depends on `BambuProjectStorage`, not directly on FTPS semantics.
3. `project_file.url` comes from the storage result rather than being constructed as FTP inside the MQTT codec.
4. A fake internal-eMMC storage strategy can return `brtc://emmc/...` and the transport forwards it exactly.
5. The second busy guard still runs after storage completion.
6. Production Bambu code imports neither Moonraker nor historical Bambuddy integration modules.
7. The default production factory still selects standard FTPS explicitly; there is no model-based fallback.
8. Ruff and the full test suite pass on Python 3.12 and Python 3.13.

## Next validation step

The next X2D-specific slice should be hardware-led rather than architecture-led:

1. identify which storage services the physical X2D exposes in the target LAN mode/firmware;
2. validate read-only capability discovery before attempting writes;
3. upload a small test 3MF without issuing `project_file`;
4. verify the remote artifact and the project URL expected by the printer;
5. only then implement a production `BambuProjectStorage` strategy based on the validated protocol;
6. document any external reverse-engineering source/provenance actually used by that new implementation.
