# Umbrel deployment

This directory is reserved for FoxForge's Umbrel application packaging.

Umbrel should package the same FoxForge container/runtime used by normal Docker deployments rather than maintain a divergent application fork.

Target constraints:

- ARM64-friendly defaults for Raspberry Pi 5 class hosts;
- persistent application data through Umbrel volumes;
- health checks and App Proxy integration;
- no privileged Docker socket access unless a future documented feature genuinely requires it;
- release/version metadata tied to tested FoxForge images.

The Umbrel package will be implemented after the server API and production container entrypoint are stable enough to smoke-test end to end.
