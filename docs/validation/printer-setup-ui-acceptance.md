# Printer setup UI acceptance criteria

- **Status:** current regression/acceptance contract
- **Updated:** 2026-09-06
- **Related:** [application-managed setup](../design/app-managed-printer-setup.md), [Pre-Alpha 5 validation](../testing/pre-alpha-5-bambu-physical-validation.md)

The printer setup UI is acceptable when the browser and backend preserve the following behavior.

## Common setup

- Add Printer opens the real production setup dialog outside explicit `?demo=1` mode.
- Bambu and Moonraker forms use FoxForge `/api/v1` setup DTOs only.
- Test connection performs a real backend preflight and shows normalized actionable errors.
- successful Add appears in the live fleet without process restart;
- Reconnect invokes the real backend reconnect path;
- Remove changes FoxForge configuration only and does not imply a physical-printer reset;
- credentials are never returned by configuration reads or persisted by the browser.

## Bambu Pre-Alpha 5 additions

- manual entry remains available;
- discovery scans only an explicitly selected bounded private subnet and returns candidates only;
- discovered metadata may prefill identity but never bypasses authenticated Test/Add;
- failed Add does not persist a dead printer;
- failed Update preserves/restores the previous working config/secret/adapter;
- terminal sanitized failed Add/Update replay is deterministic under the same command identity;
- reconnect Diagnostics displays only normalized secret-safe context.

## Command/access behavior

- protected setup actions require Operator Access;
- browser operator credential remains memory-only and clears on Lock/401/reload lifecycle;
- production does not rely on anonymous tokenless operator-session bootstrap;
- explicit demo mode cannot perform production setup mutations.

## Separation of concerns

Printer setup owns connection/configuration lifecycle. Queue/artifact print submission, inventory mutations and common job control are separate real feature surfaces; they are not implemented inside the setup dialog and must not be simulated there.

## Automated gates

Applicable changes keep TypeScript/Vitest/build, backend setup/idempotency tests, production-container browser acceptance, container and deployment-auth gates green.

Real X2D/OpenKE reachability and physical print/control remain separate device evidence, not software-UI acceptance.
