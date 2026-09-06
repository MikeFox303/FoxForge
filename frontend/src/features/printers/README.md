# Printer feature UI

`PrinterSetupLauncher` and `PrinterSetupDialog` are the browser-facing configuration surface for Bambu LAN and Moonraker/Klipper printers.

They consume FoxForge `/api/v1` contracts through typed frontend clients. Vendor protocol details, MQTT/WebSocket clients, SecretStore and runtime persistence never enter frontend code.

Current printer feature responsibilities include:

- Add/Update/Remove/Reconnect;
- Bambu discovery with manual fallback;
- normalized setup errors;
- reconnect diagnostics;
- capability-driven common Pause/Resume/Cancel in the separate job-control component;
- normalized material-system/printer-detail presentation.

Setup remains separate from queue/artifact dispatch: a printer configuration dialog must not directly implement file transfer or print-start semantics. Those use the queue/print-execution feature boundaries.

Production setup mutations are unavailable in explicit `?demo=1` mode. Operator credentials remain memory-only through the shared security/command client boundary.
