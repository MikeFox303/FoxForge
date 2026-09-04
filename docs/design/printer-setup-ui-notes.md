# Printer setup UI implementation notes

The printer setup UI intentionally remains separate from printer detail and queue controls.

- Setup owns connection configuration and lifecycle only.
- Fleet read models remain the source of displayed printer state.
- Print submission/file transfer remains out of scope until physical validation.
- Inventory mutations are implemented as a separate bounded-context command surface.

This separation keeps printer connection management useful on UmbrelOS without prematurely coupling it to print dispatch behavior.
