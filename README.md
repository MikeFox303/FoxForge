# FoxForge

FoxForge is an open-source project by MikeFox303 for 3D-printing integrations, tooling, experiments, and upstream-oriented development.

## Current development

- Umbrel packaging remains in `MikeFox303/umbrel-3d-printing-store`.
- Bambuddy production uses official `maziggy/bambuddy` stable releases directly.
- Bambuddy/X2D experimental work is preserved under [`integrations/bambuddy/`](integrations/bambuddy/) instead of maintaining a separate production fork.

Current preserved work includes the X2D `BambuTunnelLocal :6000` internal-storage transport, its unit tests/CI, reviewed RU/UK localization notes, and the retired-fork migration record.

## Architecture and design

Durable architecture decisions and interface designs are tracked under [`docs/`](docs/README.md).

Current baseline:

- [ADR 0001: PrinterAdapter architecture](docs/adr/0001-printer-adapter-architecture.md)
- [Printer contracts v1](docs/design/printer-contracts.md) for `PrinterAdapter`, `PrintExecutionCapability`, and `MaterialSystemCapability`

## ❤️ Support FoxForge

FoxForge is free and open-source. If you find the project useful and would like to support its continued development, testing hardware, and infrastructure, you can make a voluntary contribution on Ko-fi.

[☕ Support FoxForge on Ko-fi](https://ko-fi.com/mikefox303)

Support is completely optional and does not affect access to FoxForge or its source code.

## License

FoxForge is licensed under the **GNU Affero General Public License v3.0 only (AGPL-3.0-only)**.

See [`LICENSE`](LICENSE) for the full license text.
