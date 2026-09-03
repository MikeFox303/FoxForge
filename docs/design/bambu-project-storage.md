# Bambu project storage strategy

- **Status:** Proposed implementation seam
- **Related ADR:** [ADR 0001: PrinterAdapter architecture](../adr/0001-printer-adapter-architecture.md)
- **Related design:** [Bambu LAN production transport](bambu-lan-transport.md)
- **Date:** 2026-09-04

## Context

Phase 7 established a Bambu LAN transport that combines MQTT control/status with the conventional implicit-FTPS project upload path. That is appropriate for Bambu families that expose the standard FTPS storage service, but it is too strong an architectural assumption for every Bambu printer.

FoxForge also preserves experimental X2D/N6 work under `integrations/bambuddy/x2d_port6000/`. That research targets BambuTunnelLocal on TLS port 6000 and internal eMMC project references such as `brtc://emmc/<name>`.

The production adapter must not import that experiment before physical validation, but the production architecture should not force a future X2D implementation to rewrite MQTT control, queue dispatch, or the common printer contracts merely because project storage differs.

## Decision

Separate **project delivery** from **print control** inside the Bambu adapter package.

`BambuLanTransport` continues to own:

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
- `INTERNAL_EMMC` — reserved contract shape for a validated internal-storage implementation, returning `brtc://emmc/<name>`.

`INTERNAL_EMMC` in the value model does **not** mean an X2D production uploader has been accepted. It allows tests and future implementations to prove that MQTT control is independent from upload transport.

## Default implementation

`FtpsBambuProjectStorage` wraps the Phase 7 `BambuFtpsWire` implementation. Therefore existing production factory behavior remains unchanged:

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

No automatic model detection or silent FTPS-to-port-6000 fallback is introduced in this phase.

## Future X2D/N6 implementation

After physical validation, a production X2D storage strategy may implement the same Bambu-specific contract:

```text
X2dEmmcProjectStorage.upload(...)
        |
        +-- validated :6000 transfer
        `-- BambuStoredProject(
              remote_filename="job.3mf",
              project_url="brtc://emmc/job.3mf",
              storage_kind=INTERNAL_EMMC,
            )
```

The existing `BambuLanTransport` can then send the returned URL through `project_file` without changing QueueService, FleetService, `PrintExecutionCapability`, or the common printer domain.

The preserved `integrations/bambuddy/x2d_port6000` package remains a research/provenance source only. Architecture tests forbid production Bambu adapter modules from importing it.

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

### Put the port-6000 experiment directly into `BambuLanTransport`

Rejected. The experimental implementation has not yet passed the physical X2D validation gate and should not become a hidden fallback in production code.

### Add a common `FileStorageCapability`

Deferred. Moonraker and Bambu file handling currently have different application semantics, and the queue does not need a generic user-facing file manager to dispatch prints. A common capability can be introduced later if multiple vendors demonstrate the same stable use case.

## Acceptance criteria

1. Standard FTPS dispatch behavior is unchanged.
2. `BambuLanTransport` depends on `BambuProjectStorage`, not directly on FTPS semantics.
3. `project_file.url` comes from the storage result rather than being constructed as FTP inside the MQTT codec.
4. A fake internal-eMMC storage strategy can return `brtc://emmc/...` and the transport forwards it exactly.
5. The second busy guard still runs after storage completion.
6. The production Bambu package imports neither Moonraker nor the preserved X2D experiment.
7. The default production factory still selects standard FTPS explicitly; there is no model-based fallback in this phase.
8. Ruff and the full test suite pass on Python 3.12 and Python 3.13.

## Next validation step

The next X2D-specific slice should be hardware-led rather than architecture-led:

1. validate read-only :6000 connection/media ability on the physical X2D;
2. upload a small test 3MF to internal eMMC without issuing `project_file`;
3. verify the remote artifact and expected `brtc://emmc/...` reference;
4. only then implement a production `BambuProjectStorage` strategy based on the validated protocol;
5. preserve/record upstream reverse-engineering provenance in the production implementation.
