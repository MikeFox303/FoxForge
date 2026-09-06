# Bambu project storage

- **Status:** implemented FTPS storage boundary; physical X2D validation pending
- **Updated:** 2026-09-06
- **Related:** [Bambu LAN transport](bambu-lan-transport.md), [certificate trust](bambu-certificate-trust.md)

## Purpose

Bambu print execution requires artifact delivery before MQTT print start. File/project delivery is therefore isolated behind a Bambu-specific storage port instead of being embedded in queue or common print-execution code.

```text
QueueService
  -> PrintExecutionCapability
     -> BambuPrintExecutionCapability
        -> BambuProjectStorage
        -> BambuLanTransport (start command)
```

## Contract

`BambuProjectStorage` owns vendor-specific storage publication and returns a remote path/identity only after delivery is complete and validated according to the implementation.

Queue/common code never speaks FTPS and never depends on a Bambu remote-path convention.

## Current implementation

`FtpsBambuProjectStorage` implements the standard LAN storage strategy with:

- implicit FTPS/TLS;
- authenticated file upload using Bambu LAN credentials;
- deterministic safe remote naming;
- temporary/incomplete upload handling so interrupted transfer is not exposed as a completed project;
- cleanup/best-effort cleanup on failure;
- normalized FoxForge errors;
- optional independent FTPS certificate pin verification before credential-bearing storage work.

The retired port-6000/X2D experiment is not part of the production tree. If real X2D evidence proves standard FTPS insufficient, a newly validated storage implementation can be added behind this port without changing queue semantics.

## Submission safety

The Bambu print capability performs storage before MQTT start submission.

- definite storage failure occurs before printer-side start and can be classified accordingly;
- once MQTT start may have been emitted, uncertain acknowledgement is treated as `INDETERMINATE`;
- queue dispatch identity/receipt/reconciliation remain FoxForge-owned.

The storage layer must not retry the print-start command itself.

## Credentials

Storage receives the required Bambu credential only through runtime adapter composition. Secrets are not persisted in public config DTOs or returned by the storage result/error surface.

## Provenance

The production storage implementation is newly written FoxForge code. Bambuddy/open networking research may inform behavior, but any copied/derived implementation must be recorded separately with exact upstream commit/path/license/notices.

## Physical validation

The active X2D gate must prove:

- real project upload through the exact Umbrel candidate;
- remote path/plate semantics required by the X2D;
- successful print start after upload;
- interrupted upload/connection failure does not produce a duplicate start;
- certificate trust behavior when pins are enabled;
- recovery without deleting unrelated printer configuration.

If physical results require a different X2D storage strategy, update this design and publish a new immutable validation candidate before carrying evidence forward.
