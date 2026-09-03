# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

from collections.abc import Callable, Mapping

from foxforge.domain.printers import PrinterAdapter, PrinterIdentity

AdapterSettings = Mapping[str, object]
AdapterFactory = Callable[[PrinterIdentity, AdapterSettings], PrinterAdapter]


class AdapterRegistryError(RuntimeError):
    """Base error raised while resolving an adapter factory."""


class AdapterKindAlreadyRegisteredError(AdapterRegistryError):
    def __init__(self, adapter_kind: str) -> None:
        self.adapter_kind = adapter_kind
        super().__init__(f"adapter kind is already registered: {adapter_kind}")


class UnknownAdapterKindError(AdapterRegistryError):
    def __init__(self, adapter_kind: str) -> None:
        self.adapter_kind = adapter_kind
        super().__init__(f"adapter kind is not registered: {adapter_kind}")


class AdapterFactoryIdentityError(AdapterRegistryError):
    def __init__(self, expected: PrinterIdentity, actual: PrinterIdentity) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"adapter factory returned identity {actual.printer_id!r} "
            f"for requested printer {expected.printer_id!r}"
        )


class AdapterRegistry:
    """Composition-root registry mapping persisted adapter kinds to factories.

    The registry intentionally knows nothing about Bambu, Moonraker, or any
    other vendor. Concrete factories are registered by the composition root.
    """

    def __init__(self) -> None:
        self._factories: dict[str, AdapterFactory] = {}

    @property
    def adapter_kinds(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))

    def register(
        self,
        adapter_kind: str,
        factory: AdapterFactory,
        *,
        replace: bool = False,
    ) -> None:
        kind = adapter_kind.strip()
        if not kind:
            raise ValueError("adapter_kind must not be empty")
        if kind in self._factories and not replace:
            raise AdapterKindAlreadyRegisteredError(kind)
        self._factories[kind] = factory

    def unregister(self, adapter_kind: str) -> None:
        self._factories.pop(adapter_kind, None)

    def create(
        self,
        identity: PrinterIdentity,
        settings: AdapterSettings | None = None,
    ) -> PrinterAdapter:
        factory = self._factories.get(identity.adapter_kind)
        if factory is None:
            raise UnknownAdapterKindError(identity.adapter_kind)

        adapter = factory(identity, settings or {})
        if adapter.identity != identity:
            raise AdapterFactoryIdentityError(identity, adapter.identity)
        return adapter
