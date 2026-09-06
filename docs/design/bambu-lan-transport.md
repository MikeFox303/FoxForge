# Bambu LAN transport

- **Status:** implemented alpha transport; physical X2D acceptance in progress
- **Updated:** 2026-09-06
- **Related:** [Bambu adapter foundation](bambu-adapter-foundation.md), [project storage](bambu-project-storage.md), [certificate trust](bambu-certificate-trust.md)

## Purpose

FoxForge's Bambu LAN transport provides the production adapter with MQTT/TLS state and command delivery while keeping protocol details below the `PrinterAdapter` boundary.

The implementation is newly written FoxForge code. Bambuddy is used as a behavior/protocol reference; no Bambuddy service file is copied into this transport.

## Runtime boundary

```text
BambuAdapter
   |
BambuLanTransport
   |
BambuLanWireClient
   |
TLS MQTT (default port 8883)
```

The wire layer owns broker connection/subscription/publication. The codec/native layer owns Bambu payload parsing and mapping. Common application code sees only FoxForge snapshots/events/errors/capabilities.

## Connection model

The transport:

1. connects to the configured Bambu LAN endpoint over TLS;
2. authenticates with LAN-mode credentials;
3. subscribes to the printer report topic;
4. requests a full status report;
5. waits for a valid initial report before declaring the adapter connected;
6. routes later reports into normalized state/events;
7. maps connect/auth/timeout/remote failures to FoxForge error categories.

A successful socket/MQTT handshake alone is not enough to claim a usable connected printer; initial state must be obtained.

## Setup/discovery interaction

Pre-Alpha 5 adds a conservative discovery helper, but discovery is not part of MQTT authentication:

- operator selects a bounded RFC1918 IPv4 subnet;
- candidate probes require expected MQTT/FTPS ports;
- SSDP metadata may help populate serial/name/model;
- the candidate must still pass the normal authenticated live preflight before Add/Update persistence.

Manual host entry remains supported when deployment networking prevents discovery.

## State and events

Native Bambu report fields are mapped inside the adapter into normalized printer/job/material-system state. Sparse reports preserve prior known fields when the protocol omits unchanged data; a full report after connect/reconnect is used to re-establish current state.

Raw Bambu payloads and native status strings are not public API contracts.

## Commands and print start

The transport publishes Bambu command payloads through the same authenticated MQTT connection. Print execution first uses the separate `BambuProjectStorage` boundary for artifact delivery and then submits the Bambu print command.

Failure classification is fail-safe:

- a confirmed pre-command/storage failure may be definite/retryable according to the normalized error;
- once a start/control side effect may have been emitted, uncertainty becomes `INDETERMINATE` rather than an automatic retry.

## TLS trust

Current alpha supports optional independent SHA-256 certificate pins for MQTT and FTPS. Pin mismatch fails closed. Default trust policy remains subject to real X2D certificate evidence; CI does not prove device certificate stability.

See [bambu-certificate-trust.md](bambu-certificate-trust.md).

## Secrets and diagnostics

LAN access codes are hydrated through `SecretStore` only at runtime composition/testing boundaries. They must not appear in config read DTOs, reconnect diagnostics, audit records or normalized setup errors.

Reconnect supervision is vendor-independent and operates through `FleetService.connect()`; the Bambu transport owns only its connection handshake/state.

## Physical validation

Before final Alpha 5, real X2D/Umbrel evidence must cover:

- valid and invalid setup credentials/identity;
- connect/reconnect and state synchronization;
- deployment-container reachability;
- TLS certificate observations when trust validation is evaluated;
- AMS 2 Pro/external material observations;
- project upload and exactly-one intended print start;
- guarded Pause/Resume/Cancel or completion;
- network interruption/ambiguous-outcome handling.

Use [Pre-Alpha 5 Bambu physical validation](../testing/pre-alpha-5-bambu-physical-validation.md) for the exact candidate.
