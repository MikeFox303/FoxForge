# Bambuddy integration work

FoxForge keeps only Bambuddy-related work that is useful for future upstream contributions or local integration experiments. It is **not** a replacement Bambuddy distribution.

Production on Umbrel must continue to consume official stable releases from `maziggy/bambuddy` through `MikeFox303/umbrel-3d-printing-store`.

## X2D native internal-storage transport

`x2d-port6000/` preserves the tested `BambuTunnelLocal :6000` transport work for X2D/N6-style internal eMMC uploads. The transport is intentionally isolated from Bambuddy's scheduler and MQTT print dispatch until hardware validation is completed.

Origin before migration:

- former fork branch: `MikeFox303/bambuddy:contrib/x2d-port6000`
- upstream base at migration: `maziggy/bambuddy@2d16ed9ad01ec705d7e746d2ee48797ac20218c1`
- fork transport CI result: Ruff + unit tests PASS

The protocol implementation was derived from independently reverse-engineered AGPL work in `ClusterM/open-bamboo-networking`; attribution is retained in the source module.

## Russian / Ukrainian Bambuddy localization

The former fork also contained a small reviewed localization patch based directly on the same upstream main:

- Russian: `Не активно` → `Неактивно`; `многостольный` → `многопластинный`.
- Ukrainian: terminology/grammar normalization including `за умовчанням` → `за замовчуванням`, `Тестове підключення` → `Перевірити підключення`, `Продавець` → `Виробник`, Spoolman wording, time labels and several capitalization/grammar fixes.

The original contribution was one commit (`2b96bc7ee920402e8290fc7d3fa62fb2ae8c3c08`) changing only `frontend/src/i18n/locales/ru.ts` and `uk.ts`. It should be recreated against the then-current upstream files when submitted, rather than maintaining a permanent Bambuddy fork.

## Retired fork

The former `MikeFox303/bambuddy` repository was used temporarily for X2D/FilaMan production development. Its production role ended on 2026-09-03 when the Umbrel Store moved to official `maziggy/bambuddy` releases. FoxForge is the new home for any future experimental work.
