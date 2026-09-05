// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import i18n from './i18n';

export const inventoryOperatorTranslations = {
  en: {
    operatorRequired: 'Unlock Operator access to change inventory.',
    createTitle: 'Add spool', correctTitle: 'Correct remaining mass', moveTitle: 'Assign or move spool', historyTitle: 'Spool history',
    materialFamily: 'Material', manufacturer: 'Manufacturer', productName: 'Product', color: 'Color', initialMass: 'Initial filament mass (g)',
    remainingMass: 'Remaining filament mass (g)', emptySpoolMass: 'Empty spool mass (g)', purchaseDate: 'Purchase date', note: 'Note', printerSlot: 'Printer slot',
    selectSlot: 'Select a physical slot', save: 'Save', create: 'Add spool', cancel: 'Cancel', saving: 'Saving…', close: 'Close',
    unassign: 'Unassign', archive: 'Archive', history: 'History', editEmptyMass: 'Empty spool mass',
    confirmUnassign: 'Unassign this spool from its physical printer slot?', confirmArchive: 'Archive this spool? Archived spools remain in history and cannot be assigned.',
    archiveAssigned: 'Unassign the spool before archiving it.', noSlots: 'No printer material slots are currently reported.', historyEmpty: 'No mass adjustments have been recorded yet.',
    commandFailed: 'Inventory command failed.', invalidPositiveMass: 'Enter a mass greater than zero.', invalidNonnegativeMass: 'Enter a mass of zero or greater.',
    kinds: { consumption: 'Consumption', correction: 'Correction', return: 'Return', waste: 'Waste' },
  },
  ru: {
    operatorRequired: 'Разблокируйте доступ оператора, чтобы изменять инвентарь.',
    createTitle: 'Добавить катушку', correctTitle: 'Скорректировать остаток', moveTitle: 'Назначить или переместить катушку', historyTitle: 'История катушки',
    materialFamily: 'Материал', manufacturer: 'Производитель', productName: 'Продукт', color: 'Цвет', initialMass: 'Начальная масса филамента (г)',
    remainingMass: 'Остаток филамента (г)', emptySpoolMass: 'Масса пустой катушки (г)', purchaseDate: 'Дата покупки', note: 'Примечание', printerSlot: 'Слот принтера',
    selectSlot: 'Выберите физический слот', save: 'Сохранить', create: 'Добавить катушку', cancel: 'Отмена', saving: 'Сохранение…', close: 'Закрыть',
    unassign: 'Снять назначение', archive: 'Архивировать', history: 'История', editEmptyMass: 'Масса пустой катушки',
    confirmUnassign: 'Снять назначение этой катушки с физического слота принтера?', confirmArchive: 'Архивировать катушку? Она останется в истории и больше не сможет назначаться.',
    archiveAssigned: 'Перед архивированием снимите назначение катушки.', noSlots: 'Принтеры сейчас не сообщают доступных материальных слотов.', historyEmpty: 'Изменений массы пока нет.',
    commandFailed: 'Команда инвентаря завершилась ошибкой.', invalidPositiveMass: 'Введите массу больше нуля.', invalidNonnegativeMass: 'Введите массу не меньше нуля.',
    kinds: { consumption: 'Расход', correction: 'Коррекция', return: 'Возврат', waste: 'Отходы' },
  },
  uk: {
    operatorRequired: 'Розблокуйте доступ оператора, щоб змінювати інвентар.',
    createTitle: 'Додати котушку', correctTitle: 'Скоригувати залишок', moveTitle: 'Призначити або перемістити котушку', historyTitle: 'Історія котушки',
    materialFamily: 'Матеріал', manufacturer: 'Виробник', productName: 'Продукт', color: 'Колір', initialMass: 'Початкова маса філаменту (г)',
    remainingMass: 'Залишок філаменту (г)', emptySpoolMass: 'Маса порожньої котушки (г)', purchaseDate: 'Дата придбання', note: 'Примітка', printerSlot: 'Слот принтера',
    selectSlot: 'Оберіть фізичний слот', save: 'Зберегти', create: 'Додати котушку', cancel: 'Скасувати', saving: 'Збереження…', close: 'Закрити',
    unassign: 'Зняти призначення', archive: 'Архівувати', history: 'Історія', editEmptyMass: 'Маса порожньої котушки',
    confirmUnassign: 'Зняти призначення цієї котушки з фізичного слота принтера?', confirmArchive: 'Архівувати котушку? Вона залишиться в історії та більше не зможе призначатися.',
    archiveAssigned: 'Перед архівуванням зніміть призначення котушки.', noSlots: 'Принтери зараз не повідомляють доступних матеріальних слотів.', historyEmpty: 'Змін маси ще не записано.',
    commandFailed: 'Команда інвентарю завершилася помилкою.', invalidPositiveMass: 'Введіть масу більше нуля.', invalidNonnegativeMass: 'Введіть масу не менше нуля.',
    kinds: { consumption: 'Витрата', correction: 'Корекція', return: 'Повернення', waste: 'Відходи' },
  },
} as const;

for (const language of ['en', 'ru', 'uk'] as const) {
  i18n.addResourceBundle(language, 'translation', { inventoryOperator: inventoryOperatorTranslations[language] }, true, true);
}
