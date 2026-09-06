# Test coverage policy

- **Status:** active CI policy; originally introduced during AUD-019 remediation
- **Updated:** 2026-09-06

Coverage is a regression floor, not a substitute for behavior-focused tests, production-container browser acceptance, security gates or physical printer validation.

## Backend gate

The Python 3.12 printer/domain job measures branch coverage for the `foxforge` package:

```text
coverage run --branch --source=foxforge -m pytest -q
coverage report --show-missing --fail-under=75
```

The policy was calibrated on 2026-09-05 from a ~76% branch-aware aggregate baseline; CI enforces **75%**. The historical test/statement/branch counts from that calibration are not treated as current project-size metrics.

Python 3.13 runs the full backend suite separately as interpreter-compatibility evidence.

## Changing the floor

Lowering the floor requires a dedicated justified change with a follow-up plan. Raising it is encouraged when meaningful tests sustainably improve the baseline. Do not add low-value tests merely to inflate the percentage.

## Critical behavior still needs explicit tests

Regardless of aggregate coverage, scenario tests remain mandatory for:

- queue dispatch, receipts and `INDETERMINATE` reconciliation;
- command authentication/authorization/idempotency/audit;
- printer Add/Update test-before-save and rollback;
- reconnect supervision/diagnostic sanitization;
- persistence migrations and inventory atomicity;
- Bambu/Moonraker transport failure classification;
- certificate/endpoint trust;
- browser Operator Access, setup, file staging, realtime resync and unavailable states.

Physical Bambu/Moonraker behavior is never inferred from code coverage.

## Frontend

Frontend correctness is currently guarded by TypeScript checking, Vitest, production build and production-container Playwright acceptance across representative viewports/workflows. A numeric frontend coverage floor is not adopted yet; if added, it must be reproducibly pinned/calibrated and must not replace browser acceptance.

## Static typing

Python does not currently use a separate static type-checker as a release gate. Ruff plus runtime/contract tests are the current checks. Introducing mypy/Pyright or equivalent requires explicit reproducible repository configuration and CI ownership.
