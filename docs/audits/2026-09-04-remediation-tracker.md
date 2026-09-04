# FoxForge independent audit remediation tracker — 2026-09-04

**Source audit:** `docs/audits/2026-09-04-independent-project-audit.md`  
**Active remediation:** successive stabilization PRs from current `main`  
**Feature freeze:** P3 automatic filament accounting is preserved in draft PR #58 and must not merge until the stabilization/resume gate is satisfied.

This file tracks active remediation. The independent audit remains the immutable finding snapshot; this tracker records implementation progress and evidence.

## Status definitions

- `OPEN` — not yet addressed.
- `IN PROGRESS` — implementation/design work exists but acceptance evidence is incomplete.
- `VALIDATION REQUIRED` — code foundation is complete but deployment/physical evidence is still required.
- `RESOLVED` — every applicable audit acceptance criterion has repository evidence and regression coverage.

## Current tracker

| ID | Priority | Status | Active remediation |
| --- | --- | --- | --- |
| AUD-001 | P0 | RESOLVED | PR #60 merged as `3a242a6250af923080ccc4399e2a2b1317b72a56`. Release identity preflight blocks existing/mismatched Git tags, GitHub releases and semantic GHCR tags before publication; regression tests and exact-head backend/container CI passed. |
| AUD-002 | P0 | RESOLVED | PR #60 removed `v*`/semver publication from `container.yml`; only `main` + `sha-*` development identities remain. Policy regression test and exact-head CI passed. |
| AUD-003 | P0 | VALIDATION REQUIRED | PR #61 aligned standalone Compose with explicit `FOXFORGE_COMMAND_TOKEN`, memory-only browser operator access and truthful read-only behavior when no token is configured. PR #88 adds a production-container deployment-auth contract proving read-only 503 fail-closed behavior, explicit-token write success, wrong-token 401 rejection, tokenless `/operator-session` rejection and startup failure for unsafe trusted-browser mode. The historical Umbrel `alpha.3` Store Compose is now documented truthfully as lacking an ADR-0005-compatible bootstrap. A representative future Umbrel/package path still requires exact packaged write/read-only validation before this finding can be resolved. |
| AUD-004 | P0 | VALIDATION REQUIRED | PR #61/ADR 0005 defines the browser/deployment trust model and production rejects tokenless trusted-browser mode. PR #88 adds production-container evidence that tokenless sessions remain disabled and the unsafe trusted-browser flag fails startup. A representative authenticated future Umbrel/reverse-proxy boundary still needs validation before production trust claims. |
| AUD-005 | P1 | RESOLVED | PR #61 removed the duplicate root `PrinterSetupLauncher` and added a one-launcher regression. PR #62 added production-container browser acceptance across supported desktop/tablet/mobile layouts, preserving a reachable canonical Add Printer entry point. |
| AUD-006 | P1 | RESOLVED | PR #62 merged as `cfa1e7c74367940eb55d41b770b3e4498c31d51a`: committed frontend lock and backend constraints, frozen installs, lock verification, dependency audits and exact-head security/container/browser gates. |
| AUD-007 | P1 | RESOLVED | PR #61 merged as `da71d4d3a08557c6b5b6988fd6ee2eea8b20056e`; ADR 0005 supersedes the stale browser-auth deferral in ADR 0004 and records the implemented standalone/Umbrel trust boundary and required validation. |
| AUD-008 | P1 | RESOLVED | PR #74 merged as `52026bc62c58a1830142cb65f69b85d4afb1623a`: config v1→v2 migration with backup, centralized SQLite `user_version` ownership, SQLite Backup API, transactional schema validation, historical fixtures, restart/rollback/corruption tests and persistence diagnostics. |
| AUD-009 | P1 | RESOLVED | PR #87 aligns README and `docs/project-status.md` with the audit stabilization order and the existing P3 freeze record. Active documentation now requires representative physical/deployment validation and a complete normal inventory operator workflow before draft PR #58 may resume; historical release notes remain unchanged. |
| AUD-010 | P2 | RESOLVED | PR #75 merged as `c53c8c776b333a744008d75a7e8ad885d3a26355`. Inventory adjustment idempotency, archive/balance validation and INSERT now share one atomic persistence boundary; concurrency/restart/duplicate/insufficient-balance tests pass. |
| AUD-011 | P2 | RESOLVED | PR #76 merged as `df0818be2c3a98635b22c9d59d49894ed1c8fb57`. Artifact storage now has committed quota, minimum free-space reserve, normalized capacity failure, safe orphan retention/GC, stale-temp cleanup and non-secret storage diagnostics. Queue-referenced artifacts are never GC candidates. |
| AUD-012 | P2 | RESOLVED | PR #77 merged as `273bcf2c7a43b40255063c53a1ac36ddca91d2fa`. Reconnect supervision uses per-printer workers, global bounded concurrency, independent exponential backoff/jitter and dynamic worker discovery; fairness/recovery/concurrency tests and exact-head packaged/browser/security gates passed. |
| AUD-013 | P2 | VALIDATION REQUIRED | PR #82 merged as `9bc33338782ab841ded4798bfe7282772ea07f8d`. Bambu LAN now supports independent optional SHA-256 certificate pins for MQTT and FTPS, checks them before MQTT subscription/FTPS login, fails closed on mismatch without fingerprint disclosure, and does not assume both services share a certificate. The compatibility default remains unchanged until physical X2D certificate behavior is validated. |
| AUD-014 | P2 | RESOLVED | PR #79 merged as `217a876a3b153e11ce6979aab361f8b861bdc5de`. Production Moonraker composition validates every resolved address against explicit RFC1918/ULA defaults, rejects mixed unsafe DNS answers, redirects and URL userinfo, and requires independent overrides for public/loopback/link-local targets. Exact-head backend/container/browser/security gates passed. |
| AUD-015 | P2 | RESOLVED | PR #80 merged as `be04cf3e69abfe1beb99acc41ddcf761e91e439d`. `SecretStore` now separates Bambu access codes and Moonraker API keys from normal runtime config, migrates legacy inline credentials with a sensitive recovery backup, hydrates only at runtime adapter boundaries, and documents all `/data` backups as credential-bearing. Exact-head backend/container/browser/security gates passed. |
| AUD-016 | P2 | RESOLVED | PR #62 disables public production Vite source maps. Production-container browser acceptance also asserts that public source-map assets are absent. |
| AUD-017 | P2 | RESOLVED | PR #62 replaced unconditional recursive `/data` ownership changes with targeted/versioned ownership initialization, avoiding repeated whole-volume `chown -R`. |
| AUD-018 | P2 | RESOLVED | PR #83 merged as `d105cb0fc9dcc8fa667fbe6010ab3e712d49d8cd`. Production-container Playwright now covers desktop/tablet/phone layouts, routing, the single Add Printer entry, Escape-close keyboard behavior, explicit memory-only write bootstrap, truthful unavailable queue state, browser file hashing/staging/enqueue, and deterministic realtime `resync_required` HTTP refetch. The expanded gate found and fixed a real Add Printer Escape defect; final 15/15 browser tests passed without retries. |
| AUD-019 | P3 | RESOLVED | PR #84 merged as `0b4ab02e00657f30710952bfcd2b897932f2edd5`. Together with existing `SECURITY.md`, Dependabot, frozen npm/pip audits and final-image vulnerability scanning, FoxForge now measures backend branch coverage with pinned coverage.py. The measured baseline is 76% across 253 tests, 7,003 statements and 1,840 branches; CI enforces a 75% non-regression floor and documents governance in `docs/testing/coverage-policy.md`. Python static type checking is not currently adopted, so the audit's conditional type-checker recommendation does not apply yet. |

## P3 freeze record

The detailed frozen P3 implementation state is recorded in `docs/status/p3-frozen-state-2026-09-04.md`.

P3 is not discarded. The draft already contains reservation/reconciliation semantics, exact Decimal accounting, full material-plan enforcement, restart/idempotency protections and UI work. It remains intentionally unmerged until the audit blockers and P3 resume criteria are satisfied.

## Execution order

1. **Release integrity:** AUD-001, AUD-002 — resolved in PR #60.
2. **Browser/deployment security foundation:** AUD-003, AUD-004, AUD-007 — software design and production-container contracts are complete through PR #61/#88; representative future Umbrel/package validation remains for AUD-003/004.
3. **UI/build/browser reproducibility:** AUD-005, AUD-006, AUD-016, AUD-017, AUD-018 — resolved through PR #61/#62/#83.
4. **Persistent data foundation:** AUD-008 — resolved in PR #74.
5. **Roadmap stabilization:** AUD-009 — active README/project-status sequencing aligned in PR #87; P3 remains frozen behind its resume gate.
6. **Atomic inventory concurrency:** AUD-010 — resolved in PR #75.
7. **Artifact lifecycle:** AUD-011 — resolved in PR #76.
8. **Reconnect scalability:** AUD-012 — resolved in PR #77.
9. **Moonraker endpoint security:** AUD-014 — resolved in PR #79.
10. **Credential storage boundary:** AUD-015 — resolved in PR #80.
11. **Bambu certificate-trust foundation:** AUD-013 software work is complete in PR #82; physical X2D validation remains before any trust-default change.
12. **Public-project governance:** AUD-019 — resolved through PR #62/#84 with security policy, dependency/update scanning and measured coverage governance.
13. **Representative physical/deployment validation:** X2D, Moonraker/OpenKE, Raspberry Pi 5/Umbrel, including the remaining AUD-003/004 and certificate-trust evidence for AUD-013.
14. **Inventory operator workflow:** complete normal create/correct/move/assign/unassign/archive/history UX before automatic accounting is resumed.
15. **Resume P3:** synchronize PR #58 with current `main`, rerun all exact-head gates, finish docs, then merge only if all resume criteria pass.

## Resolution rule

Do not mark any finding `RESOLVED` solely because code was written. A resolution requires, where applicable:

- implementation fix;
- automated regression test;
- deployment/integration test for cross-process/proxy behavior;
- ADR/documentation update when a contract changes;
- physical validation evidence for printer-specific claims;
- exact final-head CI evidence before merge.
