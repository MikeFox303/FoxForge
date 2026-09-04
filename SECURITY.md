# Security policy

FoxForge controls physical 3D printers and stores printer/network credentials, so security reports are treated as potentially safety-relevant.

## Supported versions

FoxForge is currently pre-release alpha software. Security fixes are made against the current `main` branch and, when appropriate, a new guarded pre-release is published. Historical alpha images are immutable and are not silently replaced under an existing semantic version tag.

## Reporting a vulnerability

Please do **not** open a public GitHub issue for a vulnerability that could enable unauthorized printer control, credential disclosure, remote code execution, authentication bypass, SSRF, destructive data mutation, or another exploitable security defect.

Use GitHub's private vulnerability reporting / Security Advisory flow for `MikeFox303/FoxForge` when it is available for the repository. Include:

- affected commit/version;
- deployment mode (Docker, Umbrel, other);
- concise reproduction steps;
- expected versus observed behavior;
- potential impact;
- any proposed mitigation or patch if available.

If private vulnerability reporting is unavailable, contact the maintainer privately through the contact method published on the maintainer's GitHub profile rather than disclosing exploit details in a public issue.

## Security boundaries

Important current boundaries are documented in the repository ADRs and design documents. In particular:

- protected writes require FoxForge command authentication;
- reverse-proxy authentication is defense in depth and is not automatically an application principal;
- browser command credentials must not be persisted by FoxForge in browser storage;
- printer credentials in the current alpha are sensitive data inside the private `/data` volume and its backups;
- vendor transports remain behind FoxForge application/domain boundaries;
- ambiguous printer side effects are not blindly retried.

## Disclosure and fixes

Please allow reasonable time for triage, patch development and release validation before public disclosure. FoxForge will preserve provenance and security-fix history in the Git repository and release notes without publishing unnecessary credential or exploit material.
