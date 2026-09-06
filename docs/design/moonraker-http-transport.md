# Moonraker HTTP/WebSocket transport

- **Status:** implemented production transport foundation; physical OpenKE validation pending
- **Updated:** 2026-09-06
- **Related:** [Moonraker adapter foundation](moonraker-adapter-foundation.md), AUD-014

## Purpose

The Moonraker transport maps official HTTP/WebSocket behavior into FoxForge's adapter seams without leaking JSON-RPC objects or endpoint details into common application code.

## Runtime responsibilities

Current source implements:

- Moonraker HTTP reads;
- WebSocket subscription/current-state reconciliation;
- G-code upload and print start;
- Pause/Resume/Cancel control calls;
- optional API-key authentication;
- normalized transport/error classification;
- redirect/address/userinfo endpoint policy.

The adapter converts resulting native state into FoxForge snapshots/events/material/job capabilities.

## Endpoint security policy

A configured Moonraker URL is treated as a network-security boundary, especially when an API key may be attached.

Current policy validates the initial and resolved destination according to configured LAN/override rules, rejects embedded userinfo, controls redirects and prevents credentials from being silently forwarded to an unexpected destination.

Private/self-hosted deployments may require deliberate endpoint-policy overrides, but unsafe widening must be explicit rather than inferred from a redirect/DNS response.

## Print execution

The Moonraker print capability uploads a server-owned G-code artifact and starts the resulting file through Moonraker. Queue semantics remain above the transport:

- durable `dispatchId` exists before submit;
- confirmed start produces a receipt/job identity when available;
- uncertain start becomes `INDETERMINATE` rather than blind resubmit;
- lifecycle is followed through normalized printer/job observations.

## Material system

Moonraker currently exposes one normalized external material source. It is not modeled as AMS/CFS and does not fabricate unsupported material metadata. Inventory may associate a spool with its opaque physical `slotId`.

## Physical validation

Representative Ender 3 V3 KE/OpenKE evidence remains required for:

- real endpoint/port policy compatibility;
- connect/reconnect and WebSocket state;
- upload/start;
- Pause/Resume/Cancel;
- completion/failure;
- interrupted network/ambiguous start/control behavior.

The actual deployment URL/port must be recorded at validation time rather than hard-coded into common FoxForge logic.
