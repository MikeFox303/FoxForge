# Bambuddy RU/UK localization patch record

This file preserves the reviewed localization changes that were previously kept in `MikeFox303/bambuddy` commit `2b96bc7ee920402e8290fc7d3fa62fb2ae8c3c08`.

The patch was based on `maziggy/bambuddy@2d16ed9ad01ec705d7e746d2ee48797ac20218c1` and changed only:

- `frontend/src/i18n/locales/ru.ts`
- `frontend/src/i18n/locales/uk.ts`

When contributing upstream, recreate these values against the then-current locale files instead of reviving a permanent fork.

## Russian

- `slice.processSettingsInactive`: `Неактивно`
- `slice.actionAllTitle`: `Нарезать все пластины в один многопластинный результат и сохранить в одном архиве. Выбор филаментов охватывает все слоты, используемые проектом.`

## Ukrainian

Reviewed target wording:

- maintenance system-task wording: use `за замовчуванням` instead of `за умовчанням`.
- default print options: `Параметри друку за замовчуванням`.
- custom mapping: `Розгорнути настроюване зіставлення за замовчуванням`.
- connection actions: `Перевірити підключення` instead of `Тестове підключення` wherever the key is a connection test action.
- catalog weight: `Маса`.
- catalog/material table headers: `Матеріал`.
- default printer: `Принтер за замовчуванням`.
- relative time: `{{count}} хв тому`.
- Docker heading: `Інформація про Docker`.
- image name: `Назва образу`.
- business tagline: `Кількість принтерів: {{count}}. Пріоритетна підтримка, комерційне ліцензування та виставлення рахунків доступні для команд і друкарень.`
- filament vendor: `Виробник`.
- filament temperature: `Температура`.
- filament delete confirmation: `Ви впевнені, що хочете видалити цей філамент?`.
- Spoolman title: `Інтеграція зі Spoolman`.
- Spoolman enabled: `Spoolman увімкнено`.
- Spoolman link action: `Пов’язати зі Spoolman`.
- Spoolman unlink action: `Відв’язати котушку`.
- Spoolman select action: `Вибрати котушку`.
- Spoolman weight: `Маса`.
- Spoolman weight-sync label: `Вимкнути синхронізацію розрахункової маси AMS`.
- Spoolman weight-sync description: `Не оновлювати залишок за оцінкою AMS. Використовуйте цю опцію, якщо надаєте перевагу обліку витрати у Spoolman замість відсоткової оцінки AMS. Для нових котушок оцінка AMS усе одно використовуватиметься як початкова маса.`
- Spoolman partial-usage label: `Обліковувати часткову витрату для невдалих друків`.
- Spoolman partial-usage description: `Якщо друк завершується помилкою або скасовується, обліковувати приблизну кількість філаменту, витраченого до цього моменту, за прогресом шарів.`
- mixed-content title: `Spoolman не завантажується через HTTPS: браузер заблокував змішаний вміст`.
- mixed-content body: `Bambuddy відкрито через HTTPS (через зворотний проксі), але URL Spoolman досі використовує звичайний HTTP. Браузер блокує такий змішаний вміст, тому вбудований інтерфейс Spoolman не відображається. Для вбудованого інтерфейсу Spoolman має бути доступний через HTTPS.`
- mixed-content reverse-proxy fix: `Розмістіть Spoolman за тим самим зворотним проксі, що й Bambuddy (Traefik / Nginx / Caddy), увімкніть HTTPS і вкажіть нову HTTPS-адресу Spoolman у налаштуваннях.`
- mixed-content new-tab workaround: `Як обхідний варіант відкрийте Spoolman через HTTP у новій вкладці. Обмеження змішаного вмісту застосовується лише до вбудованих фреймів, тому окрема вкладка працюватиме.`
- open Spoolman action: `Відкрити Spoolman у новій вкладці`.
- cloud default state: `Хмара не підключена (за замовчуванням)`.
- AMS temperature: `Температура`.
- AMS history: `Історія AMS`.
- backup default output path: `Залиште порожнім для розташування за замовчуванням`.
- spool UUID: `Копіювати UUID котушки`.
- relative time future/past labels: `{{count}} хв тому`, `через {{count}} хв`, `через {{count}} год`, `через {{count}} дн.`.
- SpoolBuddy/material labels: `Матеріал`.
- stock forecast material: `Матеріал`.
- effective lead-time hint: `макс. (загальний {{global}} дн., для SKU {{sku}} дн.)`.

This record intentionally stores the reviewed target wording rather than a long-lived copy of Bambuddy locale source files.
