# Printer setup UI

`PrinterSetupLauncher` and `PrinterSetupDialog` are the browser-facing configuration surface for Bambu LAN and Moonraker/Klipper connections.

They depend only on FoxForge `/api/v1` DTOs through `data/printerSetupClient.ts`. Vendor protocol details, MQTT/WebSocket clients and runtime persistence never enter frontend code.

Production setup mutations are hidden in explicit demo mode. Unsupported print/file operations must not be represented as successful or functional controls.
