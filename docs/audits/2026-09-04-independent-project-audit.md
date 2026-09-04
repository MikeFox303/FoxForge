# Independent FoxForge project audit — 2026-09-04

- **Audit type:** independent repository / architecture / release / UI / deployment review
- **Audited repository:** `MikeFox303/FoxForge`
- **Audited `main`:** `2e17e3963bb209c9cd8fc4598e1ea51d474ba510`
- **Published release at audit time:** `v0.1.0-alpha.3`
- **Status:** active remediation reference

This document is a durable snapshot of findings from an independent review of FoxForge. It is intended to be used as a development-direction and regression-prevention checklist. It is **not** a claim that every item remains open forever: future work should update each finding with evidence and mark it resolved only after the acceptance criteria are satisfied.

## Executive assessment

FoxForge has a strong architectural foundation for an alpha-stage self-hosted printer-management platform. The repository already has clear domain/application/adapter/infrastructure boundaries, typed printer capabilities, deep Bambu isolation, Moonraker support, a durable queue with explicit uncertain-state handling, inventory persistence, command authentication/idempotency/audit, a React frontend, Docker/Umbrel packaging foundations and a substantial automated test suite.

The main risk is not a fundamental architectural mistake. The main risk is that implementation has advanced faster than the integration, release, browser-authentication, persistence-migration and end-to-end validation layers.

The recommended direction is therefore:

```text
P2 current source
    |
    v
Stabilization gate
    |
    +-- release integrity
    +-- browser auth / deployment boundary
    +-- UI regression coverage
    +-- reproducible dependencies
    +-- persistent-data migration foundation
    |
    v
Physical X2D / Moonraker / Pi 5 validation
    |
    v
Inventory operator workflow
    |
    v
Automatic filament accounting
    |
    v
Persistent farm scheduling
    |
    v
Deep Bambu expansion
```

Do not treat a green unit/build CI state as proof that the complete installed product flow works. Several findings below are integration defects that individual component tests do not detect.

## Finding status convention

- `OPEN` — confirmed issue or missing safety layer.
- `NEEDS DESIGN` — implementation should not proceed until an architectural/deployment decision is documented.
- `VALIDATION REQUIRED` — software foundations exist but real-device/deployment evidence is required.
- `RESOLVED` — use only after acceptance criteria and tests are recorded in the repository.

## Priority summary

| ID | Priority | Status | Finding |
| --- | --- | --- | --- |
| AUD-001 | P0 | OPEN | Release workflow can publish a versioned image before proving the Git release/tag identity is valid |
| AUD-002 | P0 | OPEN | `container.yml` provides a second semver image publication path outside the guarded release workflow |
| AUD-003 | P0 | OPEN | Browser write workflows and standard Docker/Umbrel deployment configuration are not aligned |
| AUD-004 | P0 | NEEDS DESIGN | Trusted browser session bootstrap depends on deployment trust that the application itself does not prove |
| AUD-005 | P1 | OPEN | `PrinterSetupLauncher` is rendered twice, including in `v0.1.0-alpha.3` |
| AUD-006 | P1 | OPEN | Frontend/backend dependency graphs are not fully reproducible because lock/constraints files are absent |
| AUD-007 | P1 | OPEN | ADR 0004 no longer completely matches the implemented browser/configuration-write security model |
| AUD-008 | P1 | OPEN | Persistent configuration/database migration policy is missing before further schema growth |
| AUD-009 | P1 | OPEN | Roadmap sequencing puts automatic accounting before sufficient operator UI and physical validation |
| AUD-010 | P2 | OPEN | Inventory read-check-write validation is not atomic enough for future concurrent automatic accounting |
| AUD-011 | P2 | OPEN | Artifact storage has per-file limits but no total quota/retention/garbage-collection policy |
| AUD-012 | P2 | OPEN | Reconnect supervision is sequential and will scale poorly for a larger farm |
| AUD-013 | P2 | OPEN | Bambu LAN TLS verification defaults to disabled without certificate pinning/TOFU |
| AUD-014 | P2 | OPEN | Moonraker user-configured absolute URL is an operator-controlled server-side request surface |
| AUD-015 | P2 | OPEN | Printer credentials are protected by file permissions but remain plaintext in `/data/config.json` |
| AUD-016 | P2 | OPEN | Production Vite build publishes source maps in the runtime image |
| AUD-017 | P2 | OPEN | Container entrypoint recursively changes ownership of all `/data` on every root startup |
| AUD-018 | P2 | OPEN | Frontend CI lacks browser/component end-to-end coverage capable of catching DOM/layout regressions |
| AUD-019 | P3 | OPEN | Public-project security/dependency governance should be expanded before Beta |

---

## AUD-001 — Release preflight occurs too late

**Priority:** P0  
**Status:** OPEN

At the audited commit, `release/manifest.json` still identifies `0.1.0-alpha.3`, while `main` has moved beyond that immutable release. The guarded release workflow allows manual dispatch and performs image publication work before the workflow has fully proven that an already-existing Git release tag is consistent with the current source commit.

That creates a dangerous failure mode: a manual re-run from newer `main` can potentially update the GHCR semantic version tag and only afterwards discover that the Git tag already belongs to the historical release commit.

### Required direction

All release identity validation must happen **before** Docker login/build/push that can affect a versioned tag.

### Acceptance criteria

- Existing `vX.Y.Z` releases cannot cause a new image to be pushed under `X.Y.Z`.
- Manual release execution against an old manifest stops before versioned publication.
- Git release tag, release manifest, package versions, release notes and image version are validated as one release identity.
- A failed release attempt cannot mutate an already-published semantic version tag.
- CI has an explicit duplicate-release/mismatched-tag test or script-level validation.

---

## AUD-002 — Two independent semver publication paths

**Priority:** P0  
**Status:** OPEN

`.github/workflows/container.yml` can publish on both `main` and `refs/tags/v*` and generates semver metadata for tag builds. The dedicated release workflow can also publish release images.

FoxForge should have exactly one authority for immutable versioned images.

### Required direction

- `container.yml`: publish only development identities such as `main` and `sha-<commit>`.
- `release.yml`: be the only workflow allowed to publish `X.Y.Z` version tags.

### Acceptance criteria

- Creating an arbitrary `v*` Git tag cannot bypass release-manifest validation.
- Only one workflow is capable of publishing semantic release tags.
- Versioned release image provenance points to the same commit as the Git release tag.

---

## AUD-003 — Browser writes and deployment configuration are not aligned

**Priority:** P0  
**Status:** OPEN

The frontend command client obtains a short-lived bearer through `/api/v1/operator-session` before protected browser mutations. However the standard standalone Compose and the published Umbrel packaging path, as audited, do not consistently configure the runtime prerequisites needed for that browser-session flow.

The product can therefore render write-capable UI while the installed runtime refuses the session bootstrap.

Affected user-facing flows include printer setup and other protected command workflows.

### Required direction

Define and test complete deployment-specific authentication bootstraps rather than treating frontend, backend and proxy settings as independent features.

### Acceptance criteria

For every officially documented installation mode:

- a documented write-authentication path exists;
- Add Printer either works end to end or is deliberately unavailable with a truthful explanation;
- queue/inventory/printer controls never appear functional while authentication is impossible;
- production package tests exercise the same environment variables/proxy assumptions as the real package.

---

## AUD-004 — Trusted browser session boundary requires an explicit security design

**Priority:** P0  
**Status:** NEEDS DESIGN

`TrustedBrowserCommandSessions(enabled=True)` permits the browser-session bootstrap path. The current security assumption is that this flag is only enabled when FoxForge is protected by a genuinely authenticating reverse proxy such as the Umbrel App Proxy.

The application does not independently prove that a request to `/api/v1/operator-session` came through that trusted authentication boundary. A standalone Docker operator who enables the flag while exposing FoxForge directly on the LAN could unintentionally make operator-session acquisition available to any reachable client.

### Required direction

Create an ADR (or superseding amendment to ADR 0004) for browser authentication and trusted reverse-proxy semantics.

It should define at minimum:

- standalone Docker authentication/bootstrap;
- Umbrel App Proxy trust assumptions;
- whether direct backend reachability is allowed when trusted sessions are enabled;
- session TTL/rotation/revocation;
- proxy assertion/shared-secret/HMAC requirements if used;
- CSRF/XSS assumptions;
- future multi-user identity compatibility.

### Acceptance criteria

- Enabling browser sessions cannot silently convert an unauthenticated directly-exposed runtime into a full operator-token dispenser.
- Umbrel behavior is tested through a representative proxy boundary.
- Browser credentials are not persisted to `localStorage`, URLs, public DTOs or logs.
- The selected model is recorded in an accepted ADR before being treated as a production security contract.

---

## AUD-005 — Duplicate `PrinterSetupLauncher`

**Priority:** P1  
**Status:** OPEN

`FoxForgeApp.tsx` renders `PrinterSetupLauncher` in the topbar, while `frontend/src/main.tsx` also renders another independent `PrinterSetupLauncher` next to `<FoxForgeApp />`.

This creates two separate launcher/dialog state trees. The defect is also present in the `v0.1.0-alpha.3` source.

Narrow-mobile CSS hides the topbar secondary action, which makes the duplicated out-of-layout launcher especially problematic for mobile behavior.

### Required direction

Keep one canonical launcher location and define an intentional mobile entry point.

### Acceptance criteria

- Exactly one Add Printer launcher/dialog tree exists in the rendered application.
- Add Printer remains reachable on supported narrow phone layouts.
- Component/browser test asserts only one actionable launcher exists.
- Desktop/tablet/mobile visual smoke tests are added.

---

## AUD-006 — Dependency builds are not fully reproducible

**Priority:** P1  
**Status:** OPEN

The frontend uses semver ranges without a committed Node lockfile, and the backend uses dependency ranges without a frozen release lock/constraints mechanism. CI and the Dockerfile resolve packages during each build.

A source commit can therefore resolve to a different transitive dependency graph at a later date.

### Required direction

- Commit `package-lock.json` (or an explicitly chosen equivalent) and use `npm ci` in CI/container builds.
- Adopt a Python reproducibility mechanism such as `uv.lock` or pinned constraints for release builds.
- Add dependency/security scanning without weakening existing SBOM/provenance generation.

### Acceptance criteria

- Clean installs use frozen dependency graphs.
- Release build fails if lock metadata is inconsistent.
- Dependency update PRs are explicit and testable.
- Final container image receives vulnerability scanning in CI/release gates.

---

## AUD-007 — ADR 0004 and implementation have diverged

**Priority:** P1  
**Status:** OPEN

ADR 0004 originally defers browser mutations until a browser-safe authentication design exists and treats printer credential/configuration writes as a later phase. Current source already implements browser operator sessions and authenticated printer configuration mutations.

The code may be valid, but the canonical architecture record no longer fully describes the security model actually in use.

### Required direction

Create a new ADR or formally amend/supersede the relevant ADR 0004 sections.

### Acceptance criteria

- Repository architecture documentation and actual command/browser/config security model agree.
- Future contributors can determine the current security boundary without relying on commit history or chat history.
- The ADR explicitly links deployment assumptions and required tests.

---

## AUD-008 — Persistent migration foundation is missing

**Priority:** P1  
**Status:** OPEN

`config.json` has a schema version but the loader accepts only the current exact version. SQLite is already a durable user-data store and will continue to grow as inventory/accounting/farm functionality expands.

A migration framework should be established before many real installations accumulate state that future releases must transform.

### Required direction

Introduce explicit migration/version ownership for both runtime configuration and SQLite persistence.

### Acceptance criteria

- Historical fixture -> current migration tests exist.
- Current state survives restart after migration.
- Interrupted/corrupt migration behavior is deterministic and documented.
- Backup/restore procedure is documented.
- No destructive migration happens silently.
- Schema/migration version is available in diagnostics.

---

## AUD-009 — Roadmap sequencing should add a stabilization gate

**Priority:** P1  
**Status:** OPEN

Current roadmap direction places automatic filament accounting ahead of complete physical printer validation and ahead of a mature browser inventory mutation workflow.

Automatic accounting is difficult to validate or correct if users cannot reliably create, assign, move and correct spool records from the normal UI.

### Recommended sequencing

1. Stabilization gate (AUD-001..AUD-008 as applicable).
2. Physical X2D / Moonraker / Raspberry Pi + Umbrel validation.
3. Minimum inventory operator workflow (create/correct/move/assign/history).
4. Automatic accounting with reservations/reconciliation.
5. Persistent scheduler/farm policies.
6. Deep Bambu capability expansion in parallel where boundaries remain clean.

---

## AUD-010 — Inventory mutation requires an atomic concurrency contract before automatic accounting

**Priority:** P2  
**Status:** OPEN

The service-layer accounting path can read a balance, calculate/validate a next balance and then append an adjustment. This is acceptable for low-contention alpha usage but can race once background completion events, corrections and automatic consumers operate concurrently.

### Required direction

Introduce an atomic ledger mutation/CAS or revision contract at the persistence boundary.

### Acceptance criteria

Tests cover:

- two simultaneous deductions;
- manual correction racing automatic consumption;
- duplicate completion event;
- replay after restart;
- insufficient balance conflict;
- late/out-of-order completion where relevant.

---

## AUD-011 — Artifact store needs lifecycle policy

**Priority:** P2  
**Status:** OPEN

Artifact staging validates SHA-256, uses content-addressed storage and enforces a per-artifact size limit. There is no equivalent total-storage quota/retention/garbage-collection policy.

### Required direction

Add explicit artifact lifecycle management before large farm usage.

Potential requirements:

- reference tracking/orphan detection;
- configurable total quota;
- retention policy;
- manual cleanup;
- disk free-space health signal;
- stale temporary upload cleanup.

---

## AUD-012 — Sequential reconnect supervision will not scale to a farm

**Priority:** P2  
**Status:** OPEN

The runtime reconnect supervisor iterates offline printers and awaits each connection attempt sequentially. With many unreachable printers and non-trivial timeouts, later printers can experience large reconnect delays.

### Required direction

Before persistent farm scheduling, use bounded concurrent reconnect with per-printer backoff/jitter.

### Acceptance criteria

- concurrency is bounded;
- one offline printer does not block unrelated reconnect attempts;
- network recovery does not trigger an unbounded connection storm;
- retry state remains observable and deterministic in tests.

---

## AUD-013 — Bambu TLS trust model should evolve beyond verification disabled

**Priority:** P2  
**Status:** OPEN

Bambu LAN settings default to `tls_verify=False`. This is understandable for printer-local certificates, but long-term LAN security would benefit from certificate fingerprint pinning or a TOFU-style device trust record instead of permanent verification bypass.

### Recommended direction

Explore a device-certificate trust capability that preserves normal Bambu LAN usability while detecting unexpected certificate changes.

Physical-device validation is mandatory before changing current transport defaults.

---

## AUD-014 — Moonraker endpoint is an operator-controlled server-side request surface

**Priority:** P2  
**Status:** OPEN

Moonraker configuration accepts an absolute HTTP(S) URL and FoxForge connects to it from the server. Private/LAN addresses are legitimate and must remain usable, but the capability should still have an explicit endpoint-security policy before multi-user or remote-admin deployments.

### Required direction

Define allowed redirect/address-resolution behavior, handling of loopback/link-local/metadata-style destinations and an advanced override model where necessary.

Do not blindly block RFC1918/private ranges because those are the normal printer deployment targets.

---

## AUD-015 — Printer credentials are plaintext inside `/data`

**Priority:** P2  
**Status:** OPEN

Runtime config persistence uses atomic writes and restrictive Unix permissions, which is good. Bambu access codes and Moonraker API keys are nevertheless stored as plaintext values in the private application data directory.

### Required direction

Short term:

- explicitly document that backups of `/data` contain printer credentials;
- keep credentials out of read DTOs, logs and diagnostics.

Long term:

- introduce a `SecretStore` infrastructure boundary so external/container secret providers can be adopted without changing printer domain/application contracts.

---

## AUD-016 — Production source maps are shipped

**Priority:** P2  
**Status:** OPEN

`frontend/vite.config.ts` enables source maps and the production Dockerfile copies the complete `dist` tree into the served runtime assets.

### Required direction

Prefer production source maps disabled, hidden, or stored only as separate CI/debug artifacts unless a concrete production error-reporting use case requires public maps.

---

## AUD-017 — Recursive `/data` ownership repair on every startup

**Priority:** P2  
**Status:** OPEN

The container entrypoint performs recursive ownership correction for `/data` when started as root. As artifact/history volume grows, every restart can become increasingly expensive.

### Required direction

Use targeted ownership initialization or a versioned storage ownership migration rather than an unconditional full-tree recursive walk.

---

## AUD-018 — Frontend test pyramid lacks browser-level regression coverage

**Priority:** P2  
**Status:** OPEN

Current frontend CI validates TypeScript, Vitest/unit logic and production build, but browser composition/layout/state flows are not covered strongly enough. The duplicate launcher reached the published alpha while all current build gates remained green.

### Required direction

Add a browser acceptance layer, preferably against the unified production container.

Suggested minimum:

- desktop viewport;
- tablet / ~900px;
- narrow phone / <=620px;
- routing;
- one Add Printer entry point;
- setup dialog keyboard behavior;
- authenticated write bootstrap;
- file selection/staging workflow;
- realtime reconnect/resync;
- truthful unavailable/disabled states.

---

## AUD-019 — Public-project security/dependency governance should mature before Beta

**Priority:** P3  
**Status:** OPEN

The repository already has strong architecture documentation, automated tests, SBOM/provenance for published images and AGPL/provenance discipline. Before Beta, add the remaining public-project maintenance surface.

Recommended additions:

- `SECURITY.md` with vulnerability-reporting policy;
- Dependabot/Renovate or equivalent controlled dependency updates;
- Python dependency audit;
- Node dependency audit;
- final-image vulnerability scanning;
- measured test coverage reporting/threshold policy;
- Python static type-checking gate if adopted by the project.

---

## Strengths to preserve

The audit does **not** recommend rewriting the core architecture. The following should remain project invariants:

### Vendor-independent common core with deep vendor capabilities

Keep `PrinterAdapter` and common typed capabilities small. Deep Bambu behavior should remain explicit Bambu-specific capability families rather than forcing non-Bambu printers into fake equivalents.

### Durable queue safety

Preserve `dispatch_id`, durable transitions, `INDETERMINATE`, receipt identity and explicit reconciliation semantics. A future scheduler must sit above these rules rather than replace them.

### Application-level realtime invalidation

Keep SSE/application events as an invalidation/replay layer while canonical HTTP snapshots remain the source of truth. Restart/epoch changes should continue to force safe resynchronization.

### Upstream provenance discipline

Continue distinguishing `inspired`, `derived` and `copied` upstream work and preserve exact repository/commit/path/license provenance when material implementation is reused.

### Validation honesty

Automated tests, mocks and QEMU are not substitutes for real X2D, Moonraker/OpenKE and Raspberry Pi/Umbrel validation. Continue recording physical validation separately under `docs/validation/`.

---

## Stabilization execution plan

### S0.1 — Release integrity

Resolve AUD-001 and AUD-002 before the next versioned release.

### S0.2 — Browser/deployment security

Resolve the design behind AUD-003, AUD-004 and AUD-007 before browser writes are treated as a reliable production deployment contract.

### S0.3 — UI regression cleanup

Resolve AUD-005 and add the first browser-level regression coverage from AUD-018.

### S0.4 — Reproducible builds

Resolve AUD-006 and begin AUD-019 dependency/security automation.

### S0.5 — Persistent data foundation

Resolve AUD-008 before major P3/P5 schema expansion.

### S1 — Representative physical/deployment validation

Record real-device evidence for:

- Bambu X2D connection/reconnect, state, `.3mf` delivery/start, pause/resume/cancel, lifecycle and ambiguous outcomes;
- Moonraker/OpenKE HTTP/WebSocket, upload/start, pause/resume/cancel, reconnect and lifecycle;
- Raspberry Pi 5/Umbrel install, restart persistence, printer reachability, proxy/browser command bootstrap and SSE reconnect/resync.

### S2 — Inventory operator workflow

Make normal UI workflows available for spool create/edit/correct/move/assign/unassign/archive/history so users can recover from or reconcile automatic accounting.

### P3 — Automatic filament accounting

Proceed only with atomic/revisioned inventory mutation, durable job identity, idempotent completion, reservation/reconciliation semantics and replay/restart tests.

### P5 — Persistent farm scheduler

Do not allow scheduler code to bypass queue safety. Add durable leases/CAS, bounded reconnect behavior, inventory reservations and deterministic eligibility tests.

### P6 — Deep Bambu

Expand AMS/drying/HMS/K-profile/calibration/dual-nozzle/X2D functionality behind Bambu-specific typed capability boundaries and require physical validation for support claims.

---

## Revalidation checklist

When performing a future independent audit, start by checking the status of every `AUD-*` item in this file, then compare the current `main` against the audited commit above.

A finding should only be changed to `RESOLVED` when the repository contains all of the following where applicable:

1. implementation fix;
2. automated regression test;
3. deployment/integration test if the bug crosses process/proxy boundaries;
4. architecture/documentation update if a contract changed;
5. physical validation evidence if printer-specific behavior is claimed.

If a fix changes the architectural direction rather than only implementation, document that decision in an ADR and link it from this audit.

This audit is a reference snapshot, not a replacement for `docs/project-status.md`. `project-status.md` should describe the current state; this document should preserve the independent findings and their remediation history.
