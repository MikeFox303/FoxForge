# X2D regression fixtures

These fixtures are **sanitized, physical-derived regression fixtures**, not raw printer captures and not physical-validation evidence.

They encode only the protocol/state shapes that were required to reproduce real Candidate 5 findings from the Raspberry Pi 5 + Umbrel + X2D validation path:

- PR #152: a valid incremental X2D `print.push_status` may omit `gcode_state` while still carrying current status such as `device`, `wifi_signal` and `vir_slot`;
- PR #153: X2D/H2-family firmware reports the complete dual external-source inventory through `print.vir_slot`, which takes precedence over a legacy/single-active-source `vt_tray` view.

The payload values in this directory are intentionally synthetic and secret-safe. They must not contain real printer serial numbers, LAN addresses, access codes, command tokens, cookies or other operator credentials.

The purpose is to make real-device discoveries durable in automated tests without turning private hardware telemetry into repository data. A passing fixture test does **not** replace the exact immutable Candidate 6 physical gate.

SPDX-License-Identifier: AGPL-3.0-only
Copyright (C) 2026 MikeFox303
