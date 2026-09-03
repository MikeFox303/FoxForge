# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from dataclasses import replace

import pytest

from foxforge.infrastructure.printers import (
    AdapterFactoryIdentityError,
    AdapterKindAlreadyRegisteredError,
    AdapterRegistry,
    UnknownAdapterKindError,
)
from foxforge.testing import FakePrinterAdapter


def test_registry_creates_adapter_from_registered_factory(printer_identity) -> None:
    registry = AdapterRegistry()
    seen_settings: dict[str, object] = {}

    def factory(identity, settings):
        seen_settings.update(settings)
        return FakePrinterAdapter(identity)

    registry.register("fake", factory)
    adapter = registry.create(printer_identity, {"endpoint": "memory://printer"})

    assert adapter.identity == printer_identity
    assert seen_settings == {"endpoint": "memory://printer"}
    assert registry.adapter_kinds == ("fake",)


def test_registry_rejects_duplicate_adapter_kind(printer_identity) -> None:
    registry = AdapterRegistry()
    factory = lambda identity, settings: FakePrinterAdapter(identity)
    registry.register("fake", factory)

    with pytest.raises(AdapterKindAlreadyRegisteredError):
        registry.register("fake", factory)

    replacement = lambda identity, settings: FakePrinterAdapter(identity)
    registry.register("fake", replacement, replace=True)
    assert registry.create(printer_identity).identity == printer_identity


def test_registry_rejects_unknown_adapter_kind(printer_identity) -> None:
    registry = AdapterRegistry()

    with pytest.raises(UnknownAdapterKindError) as caught:
        registry.create(printer_identity)

    assert caught.value.adapter_kind == "fake"


def test_registry_rejects_factory_identity_mismatch(printer_identity) -> None:
    registry = AdapterRegistry()

    def bad_factory(identity, settings):
        return FakePrinterAdapter(replace(identity, printer_id="different-printer"))

    registry.register("fake", bad_factory)

    with pytest.raises(AdapterFactoryIdentityError):
        registry.create(printer_identity)
