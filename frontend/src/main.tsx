// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { AppProviders } from './app/providers';
import { OperatorAccess } from './features/security/OperatorAccess';
import { FoxForgeApp } from './FoxForgeApp';
import './jobControlTranslations';
import './inventoryOperatorTranslations';
import './operatorAccessTranslations';
import './styles.css';
import './refinements.css';
import './inventory.css';
import './printer-detail.css';
import './job-control.css';
import './printer-setup.css';
import './operator-access.css';
import './mobile.css';
import './functional-controls.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders>
      <FoxForgeApp />
      <div className="operator-access-shell">
        <OperatorAccess />
      </div>
    </AppProviders>
  </StrictMode>,
);
