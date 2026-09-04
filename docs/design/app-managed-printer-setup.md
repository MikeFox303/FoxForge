# App-managed printer setup

Status: implemented in `main` backend and the printer-setup UI feature branch.

## User workflow

FoxForge printer configuration is managed by the application. `/data/config.json` is private restart persistence, not a user-facing setup interface.

For Bambu Lab LAN:

1. enable LAN mode / local network access on the printer as required by the printer firmware;
2. open **Add printer** in FoxForge;
3. choose **Bambu Lab (LAN mode)**;
4. enter a stable FoxForge printer ID, display name, printer serial number, IP/hostname and LAN access code;
5. use **Test connection** to verify that FoxForge can obtain a live normalized state;
6. use **Save and connect** to persist the configuration and add the adapter to the running fleet without restarting FoxForge.

For Klipper/Moonraker:

1. open **Add printer**;
2. choose **Klipper / Moonraker**;
3. enter the Moonraker base URL, normally `http://<printer-ip>:7125`, and an API key only when the Moonraker installation requires one;
4. test and save in the same way.

Configured printers can be reconnected or removed from the same dialog. Removing a printer changes FoxForge only; it does not modify the physical printer.

## Runtime behavior

The management path is:

```text
React setup UI
    -> authenticated /api/v1/printers commands
    -> PrinterManagementService
    -> app-owned atomic runtime persistence
    -> AdapterRegistry
    -> dynamic FleetService
    -> BambuAdapter or MoonrakerAdapter
    -> normalized live fleet read model
```

A failed initial connection does not discard the saved printer. FoxForge keeps it visible as unavailable/offline and the runtime reconnect supervisor may recover it later.

## Security

Printer credentials are write-only from the browser's perspective. Configuration read models expose only whether a Bambu access code or Moonraker API key is configured; the secret itself is never returned.

State-changing setup commands use ADR 0004 authentication and idempotency. Trusted browser sessions are an opt-in deployment mode intended for a trusted authenticating reverse proxy such as Umbrel App Proxy. The mode is disabled by default for standalone deployments.

## Current scope

Included:

- Bambu LAN connection testing and live state reads;
- Moonraker/Klipper connection testing and live state reads;
- runtime add/remove/reconnect without server restart;
- restart-safe configuration persistence;
- Bambu material-system/AMS information already exposed by the adapter;
- normalized printer/job/fault state already supported by each adapter.

Not included in this milestone:

- file upload or print submission validation on physical hardware;
- pause/stop/start controls from the browser;
- printer discovery by broadcast/mDNS;
- cloud-based Bambu login.

Unavailable print/file actions are intentionally not shown as disabled placeholders in the production UI.
