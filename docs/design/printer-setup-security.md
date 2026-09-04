# Printer setup browser security boundary

Printer setup is a state-changing operation and therefore uses ADR 0004 command authentication.

For UmbrelOS, FoxForge may enable trusted browser sessions only when the application is reachable through an authenticating reverse proxy such as Umbrel App Proxy. The generated browser Bearer token is random, short-lived and stored only in JavaScript memory. It is not persisted to localStorage, cookies, config files or public API DTOs.

Standalone deployments keep trusted browser sessions disabled by default. A deployment must explicitly choose an application-authentication path before enabling browser mutations.

Printer credentials are write-only from the browser point of view. Bambu LAN access codes and Moonraker API keys are accepted by setup commands and persisted in the private runtime configuration, but configuration reads expose only `...Configured` booleans.
