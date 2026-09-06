# Private discovery subnet suggestions

Status: Pre-Alpha 5 discovery UX contract.

## Decision

FoxForge may suggest private IPv4 CIDRs visible to the server process, but a suggestion is never permission to scan automatically.

The Bambu setup flow remains:

`load authenticated suggestions -> operator selects/edits CIDR -> operator explicitly starts scan -> candidate -> authenticated test-before-save`

Manual CIDR entry remains available at all times.

## Safety rules

Suggestions are derived only from IPv4 address/netmask pairs visible to the FoxForge server process and are filtered to RFC1918 ranges:

- `10.0.0.0/8`;
- `172.16.0.0/12`;
- `192.168.0.0/16`.

Loopback, link-local, public, malformed and unsupported addresses are ignored.

Every returned suggestion must satisfy the existing Bambu active-discovery bound of `/22` or smaller. If the server is attached to a wider private interface such as `/16`, FoxForge suggests only the `/24` containing the server address instead of proposing a sweep of the entire interface network.

The endpoint returns normalized CIDR strings only. It does not expose interface names, MAC addresses, host interface addresses or credentials.

## Docker and Umbrel

A container may see Docker bridge networks instead of, or in addition to, the physical printer LAN. FoxForge cannot safely infer which private interface is the user's printer LAN from that fact alone.

Therefore:

- all suggestions are labeled as server-visible hints;
- no suggestion is selected as a trusted printer network by backend policy;
- the browser may prefill the first suggestion only as editable operator input;
- scan still requires a separate explicit click;
- manual CIDR remains the fallback when the real printer subnet is not visible from the container.

Physical Candidate validation must still prove that the Umbrel container can reach the real X2D LAN.

## Authentication

`GET /api/v1/printers/discovery/bambu/subnets` requires the existing `printer.config` Operator Access permission. Network enumeration does not occur for an unauthorized request.

Failure to enumerate local interfaces is a safe empty read (`subnets: []`), not permission to fall back to a guessed `192.168.1.0/24`.

## Acceptance criteria

- only bounded RFC1918 IPv4 CIDRs are suggested;
- wider private networks are reduced to a local `/24` scan slice;
- public, loopback and link-local addresses are excluded;
- suggestions are deterministic and deduplicated;
- every suggestion passes the existing Bambu `discovery_network()` validator;
- unauthorized reads do not enumerate interfaces;
- enumeration failure returns an empty suggestion set;
- browser suggestions never auto-start a scan;
- manual CIDR fallback remains available;
- EN/RU/UK copy explains the Docker/Umbrel bridge limitation.
