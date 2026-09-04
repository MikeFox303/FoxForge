# Printer setup UI acceptance criteria

The app-managed printer setup milestone is ready to merge only when all of the following are true:

- **Add printer** opens a real setup dialog in normal runtime mode.
- Bambu setup requires printer ID, display name, serial number, host and LAN access code.
- Moonraker setup requires printer ID, display name and base URL; API key remains optional.
- **Test connection** calls the backend and reports the normalized live connection outcome.
- **Save and connect** persists the printer and makes it appear in the live fleet without a server restart.
- **Reconnect** performs a real backend reconnect attempt.
- **Delete** removes the printer from FoxForge without implying any physical-printer configuration change.
- Printer secrets are never returned by configuration read APIs or rendered back into the browser.
- The browser session token exists only in memory.
- Unimplemented print/file controls are absent rather than simulated or left as disabled placeholders.
- The existing explicit `?demo=1` mode does not expose production setup mutations.
- TypeScript check, Vitest and production Vite build pass.
- The unified FoxForge container smoke test passes.

Physical Bambu X2D/OpenKE reachability remains a separate hardware-validation step and is not claimed by these software gates.
