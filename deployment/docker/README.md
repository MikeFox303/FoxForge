# Docker deployment

This directory is reserved for FoxForge's production container build and local/self-hosted compose configuration.

Target constraints:

- Linux amd64 and ARM64;
- one application runtime serving the Python API and compiled frontend assets;
- persistent data mounted outside the image;
- health checks suitable for container orchestration and Umbrel packaging;
- no development-time Node.js process in the production image.

Docker implementation will be added only with runtime smoke tests and multi-architecture CI coverage.
