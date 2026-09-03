# Bambuddy integration work

FoxForge keeps only Bambuddy-related records that are useful for future upstream contributions or migration/provenance history. It is **not** a replacement Bambuddy distribution.

Production on Umbrel must continue to consume official stable releases from `maziggy/bambuddy` through `MikeFox303/umbrel-3d-printing-store`.

## X2D storage experiment retired

The former `integrations/bambuddy/x2d_port6000/` implementation and its dedicated CI workflow were removed on 2026-09-04.

FoxForge no longer keeps or plans to promote that experimental implementation. If X2D/N6 internal-eMMC storage requires a transport different from standard implicit FTPS, it will be implemented as new production FoxForge code behind the Bambu-specific `BambuProjectStorage` boundary, based on fresh physical validation and with any required upstream/reverse-engineering provenance documented at that time.

The historical experiment originated from the former `MikeFox303/bambuddy:contrib/x2d-port6000` branch and was informed by AGPL-compatible reverse-engineering work in `ClusterM/open-bamboo-networking`. Git history remains the canonical historical record; the experimental source itself is intentionally no longer present in the current tree.

## Russian / Ukrainian Bambuddy localization

The former fork also contained a small reviewed localization patch based directly on the same upstream main:

- Russian: `Не активно` → `Неактивно`; `многостольный` → `многопластинный`.
- Ukrainian: terminology/grammar normalization including `за умовчанням` → `за замовчуванням`, `Тестове підключення` → `Перевірити підключення`, `Продавець` → `Виробник`, Spoolman wording, time labels and several capitalization/grammar fixes.

The original contribution was one commit (`2b96bc7ee920402e8290fc7d3fa62fb2ae8c3c08`) changing only `frontend/src/i18n/locales/ru.ts` and `uk.ts`. It should be recreated against the then-current upstream files when submitted, rather than maintaining a permanent Bambuddy fork.

## Retired fork

The former `MikeFox303/bambuddy` repository was used temporarily for X2D/FilaMan production development. Its production role ended on 2026-09-03 when the Umbrel Store moved to official `maziggy/bambuddy` releases. FoxForge is the home for durable architecture, newly written printer-management code, and selected migration/upstream records.
