// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { AppProviders } from './app/providers';
import { FoxForgeApp } from './FoxForgeApp';
import './styles.css';
import './refinements.css';
import './inventory.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders>
      <FoxForgeApp />
    </AppProviders>
  </StrictMode>,
);
