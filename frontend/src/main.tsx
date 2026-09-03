// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
import { AppProviders } from './app/providers';
import './styles.css';
import './refinements.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders>
      <App />
    </AppProviders>
  </StrictMode>,
);
