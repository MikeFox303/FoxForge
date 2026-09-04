// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import i18n from './i18n';

const bundles = {
  en: {
    alpha: {
      shell: { build: 'Alpha build', liveApi: 'Live API', workspace: 'Workspace', support: 'Support FoxForge', addPrinter: 'Add printer' },
      overview: {
        eyebrow: 'Mixed fleet, one workspace',
        title: 'Your printers, jobs and materials in one place.',
        text: 'Common workflows stay consistent while typed capabilities preserve deep vendor-specific features.',
        printers: 'Printers', connected: '{{count}} connected', printingNow: 'Printing now', acrossFleet: 'Across the fleet',
        waitingBlocked: 'Waiting / blocked', queueNeedTurn: 'Queue entries needing a turn', materialAlerts: 'Material alerts', lowSlots: 'Loaded slots at or below 20%',
        fleet: 'Fleet', fleetSubtitle: 'Current status, active jobs and loaded materials.', queuePulse: 'Queue pulse', queuePulseSubtitle: 'Running, waiting and blocked work.',
        materialSystems: 'Material systems', materialSystemsSubtitle: 'Physical material currently reported by printers.',
      },
      printers: { title: 'Printers', subtitle: 'Status, jobs and loaded materials across every adapter.' },
      queue: {
        eyebrow: 'Safe print scheduling', title: 'Print queue', text: 'Blocked and uncertain starts stay explicit instead of being collapsed into generic errors.', addJob: 'Add job',
        job: 'Job', printer: 'Printer', state: 'State', attempts: 'Attempts', updated: 'Updated', dispatchAttempts: 'dispatch attempts',
        indeterminateTitle: 'Indeterminate remains a safety state', indeterminateText: 'FoxForge never blindly starts a job again when it cannot prove whether the previous dispatch reached the printer.',
      },
      materials: {
        eyebrow: 'Physical material state', title: 'Materials', text: 'What printers currently report as loaded, active or empty. Inventory ownership remains a separate FoxForge context.',
        slotCount: '{{count}} slot', slotCount_other: '{{count}} slots', unavailable: 'Material information is not available.', activeSource: 'Active source', remainingUnknown: 'Remaining unknown', remaining: '{{value}}% remaining', empty: 'Empty',
        multiSlot: 'Multi-slot', external: 'External', toolhead: 'Toolhead', materialUnit: 'Material unit', slot: 'Slot {{number}}',
      },
      farm: {
        eyebrow: 'Farm command center', activeConnected: '{{active}} active · {{connected}}/{{total}} connected', text: 'Dense fleet monitoring without vendor-specific branching.',
        utilization: 'Current utilization', queued: '{{count}} queued', left: 'left', ready: 'Ready for dispatch', openPrinter: 'Open printer →',
      },
      system: {
        eyebrow: 'Application status', title: 'System', text: 'Runtime, deployment and interface preferences. Developer details stay secondary.',
        runtime: 'Runtime', runtimeTitle: 'Alpha runtime', runtimeText: 'The interface reads the live FoxForge API; demo data is available only with ?demo=1.', uiRunning: 'UI + API running',
        architecture: 'Architecture', architectureTitle: 'Vendor-independent core', architectureText: 'Backend, frontend and deployment share stable application contracts while vendor adapters remain isolated.',
        languageText: 'English, Russian and Ukrainian share one component tree.', diagnostics: 'Developer diagnostics', frontend: 'Frontend', routing: 'Routing', serverState: 'Server state', inventorySource: 'Inventory source', backendApi: 'Backend API', realtime: 'Realtime',
        inventoryLive: 'Live InventoryService read model', apiConnected: 'Connected /api/v1', realtimeReserved: 'Polling now; WebSocket / SSE next',
      },
      printer: {
        activeJob: 'Active job', elapsed: 'elapsed', left: 'left', layers: 'layers', idle: 'Idle · ready for the next queue entry', connection: 'Connection', material: 'Material', updated: 'Updated', open: 'Open printer →',
      },
      materialSource: { none: 'No material loaded', loaded: 'Material loaded' },
      status: { stale: 'Stale', disconnected: 'Disconnected', connecting: 'Connecting', connected: 'Connected', degraded: 'Degraded', offline: 'Offline', idle: 'Idle', preparing: 'Preparing', printing: 'Printing', paused: 'Paused', completed: 'Completed', failed: 'Failed', cancelling: 'Cancelling', unknown: 'Unknown' },
      relative: { recently: 'recently', justNow: 'just now', minutes: '{{count}}m ago', hours: '{{count}}h ago', days: '{{count}}d ago' },
    },
  },
  ru: {
    alpha: {
      shell: { build: 'Альфа-сборка', liveApi: 'Живой API', workspace: 'Рабочее пространство', support: 'Поддержать FoxForge', addPrinter: 'Добавить принтер' },
      overview: {
        eyebrow: 'Разные принтеры — одно пространство', title: 'Принтеры, задания и материалы в одном месте.', text: 'Общие сценарии едины, а typed capabilities сохраняют глубокие функции каждого производителя.',
        printers: 'Принтеры', connected: 'Подключено: {{count}}', printingNow: 'Печатают сейчас', acrossFleet: 'По всей ферме', waitingBlocked: 'Ожидают / заблокированы', queueNeedTurn: 'Задания, ожидающие запуска', materialAlerts: 'Материалы', lowSlots: 'Загруженные слоты с остатком 20% или меньше',
        fleet: 'Парк принтеров', fleetSubtitle: 'Текущий статус, активные задания и загруженные материалы.', queuePulse: 'Состояние очереди', queuePulseSubtitle: 'Печать, ожидание и блокировки.', materialSystems: 'Системы материалов', materialSystemsSubtitle: 'Физическое состояние материалов по данным принтеров.',
      },
      printers: { title: 'Принтеры', subtitle: 'Статус, задания и материалы всех подключённых адаптеров.' },
      queue: {
        eyebrow: 'Безопасное планирование печати', title: 'Очередь печати', text: 'Блокировки и неопределённые старты остаются явными и не превращаются в безликую ошибку.', addJob: 'Добавить задание',
        job: 'Задание', printer: 'Принтер', state: 'Состояние', attempts: 'Попытки', updated: 'Обновлено', dispatchAttempts: 'попыток запуска', indeterminateTitle: 'Неопределённость — отдельное безопасное состояние', indeterminateText: 'FoxForge не запускает задание повторно вслепую, если невозможно доказать, дошёл ли предыдущий запуск до принтера.',
      },
      materials: {
        eyebrow: 'Физическое состояние материалов', title: 'Материалы', text: 'Что принтеры сейчас считают загруженным, активным или пустым. Учёт катушек остаётся отдельным контекстом FoxForge Inventory.',
        slotCount: '{{count}} слот', slotCount_few: '{{count}} слота', slotCount_many: '{{count}} слотов', unavailable: 'Информация о материалах недоступна.', activeSource: 'Активный источник', remainingUnknown: 'Остаток неизвестен', remaining: 'Осталось {{value}}%', empty: 'Пусто', multiSlot: 'Многослотовая система', external: 'Внешняя катушка', toolhead: 'Головка', materialUnit: 'Источник материала', slot: 'Слот {{number}}',
      },
      farm: {
        eyebrow: 'Центр управления фермой', activeConnected: 'Активно: {{active}} · подключено {{connected}}/{{total}}', text: 'Плотный мониторинг фермы без ветвления логики по производителям.', utilization: 'Текущая загрузка', queued: 'В очереди: {{count}}', left: 'осталось', ready: 'Готов к запуску', openPrinter: 'Открыть принтер →',
      },
      system: {
        eyebrow: 'Состояние приложения', title: 'Система', text: 'Runtime, развёртывание и настройки интерфейса. Детали разработчика остаются второстепенными.', runtime: 'Runtime', runtimeTitle: 'Альфа-runtime', runtimeText: 'Интерфейс читает живой FoxForge API; демо-данные доступны только с ?demo=1.', uiRunning: 'UI + API работают', architecture: 'Архитектура', architectureTitle: 'Независимое от производителя ядро', architectureText: 'Backend, frontend и deployment используют стабильные application contracts, а vendor adapters изолированы.', languageText: 'Английский, русский и украинский используют одно дерево компонентов.', diagnostics: 'Диагностика разработчика', frontend: 'Frontend', routing: 'Маршрутизация', serverState: 'Состояние сервера', inventorySource: 'Источник Inventory', backendApi: 'Backend API', realtime: 'Realtime', inventoryLive: 'Живая read model InventoryService', apiConnected: 'Подключён /api/v1', realtimeReserved: 'Сейчас polling; далее WebSocket / SSE',
      },
      printer: { activeJob: 'Активное задание', elapsed: 'прошло', left: 'осталось', layers: 'слоёв', idle: 'Ожидание · готов к следующему заданию', connection: 'Подключение', material: 'Материал', updated: 'Обновлено', open: 'Открыть принтер →' },
      materialSource: { none: 'Материал не загружен', loaded: 'Материал загружен' },
      status: { stale: 'Данные устарели', disconnected: 'Отключён', connecting: 'Подключение', connected: 'Подключён', degraded: 'Ограниченная связь', offline: 'Не в сети', idle: 'Ожидание', preparing: 'Подготовка', printing: 'Печать', paused: 'Пауза', completed: 'Завершено', failed: 'Ошибка', cancelling: 'Отмена', unknown: 'Неизвестно' },
      relative: { recently: 'недавно', justNow: 'только что', minutes: '{{count}} мин назад', hours: '{{count}} ч назад', days: '{{count}} дн назад' },
    },
  },
  uk: {
    alpha: {
      shell: { build: 'Альфа-збірка', liveApi: 'Живий API', workspace: 'Робочий простір', support: 'Підтримати FoxForge', addPrinter: 'Додати принтер' },
      overview: {
        eyebrow: 'Різні принтери — один простір', title: 'Принтери, завдання та матеріали в одному місці.', text: 'Спільні сценарії залишаються єдиними, а typed capabilities зберігають глибокі функції кожного виробника.',
        printers: 'Принтери', connected: 'Підключено: {{count}}', printingNow: 'Друкують зараз', acrossFleet: 'По всій фермі', waitingBlocked: 'Очікують / заблоковані', queueNeedTurn: 'Завдання, що очікують запуску', materialAlerts: 'Матеріали', lowSlots: 'Завантажені слоти із залишком 20% або менше', fleet: 'Парк принтерів', fleetSubtitle: 'Поточний стан, активні завдання та завантажені матеріали.', queuePulse: 'Стан черги', queuePulseSubtitle: 'Друк, очікування та блокування.', materialSystems: 'Системи матеріалів', materialSystemsSubtitle: 'Фізичний стан матеріалів за даними принтерів.',
      },
      printers: { title: 'Принтери', subtitle: 'Стан, завдання та матеріали всіх підключених адаптерів.' },
      queue: {
        eyebrow: 'Безпечне планування друку', title: 'Черга друку', text: 'Блокування та невизначені старти залишаються явними й не зводяться до загальної помилки.', addJob: 'Додати завдання', job: 'Завдання', printer: 'Принтер', state: 'Стан', attempts: 'Спроби', updated: 'Оновлено', dispatchAttempts: 'спроб запуску', indeterminateTitle: 'Невизначеність — окремий безпечний стан', indeterminateText: 'FoxForge не запускає завдання повторно навмання, якщо неможливо довести, чи дійшов попередній запуск до принтера.',
      },
      materials: {
        eyebrow: 'Фізичний стан матеріалів', title: 'Матеріали', text: 'Що принтери зараз вважають завантаженим, активним або порожнім. Облік котушок залишається окремим контекстом FoxForge Inventory.', slotCount: '{{count}} слот', slotCount_few: '{{count}} слоти', slotCount_many: '{{count}} слотів', unavailable: 'Інформація про матеріали недоступна.', activeSource: 'Активне джерело', remainingUnknown: 'Залишок невідомий', remaining: 'Залишилось {{value}}%', empty: 'Порожньо', multiSlot: 'Багатослотова система', external: 'Зовнішня котушка', toolhead: 'Головка', materialUnit: 'Джерело матеріалу', slot: 'Слот {{number}}',
      },
      farm: {
        eyebrow: 'Центр керування фермою', activeConnected: 'Активно: {{active}} · підключено {{connected}}/{{total}}', text: 'Щільний моніторинг ферми без розгалуження логіки за виробниками.', utilization: 'Поточне завантаження', queued: 'У черзі: {{count}}', left: 'залишилось', ready: 'Готовий до запуску', openPrinter: 'Відкрити принтер →',
      },
      system: {
        eyebrow: 'Стан застосунку', title: 'Система', text: 'Runtime, розгортання та налаштування інтерфейсу. Деталі розробника залишаються другорядними.', runtime: 'Runtime', runtimeTitle: 'Альфа-runtime', runtimeText: 'Інтерфейс читає живий FoxForge API; демо-дані доступні лише з ?demo=1.', uiRunning: 'UI + API працюють', architecture: 'Архітектура', architectureTitle: 'Незалежне від виробника ядро', architectureText: 'Backend, frontend і deployment використовують стабільні application contracts, а vendor adapters ізольовані.', languageText: 'Англійська, російська та українська використовують одне дерево компонентів.', diagnostics: 'Діагностика розробника', frontend: 'Frontend', routing: 'Маршрутизація', serverState: 'Стан сервера', inventorySource: 'Джерело Inventory', backendApi: 'Backend API', realtime: 'Realtime', inventoryLive: 'Жива read model InventoryService', apiConnected: 'Підключено /api/v1', realtimeReserved: 'Зараз polling; далі WebSocket / SSE',
      },
      printer: { activeJob: 'Активне завдання', elapsed: 'минуло', left: 'залишилось', layers: 'шарів', idle: 'Очікування · готовий до наступного завдання', connection: 'Підключення', material: 'Матеріал', updated: 'Оновлено', open: 'Відкрити принтер →' },
      materialSource: { none: 'Матеріал не завантажено', loaded: 'Матеріал завантажено' },
      status: { stale: 'Дані застаріли', disconnected: 'Відключено', connecting: 'Підключення', connected: 'Підключено', degraded: 'Обмежений зв’язок', offline: 'Не в мережі', idle: 'Очікування', preparing: 'Підготовка', printing: 'Друк', paused: 'Пауза', completed: 'Завершено', failed: 'Помилка', cancelling: 'Скасування', unknown: 'Невідомо' },
      relative: { recently: 'нещодавно', justNow: 'щойно', minutes: '{{count}} хв тому', hours: '{{count}} год тому', days: '{{count}} дн тому' },
    },
  },
} as const;

for (const language of ['en', 'ru', 'uk'] as const) {
  i18n.addResourceBundle(language, 'translation', bundles[language], true, true);
}

export { bundles as alphaTranslations };
