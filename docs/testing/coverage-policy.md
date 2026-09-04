# Test coverage policy

Status: active stabilization policy for AUD-019.

FoxForge uses measured code coverage as a regression floor, not as a substitute for behavior-focused tests, production-container browser acceptance, security gates, or physical printer validation.

## Backend coverage gate

The Python 3.12 `Printer domain contracts` job runs the complete backend test suite under coverage.py with branch measurement enabled for the `foxforge` package:

```text
coverage run --branch --source=foxforge -m pytest -q
coverage report --show-missing --fail-under=75
```

The baseline measured while introducing this policy on 2026-09-05 was:

- 253 tests passed;
- 7,003 executable statements measured;
- 1,840 branches measured;
- reported aggregate branch-aware coverage: **76%**.

The enforced floor is **75%**. It is deliberately one percentage point below the measured baseline so normal reporting precision does not create a brittle gate, while a material suite/code regression still fails CI.

Python 3.13 continues to execute the full test suite without instrumentation as a separate interpreter-compatibility signal.

## How the floor may change

The floor may only move downward in a dedicated PR that explains why the reduction is temporary, identifies the uncovered behavior, and records a follow-up plan. Ordinary feature/refactor PRs must keep the current floor green.

Raising the floor is encouraged when meaningful tests increase the sustained baseline. Do not add low-value tests solely to increase the percentage.

## Coverage is not the safety model

Global coverage cannot prove printer-side safety. Critical behavior continues to require explicit scenario tests even when the aggregate floor is satisfied, especially:

- queue dispatch and `INDETERMINATE` reconciliation;
- command authentication, authorization, idempotency and audit;
- SQLite migrations, persistence atomicity and restart recovery;
- inventory balance/idempotency boundaries;
- Bambu and Moonraker transport failure classification;
- certificate/endpoint trust boundaries;
- browser write bootstrap, file staging, realtime resync and unavailable states.

Physical Bambu/Moonraker behavior is never inferred from code coverage.

## Frontend policy

Frontend correctness is currently guarded by TypeScript checking, Vitest unit tests, production build and the production-container Playwright acceptance matrix for desktop, tablet and phone layouts. A separate numeric frontend line-coverage threshold is not adopted at this stage because the project prioritizes browser-level state/workflow coverage over an uncalibrated percentage. If quantitative frontend coverage is adopted later, its tooling must be pinned in `package-lock.json`, its baseline measured before selecting a floor, and it must not weaken the existing browser acceptance gate.

## Static typing

FoxForge has not adopted a Python static type-checker as a release gate yet. Ruff and runtime/contract tests remain the current Python checks. If mypy, Pyright or another checker is adopted, it must be introduced as an explicit repository decision with a reproducible configuration and CI gate rather than as an undocumented local convention.
